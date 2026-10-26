"""Step 4: convert whatever colour format is left into plain 8-bit sRGB.

Decision order (the first that applies wins):

    16/32-bit greyscale?      -> bit_depth.py scales it to 8-bit first
    embedded ICC profile?     -> color_profile.py converts exactly to sRGB
    CMYK without profile?     -> Pillow's simple formula (colours approximate)
    greyscale / palette / ... -> plain conversion to RGB
    already RGB?              -> unchanged
"""

from __future__ import annotations

from PIL import Image

from bgchange.io.bit_depth import HIGH_BIT_DEPTH_MODES, to_8bit
from bgchange.io.color_profile import convert_with_icc_profile


def to_srgb(image: Image.Image, notes: list[str]) -> Image.Image:
    """Return the image as mode "RGB", 8 bits per channel, sRGB colours.

    Args:
        image: the image without alpha (see transparency.py), in any mode.
        notes: list that a sentence is appended to for every conversion.
    """
    # 16-bit and 32-bit greyscale must be scaled by hand first (see bit_depth.py).
    if image.mode in HIGH_BIT_DEPTH_MODES:
        image = to_8bit(image, notes)

    # An embedded ICC profile says "my numbers mean these exact colours".
    # When present and readable, it gives the most accurate conversion.
    icc = image.info.get("icc_profile")
    if icc:
        converted = convert_with_icc_profile(image, icc, notes)
        if converted is not None:
            return converted
        # None = the profile was broken; fall through to the plain conversion.

    if image.mode == "CMYK":
        # No profile to go on: use Pillow's simple formula. Colours are
        # approximate, but far better than failing.
        notes.append("converted CMYK to RGB (no colour profile, colours approximate)")
    elif image.mode == "L":
        notes.append("converted greyscale to RGB")
    elif image.mode != "RGB":
        notes.append(f"converted {image.mode} to RGB")

    return image.convert("RGB")
