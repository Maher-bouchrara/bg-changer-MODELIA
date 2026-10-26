"""Convert an image from its embedded colour profile (ICC) to standard sRGB.

A colour profile says what the numbers in the file *mean*. The same numbers
(255, 0, 0) are a different red in different profiles:

    iPhone photos   Display-P3   (wider colours than sRGB)
    print files     CMYK profiles (ink, not light)
    the web / us    sRGB         (what the model and the output assume)

Reading a P3 photo as if it were sRGB makes colours look washed out, so the
numbers are converted using the profile when the file has one.
"""

from __future__ import annotations

import io

from PIL import Image, ImageCms


def convert_with_icc_profile(image: Image.Image, icc: bytes, notes: list[str]) -> Image.Image | None:
    """Convert `image` from the profile `icc` to sRGB, as mode "RGB".

    Args:
        image: the image without alpha.
        icc: the raw bytes of the embedded profile (image.info["icc_profile"]).
        notes: list that a sentence is appended to.

    Returns:
        The converted image, or None if the profile is broken or unsupported.
        The caller then falls back to a plain conversion instead of rejecting a
        photo that is otherwise fine.
    """
    try:
        source_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        srgb_profile = ImageCms.createProfile("sRGB")
        converted = ImageCms.profileToProfile(
            image, source_profile, srgb_profile, outputMode="RGB"
        )
    except (ImageCms.PyCMSError, OSError, ValueError):
        notes.append("ignored an unreadable colour profile")
        return None

    profile_name = ImageCms.getProfileDescription(source_profile).strip() or "embedded profile"
    notes.append(f"converted colours from '{profile_name}' to sRGB")
    return converted
