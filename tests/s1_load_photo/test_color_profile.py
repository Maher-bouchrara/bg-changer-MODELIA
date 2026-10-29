"""Tests for bgchange/s1_load_photo/color_profile.py: embedded ICC colour profiles."""

from __future__ import annotations

from PIL import Image, ImageCms

from bgchange.s1_load_photo import load_image


def test_embedded_colour_profile_is_applied(encode):
    """An image with an embedded ICC profile goes through colour management."""
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    data = encode(Image.new("RGB", (10, 10), (200, 100, 50)), "PNG", icc_profile=srgb)
    loaded = load_image(data)

    # sRGB -> sRGB must leave the colour (almost) unchanged.
    red, green, blue = loaded.rgb.getpixel((5, 5))
    assert abs(red - 200) <= 2 and abs(green - 100) <= 2 and abs(blue - 50) <= 2
    assert any("to sRGB" in note for note in loaded.notes)


def test_broken_colour_profile_does_not_fail_the_load(encode):
    """A corrupt profile must not reject an otherwise fine photo."""
    data = encode(Image.new("RGB", (10, 10), (1, 2, 3)), "PNG", icc_profile=b"garbage")
    loaded = load_image(data)

    assert loaded.rgb.getpixel((0, 0)) == (1, 2, 3)
    assert any("unreadable colour profile" in note for note in loaded.notes)
