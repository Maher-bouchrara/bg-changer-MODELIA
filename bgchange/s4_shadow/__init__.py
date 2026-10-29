"""Shadow: give the subject a shadow on the new background.

    photo + mask  ->  shadow map (height, width), 0 = no shadow, 1 = no light at all

The new colour is then darkened by that amount (s5_new_background/background.py).
Only the DARKNESS is used, never the old floor's colour or texture.

One file per job (see docs/06c-shadows.md):

    lit_background.py   find_lit_background(): how bright the floor would be without the shadow
    shadow_map.py       extract_shadow(): the photo's REAL shadow, near the bottom of the subject
    fake_shadow.py      make_fake_shadow(): a soft shadow computed from the mask alone
    choose.py           make_shadow(): "real", "fake", "mix" or "none", times the strength

Usage elsewhere in the code:

    from bgchange.s4_shadow import make_shadow
    shadow = make_shadow("real", loaded.rgb, mask, strength=1.0)
"""

from bgchange.s4_shadow.choose import SHADOW_KINDS, make_shadow
from bgchange.s4_shadow.fake_shadow import make_fake_shadow
from bgchange.s4_shadow.lit_background import find_lit_background
from bgchange.s4_shadow.shadow_map import extract_shadow

__all__ = ["SHADOW_KINDS", "extract_shadow", "find_lit_background", "make_fake_shadow", "make_shadow"]
