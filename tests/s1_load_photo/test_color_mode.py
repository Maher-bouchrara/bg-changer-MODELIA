"""Tests for step 4 (bgchange/s1_load_photo/color_mode.py): plain colour-mode conversions."""

from __future__ import annotations

from PIL import Image

from bgchange.s1_load_photo import load_image


def test_cmyk_jpeg_becomes_rgb(encode):
    """Print files are CMYK; pure magenta + yellow ink should come out red."""
    loaded = load_image(encode(Image.new("CMYK", (10, 10), (0, 255, 255, 0)), "JPEG"))

    red, green, blue = loaded.rgb.getpixel((5, 5))
    assert loaded.rgb.mode == "RGB"
    assert red > 200 and green < 60 and blue < 60
    assert any("CMYK" in note for note in loaded.notes)


def test_greyscale_becomes_rgb(encode):
    loaded = load_image(encode(Image.new("L", (10, 10), 100), "PNG"))

    assert loaded.rgb.mode == "RGB"
    assert loaded.rgb.getpixel((0, 0)) == (100, 100, 100)
    assert any("greyscale" in note for note in loaded.notes)
