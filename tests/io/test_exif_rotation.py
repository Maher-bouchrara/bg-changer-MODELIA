"""Tests for step 2 (bgchange/io/exif_rotation.py): EXIF rotation."""

from __future__ import annotations

from PIL import Image

from bgchange.io import load_image


def test_exif_rotation_is_applied(encode):
    """A phone photo stored sideways (EXIF orientation 6 = rotate 90 deg clockwise).

    The stored pixels are 40 wide x 20 tall; the photo as people see it is
    20 wide x 40 tall. The loader must return the version people see.
    """
    stored = Image.new("RGB", (40, 20), (0, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    loaded = load_image(encode(stored, "JPEG", exif=exif))

    assert loaded.size == (20, 40)
    assert any("EXIF orientation 6" in note for note in loaded.notes)


def test_upright_photo_is_not_touched(encode):
    """Orientation 1 means "already upright": no rotation, no note."""
    exif = Image.Exif()
    exif[0x0112] = 1
    loaded = load_image(encode(Image.new("RGB", (40, 20)), "JPEG", exif=exif))

    assert loaded.size == (40, 20)
    assert not any("EXIF" in note for note in loaded.notes)
