"""Tests for bgchange/compose/save.py: output path and PNG writing."""

from pathlib import Path

import numpy as np
from PIL import Image

from bgchange.color import Color
from bgchange.compose import default_output_path, save_png


def test_default_path_names_photo_and_colour():
    assert default_output_path(Path("C:/photos/shoe.jpg"), Color(255, 0, 102)) == Path("outputs/shoe_on_FF0066.png")
    assert default_output_path(Path("shoe.jpg"), Color(0, 0, 0, 0)).name == "shoe_on_00000000.png"


def test_save_png_is_lossless_and_creates_the_folder(tmp_path):
    pixels = np.random.default_rng(0).integers(0, 256, (5, 7, 4), dtype=np.uint8)
    path = save_png(Image.fromarray(pixels, mode="RGBA"), tmp_path / "new" / "out.jpg")
    assert path.suffix == ".png"  # always PNG, even if asked for .jpg
    assert np.array_equal(np.asarray(Image.open(path)), pixels)
