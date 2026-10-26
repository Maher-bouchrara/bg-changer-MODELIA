"""Step 2: rotate phone photos upright using their EXIF orientation tag.

Phones usually save the pixels in the sensor's orientation and add an EXIF tag
saying "rotate 90 degrees when displaying". Photo viewers obey the tag; raw
pixel code (like our model) does not. Without this step a portrait photo would
be processed and returned lying on its side.

    stored pixels (40 x 20)              what people see (20 x 40)
    +----------------+                   +--------+
    | person lying   |   EXIF tag 6 -->  | person |
    | on their side  |                   | upright|
    +----------------+                   |        |
                                         +--------+
"""

from __future__ import annotations

from PIL import Image, ImageOps

# EXIF tag number that stores the camera orientation.
# 1 = already upright; 2-8 = some combination of rotation and mirroring.
_EXIF_ORIENTATION_TAG = 0x0112


def fix_exif_rotation(image: Image.Image, notes: list[str]) -> Image.Image:
    """Return the image with its pixels physically rotated/flipped upright.

    Args:
        image: the opened image.
        notes: list that a sentence is appended to if the image was rotated.
    """
    orientation = image.getexif().get(_EXIF_ORIENTATION_TAG, 1)
    if orientation == 1:
        return image  # already upright, nothing to do

    # exif_transpose applies the rotation/flip to the pixels and removes the
    # tag, so the result is upright no matter which viewer opens it later.
    upright = ImageOps.exif_transpose(image)
    notes.append(f"rotated upright using EXIF orientation {orientation}")
    return upright
