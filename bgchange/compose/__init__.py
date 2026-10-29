"""Compositing: put the subject on the new background colour.

    photo (RGB) + mask (0..1, from the model) + Color  ->  final image

One file per job (see docs/06-compositing.md):

    linear_light.py   sRGB <-> linear light (blending is done in linear light)
    background.py     make_background(): a plain layer of the chosen colour
    blend.py          composite(): out = photo x mask + background x (1 - mask)
    save.py           default_output_path() and save_png()

Usage elsewhere in the code:

    from bgchange.compose import composite, save_png
    result = composite(loaded.rgb, alpha, parse_hex_color("#FF0066"))
"""

from bgchange.compose.background import make_background
from bgchange.compose.blend import composite
from bgchange.compose.save import default_output_path, save_png

__all__ = ["composite", "default_output_path", "make_background", "save_png"]
