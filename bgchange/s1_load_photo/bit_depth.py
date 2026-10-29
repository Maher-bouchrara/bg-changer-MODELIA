"""Scale 16-bit (and 32-bit) greyscale images down to 8-bit correctly.

Why this needs its own code: Pillow's image.convert("L") *clips* values above
255 instead of scaling them.

    16-bit value      correct 8-bit      Pillow's convert("L")
    0      (black)    0                  0
    32768  (mid-grey) 128                255  <- white!
    65535  (white)    255                255

So with a plain conversion, most of a 16-bit photo turns white.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

# Pillow mode names for greyscale images with more than 8 bits per pixel:
# "I;16*" = 16-bit integers, "I" = 32-bit integers, "F" = 32-bit floats.
HIGH_BIT_DEPTH_MODES = ("I", "I;16", "I;16L", "I;16B", "I;16N", "F")


def to_8bit(image: Image.Image, notes: list[str]) -> Image.Image:
    """Return an 8-bit greyscale ("L") version of a high bit depth image.

    Args:
        image: an image whose mode is in HIGH_BIT_DEPTH_MODES.
        notes: list that a sentence is appended to.
    """
    values = np.asarray(image, dtype=np.float64)

    if image.mode == "F":
        # Floating-point images usually store 0..1; otherwise assume 0..255.
        scale = 255.0 if values.max() <= 1.0 else 1.0
    else:
        # 16-bit data is 0..65535, and 65535 / 257 = 255 exactly. If the values
        # never exceed 255, the file was 8-bit data in a wide container: keep it.
        scale = 1 / 257 if values.max() > 255 else 1.0

    eight_bit = np.clip(values * scale, 0, 255).round().astype(np.uint8)
    notes.append(f"scaled {image.mode} (high bit depth) down to 8-bit")
    return Image.fromarray(eight_bit, mode="L")
