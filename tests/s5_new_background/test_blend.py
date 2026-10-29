"""Tests for bgchange/s5_new_background/blend.py and background.py: composite().

Built from tiny images in code: a 2x2 photo and hand-written masks, so the
expected pixel of every case can be worked out by hand.
"""

import numpy as np
import pytest
from PIL import Image

from bgchange.s2_read_color import Color
from bgchange.s5_new_background import composite, make_background

PINK = Color(255, 0, 102)


@pytest.fixture
def photo():
    """2x2 photo with four different colours."""
    pixels = np.array([[[10, 20, 30], [200, 100, 50]], [[0, 0, 0], [255, 255, 255]]], dtype=np.uint8)
    return Image.fromarray(pixels, mode="RGB")


def test_mask_one_keeps_the_photo_exactly(photo):
    result = composite(photo, np.ones((2, 2), np.float32), PINK)
    assert np.array_equal(np.asarray(result), np.asarray(photo))


def test_mask_zero_gives_the_colour_exactly(photo):
    result = composite(photo, np.zeros((2, 2), np.float32), PINK)
    assert (np.asarray(result) == PINK.rgb).all()


def test_half_mask_mixes_light_not_pixel_values():
    """Half black + half white = half the light = sRGB 188, not 128.

    128 is what a naive mix of pixel values gives; it makes soft edges too dark.
    """
    black = Image.new("RGB", (1, 1), (0, 0, 0))
    result = composite(black, np.full((1, 1), 0.5, np.float32), Color(255, 255, 255))
    assert np.asarray(result)[0, 0].tolist() == [188, 188, 188]


def test_solid_colour_gives_rgb_same_size(photo):
    result = composite(photo, np.zeros((2, 2), np.float32), PINK)
    assert result.mode == "RGB" and result.size == photo.size


def test_fully_transparent_colour_gives_a_cut_out(photo):
    """#00000000: the output's transparency is the mask itself, the subject is unchanged.

    Edge cleanup is off here so the half-mask pixel can be compared with the photo.
    """
    mask = np.array([[1.0, 0.0], [0.5, 1.0]], np.float32)
    result = composite(photo, mask, Color(0, 0, 0, 0), clean_edges=False)
    rgba = np.asarray(result)
    assert result.mode == "RGBA"
    assert rgba[..., 3].tolist() == [[255, 0], [128, 255]]
    assert np.array_equal(rgba[0, 0, :3], np.asarray(photo)[0, 0])  # mask 1: photo kept
    assert np.array_equal(rgba[1, 0, :3], np.asarray(photo)[1, 0])  # mask 0.5: colour not darkened


def test_edge_cleanup_is_on_by_default_and_only_changes_edges():
    """A red subject edge over green: cleaned, the edge pixel is redder than without cleanup."""
    pixels = np.zeros((10, 20, 3), np.uint8)
    pixels[:, :10] = (200, 10, 10)  # red subject
    pixels[:, 10] = (145, 120, 10)  # edge: red and green mixed
    pixels[:, 11:] = (10, 160, 10)  # green background
    mask = np.zeros((10, 20), np.float32)
    mask[:, :10], mask[:, 10] = 1.0, 0.5
    photo = Image.fromarray(pixels, mode="RGB")

    cleaned = np.asarray(composite(photo, mask, Color(255, 255, 255)))
    raw = np.asarray(composite(photo, mask, Color(255, 255, 255), clean_edges=False))
    assert cleaned[0, 10, 1] < raw[0, 10, 1]  # less green left in the edge
    assert np.array_equal(cleaned[:, :10], raw[:, :10])  # subject untouched


def test_half_transparent_colour_gives_half_opaque_background(photo):
    result = composite(photo, np.zeros((2, 2), np.float32), Color(255, 0, 102, 128))
    rgba = np.asarray(result)
    assert (rgba[..., :3] == PINK.rgb).all()
    assert (rgba[..., 3] == 128).all()


def test_mask_values_outside_0_1_are_clipped(photo):
    result = composite(photo, np.full((2, 2), 1.7, np.float32), PINK)
    assert np.array_equal(np.asarray(result), np.asarray(photo))


def test_wrong_mask_size_is_refused(photo):
    with pytest.raises(ValueError, match="does not match"):
        composite(photo, np.ones((3, 3), np.float32), PINK)


def test_non_rgb_photo_is_refused():
    with pytest.raises(ValueError, match="mode RGB"):
        composite(Image.new("L", (2, 2)), np.ones((2, 2), np.float32), PINK)


def test_background_layer_shape_and_opacity():
    layer = make_background(Color(255, 255, 255, 51), (4, 3))
    assert layer.shape == (3, 4, 4)
    assert layer[0, 0].tolist() == pytest.approx([1.0, 1.0, 1.0, 0.2])
