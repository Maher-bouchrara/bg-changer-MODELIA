"""Compositing: put the subject on the new background colour.

    photo (RGB) + mask (0..1, from the model) + Color  ->  final image

One file per job (see docs/06-compositing.md):

    linear_light.py   sRGB <-> linear light (blending is done in linear light)
    background.py     make_background(): a plain layer of the chosen colour
    foreground.py     estimate_foreground(): remove the old background from the edges
    blend.py          composite(): out = photo x mask + background x (1 - mask)
    save.py           default_output_path() and save_png()

Usage elsewhere in the code:

    from bgchange.s5_new_background import composite, save_png
    result = composite(loaded.rgb, alpha, parse_hex_color("#FF0066"))
"""

from bgchange.s5_new_background.background import make_background
from bgchange.s5_new_background.blend import composite
from bgchange.s5_new_background.foreground import estimate_foreground
from bgchange.s5_new_background.save import default_output_path, save_png

__all__ = ["composite", "default_output_path", "estimate_foreground", "make_background", "save_png"]
