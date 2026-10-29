"""composite(): put the subject on the new background.

For every pixel, the mask says how much of it is subject (1), background (0),
or a mix (soft edge, hair):

    out = photo x mask + background x (1 - mask)

    mask = 1    -> the photo's pixel, unchanged
    mask = 0    -> the new colour
    mask = 0.3  -> 30% photo + 70% new colour (soft edge)

The mix is done in linear light (see linear_light.py) so soft edges keep the
right brightness.

Transparent colour (e.g. "#FF006680", or "#00000000" for a plain cut-out):
the background only covers part of the pixel, so the output gets an alpha
channel too ("over" operator):

    out_alpha = mask + bg_alpha x (1 - mask)
    out_rgb   = (photo x mask + bg_rgb x bg_alpha x (1 - mask)) / out_alpha

With a solid colour (bg_alpha = 1) this is exactly the first formula and
out_alpha is 1 everywhere, so the result is a plain RGB image.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from bgchange.s2_read_color import Color
from bgchange.s5_new_background.background import make_background
from bgchange.s5_new_background.linear_light import linear_to_srgb, srgb_to_linear, to_uint8


def composite(photo: Image.Image, mask: np.ndarray, color: Color) -> Image.Image:
    """Place the subject of `photo` on a background of `color`.

    Args:
        photo: the upright 8-bit RGB photo (LoadedImage.rgb).
        mask: float array (height, width) in [0, 1] from the model, same size as `photo`.
        color: the new background colour.

    Returns:
        Same size as `photo`. Mode "RGB" when the colour is solid, "RGBA" when
        it has transparency.

    Raises:
        ValueError: if the photo is not RGB or the mask has the wrong shape.
    """
    if photo.mode != "RGB":
        raise ValueError(f"photo must be mode RGB, got {photo.mode}")
    if mask.shape != (photo.height, photo.width):
        raise ValueError(f"mask shape {mask.shape} does not match photo size {photo.height}x{photo.width}")

    # 1. Everything to float, in linear light. [..., None] turns the mask from
    #    (h, w) into (h, w, 1) so it multiplies all 3 colour channels at once.
    fg = srgb_to_linear(np.asarray(photo, dtype=np.float32) / 255.0)
    a = np.clip(mask.astype(np.float32), 0.0, 1.0)[..., None]
    bg = make_background(color, photo.size)
    bg_rgb, bg_a = bg[..., :3], bg[..., 3:]

    # 2. The mix ("over" operator, see the module docstring).
    out_a = a + bg_a * (1.0 - a)
    premultiplied = fg * a + bg_rgb * bg_a * (1.0 - a)

    # 3. Solid colour: out_a is 1 everywhere, so no division and no alpha channel.
    if color.is_opaque:
        return Image.fromarray(to_uint8(linear_to_srgb(premultiplied)), mode="RGB")

    # Transparent colour: divide back out the coverage. Where out_a is 0 the pixel
    # is invisible anyway, so its colour is set to 0 instead of dividing by 0.
    rgb = np.divide(premultiplied, out_a, out=np.zeros_like(premultiplied), where=out_a > 0)
    rgba = np.concatenate([to_uint8(linear_to_srgb(rgb)), to_uint8(out_a)], axis=-1)
    return Image.fromarray(rgba, mode="RGBA")
