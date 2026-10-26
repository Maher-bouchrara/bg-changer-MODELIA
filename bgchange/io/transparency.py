"""Step 3: separate any existing transparency from the colour channels.

If a user uploads a PNG that is already partly cut out, those transparent
pixels are background for certain. The compositing step later uses this as a
"hint" so they stay transparent even if the model disagrees.

Image modes that can carry transparency:
    RGBA / LA   colour (or grey) + a separate alpha channel
    P           palette image where one palette colour is marked transparent
    PA          palette + alpha channel
    RGBa / La   alpha already multiplied into the colours ("premultiplied")
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def split_alpha(image: Image.Image, notes: list[str]) -> tuple[Image.Image, np.ndarray | None]:
    """Split the image into (colour part, alpha hint).

    Args:
        image: the upright image, in any mode.
        notes: list that a sentence is appended to if transparency was found.

    Returns:
        (image without alpha, alpha as float32 (height, width) in [0, 1] or None)
    """
    # Palette images mark transparency in a special way. Turning them into
    # RGBA makes it a normal alpha channel that the code below understands.
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    elif image.mode in ("PA", "La", "RGBa"):
        image = image.convert("RGBA")

    # Only these two modes carry a separate alpha channel at this point.
    if image.mode not in ("RGBA", "LA"):
        return image, None

    # Alpha 0..255 -> 0.0..1.0 (0 = fully transparent, 1 = fully opaque).
    alpha = np.asarray(image.getchannel("A"), dtype=np.float32) / 255.0
    colour_only = image.convert("RGB" if image.mode == "RGBA" else "L")

    # A fully opaque alpha channel tells us nothing; drop it to keep things simple.
    if alpha.min() >= 1.0:
        return colour_only, None

    notes.append("kept the file's existing transparency as a hint")
    return colour_only, alpha
