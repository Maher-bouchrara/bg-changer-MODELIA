"""Put the subject of a photo on a new background colour.

Run:
    uv run python scripts/change_background.py photo.jpg --color "#FF0066"
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" --model ben2
    uv run python scripts/change_background.py photo.jpg --color "#00000000"    # plain cut-out
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" -o result.png
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" --no-edge-cleanup
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" --shadow fake    # real, fake, mix, none
    uv run python scripts/change_background.py photo.jpg --color "#FF0066" --shadow-strength 0.5

The steps, each from its own package:

    1. load the photo      bgchange/s1_load_photo/        (EXIF rotation, CMYK, 16-bit...)
    2. read the colour     bgchange/s2_read_color/        ("#FF0066" -> Color)
    3. predict the mask    bgchange/s3_ai_models/         (BiRefNet by default)
    4. make the shadow     bgchange/s4_shadow/            (the photo's real one by default)
    5. clean edges, blend  bgchange/s5_new_background/    -> outputs/photo_on_FF0066.png

The colour is checked before the model is loaded, so a typo fails at once
instead of after several seconds of loading.
"""

import argparse
import time
from pathlib import Path

from bgchange.s1_load_photo import ImageLoadError, load_image
from bgchange.s2_read_color import ColorParseError, parse_hex_color
from bgchange.s3_ai_models import DEFAULT_MODEL, MODELS, get_segmenter
from bgchange.s4_shadow import SHADOW_KINDS, make_shadow
from bgchange.s5_new_background import composite, default_output_path, save_png


def strength(text: str) -> float:
    """--shadow-strength: a number from 0 (no shadow) to 1 (the shadow as computed)."""
    value = float(text)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {value}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", type=Path, help="input photo")
    parser.add_argument("--color", required=True, help='new background, e.g. "#FF0066" (quotes needed in PowerShell)')
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, choices=list(MODELS), help=f"which model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument("-o", "--output", type=Path, help="where to save the PNG")
    parser.add_argument(
        "--no-edge-cleanup",
        action="store_true",
        help="skip removing the old background from the edges (to compare); saves *_no-cleanup.png",
    )
    parser.add_argument(
        "--shadow",
        default=SHADOW_KINDS[0],
        choices=SHADOW_KINDS,
        help="real = the photo's own shadow (default), fake = computed from the outline, mix = both, none",
    )
    parser.add_argument(
        "--shadow-strength",
        type=strength,
        default=1.0,
        help="how dark the shadow is: 0 = none, 1 = as computed (default: 1)",
    )
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

    # 4: the shadow.
    start = time.perf_counter()
    shadow = make_shadow(args.shadow, loaded.rgb, mask, args.shadow_strength)
    print(f"shadow : {args.shadow}, strength {args.shadow_strength:g}, {time.perf_counter() - start:.2f}s")

    # 5: blend and save.
    start = time.perf_counter()
    result = composite(loaded.rgb, mask, color, clean_edges=not args.no_edge_cleanup, shadow=shadow)
    output = args.output or default_output_path(args.image, color)
    if not args.output:  # keep the versions side by side when comparing options
        if args.no_edge_cleanup:
            output = output.with_stem(output.stem + "_no-cleanup")
        if args.shadow != SHADOW_KINDS[0]:
            output = output.with_stem(f"{output.stem}_shadow-{args.shadow}")
    output = save_png(result, output)
    print(f"blend  : {time.perf_counter() - start:.2f}s")
    print(f"saved  : {output}")


if __name__ == "__main__":
    main()
