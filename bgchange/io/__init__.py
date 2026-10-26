"""Input handling: load any image file into one predictable format.

Every later stage (the model, the shadow code, the compositing) assumes a plain,
upright, 8-bit sRGB image. This package is the single place that guarantees it.

One file per step, in the order they run (see README section 3.1):

    loader.py          load_image(): runs the steps below, returns a LoadedImage
    open_file.py       1. open + validate (not an image? truncated? too big?)
    exif_rotation.py   2. rotate phone photos upright
    transparency.py    3. keep any existing transparency as an "alpha hint"
    color_mode.py      4. convert to 8-bit sRGB, using:
      bit_depth.py          - 16/32-bit greyscale -> 8-bit (scaled, not clipped)
      color_profile.py      - embedded ICC profiles (iPhone P3, CMYK) -> sRGB
    errors.py          ImageLoadError, the one error type this package raises

Usage elsewhere in the code:

    from bgchange.io import load_image, ImageLoadError

Note on the name: this package is `bgchange.io`. It does not clash with
Python's built-in `io` module because it is always imported by its full name.
"""

from bgchange.io.errors import ImageLoadError
from bgchange.io.loader import LoadedImage, load_image
from bgchange.io.open_file import MAX_PIXELS

__all__ = ["ImageLoadError", "LoadedImage", "load_image", "MAX_PIXELS"]
