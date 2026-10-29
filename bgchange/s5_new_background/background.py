"""make_background(): the new background, a plain layer of one colour.

    Color(255, 0, 102, 255)  ->  array (height, width, 4)
                                  [..., :3] the colour in linear light
                                  [..., 3]  its opacity (1 = solid)

Today it is a single colour, as the brief asks. Keeping it as its own layer
means a gradient or a background photo later only changes this file.
"""

from __future__ import annotations

import numpy as np

from bgchange.s2_read_color import Color
from bgchange.s5_new_background.linear_light import srgb_to_linear


def make_background(color: Color, size: tuple[int, int]) -> np.ndarray:
    """A (height, width, 4) float32 layer filled with `color`.

    Args:
        color: the parsed hex colour (its alpha = background opacity).
        size: (width, height), the size of the photo (Pillow order).

    Returns:
        float32 array (height, width, 4): RGB in linear light, then opacity, all in [0, 1].
    """
    width, height = size
    rgb = srgb_to_linear(np.array(color.rgb, dtype=np.float32) / 255.0)
    pixel = np.append(rgb, color.a / 255.0).astype(np.float32)
    # broadcast_to repeats one pixel without copying it into memory 4 x width x height times
    return np.broadcast_to(pixel, (height, width, 4))
