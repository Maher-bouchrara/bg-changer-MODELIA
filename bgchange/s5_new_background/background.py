"""make_background(): the new background layer, a colour or a picture, with the shadow.

    Color(255, 0, 102, 255)  ->  array (height, width, 4)
                                  [..., :3] the colour in linear light
                                  [..., 3]  its opacity (1 = solid)

    a picture (PIL Image)    ->  the same array: the picture cut to the photo's
                                  size (background_image.py), opacity 1

With a shadow map (s4_shadow), each pixel gets a layer of black on top, as
opaque as the shadow is dark:

    shadow 0.4 on a solid colour        -> the colour with 40% less light
    shadow 0.4 on a picture             -> that pixel of the picture with 40%
                                           less light (its texture stays visible)
    shadow 0.4 on "#00000000" (cut-out) -> black at 40% opacity, so the
                                           shadow is kept in a transparent PNG too

The shadow map is measured on the original photo only, so it is the same
whatever the new background is.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from bgchange.s2_read_color import Color
from bgchange.s5_new_background.background_image import fit_background
from bgchange.s5_new_background.linear_light import srgb_to_linear


def make_background(
    background: Color | Image.Image, size: tuple[int, int], shadow: np.ndarray | None = None
) -> np.ndarray:
    """A (height, width, 4) float32 layer of `background`, darkened by `shadow`.

    Args:
        background: the parsed hex colour (its alpha = background opacity), or a
            picture, which is scaled and cropped to `size` and is always opaque.
        size: (width, height), the size of the photo (Pillow order).
        shadow: optional float array (height, width) in [0, 1], 1 = no light at all.

    Returns:
        float32 array (height, width, 4): RGB in linear light, then opacity, all in [0, 1].
    """
    width, height = size
    if isinstance(background, Image.Image):
        picture = np.asarray(fit_background(background, size), dtype=np.float32) / 255.0
        rgb = srgb_to_linear(picture)  # (h, w, 3)
        layer = np.concatenate([rgb, np.ones((height, width, 1), np.float32)], axis=-1)
    else:
        rgb = srgb_to_linear(np.array(background.rgb, dtype=np.float32) / 255.0)
        pixel = np.append(rgb, background.a / 255.0).astype(np.float32)
        # broadcast_to repeats one pixel without copying it into memory 4 x width x height times
        layer = np.broadcast_to(pixel, (height, width, 4))
    if shadow is None:
        return layer

    # Black at opacity `s` over the background ("over" operator, as in blend.py):
    #   opacity = s + background_opacity x (1 - s)
    #   colour  = colour x background_opacity x (1 - s) / opacity      (black adds no light)
    s = np.clip(shadow.astype(np.float32), 0.0, 1.0)[..., None]
    colour, bg_opacity = layer[..., :3], layer[..., 3:]
    opacity = s + bg_opacity * (1.0 - s)
    premultiplied = colour * bg_opacity * (1.0 - s)
    colour = np.divide(premultiplied, opacity, out=np.zeros_like(premultiplied), where=opacity > 0)
    return np.concatenate([colour, opacity], axis=-1)
