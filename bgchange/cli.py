"""The `bgchange` command: put the subject of a photo on a new background colour.

Run (from the project folder, after `uv sync`):

    uv run bgchange photo.jpg --color "#FF0066"
    uv run bgchange photo.jpg --color "#FF0066" --shadow mix --shadow-strength 0.7
    uv run bgchange photo.jpg --color "#00000000"                 # transparent cut-out
    uv run bgchange photo.jpg --color "#FF0066" -o result.png
    uv run bgchange photo.jpg --color "#FF0066" --model ben2
    uv run bgchange --help

The result goes to outputs/<photo>_on_<HEX>.png unless -o is given.

This file only reads the options and prints; the work is done by
change_background() in pipeline.py, the same function the API uses.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from bgchange.pipeline import change_background
from bgchange.s1_load_photo import ImageLoadError
from bgchange.s2_read_color import ColorParseError
from bgchange.s3_ai_models import DEFAULT_MODEL, MODELS
from bgchange.s4_shadow import SHADOW_KINDS
from bgchange.s5_new_background import default_output_path, save_png


def _strength(text: str) -> float:
    """--shadow-strength: a number from 0 (no shadow) to 1 (the shadow as computed)."""
    value = float(text)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    """All the command's options, with the help text shown by --help."""
    parser = argparse.ArgumentParser(
        prog="bgchange",
        description="Put the subject of a photo (person or product) on a new background colour.",
    )
    parser.add_argument("image", type=Path, help="input photo (JPEG, PNG, WebP, ...)")
    parser.add_argument(
        "--color", required=True, help='new background as hex, e.g. "#FF0066" (keep the quotes in PowerShell)'
    )
    parser.add_argument(
        "--shadow",
        default=SHADOW_KINDS[0],
        choices=SHADOW_KINDS,
        help="real = the photo's own shadow (default), fake = computed from the outline, mix = both, none",
    )
    parser.add_argument(
        "--shadow-strength", type=_strength, default=1.0, help="how dark the shadow is: 0 = none, 1 = as computed (default)"
    )
    parser.add_argument("-o", "--output", type=Path, help="where to save the PNG (default: outputs/...)")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, choices=list(MODELS), help=f"which AI model makes the mask (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--no-edge-cleanup",
        action="store_true",
        help="skip removing the old background from the edges (to compare)",
    )
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"], help="default: GPU if available")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point of the `bgchange` command. `argv` is for tests; None reads the real command line."""
    args = build_parser().parse_args(argv)

    if not MODELS[args.model].commercial_use:
        print(f"warning: {args.model} is licensed {MODELS[args.model].license} (non-commercial use only)")

    try:
        result = change_background(
            args.image,
            args.color,
            model=args.model,
            shadow=args.shadow,
            shadow_strength=args.shadow_strength,
            clean_edges=not args.no_edge_cleanup,
            device=args.device,
        )
    except (ColorParseError, ImageLoadError, FileNotFoundError) as error:
        # Expected mistakes (bad colour, bad file, model not downloaded): one clear line, no traceback.
        raise SystemExit(f"error  : {error}") from None

    # Default name: outputs/photo_on_FF0066.png; non-default options are added to
    # it, so versions made to compare sit side by side instead of overwriting.
    output = args.output
    if output is None:
        output = default_output_path(args.image, result.color)
        if args.no_edge_cleanup:
            output = output.with_stem(output.stem + "_no-cleanup")
        if args.shadow != SHADOW_KINDS[0]:
            output = output.with_stem(f"{output.stem}_shadow-{args.shadow}")
    output = save_png(result.image, output)

    t = result.timings
    print(f"image  : {args.image} ({result.image.width}x{result.image.height})")
    for note in result.notes:  # every fix the loader applied, e.g. EXIF rotation
        print(f"  note : {note}")
    print(f"colour : {result.color.to_hex()}")
    print(f"model  : {args.model}, loaded in {t['load_model']:.1f}s, mask in {t['mask']:.2f}s")
    print(f"shadow : {args.shadow}, strength {args.shadow_strength:g}, {t['shadow']:.2f}s")
    print(f"blend  : {t['blend']:.2f}s")
    print(f"saved  : {output}")


if __name__ == "__main__":
    main()
