"""Parse the background colour the user types, e.g. "#FF0066".

The pipeline (see README section 3.2):

    "  #ff0066 "
      1. trim spaces              -> "#ff0066"
      2. strip the optional "#"   -> "ff0066"
      3. check length + digits    -> must be 3, 4, 6 or 8 hex digits
      4. expand the short forms   -> "F06" becomes "FF0066"
      5. convert pairs to numbers -> Color(r=255, g=0, b=102, a=255)

Accepted formats:

    #RGB        short form          #F06       -> (255,   0, 102)
    #RGBA       short + alpha       #F068      -> (255,   0, 102, 136)
    #RRGGBB     standard            #FF0066    -> (255,   0, 102)
    #RRGGBBAA   standard + alpha    #FF006680  -> (255,   0, 102, 128)

Known trap: a truncated "#FF00" is not an error. It is valid #RGBA, meaning
fully transparent yellow. This follows the CSS standard, so it is kept, and the
README warns about it.

The "#" is optional and letters can be upper or lower case. Colour names such
as "red" are deliberately not accepted: the brief asks for hex, and one strict
format is easier to test and to explain in an error message.
"""

from __future__ import annotations

from dataclasses import dataclass

# Shown in every error message so the user knows exactly what to type instead.
_ACCEPTED_FORMATS = "#RGB, #RGBA, #RRGGBB or #RRGGBBAA (e.g. #FF0066)"

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class ColorParseError(ValueError):
    """Raised when the colour text is not a valid hex colour.

    Like ImageLoadError, the message is written for the end user and shown
    as-is by the CLI and the API.
    """


@dataclass(frozen=True)
class Color:
    """An 8-bit RGBA colour. Each channel is an integer from 0 to 255.

    `a` is the background's opacity: 255 = solid colour (the normal case),
    0 = fully transparent (the output becomes a plain cut-out PNG).
    """

    r: int
    g: int
    b: int
    a: int = 255

    @property
    def rgb(self) -> tuple[int, int, int]:
        """The colour without alpha, e.g. (255, 0, 102)."""
        return (self.r, self.g, self.b)

    @property
    def is_opaque(self) -> bool:
        """True when the background is solid (no transparency in the output)."""
        return self.a == 255

    def to_hex(self) -> str:
        """Canonical form: "#RRGGBB" if opaque, "#RRGGBBAA" otherwise."""
        text = f"#{self.r:02X}{self.g:02X}{self.b:02X}"
        return text if self.is_opaque else f"{text}{self.a:02X}"


def parse_hex_color(text: str) -> Color:
    """Turn a hex colour string into a Color.

    Args:
        text: e.g. "#FF0066", "ff0066", "#F06" or "#FF006680".

    Returns:
        The parsed Color (alpha is 255 when not given).

    Raises:
        ColorParseError: with a message that names the accepted formats.
    """
    if not isinstance(text, str):
        raise ColorParseError(f"Colour must be text such as \"#FF0066\", got {type(text).__name__}.")

    # Steps 1 + 2: tolerate copy-paste spaces, and a missing "#".
    digits = text.strip().removeprefix("#")

    if not digits:
        raise ColorParseError(f"No colour given. Use {_ACCEPTED_FORMATS}.")

    # Step 3a: every character must be a hex digit (0-9, a-f).
    bad = sorted({ch for ch in digits if ch not in _HEX_DIGITS})
    if bad:
        raise ColorParseError(
            f"\"{text}\" is not a hex colour: {', '.join(repr(ch) for ch in bad)} "
            f"is not a hex digit. Use {_ACCEPTED_FORMATS}."
        )

    # Step 3b: only these lengths have a meaning.
    if len(digits) not in (3, 4, 6, 8):
        raise ColorParseError(
            f"\"{text}\" has {len(digits)} hex digits; expected 3, 4, 6 or 8. "
            f"Use {_ACCEPTED_FORMATS}."
        )

    # Step 4: short forms repeat each digit: "F06" -> "FF0066", "F068" -> "FF006688".
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits)

    # Step 5: read the digits two at a time as base-16 numbers (00..FF = 0..255).
    channels = [int(digits[i : i + 2], 16) for i in range(0, len(digits), 2)]
    if len(channels) == 3:
        channels.append(255)  # no alpha given -> solid colour

    return Color(*channels)
