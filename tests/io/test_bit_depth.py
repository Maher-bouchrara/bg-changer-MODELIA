"""Tests for bgchange/io/bit_depth.py: 16-bit greyscale scaling."""

from __future__ import annotations

import numpy as np
from PIL import Image

from bgchange.io import load_image


def test_sixteen_bit_greyscale_is_scaled_not_clipped(encode):
    """The Pillow pitfall: a plain convert("L") would turn mid-grey into white."""
    mid_grey_16bit = np.full((10, 10), 32768, dtype=np.uint16)  # half of 65535
    loaded = load_image(encode(Image.fromarray(mid_grey_16bit), "PNG"))

    value = loaded.rgb.getpixel((5, 5))[0]
    assert 125 <= value <= 130  # about 128 (mid-grey), not 255 (white)
    assert any("8-bit" in note for note in loaded.notes)


def test_sixteen_bit_white_stays_white(encode):
    """The top of the 16-bit range (65535) must map to the top of 8-bit (255)."""
    white_16bit = np.full((4, 4), 65535, dtype=np.uint16)
    loaded = load_image(encode(Image.fromarray(white_16bit), "PNG"))

    assert loaded.rgb.getpixel((0, 0)) == (255, 255, 255)
