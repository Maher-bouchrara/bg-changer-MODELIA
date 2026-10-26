"""bgchange: replace the background of a person/product photo with a solid colour.

The package is organised as a pipeline of small, independent stages so that each
one can be read, tested and swapped on its own:

    io/           -> load the image safely (EXIF rotation, colour modes, alpha);
                     one file per loading step
    color/        -> parse the user's hex colour ("#RGB", "#RRGGBB", "#RRGGBBAA")
    segmenters/   -> the AI models; each one only predicts an alpha matte
    matte.py      -> clean the subject's edge colours (remove the old background's tint)
    shadow.py     -> extract the subject's shadow from the original background
    composite.py  -> blend subject + shadow onto the new colour

The CLI (cli.py) and the HTTP API (api/) are thin wrappers around this core, so
both always produce identical results.
"""

__version__ = "0.1.0"
