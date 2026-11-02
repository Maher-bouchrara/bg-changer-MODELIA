"""fit_background(): a picture used as the new background, cut to the photo's size.

The background picture rarely has the photo's size or shape. It is scaled to
COVER the photo (no empty bands), keeping its proportions (never stretched),
then the overflow is cut off equally on both sides ("cover" + centre crop,
like CSS object-fit: cover):

    photo 1600 x 1200 (4:3), background 3000 x 1000 (3:1)

    1. scale so both sides are at least the photo's:  x 1.2  -> 3600 x 1200
    2. cut the extra width, half on each side:         -> 1600 x 1200

        +--------------------------------------+
        |######|                      |########|   # = cut off
        |######|   kept: 1600 x 1200  |########|
        +--------------------------------------+

The picture is loaded with the same safe loader as the photo (s1_load_photo),
so phone rotation, CMYK, 16-bit and huge files are handled the same way. Any
transparency in the background picture is ignored: a background is opaque.
"""

from __future__ import annotations

from PIL import Image


def fit_background(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale `image` to cover `size`, keep its proportions, crop the centre.

    Args:
        image: the background picture (any mode; converted to RGB).
        size: (width, height) of the photo, Pillow order.

    Returns:
        An RGB image of exactly `size`.
    """
    width, height = size
    image = image.convert("RGB")
    # 1. The scale that makes BOTH sides at least the photo's (the larger of the two ratios).
    scale = max(width / image.width, height / image.height)
    scaled = (max(width, round(image.width * scale)), max(height, round(image.height * scale)))
    # LANCZOS: the best quality for both shrinking and enlarging.
    image = image.resize(scaled, Image.LANCZOS)
    # 2. Cut the overflow, half on each side.
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height))
