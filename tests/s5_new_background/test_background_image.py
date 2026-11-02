"""Tests for a picture as the new background: background_image.py (fit_background)
and composite() with a picture instead of a colour.

The pictures are made in code (stripes, halves of two colours), so the expected
pixels can be worked out by hand.
"""

import numpy as np
import pytest
from PIL import Image

from bgchange.s5_new_background import composite, fit_background, make_background


def halves(size, left, right):
    """A picture whose left half is `left` and right half is `right`."""
    w, h = size
    pixels = np.zeros((h, w, 3), np.uint8)
    pixels[:, : w // 2] = left
    pixels[:, w // 2 :] = right
    return Image.fromarray(pixels, mode="RGB")


# --- fit_background(): cover + centre crop -------------------------------------


def test_result_has_exactly_the_photo_size():
    for size in [(80, 60), (60, 80), (33, 17)]:
        assert fit_background(Image.new("RGB", (300, 100)), size).size == size


def test_wide_picture_is_cropped_left_and_right_not_stretched():
    """300x100 with three 100 px stripes, onto a square photo: only the middle stripe remains."""
    pixels = np.zeros((100, 300, 3), np.uint8)
    pixels[:, :100] = (255, 0, 0)
    pixels[:, 100:200] = (0, 255, 0)
    pixels[:, 200:] = (0, 0, 255)
    out = np.asarray(fit_background(Image.fromarray(pixels), (50, 50)))
    assert (out[5:-5, 5:-5] == (0, 255, 0)).all()


def test_small_picture_is_enlarged_to_cover():
    out = fit_background(halves((10, 10), (0, 0, 0), (255, 255, 255)), (100, 100))
    a = np.asarray(out)
    assert out.size == (100, 100)
    # LANCZOS softens about 3 source pixels (30 px here) around the black/white edge
    assert (a[:, :15] == 0).all() and (a[:, 85:] == 255).all()


def test_transparent_or_grey_pictures_become_rgb():
    assert fit_background(Image.new("RGBA", (20, 20), (9, 9, 9, 0)), (10, 10)).mode == "RGB"
    assert fit_background(Image.new("L", (20, 20), 128), (10, 10)).mode == "RGB"


# --- composite() with a picture --------------------------------------------------


@pytest.fixture
def photo():
    return Image.new("RGB", (40, 20), (10, 20, 30))


def test_mask_zero_shows_the_picture(photo):
    picture = halves((40, 20), (255, 0, 0), (0, 0, 255))
    result = composite(photo, np.zeros((20, 40), np.float32), picture, clean_edges=False)
    assert result.mode == "RGB"
    assert (np.asarray(result) == np.asarray(picture)).all()


def test_mask_one_keeps_the_photo(photo):
    picture = halves((40, 20), (255, 0, 0), (0, 0, 255))
    result = composite(photo, np.ones((20, 40), np.float32), picture, clean_edges=False)
    assert (np.asarray(result) == (10, 20, 30)).all()


def test_shadow_darkens_the_picture_like_a_colour(photo):
    """Shadow 0.5 = half the light, on every pixel of the picture: white -> 188, black stays 0."""
    picture = halves((40, 20), (255, 255, 255), (0, 0, 0))
    shadow = np.full((20, 40), 0.5, np.float32)
    result = np.asarray(composite(photo, np.zeros((20, 40), np.float32), picture, clean_edges=False, shadow=shadow))
    assert (result[:, :20] == 188).all()
    assert (result[:, 20:] == 0).all()


def test_picture_layer_is_opaque():
    layer = make_background(Image.new("RGB", (8, 8), (255, 0, 102)), (4, 3))
    assert layer.shape == (3, 4, 4)
    assert (layer[..., 3] == 1.0).all()
