"""extract_shadow(): the photo's REAL shadow, from 0 (none) to 1 (no light at all).

    shadow = 1 - (photo brightness / lit floor brightness)

    lit floor 0.9, photo 0.9   ->  shadow 0     (fully lit)
    lit floor 0.9, photo 0.54  ->  shadow 0.4   (40% less light)

Then three filters, so that only the subject's own shadow is kept:

    1. only the floor       the subject itself is never "shadow" (1 - mask)
    2. only at the bottom   a shadow touches the floor where the subject stands:
                            its lowest 15% (feet, base of a product). The map
                            fades to 0 at 5% of the photo size from there, so
                            dark things elsewhere in a busy scene are ignored
    3. ignore tiny dips     the floor's texture and JPEG noise make a few %
                            of darkness everywhere: below 5% is set to 0,
                            and the map is smoothed a little

Brightness is measured in linear light (= amount of light), like the blend.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from bgchange.s4_shadow.lit_background import find_lit_background
from bgchange.s5_new_background.linear_light import srgb_to_linear

#: The part of the subject that touches the floor: its lowest 15%.
BOTTOM_PART = 0.15

#: How far from that part a shadow can reach, as a fraction of the photo's longer side.
SEARCH_DISTANCE = 0.05

#: Darkness below this is texture or noise, not shadow.
NOISE_FLOOR = 0.05

#: Smoothing of the final map, as a fraction of the photo's longer side.
SMOOTHING = 0.005

# Pixels with mask below this count as floor when guessing the lit floor.
_FLOOR_MASK = 0.1

# Share of red, green and blue in perceived brightness (standard Rec. 709 weights).
_LUMINANCE = np.array([0.2126, 0.7152, 0.0722], np.float32)


def extract_shadow(photo: Image.Image, mask: np.ndarray) -> np.ndarray:
    """The real shadow on the floor around the bottom of the subject.

    Args:
        photo: the upright 8-bit RGB photo (LoadedImage.rgb).
        mask: float array (height, width) in [0, 1] from the model.

    Returns:
        float32 (height, width) in [0, 1]: 0 = no shadow, 1 = no light at all.
        All zeros if the mask is empty.
    """
    mask = np.clip(mask.astype(np.float32), 0.0, 1.0)
    subject = mask > 0.5
    if not subject.any():
        return np.zeros_like(mask)

    rgb = srgb_to_linear(np.asarray(photo, dtype=np.float32) / 255.0)
    brightness = rgb @ _LUMINANCE  # (h, w): one brightness value per pixel
    longer_side = max(mask.shape)

    # The main formula: how much darker than the lit floor each pixel is.
    lit = find_lit_background(brightness, mask < _FLOOR_MASK)
    shadow = 1.0 - brightness / np.maximum(lit, 1e-4)

    # Filter 3 first (on the raw map): ignore tiny dips, then rescale so 5% -> 0 and 100% -> 100%.
    shadow = np.clip((shadow - NOISE_FLOOR) / (1.0 - NOISE_FLOOR), 0.0, 1.0)

    # Filter 1: only the floor. Where the subject covers the pixel, no shadow.
    shadow *= 1.0 - mask

    # Filter 2: only near the bottom of the subject.
    shadow *= _near_bottom(subject, longer_side)

    # Smooth a little: real shadows are soft, noise is grainy.
    k = max(3, round(longer_side * SMOOTHING) | 1)
    return cv2.GaussianBlur(shadow.astype(np.float32), (k, k), 0)


def _near_bottom(subject: np.ndarray, longer_side: int) -> np.ndarray:
    """1 at the lowest part of the subject, fading to 0 at SEARCH_DISTANCE from it."""
    rows = np.nonzero(subject.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    base = subject.copy()
    base[: int(bottom - BOTTOM_PART * (bottom - top))] = False  # keep only the lowest 15%
    # distanceTransform: for every pixel, the distance in pixels to the nearest
    # base pixel (the pixels where its input is 0).
    distance = cv2.distanceTransform((~base).astype(np.uint8), cv2.DIST_L2, 5)
    return np.clip(1.0 - distance / (SEARCH_DISTANCE * longer_side), 0.0, 1.0)
