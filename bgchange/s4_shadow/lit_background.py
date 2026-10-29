r"""find_lit_background(): how bright the floor would be WITHOUT the shadow.

A shadow is the floor receiving less light. To measure it we need to know how
bright that same spot of floor would be if nothing blocked the light.

The idea: a shadow is always DARKER than the lit floor around it. So for each
spot, take the brightest floor pixels nearby:

    brightness of the floor      _____      ________
    (one row of pixels)               \____/            <- shadow
    lit floor guess              ___________________     <- brightest nearby

    1. ignore the subject (it is not floor)
    2. "brightest nearby" = a max filter over a big window (1/4 of the photo),
       so it reaches the lit floor even from the middle of a large shadow
    3. smooth it, so the guess changes gently across the photo (real lighting
       does: e.g. a studio background that is brighter in the middle)

Done on a small copy of the photo (256 px): the lighting changes slowly, so
detail is not needed, and it takes a few milliseconds instead of seconds.
"""

from __future__ import annotations

import cv2
import numpy as np

#: Size of the small working copy, in pixels (longer side).
WORK_SIZE = 256

#: Window of the "brightest nearby" search, as a fraction of the photo's longer side.
WINDOW = 0.25


def find_lit_background(brightness: np.ndarray, floor: np.ndarray) -> np.ndarray:
    """Guess the brightness of the floor without shadows.

    Args:
        brightness: float32 (height, width), the photo's brightness in linear light, [0, 1].
        floor: bool (height, width), True where the pixel is floor (not the subject).

    Returns:
        float32 (height, width): the lit-floor brightness at every pixel, full size.
    """
    height, width = brightness.shape
    scale = WORK_SIZE / max(height, width)
    small_size = (max(1, round(width * scale)), max(1, round(height * scale)))  # cv2 wants (w, h)

    # 1. Small copy; the subject is set to 0 so it never wins the "brightest" contest.
    small = cv2.resize(brightness, small_size, interpolation=cv2.INTER_AREA)
    small_floor = cv2.resize(floor.astype(np.float32), small_size, interpolation=cv2.INTER_AREA) > 0.5
    small = np.where(small_floor, small, 0.0).astype(np.float32)

    # 2. Brightest floor pixel in the window around each pixel (a "max filter").
    k = max(3, round(WORK_SIZE * WINDOW) | 1)  # odd size, so the window has a centre
    lit = cv2.dilate(small, np.ones((k, k), np.uint8))

    # Spots with no floor in the window at all (deep inside a big subject): use the
    # brightest floor pixel of the whole photo instead of 0.
    brightest = float(small.max())
    lit = np.where(lit > 0, lit, brightest)

    # 3. Smooth, then back to full size.
    lit = cv2.blur(lit, (k, k))
    return cv2.resize(lit, (width, height), interpolation=cv2.INTER_LINEAR).astype(np.float32)
