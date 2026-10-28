"""Run one segmentation model on one photo and save its mask as a greyscale PNG.

Run:
    uv run python scripts/predict_mask.py photo.jpg                   # default model (BiRefNet)
    uv run python scripts/predict_mask.py photo.jpg --model ben2      # any of the 5 models
    uv run python scripts/predict_mask.py photo.jpg -o my_mask.png    # choose the output file

The mask goes to outputs/<photo>_<model>_mask.png by default (white = subject,
black = background), so masks from different models never overwrite each other.

It loads the photo with the same loader as the real pipeline (bgchange/io/),
so EXIF rotation, CMYK, 16-bit files etc. are handled here too.
"""

import argparse
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from bgchange.io import ImageLoadError, load_image
from bgchange.segmenters import DEFAULT_MODEL, MODELS, get_segmenter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", type=Path, help="input photo")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, choices=list(MODELS), help=f"which model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument("-o", "--output", type=Path, help="where to save the mask PNG")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    output = args.output or Path("outputs") / f"{args.image.stem}_{args.model}_mask.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        loaded = load_image(args.image)
    except ImageLoadError as error:
        raise SystemExit(f"error  : {error}") from None
    image = loaded.rgb
    print(f"image  : {args.image} ({image.width}x{image.height})")
    for note in loaded.notes:  # every fix the loader applied, e.g. EXIF rotation
        print(f"  note : {note}")

    if not MODELS[args.model].commercial_use:
        print(f"warning: {args.model} is licensed {MODELS[args.model].license} (non-commercial use only)")

    start = time.perf_counter()
    segmenter = get_segmenter(args.model, args.device)
    print(f"model  : {args.model} loaded in {time.perf_counter() - start:.1f}s")

    start = time.perf_counter()
    alpha = segmenter.predict(image)
    if torch.cuda.is_available() and args.device != "cpu":
        torch.cuda.synchronize()  # wait for the GPU so the time is real
    print(f"predict: {time.perf_counter() - start:.2f}s (first run includes GPU warm-up)")

    Image.fromarray((alpha * 255).round().astype(np.uint8), mode="L").save(output)
    print(f"saved  : {output}")


if __name__ == "__main__":
    main()
