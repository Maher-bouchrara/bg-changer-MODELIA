"""Tests for step 1 (bgchange/io/open_file.py): opening and validating files."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from bgchange.io import ImageLoadError, load_image


def test_plain_rgb_jpeg_loads_unchanged(encode):
    """The normal case: an RGB JPEG needs no fixes, so no notes are added."""
    loaded = load_image(encode(Image.new("RGB", (30, 20), (10, 120, 200)), "JPEG"))

    assert loaded.rgb.mode == "RGB"
    assert loaded.size == (30, 20)
    assert loaded.alpha_hint is None
    assert loaded.notes == []


def test_path_and_bytes_give_the_same_result(encode, tmp_path):
    """The CLI passes a path and the API passes bytes; both must behave the same."""
    data = encode(Image.new("RGB", (8, 8), (200, 50, 50)), "PNG")
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


def test_truncated_file_gives_clear_error(encode):
    """A download cut off halfway: the header is fine but the pixels are missing."""
    noise = np.random.default_rng(0).integers(0, 255, (200, 200, 3), dtype=np.uint8)
    data = encode(Image.fromarray(noise), "JPEG")
    with pytest.raises(ImageLoadError, match="damaged or incomplete"):
        load_image(data[: len(data) // 2])


def test_too_large_image_is_refused_before_decoding(encode):
    """The size check must happen before the pixels are decoded (bomb protection)."""
    data = encode(Image.new("RGB", (20, 20)), "PNG")  # 400 pixels
    with pytest.raises(ImageLoadError, match="too large"):
        load_image(data, max_pixels=100)


def test_animated_gif_uses_first_frame():
    frames = [Image.new("RGB", (10, 10), (255, 0, 0)), Image.new("RGB", (10, 10), (0, 0, 255))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:])
    loaded = load_image(buffer.getvalue())

    red, _, blue = loaded.rgb.getpixel((5, 5))
    assert red > 200 and blue < 50  # the first (red) frame, not the blue one
    assert any("frames" in note for note in loaded.notes)
