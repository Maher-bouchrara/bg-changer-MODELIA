"""Tests for bgchange/s2_read_color/hex_parser.py: parse_hex_color."""

import pytest

from bgchange.s2_read_color import Color, ColorParseError, parse_hex_color

# --- Accepted inputs ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#FF0066", Color(255, 0, 102)),  # standard
        ("#ff0066", Color(255, 0, 102)),  # lower case
        ("FF0066", Color(255, 0, 102)),  # without "#"
        ("  #FF0066  ", Color(255, 0, 102)),  # copy-paste spaces
        ("#F06", Color(255, 0, 102)),  # short form
        ("#FF006680", Color(255, 0, 102, 128)),  # with alpha
        ("#F068", Color(255, 0, 102, 136)),  # short form with alpha
        ("#000000", Color(0, 0, 0)),  # black
        ("#FFFFFF", Color(255, 255, 255)),  # white
        ("#00000000", Color(0, 0, 0, 0)),  # fully transparent -> plain cut-out
    ],
)
def test_valid_colours(text, expected):
    assert parse_hex_color(text) == expected


@pytest.mark.parametrize(("text", "canonical"), [("f06", "#FF0066"), ("#F06F", "#FF0066")])
def test_short_forms_round_trip_to_canonical_hex(text, canonical):
    """Short forms expand correctly; an explicit "F" alpha means opaque."""
    assert parse_hex_color(text).to_hex() == canonical


def test_four_digits_is_short_rgba_not_an_error():
    """Known trap: "#FF00" looks like a typo but is valid #RGBA (transparent yellow).

    It follows the CSS standard, so it is accepted; the README warns about it.
    """
    assert parse_hex_color("#FF00") == Color(255, 255, 0, 0)


# --- Rejected inputs ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "message_part"),
    [
        ("", "No colour given"),
        ("   ", "No colour given"),
        ("#", "No colour given"),
        ("red", "not a hex digit"),  # colour names are not accepted
        ("#GG0000", "not a hex digit"),
        ("#FF 0066", "not a hex digit"),  # space in the middle
        ("##FF0066", "not a hex digit"),  # only one "#" is stripped
        ("#FF", "expected 3, 4, 6 or 8"),
        ("#FF006", "expected 3, 4, 6 or 8"),
        ("#FF0066FF00", "expected 3, 4, 6 or 8"),
    ],
)
def test_invalid_colours_give_helpful_errors(text, message_part):
    with pytest.raises(ColorParseError, match=message_part) as error:
        parse_hex_color(text)
    # Every message tells the user what to type instead.
    assert "#RRGGBB" in str(error.value)


def test_non_string_input_is_rejected():
    with pytest.raises(ColorParseError, match="must be text"):
        parse_hex_color(0xFF0066)  # type: ignore[arg-type]
