"""Convert between sRGB pixel values and linear light.

Why: pixel values in a JPEG/PNG are NOT proportional to the amount of light.
They are "gamma encoded" (sRGB) so that dark tones get more of the 256 levels.

    sRGB value 128 (looks "half grey")  =  only ~21% of the light of white

Mixing two colours is a question of light: an edge pixel that is half subject,
half background receives half the light of each. So the mix must be done on
light values, then converted back:

    sRGB 0..255 --to_linear--> light 0..1 --mix--> light 0..1 --to_srgb--> sRGB 0..255

Mixing the raw sRGB values instead makes edges between a dark and a bright
colour too dark: a thin grey/dark outline around hair and soft edges.

The formulas are the official sRGB standard (IEC 61966-2-1): a short straight
line near black, then a power curve with exponent 2.4.
"""

from __future__ import annotations

import numpy as np


def srgb_to_linear(values: np.ndarray) -> np.ndarray:
    """sRGB values in [0, 1] -> linear light in [0, 1] (float32)."""
    v = np.asarray(values, dtype=np.float32)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(values: np.ndarray) -> np.ndarray:
    """Linear light in [0, 1] -> sRGB values in [0, 1] (float32)."""
    v = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)  # clip: power of a negative is NaN
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055).astype(np.float32)


def to_uint8(srgb: np.ndarray) -> np.ndarray:
    """sRGB values in [0, 1] -> 8-bit integers 0..255 (rounded, not truncated)."""
    return np.clip(np.round(srgb * 255.0), 0, 255).astype(np.uint8)
