"""Tests for bgchange/s4_shadow/: lit_background.py and shadow_map.py (the real shadow).

The test photo is made up, the way a product shot looks:

    white floor everywhere
    a red square (the subject)
    under it: its shadow, 40% less light than the floor
    next to its TOP: a dark patch (a busy scene's object, not this shadow)
    at the far right edge: another dark object
"""

import numpy as np
import pytest
from PIL import Image

from bgchange.s4_shadow import extract_shadow, find_lit_background
from bgchange.s5_new_background.linear_light import linear_to_srgb, to_uint8

FLOOR = 0.8  # floor light, in linear light


@pytest.fixture
def product_shot():
    light = np.full((200, 600, 3), FLOOR, np.float32)
    light[140:170, 60:200] = FLOOR * 0.6  # shadow under the subject: 40% less light
    light[20:50, 150:190] = FLOOR * 0.6  # dark patch next to the subject's top
    light[60:140, 560:] = FLOOR * 0.6  # far object
    light[60:140, 60:140] = (0.6, 0.02, 0.02)  # red subject
    mask = np.zeros((200, 600), np.float32)
    mask[60:140, 60:140] = 1.0
    photo = Image.fromarray(to_uint8(linear_to_srgb(light)), mode="RGB")
    return photo, mask


def test_shadow_under_the_subject_is_kept(product_shot):
    """40% less light -> (0.4 - 0.05) / 0.95 = 0.37, a little less as it fades from the base."""
    shadow = extract_shadow(*product_shot)
    assert 0.25 < shadow[143, 100] < 0.4


def test_lit_floor_has_no_shadow(product_shot):
    shadow = extract_shadow(*product_shot)
    assert shadow[185, 300] == pytest.approx(0.0, abs=0.01)


def test_subject_is_not_shadow(product_shot):
    shadow = extract_shadow(*product_shot)
    assert shadow[100, 100] == pytest.approx(0.0, abs=0.01)


def test_dark_things_away_from_the_bottom_are_ignored(product_shot):
    """The patch near the subject's top and the far object are not its shadow."""
    shadow = extract_shadow(*product_shot)
    assert shadow[35, 170] == pytest.approx(0.0, abs=0.01)
    assert shadow[100, 580] == pytest.approx(0.0, abs=0.01)


def test_empty_mask_gives_no_shadow(product_shot):
    photo, mask = product_shot
    assert not extract_shadow(photo, np.zeros_like(mask)).any()


def test_lit_background_ignores_the_shadow():
    """Inside a shadow, the 'lit floor' guess is still the floor's full brightness."""
    brightness = np.full((100, 100), 0.8, np.float32)
    brightness[40:60, 40:60] = 0.3  # shadow
    lit = find_lit_background(brightness, np.ones((100, 100), bool))
    assert lit[50, 50] == pytest.approx(0.8, abs=0.01)
