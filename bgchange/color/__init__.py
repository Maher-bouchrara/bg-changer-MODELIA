"""Colour handling: turn the text the user types ("#FF0066") into a Color.

One file per job (see README section 3.2):

    rgba.py         Color, the value every other stage uses (r, g, b, a)
    hex_parser.py   parse_hex_color(): "#FF0066" -> Color(255, 0, 102, 255)
    errors.py       ColorParseError, the one error type this package raises

Usage elsewhere in the code:

    from bgchange.color import parse_hex_color, Color, ColorParseError
"""

from bgchange.color.errors import ColorParseError
from bgchange.color.hex_parser import ACCEPTED_FORMATS, parse_hex_color
from bgchange.color.rgba import Color

__all__ = ["ACCEPTED_FORMATS", "Color", "ColorParseError", "parse_hex_color"]
