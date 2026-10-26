"""Load any image file into one predictable format: upright, 8-bit, sRGB.

Every later stage (the model, the shadow code, the compositing) assumes a plain
RGB image. This module is the single place that guarantees it, so nothing
downstream ever has to worry about where the photo came from.

The loading pipeline (see README section 3.1):

    file / bytes
      1. open + validate     -> clear error if it is not a real image, or too big
      2. fix EXIF rotation   -> phone photos stored sideways become upright
      3. split off alpha     -> keep any existing transparency as a "hint"
      4. normalise colour    -> 16-bit, CMYK, palette, greyscale, colour profiles -> 8-bit sRGB
      = LoadedImage(rgb, alpha_hint, notes)

Why step 3 comes before step 4: colour-profile conversion works on the colour
channels only, so the transparency channel is taken out first and handled on its
own.

Note on the name: this file is `bgchange.io`. It does not clash with Python's
built-in `io` module because the package is always imported by its full name.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

# Refuse images above 50 megapixels (e.g. 8660 x 5773). That is far larger than
# any phone or studio photo, and stops "decompression bombs": tiny files that
# expand to gigabytes of pixels and freeze the machine.
MAX_PIXELS = 50_000_000

# EXIF tag number that stores the camera orientation (1 = already upright).
_EXIF_ORIENTATION_TAG = 0x0112

# Everything this function can be given: a path on disk, raw bytes (what the
# HTTP API receives from an upload), or an already-open binary file.
ImageSource = str | Path | bytes | BinaryIO


class ImageLoadError(ValueError):
    """Raised when the input cannot be turned into a usable image.

    The message is always written for the end user (it is shown as-is by the
    CLI and the API), so it says what went wrong and what to do.
    """


@dataclass(frozen=True)
class LoadedImage:
    """The result of loading: everything later stages need, in one object."""

    #: The photo itself: mode "RGB", 8 bits per channel, sRGB colours, upright.
    rgb: Image.Image

    #: Transparency that was already in the file (e.g. a PNG cut-out), as a
    #: float32 array (height, width) in [0, 1]. None when the file had no
    #: transparency, or when it was fully opaque (so it carries no information).
    alpha_hint: np.ndarray | None = None

    #: Human-readable list of every fix that was applied, e.g.
    #: ["rotated upright using EXIF orientation 6", "converted CMYK to RGB"].
    #: Printed by the CLI and returned by the API so nothing happens silently.
    notes: list[str] = field(default_factory=list)

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) of the upright image."""
        return self.rgb.size


def load_image(source: ImageSource, max_pixels: int = MAX_PIXELS) -> LoadedImage:
    """Open an image from a path, bytes or file object and normalise it.

    Args:
        source: path, raw bytes, or a binary file object.
        max_pixels: refuse images with more pixels than this.

    Returns:
        A LoadedImage whose `rgb` is always upright 8-bit sRGB.

    Raises:
        ImageLoadError: missing file, not an image, corrupted, or too large.
    """
    notes: list[str] = []

    image = _open(source, max_pixels, notes)  # step 1
    image = _fix_exif_rotation(image, notes)  # step 2
    image, alpha = _split_alpha(image, notes)  # step 3
    rgb = _to_srgb(image, notes)  # step 4

    return LoadedImage(rgb=rgb, alpha_hint=alpha, notes=notes)


# ---------------------------------------------------------------------------
# Step 1: open and validate
# ---------------------------------------------------------------------------


def _open(source: ImageSource, max_pixels: int, notes: list[str]) -> Image.Image:
    """Open the file, check its size, and fully decode it."""
    # Raw bytes (from an upload) are wrapped so Pillow can read them like a file.
    if isinstance(source, bytes):
        source = io.BytesIO(source)

    try:
        # Image.open only reads the header (format, width, height) at this
        # point, not the pixels. That lets us check the size cheaply below,
        # before spending memory on decoding.
        image = Image.open(source)
    except FileNotFoundError:
        raise ImageLoadError(f"File not found: {source}") from None
    except UnidentifiedImageError:
        raise ImageLoadError(
            "This file is not a readable image. Supported: JPEG, PNG, WebP, TIFF, BMP, GIF."
        ) from None
    except Image.DecompressionBombError:
        # Pillow's own guard fires for absurdly large images (> ~179 MP).
        raise ImageLoadError(_too_large_message(None, max_pixels)) from None

    width, height = image.size
    if width * height > max_pixels:
        raise ImageLoadError(_too_large_message((width, height), max_pixels))

    # Animated GIF / WebP / multi-page TIFF: only the first frame is used.
    if getattr(image, "n_frames", 1) > 1:
        image.seek(0)
        notes.append(f"file has {image.n_frames} frames; using the first one")

    try:
        # Now decode the pixels. A corrupted or cut-off file fails here, not
        # at open(), so this is where "truncated file" errors are caught.
        image.load()
    except OSError as exc:
        raise ImageLoadError(f"The image file is damaged or incomplete ({exc}).") from None

    return image


def _too_large_message(size: tuple[int, int] | None, max_pixels: int) -> str:
    """User-facing message for images over the pixel limit."""
    limit_mp = max_pixels / 1_000_000
    if size is None:
        return f"Image is too large (limit {limit_mp:.0f} megapixels)."
    width, height = size
    return (
        f"Image is too large: {width}x{height} = {width * height / 1_000_000:.1f} megapixels "
        f"(limit {limit_mp:.0f}). Please resize it first."
    )


# ---------------------------------------------------------------------------
# Step 2: EXIF rotation
# ---------------------------------------------------------------------------


def _fix_exif_rotation(image: Image.Image, notes: list[str]) -> Image.Image:
    """Rotate/flip the pixels so the image is upright.

    Phones usually save the pixels in the sensor's orientation and add an EXIF
    tag saying "rotate 90 degrees when displaying". Photo viewers obey the tag;
    raw pixel code (like our model) does not. Without this step a portrait
    photo would be processed and returned lying on its side.
    """
    orientation = image.getexif().get(_EXIF_ORIENTATION_TAG, 1)
    if orientation == 1:
        return image  # already upright, nothing to do

    # exif_transpose applies the rotation/flip to the pixels and removes the
    # tag, so the result is upright no matter which viewer opens it later.
    upright = ImageOps.exif_transpose(image)
    notes.append(f"rotated upright using EXIF orientation {orientation}")
    return upright


# ---------------------------------------------------------------------------
# Step 3: split off existing transparency
# ---------------------------------------------------------------------------


def _split_alpha(image: Image.Image, notes: list[str]) -> tuple[Image.Image, np.ndarray | None]:
    """Separate the transparency channel (if any) from the colour channels.

    Returns:
        (image without alpha, alpha as float32 [0, 1] or None)

    If a user uploads a PNG that is already partly cut out, those transparent
    pixels are background for certain. The compositing step later uses this as
    a hint so they stay transparent even if the model disagrees.
    """
    # Palette images ("P") can mark one palette colour as transparent. Turning
    # them into RGBA makes that transparency a normal alpha channel.
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    # "PA" = palette + alpha; "La" / "RGBa" = alpha already multiplied into colours.
    elif image.mode in ("PA", "La", "RGBa"):
        image = image.convert("RGBA")

    # Only these two modes carry a separate alpha channel at this point.
    if image.mode not in ("RGBA", "LA"):
        return image, None

    alpha_band = np.asarray(image.getchannel("A"), dtype=np.float32) / 255.0
    colour_only = image.convert("RGB" if image.mode == "RGBA" else "L")

    # A fully opaque alpha channel tells us nothing; drop it to keep things simple.
    if alpha_band.min() >= 1.0:
        return colour_only, None

    notes.append("kept the file's existing transparency as a hint")
    return colour_only, alpha_band


# ---------------------------------------------------------------------------
# Step 4: normalise colour to 8-bit sRGB
# ---------------------------------------------------------------------------


def _to_srgb(image: Image.Image, notes: list[str]) -> Image.Image:
    """Convert any remaining colour mode / colour profile to 8-bit sRGB."""
    # 16-bit and 32-bit greyscale must be handled first, by hand (see below).
    if image.mode in ("I", "I;16", "I;16L", "I;16B", "I;16N", "F"):
        image = _high_bit_depth_to_8bit(image, notes)

    # An embedded ICC profile says "my numbers mean these exact colours".
    # iPhones save in Display-P3 and print files in CMYK profiles; reading the
    # numbers as if they were sRGB makes colours look washed out or shifted.
    icc = image.info.get("icc_profile")
    if icc:
        converted = _apply_icc_profile(image, icc, notes)
        if converted is not None:
            return converted

    if image.mode == "CMYK":
        # No profile to go on: use Pillow's simple formula. Colours are
        # approximate, but far better than failing.
        notes.append("converted CMYK to RGB (no colour profile, colours approximate)")
    elif image.mode == "L":
        notes.append("converted greyscale to RGB")
    elif image.mode != "RGB":
        notes.append(f"converted {image.mode} to RGB")

    return image.convert("RGB")


def _high_bit_depth_to_8bit(image: Image.Image, notes: list[str]) -> Image.Image:
    """Scale 16/32-bit greyscale down to 8-bit.

    Why by hand: Pillow's image.convert("L") *clips* values above 255 instead
    of scaling them. A 16-bit value of 32768 (mid-grey out of 65535) would
    become 255 (white), so most of the image would turn white.
    """
    values = np.asarray(image, dtype=np.float64)

    if image.mode == "F":
        # Floating-point images usually store 0..1; otherwise assume 0..255.
        scale = 255.0 if values.max() <= 1.0 else 1.0
    else:
        # 16-bit data is 0..65535; 65535 / 257 = 255 exactly. If the values
        # never exceed 255 the file was 8-bit data in a wide container: keep it.
        scale = 1 / 257 if values.max() > 255 else 1.0

    eight_bit = np.clip(values * scale, 0, 255).round().astype(np.uint8)
    notes.append(f"scaled {image.mode} (high bit depth) down to 8-bit")
    return Image.fromarray(eight_bit, mode="L")


def _apply_icc_profile(image: Image.Image, icc: bytes, notes: list[str]) -> Image.Image | None:
    """Convert from the file's embedded colour profile to standard sRGB.

    Returns None if the profile is broken or unsupported; the caller then falls
    back to a plain conversion instead of failing the whole request.
    """
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        srgb_profile = ImageCms.createProfile("sRGB")
        converted = ImageCms.profileToProfile(
            image, source_profile, srgb_profile, outputMode="RGB"
        )
    except (ImageCms.PyCMSError, OSError, ValueError):
        notes.append("ignored an unreadable colour profile")
        return None

    profile_name = ImageCms.getProfileDescription(source_profile).strip() or "embedded profile"
    notes.append(f"converted colours from '{profile_name}' to sRGB")
    return converted
