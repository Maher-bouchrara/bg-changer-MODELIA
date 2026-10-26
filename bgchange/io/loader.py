"""load_image(): the entry point that runs every input-handling step in order.

    file / bytes
      1. open + validate     (open_file.py)      clear error if not an image or too big
      2. fix EXIF rotation   (exif_rotation.py)  phone photos stored sideways become upright
      3. split off alpha     (transparency.py)   keep existing transparency as a "hint"
      4. normalise colour    (color_mode.py)     16-bit, CMYK, palette, grey, ICC -> 8-bit sRGB
      = LoadedImage(rgb, alpha_hint, notes)

Why step 3 comes before step 4: colour-profile conversion works on the colour
channels only, so the transparency channel is taken out first and handled on its
own.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from bgchange.io.color_mode import to_srgb
from bgchange.io.exif_rotation import fix_exif_rotation
from bgchange.io.open_file import MAX_PIXELS, ImageSource, open_image
from bgchange.io.transparency import split_alpha


@dataclass(frozen=True)
class LoadedImage:
    """The result of loading: everything later stages need, in one object."""

    #: The photo itself: mode "RGB", 8 bits per channel, sRGB colours, upright.
    rgb: Image.Image

    #: Transparency that was already in the file (e.g. a PNG cut-out), as a
    #: float32 array (height, width) in [0, 1]. None when the file had no
    #: transparency, or when it was fully opaque (so it carries no information).
    alpha_hint: np.ndarray | None = None

    #: Human-readable list of every fix that was applied, e.g.
    #: ["rotated upright using EXIF orientation 6", "converted CMYK to RGB"].
    #: Printed by the CLI and returned by the API so nothing happens silently.
    notes: list[str] = field(default_factory=list)

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) of the upright image."""
        return self.rgb.size


def load_image(source: ImageSource, max_pixels: int = MAX_PIXELS) -> LoadedImage:
    """Open an image from a path, bytes or file object and normalise it.

    Args:
        source: path, raw bytes (what the API receives), or a binary file object.
        max_pixels: refuse images with more pixels than this.

    Returns:
        A LoadedImage whose `rgb` is always upright 8-bit sRGB.

    Raises:
        ImageLoadError: missing file, not an image, corrupted, or too large.
    """
    # Each step appends a sentence here when it changes something.
    notes: list[str] = []

    image = open_image(source, max_pixels, notes)  # step 1
    image = fix_exif_rotation(image, notes)  # step 2
    image, alpha = split_alpha(image, notes)  # step 3
    rgb = to_srgb(image, notes)  # step 4

    return LoadedImage(rgb=rgb, alpha_hint=alpha, notes=notes)
