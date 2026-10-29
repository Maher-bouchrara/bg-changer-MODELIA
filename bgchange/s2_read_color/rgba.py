"""Color: one 8-bit RGBA colour, the value the rest of the pipeline uses.

    Color(r=255, g=0, b=102, a=255)
          red    green  blue   alpha (opacity of the new background)

Each channel is an integer from 0 to 255.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    """An 8-bit RGBA colour.

    `a` is the background's opacity: 255 = solid colour (the normal case),
    0 = fully transparent (the output becomes a plain cut-out PNG).

    frozen=True makes it immutable: once parsed, a colour cannot be changed by
    accident somewhere else in the pipeline.
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
