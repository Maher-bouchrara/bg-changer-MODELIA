"""make_shadow(): the shadow the user asked for, by name.

    "real"   the photo's own shadow, near the bottom of the subject  (shadow_map.py)
    "fake"   a soft shadow computed from the mask                    (fake_shadow.py)
    "mix"    both: at each pixel, the darker of the two
    "none"   no shadow

Then `strength` scales it: 0 = no shadow, 1 = as computed.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from bgchange.s4_shadow.fake_shadow import make_fake_shadow
from bgchange.s4_shadow.shadow_map import extract_shadow

#: The accepted names, default first.
SHADOW_KINDS = ("real", "fake", "mix", "none")


def make_shadow(kind: str, photo: Image.Image, mask: np.ndarray, strength: float = 1.0) -> np.ndarray | None:
    """The shadow map for `kind`, or None for "none".

    Raises:
        ValueError: if `kind` is not one of SHADOW_KINDS.
    """
    if kind not in SHADOW_KINDS:
        raise ValueError(f"shadow must be one of {', '.join(SHADOW_KINDS)}, got {kind!r}")
    if kind == "none":
        return None
    if kind == "real":
        shadow = extract_shadow(photo, mask)
    elif kind == "fake":
        shadow = make_fake_shadow(mask)
    else:  # mix
        shadow = np.maximum(extract_shadow(photo, mask), make_fake_shadow(mask))
    return shadow * strength
