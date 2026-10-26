"""Tests for bgchange/color/rgba.py: the Color value."""

import pytest

from bgchange.color import Color


def test_alpha_defaults_to_opaque():
    color = Color(18, 52, 86)
    assert color.a == 255
    assert color.is_opaque


def test_rgb_property_drops_alpha():
    assert Color(255, 0, 102, 128).rgb == (255, 0, 102)


@pytest.mark.parametrize(
    ("color", "canonical"),
    [
        (Color(255, 0, 102), "#FF0066"),  # opaque: no alpha digits
        (Color(255, 0, 102, 128), "#FF006680"),  # transparent: alpha digits kept
        (Color(0, 0, 0, 0), "#00000000"),
    ],
)
def test_to_hex_gives_canonical_form(color, canonical):
    assert color.to_hex() == canonical


def test_color_cannot_be_changed_after_creation():
    """frozen=True: a parsed colour cannot be modified by accident later."""
    color = Color(1, 2, 3)
    with pytest.raises(AttributeError):
        color.r = 99  # type: ignore[misc]
