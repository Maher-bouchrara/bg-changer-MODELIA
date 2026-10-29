"""Tests for bgchange/s5_new_background/linear_light.py: sRGB <-> linear light."""

import numpy as np
import pytest

from bgchange.s5_new_background.linear_light import linear_to_srgb, srgb_to_linear, to_uint8


def test_black_and_white_do_not_change():
    assert srgb_to_linear(np.array([0.0, 1.0])) == pytest.approx([0.0, 1.0])
    assert linear_to_srgb(np.array([0.0, 1.0])) == pytest.approx([0.0, 1.0])


def test_mid_grey_is_only_about_a_fifth_of_the_light():
    """The reason this file exists: sRGB 128 is ~21.6% of white's light, not 50%."""
    assert srgb_to_linear(np.array(128 / 255)) == pytest.approx(0.2158, abs=1e-4)


def test_every_8_bit_value_survives_the_round_trip():
    """255 -> linear -> back -> 255: a pixel with mask = 1 must come out unchanged."""
    values = np.arange(256, dtype=np.uint8)
    assert np.array_equal(to_uint8(linear_to_srgb(srgb_to_linear(values / 255.0))), values)


def test_out_of_range_light_is_clipped_not_nan():
    assert not np.isnan(linear_to_srgb(np.array([-0.1, 1.5]))).any()
