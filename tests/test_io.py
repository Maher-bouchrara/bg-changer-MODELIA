"""Tests for bgchange.io.load_image.

Every hard case is generated in code (no test images to download or commit):
each test builds a small file that triggers exactly one problem, loads it, and
checks the problem was handled.

Run:  uv run pytest tests/test_io.py -v
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageCms

from bgchange.io import ImageLoadError, load_image


def _encode(image: Image.Image, fmt: str, **save_options) -> bytes:
    """Save a Pillow image to in-memory file bytes (as if read from disk)."""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save_options)
    return buffer.getvalue()


# --- Step 1: opening and validating ------------------------------------------


def test_plain_rgb_jpeg_loads_unchanged():
    """The normal case: an RGB JPEG needs no fixes, so no notes are added."""
    data = _encode(Image.new("RGB", (30, 20), (10, 120, 200)), "JPEG")
    loaded = load_image(data)

    assert loaded.rgb.mode == "RGB"
    assert loaded.size == (30, 20)
    assert loaded.alpha_hint is None
    assert loaded.notes == []


def test_path_and_bytes_give_the_same_result(tmp_path):
    """The CLI passes a path and the API passes bytes; both must behave the same."""
    data = _encode(Image.new("RGB", (8, 8), (200, 50, 50)), "PNG")
    path = tmp_path / "photo.png"
    path.write_bytes(data)

    from_path = np.asarray(load_image(path).rgb)
    from_bytes = np.asarray(load_image(data).rgb)
    assert np.array_equal(from_path, from_bytes)


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(ImageLoadError, match="File not found"):
        load_image(tmp_path / "does_not_exist.jpg")


def test_non_image_file_gives_clear_error():
    """e.g. a text file renamed to .jpg."""
    with pytest.raises(ImageLoadError, match="not a readable image"):
        load_image(b"this is just text, not an image")


def test_truncated_file_gives_clear_error():
    """A download cut off halfway: the header is fine but the pixels are missing."""
    noise = np.random.default_rng(0).integers(0, 255, (200, 200, 3), dtype=np.uint8)
    data = _encode(Image.fromarray(noise), "JPEG")
    with pytest.raises(ImageLoadError, match="damaged or incomplete"):
        load_image(data[: len(data) // 2])


def test_too_large_image_is_refused_before_decoding():
    """The size check must happen before the pixels are decoded (bomb protection)."""
    data = _encode(Image.new("RGB", (20, 20)), "PNG")  # 400 pixels
    with pytest.raises(ImageLoadError, match="too large"):
        load_image(data, max_pixels=100)


def test_animated_gif_uses_first_frame():
    frames = [Image.new("RGB", (10, 10), (255, 0, 0)), Image.new("RGB", (10, 10), (0, 0, 255))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:])
    loaded = load_image(buffer.getvalue())

    red, green, blue = loaded.rgb.getpixel((5, 5))
    assert red > 200 and blue < 50  # the first (red) frame, not the blue one
    assert any("frames" in note for note in loaded.notes)


# --- Step 2: EXIF rotation ---------------------------------------------------


def test_exif_rotation_is_applied():
    """A phone photo stored sideways (EXIF orientation 6 = rotate 90 deg clockwise).

    The stored pixels are 40 wide x 20 tall; the photo as people see it is
    20 wide x 40 tall. The loader must return the version people see.
    """
    stored = Image.new("RGB", (40, 20), (0, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    loaded = load_image(_encode(stored, "JPEG", exif=exif))

    assert loaded.size == (20, 40)
    assert any("EXIF orientation 6" in note for note in loaded.notes)


# --- Step 3: existing transparency -------------------------------------------


def test_rgba_png_keeps_alpha_as_hint():
    """A PNG that is already half cut out: the transparency becomes the hint."""
    pixels = np.zeros((10, 10, 4), dtype=np.uint8)
    pixels[..., 0] = 255  # red everywhere
    pixels[:, :5, 3] = 255  # left half opaque
    pixels[:, 5:, 3] = 0  # right half transparent
    loaded = load_image(_encode(Image.fromarray(pixels, mode="RGBA"), "PNG"))

    assert loaded.rgb.mode == "RGB"
    assert loaded.alpha_hint is not None
    assert loaded.alpha_hint.shape == (10, 10)  # (height, width)
    assert loaded.alpha_hint[0, 0] == pytest.approx(1.0)
    assert loaded.alpha_hint[0, 9] == pytest.approx(0.0)


def test_fully_opaque_alpha_is_dropped():
    """An alpha channel that is 100% opaque carries no information."""
    data = _encode(Image.new("RGBA", (10, 10), (0, 255, 0, 255)), "PNG")
    assert load_image(data).alpha_hint is None


def test_palette_png_with_transparent_colour():
    """Palette ("P") images mark transparency differently; it must still be found."""
    image = Image.new("P", (10, 10), 0)
    image.putpalette([255, 255, 255] + [255, 0, 0] * 255)  # colour 0 = white, others red
    image.paste(1, (0, 0, 5, 10))  # left half uses colour 1 (red)
    data = _encode(image, "PNG", transparency=0)  # colour 0 is transparent
    loaded = load_image(data)

    assert loaded.alpha_hint is not None
    assert loaded.alpha_hint[0, 0] == pytest.approx(1.0)  # red half: opaque
    assert loaded.alpha_hint[0, 9] == pytest.approx(0.0)  # white half: transparent


# --- Step 4: colour normalisation --------------------------------------------


def test_sixteen_bit_greyscale_is_scaled_not_clipped():
    """The Pillow pitfall: a plain convert("L") would turn mid-grey into white."""
    mid_grey_16bit = np.full((10, 10), 32768, dtype=np.uint16)  # half of 65535
    data = _encode(Image.fromarray(mid_grey_16bit), "PNG")
    loaded = load_image(data)

    value = loaded.rgb.getpixel((5, 5))[0]
    assert 125 <= value <= 130  # about 128 (mid-grey), not 255 (white)
    assert any("8-bit" in note for note in loaded.notes)


def test_cmyk_jpeg_becomes_rgb():
    """Print files are CMYK; pure magenta + yellow ink should come out red."""
    cmyk = Image.new("CMYK", (10, 10), (0, 255, 255, 0))
    loaded = load_image(_encode(cmyk, "JPEG"))

    red, green, blue = loaded.rgb.getpixel((5, 5))
    assert loaded.rgb.mode == "RGB"
    assert red > 200 and green < 60 and blue < 60
    assert any("CMYK" in note for note in loaded.notes)


def test_greyscale_becomes_rgb():
    loaded = load_image(_encode(Image.new("L", (10, 10), 100), "PNG"))
    assert loaded.rgb.mode == "RGB"
    assert loaded.rgb.getpixel((0, 0)) == (100, 100, 100)


def test_embedded_colour_profile_is_applied():
    """An image with an embedded ICC profile goes through colour management."""
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    data = _encode(Image.new("RGB", (10, 10), (200, 100, 50)), "PNG", icc_profile=srgb)
    loaded = load_image(data)

    # sRGB -> sRGB must leave the colour (almost) unchanged.
    red, green, blue = loaded.rgb.getpixel((5, 5))
    assert abs(red - 200) <= 2 and abs(green - 100) <= 2 and abs(blue - 50) <= 2
    assert any("to sRGB" in note for note in loaded.notes)


def test_broken_colour_profile_does_not_fail_the_load():
    """A corrupt profile must not reject an otherwise fine photo."""
    data = _encode(Image.new("RGB", (10, 10), (1, 2, 3)), "PNG", icc_profile=b"garbage")
    loaded = load_image(data)

    assert loaded.rgb.getpixel((0, 0)) == (1, 2, 3)
    assert any("unreadable colour profile" in note for note in loaded.notes)
