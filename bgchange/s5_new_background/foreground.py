"""estimate_foreground(): remove the old background's colour from the edges.

The problem: an edge pixel (hair, soft outline) was already a mix when the
camera took the photo:

    photo = subject x mask + old_background x (1 - mask)

The model tells us HOW MUCH is subject (the mask), but not the subject's own
colour. Mixing that pixel with the new colour as it is keeps some of the old
background in it: a faint halo.

The fix ("blur fusion", Forte & Pitie 2021, https://arxiv.org/abs/2006.14970):
guess the pure subject colour of every pixel from its neighbours.

    1. subject colour nearby    = average of the pixels around that ARE subject
                                  (a blur where each pixel counts as much as its mask)
    2. old background nearby    = the same with (1 - mask): pixels that are background
    3. correct the pixel        = subject colour nearby
                                  + mask x (what the photo has - what 1 and 2 predict)
                                  the last part keeps the detail of each hair strand

    Done twice: a big window (90 px) for a rough guess, then a small one (6 px)
    that refines it using the first round's answer.

Pixels with mask = 1 come out unchanged; only the edges really change.
Works on linear light, like the blend, because the camera mixes light.
"""

from __future__ import annotations

import cv2
import numpy as np

#: Window sizes in pixels, from the paper: rough guess first, then detail.
BIG_WINDOW = 90
SMALL_WINDOW = 6

# Added to every division so a pixel with no subject (or no background) nearby
# divides by a tiny number instead of zero.
_EPSILON = 1e-5


def estimate_foreground(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """The subject's own colour at every pixel, without the old background.

    Args:
        image: float32 (height, width, 3), the photo in linear light, [0, 1].
        mask: float32 (height, width), the model's mask, [0, 1].

    Returns:
        float32 (height, width, 3) in [0, 1], same as `image` where mask = 1.
    """
    a = mask.astype(np.float32)[..., None]  # (h, w, 1): multiplies the 3 channels at once
    image = image.astype(np.float32)

    # Round 1: big window. Both guesses start from the photo itself.
    fg, bg = _blur_fusion(image, image, image, a, BIG_WINDOW)
    # Round 2: small window, starting from round 1's subject and background guesses.
    fg, _ = _blur_fusion(image, fg, bg, a, SMALL_WINDOW)
    return fg


def _blur_fusion(
    image: np.ndarray, fg: np.ndarray, bg: np.ndarray, a: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """One round of steps 1-3 (see the module docstring). Returns (subject, background) guesses."""

    def blur(x: np.ndarray) -> np.ndarray:
        # Box blur: the average over a window x window square. cv2 drops the
        # last axis when it has size 1, so it is put back.
        out = cv2.blur(x, (window, window))
        return out[..., None] if out.ndim == 2 else out

    blurred_a = blur(a)
    # 1. Average subject colour nearby, each pixel weighted by how much it is subject.
    fg_nearby = blur(fg * a) / (blurred_a + _EPSILON)
    # 2. Average old background colour nearby, weighted by how much it is background.
    bg_nearby = blur(bg * (1 - a)) / ((1 - blurred_a) + _EPSILON)
    # 3. Start from the nearby subject colour, add back what the photo shows that
    #    steps 1 and 2 do not explain.
    fg_new = fg_nearby + a * (image - a * fg_nearby - (1 - a) * bg_nearby)
    return np.clip(fg_new, 0.0, 1.0), bg_nearby
