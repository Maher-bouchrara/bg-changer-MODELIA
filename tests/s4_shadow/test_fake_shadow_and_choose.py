"""Tests for bgchange/s4_shadow/fake_shadow.py and choose.py.

The mask: a square subject, rows 50-99 (50 px tall), in a 200 x 200 photo.
"""

import numpy as np
import pytest
from PIL import Image

from bgchange.s4_shadow import extract_shadow, make_fake_shadow, make_shadow
from bgchange.s4_shadow.fake_shadow import OPACITY


@pytest.fixture
def mask():
    m = np.zeros((200, 200), np.float32)
    m[50:100, 60:140] = 1.0
    return m


def test_fake_shadow_touches_the_subject(mask):
    """No gap: the pixel right under the subject's lowest row (99) is already shadow."""
    shadow = make_fake_shadow(mask)
    assert shadow[100, 100] > 0.2 * OPACITY


def test_fake_shadow_fades_out_below(mask):
    """10% of the subject's height (5 px) long, plus a little blur: gone 10 px below."""
    shadow = make_fake_shadow(mask)
    assert shadow[100, 100] > shadow[101, 100] > shadow[102, 100] > 0
    assert shadow[110, 100] == 0.0


def test_fake_shadow_only_under_the_subject(mask):
    shadow = make_fake_shadow(mask)
    assert shadow[30, 100] == 0.0  # above the subject
    assert shadow[101, 10] == pytest.approx(0.0, abs=0.01)  # beside it, no subject in that column


def test_fake_shadow_of_empty_mask_is_empty():
    assert not make_fake_shadow(np.zeros((20, 20), np.float32)).any()


@pytest.fixture
def photo():
    return Image.new("RGB", (200, 200), (230, 230, 230))


def test_none_gives_no_shadow(photo, mask):
    assert make_shadow("none", photo, mask) is None


def test_mix_is_the_darker_of_real_and_fake(photo, mask):
    expected = np.maximum(extract_shadow(photo, mask), make_fake_shadow(mask))
    assert np.array_equal(make_shadow("mix", photo, mask), expected)


def test_strength_scales_the_shadow(photo, mask):
    full = make_shadow("fake", photo, mask, strength=1.0)
    half = make_shadow("fake", photo, mask, strength=0.5)
    assert half == pytest.approx(full * 0.5)


def test_unknown_kind_is_refused(photo, mask):
    with pytest.raises(ValueError, match="real, fake, mix, none"):
        make_shadow("soft", photo, mask)
