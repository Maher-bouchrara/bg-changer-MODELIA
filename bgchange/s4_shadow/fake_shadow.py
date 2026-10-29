"""make_fake_shadow(): a soft shadow computed from the mask alone.

No light, no photo: only the subject's outline. For every column of pixels:

    1. find the subject's lowest pixel in that column    (where it touches the floor)
    2. draw shadow from there downwards, darkest at the   (starts 2 px inside the
       touch point, fading to nothing                      subject: never a gap)
    3. blur it, so it looks soft

       |mug|
       |___|      <- lowest pixel of each column
       #####      <- shadow starts here, dark
        ...       <- and fades out

It always points straight down, so it looks less natural than a real shadow,
but it is clean on any background. Useful when the photo has no usable shadow.
"""

from __future__ import annotations

import cv2
import numpy as np

#: Length of the shadow below the subject, as a fraction of the subject's height.
LENGTH = 0.10

#: Blur, as a fraction of the photo's longer side.
BLUR = 0.012

#: Darkness where the shadow touches the subject (0 = invisible, 1 = black).
OPACITY = 0.5

# Overlap with the subject in pixels, so there is never a gap between the two.
_OVERLAP = 2


def make_fake_shadow(mask: np.ndarray) -> np.ndarray:
    """A soft shadow under the subject, from its mask.

    Args:
        mask: float array (height, width) in [0, 1] from the model.

    Returns:
        float32 (height, width) in [0, 1]: 0 = no shadow. All zeros if the mask is empty.
    """
    height, width = mask.shape
    subject = mask > 0.5
    if not subject.any():
        return np.zeros((height, width), np.float32)

    rows = np.nonzero(subject.any(axis=1))[0]
    length = max(2.0, LENGTH * (rows.max() - rows.min() + 1))

    # 1. Lowest subject pixel of every column: search from the bottom (subject[::-1]).
    has_subject = subject.any(axis=0)
    lowest = height - 1 - np.argmax(subject[::-1], axis=0)

    # 2. Distance below that pixel, for every pixel of the photo; shadow fades with it.
    below = np.arange(height, dtype=np.float32)[:, None] - (lowest[None, :] - _OVERLAP)
    shadow = np.clip(1.0 - below / length, 0.0, 1.0) * (below >= 0) * has_subject[None, :]
    shadow = shadow**1.5  # darkest right at the touch point, then fades faster

    # 3. Soften.
    k = max(3, round(BLUR * max(height, width)) | 1)
    return (cv2.GaussianBlur(shadow.astype(np.float32), (k, k), 0) * OPACITY).astype(np.float32)
