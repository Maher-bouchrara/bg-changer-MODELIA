"""Tests for step 3 (bgchange/s1_load_photo/transparency.py): existing transparency."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from bgchange.s1_load_photo import load_image


def test_rgba_png_keeps_alpha_as_hint(encode):
    """A PNG that is already half cut out: the transparency becomes the hint."""
    pixels = np.zeros((10, 10, 4), dtype=np.uint8)
    pixels[..., 0] = 255  # red everywhere
    pixels[:, :5, 3] = 255  # left half opaque
    pixels[:, 5:, 3] = 0  # right half transparent
    loaded = load_image(encode(Image.fromarray(pixels, mode="RGBA"), "PNG"))

    assert loaded.rgb.mode == "RGB"
    assert loaded.alpha_hint is not None
    assert loaded.alpha_hint.shape == (10, 10)  # (height, width)
    assert loaded.alpha_hint[0, 0] == pytest.approx(1.0)
    assert loaded.alpha_hint[0, 9] == pytest.approx(0.0)


def test_fully_opaque_alpha_is_dropped(encode):
    """An alpha channel that is 100% opaque carries no information."""
    data = encode(Image.new("RGBA", (10, 10), (0, 255, 0, 255)), "PNG")
    assert load_image(data).alpha_hint is None


def test_palette_png_with_transparent_colour(encode):
    """Palette ("P") images mark transparency differently; it must still be found."""
    image = Image.new("P", (10, 10), 0)
    image.putpalette([255, 255, 255] + [255, 0, 0] * 255)  # colour 0 = white, others red
    image.paste(1, (0, 0, 5, 10))  # left half uses colour 1 (red)
    loaded = load_image(encode(image, "PNG", transparency=0))  # colour 0 is transparent

    assert loaded.alpha_hint is not None
    assert loaded.alpha_hint[0, 0] == pytest.approx(1.0)  # red half: opaque
    assert loaded.alpha_hint[0, 9] == pytest.approx(0.0)  # white half: transparent
