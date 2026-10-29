"""Tests for bgchange/s5_new_background/foreground.py: estimate_foreground().

The test image is a made-up edge, built the way a camera would see it:

    columns 0-9    red subject      mask 1
    column  10     half and half    mask 0.5   photo = 0.5 x red + 0.5 x green
    columns 11-20  green background mask 0
"""

import numpy as np
import pytest

from bgchange.s5_new_background.foreground import estimate_foreground

RED = np.array([0.8, 0.05, 0.05], np.float32)
GREEN = np.array([0.05, 0.6, 0.05], np.float32)


@pytest.fixture
def edge():
    mask = np.zeros((12, 21), np.float32)
    mask[:, :10] = 1.0
    mask[:, 10] = 0.5
    image = mask[..., None] * RED + (1 - mask[..., None]) * GREEN
    return image, mask


def test_edge_pixel_gets_the_subject_colour_back(edge):
    """The half-and-half column must come out red, not a red-green mix."""
    image, mask = edge
    fg = estimate_foreground(image, mask)
    assert fg[:, 10] == pytest.approx(np.tile(RED, (12, 1)), abs=0.02)
    # Without the fix, the pixel is far from red: that is the halo.
    assert np.abs(image[0, 10] - RED).max() > 0.2


def test_subject_pixels_are_unchanged(edge):
    image, mask = edge
    fg = estimate_foreground(image, mask)
    assert fg[:, :10] == pytest.approx(image[:, :10], abs=1e-5)


def test_result_stays_in_range_and_shape():
    rng = np.random.default_rng(0)
    image = rng.random((30, 40, 3), dtype=np.float32)
    mask = rng.random((30, 40), dtype=np.float32)
    fg = estimate_foreground(image, mask)
    assert fg.shape == image.shape and fg.dtype == np.float32
    assert fg.min() >= 0.0 and fg.max() <= 1.0
