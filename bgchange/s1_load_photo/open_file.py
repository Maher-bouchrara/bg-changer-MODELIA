"""Step 1: open the file and check it is a real, reasonably sized image.

Problems handled here:
    - the file does not exist
    - the file is not an image (e.g. a .txt renamed to .jpg)
    - the file is damaged or cut off (an interrupted download)
    - the image is absurdly large, or a "decompression bomb"
    - the file is animated / multi-page (only the first frame is used)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from bgchange.s1_load_photo.errors import ImageLoadError

# Refuse images above 50 megapixels (e.g. 8660 x 5773). That is far larger than
# any phone or studio photo, and stops "decompression bombs": tiny files that
# expand to gigabytes of pixels and freeze the machine.
MAX_PIXELS = 50_000_000

# Everything the loader can be given: a path on disk, raw bytes (what the HTTP
# API receives from an upload), or an already-open binary file.
ImageSource = str | Path | bytes | BinaryIO


def open_image(source: ImageSource, max_pixels: int, notes: list[str]) -> Image.Image:
    """Open the file, check its size, and fully decode it.

    Args:
        source: path, raw bytes, or a binary file object.
        max_pixels: refuse images with more pixels than this.
        notes: list that a sentence is appended to if something is changed.

    Raises:
        ImageLoadError: with a message written for the end user.
    """
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
