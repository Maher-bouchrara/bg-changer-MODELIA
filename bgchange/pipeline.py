"""change_background(): the whole tool in one function.

    photo + "#FF0066"   ->  the subject on #FF0066, with clean edges and a shadow
    photo + beach.jpg   ->  the subject on that picture (background_image=...)

It runs the 5 steps in order, each from its own folder:

    s1_load_photo       open the photo safely
    s2_read_color       "#FF0066" -> Color
    s3_ai_models        the AI predicts the mask
    s4_shadow           real / fake / mix / none
    s5_new_background   clean the edges, blend, (the caller saves)

The CLI (cli.py) and the API (api/) both call this function and nothing else,
so they always give exactly the same result for the same inputs.

The colour (or the background picture) is read BEFORE the model is loaded,
so a typo or a broken file fails at once.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from PIL import Image

from bgchange.s1_load_photo import load_image
from bgchange.s1_load_photo.open_file import ImageSource
from bgchange.s2_read_color import Color, parse_hex_color
from bgchange.s3_ai_models import DEFAULT_MODEL, get_segmenter
from bgchange.s4_shadow import SHADOW_KINDS, make_shadow
from bgchange.s5_new_background import composite


@dataclass
class Result:
    """Everything the CLI prints and the API returns."""

    #: The final image: RGB for a solid colour, RGBA for a transparent one.
    image: Image.Image
    #: The colour that was used, e.g. Color(255, 0, 102, 255); None with a background picture.
    color: Color | None
    #: Fixes the loader applied, e.g. ["rotated upright using EXIF orientation 6"].
    notes: list[str] = field(default_factory=list)
    #: Seconds spent in each part: {"load_model": ..., "mask": ..., "shadow": ..., "blend": ...}.
    timings: dict[str, float] = field(default_factory=dict)


def change_background(
    source: ImageSource,
    color: str | Color | None = None,
    *,
    background_image: ImageSource | None = None,
    model: str = DEFAULT_MODEL,
    shadow: str = SHADOW_KINDS[0],
    shadow_strength: float = 1.0,
    clean_edges: bool = True,
    device: str = "auto",
) -> Result:
    """Put the subject of a photo on a new background: a colour or a picture.

    Give exactly one of `color` and `background_image`.

    Args:
        source: path, raw bytes (an upload) or a binary file object.
        color: hex text such as "#FF0066", or an already parsed Color.
        background_image: a picture to put behind the subject instead of a colour
            (path, bytes or file object, loaded like the photo); it is scaled and
            cropped to the photo's size.
        model: which AI model makes the mask (default: BiRefNet).
        shadow: "real" (default), "fake", "mix" or "none".
        shadow_strength: 0 = no shadow, 1 = as computed.
        clean_edges: remove the old background's colour from the edges.
        device: "auto", "cuda" or "cpu".

    Returns:
        A Result with the image, the colour, the loader's notes and the timings.

    Raises:
        ColorParseError: the colour is not valid hex.
        ImageLoadError: the photo or background picture is missing, not an image, or too large.
        ValueError: unknown model or shadow, strength outside 0..1, or not
            exactly one of color / background_image.
    """
    if shadow not in SHADOW_KINDS:
        raise ValueError(f"shadow must be one of {', '.join(SHADOW_KINDS)}, got {shadow!r}")
    if not 0.0 <= shadow_strength <= 1.0:
        raise ValueError(f"shadow_strength must be between 0 and 1, got {shadow_strength}")

    if (color is None) == (background_image is None):
        raise ValueError("give exactly one background: a colour or a background picture")

    # 1 + 2: the cheap checks first.
    notes: list[str] = []
    if background_image is None:
        color = parse_hex_color(color) if isinstance(color, str) else color
        background: Color | Image.Image = color
    else:
        # Same safe loader as the photo (rotation, CMYK, size limit); its notes are kept too.
        bg = load_image(background_image)
        background = bg.rgb
        notes += [f"background: {note}" for note in bg.notes]
    loaded = load_image(source)
    notes = loaded.notes + notes
    timings: dict[str, float] = {}

    # 3: the mask. get_segmenter() keeps the model loaded, so this is instant
    # after the first call (the API relies on that).
    start = time.perf_counter()
    segmenter = get_segmenter(model, device)
    timings["load_model"] = time.perf_counter() - start

    start = time.perf_counter()
    mask = segmenter.predict(loaded.rgb)
    timings["mask"] = time.perf_counter() - start

    # 4: the shadow.
    start = time.perf_counter()
    shadow_map = make_shadow(shadow, loaded.rgb, mask, shadow_strength)
    timings["shadow"] = time.perf_counter() - start

    # 5: edges + blend.
    start = time.perf_counter()
    image = composite(loaded.rgb, mask, background, clean_edges=clean_edges, shadow=shadow_map)
    timings["blend"] = time.perf_counter() - start

    return Result(image=image, color=color, notes=notes, timings=timings)
