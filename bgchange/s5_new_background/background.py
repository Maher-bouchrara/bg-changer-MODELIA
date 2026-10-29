"""make_background(): the new background, a plain layer of one colour, with the shadow.

    Color(255, 0, 102, 255)  ->  array (height, width, 4)
                                  [..., :3] the colour in linear light
                                  [..., 3]  its opacity (1 = solid)

With a shadow map (s4_shadow), each pixel gets a layer of black on top, as
opaque as the shadow is dark:

    shadow 0.4 on a solid colour        -> the colour with 40% less light
    shadow 0.4 on "#00000000" (cut-out) -> black at 40% opacity, so the
                                           shadow is kept in a transparent PNG too

Today it is a single colour, as the brief asks. Keeping it as its own layer
means a gradient or a background photo later only changes this file.
"""

from __future__ import annotations

import numpy as np

from bgchange.s2_read_color import Color
from bgchange.s5_new_background.linear_light import srgb_to_linear


def make_background(color: Color, size: tuple[int, int], shadow: np.ndarray | None = None) -> np.ndarray:
    """A (height, width, 4) float32 layer filled with `color`, darkened by `shadow`.

    Args:
        color: the parsed hex colour (its alpha = background opacity).
        size: (width, height), the size of the photo (Pillow order).
        shadow: optional float array (height, width) in [0, 1], 1 = no light at all.

    Returns:
        float32 array (height, width, 4): RGB in linear light, then opacity, all in [0, 1].
    """
    width, height = size
    rgb = srgb_to_linear(np.array(color.rgb, dtype=np.float32) / 255.0)
    pixel = np.append(rgb, color.a / 255.0).astype(np.float32)
    # broadcast_to repeats one pixel without copying it into memory 4 x width x height times
    layer = np.broadcast_to(pixel, (height, width, 4))
    if shadow is None:
        return layer

    # Black at opacity `s` over the colour ("over" operator, as in blend.py):
    #   opacity = s + colour_opacity x (1 - s)
    #   colour  = colour x colour_opacity x (1 - s) / opacity      (black adds no light)
    s = np.clip(shadow.astype(np.float32), 0.0, 1.0)[..., None]
    opacity = s + pixel[3] * (1.0 - s)
    premultiplied = pixel[:3] * pixel[3] * (1.0 - s)
    colour = np.divide(premultiplied, opacity, out=np.zeros_like(premultiplied), where=opacity > 0)
    return np.concatenate([colour, opacity], axis=-1)
