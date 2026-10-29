"""Put the subject of a photo on a new background colour.

Run:
    uv run python scripts/change_background.py photo.jpg --color "#FF0066"
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" --model ben2
    uv run python scripts/change_background.py photo.jpg --color "#00000000"    # plain cut-out
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" -o result.png

The steps, each from its own package:

    1. load the photo          bgchange/io/          (EXIF rotation, CMYK, 16-bit...)
    2. parse the colour        bgchange/color/       ("#FF0066" -> Color)
    3. predict the mask        bgchange/segmenters/  (BiRefNet by default)
    4. blend + save            bgchange/compose/     -> outputs/photo_on_FF0066.png

The colour is checked before the model is loaded, so a typo fails at once
instead of after several seconds of loading.
"""

import argparse
import time
from pathlib import Path

from bgchange.color import ColorParseError, parse_hex_color
from bgchange.compose import composite, default_output_path, save_png
from bgchange.io import ImageLoadError, load_image
from bgchange.segmenters import DEFAULT_MODEL, MODELS, get_segmenter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", type=Path, help="input photo")
    parser.add_argument("--color", required=True, help='new background, e.g. "#FF0066" (quotes needed in PowerShell)')
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, choices=list(MODELS), help=f"which model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument("-o", "--output", type=Path, help="where to save the PNG")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    # 1 + 2: cheap checks first.
    try:
        color = parse_hex_color(args.color)
        loaded = load_image(args.image)
    except (ColorParseError, ImageLoadError) as error:
        raise SystemExit(f"error  : {error}") from None
    print(f"image  : {args.image} ({loaded.rgb.width}x{loaded.rgb.height})")
    for note in loaded.notes:  # every fix the loader applied, e.g. EXIF rotation
        print(f"  note : {note}")
    print(f"colour : {color.to_hex()}")

    if not MODELS[args.model].commercial_use:
        print(f"warning: {args.model} is licensed {MODELS[args.model].license} (non-commercial use only)")

    # 3: the model.
    start = time.perf_counter()
    segmenter = get_segmenter(args.model, args.device)
    print(f"model  : {args.model} loaded in {time.perf_counter() - start:.1f}s")

    start = time.perf_counter()
    mask = segmenter.predict(loaded.rgb)
    print(f"mask   : {time.perf_counter() - start:.2f}s (first run includes GPU warm-up)")

    # 4: blend and save.
    start = time.perf_counter()
    result = composite(loaded.rgb, mask, color)
    output = save_png(result, args.output or default_output_path(args.image, color))
    print(f"blend  : {time.perf_counter() - start:.2f}s")
    print(f"saved  : {output}")


if __name__ == "__main__":
    main()
