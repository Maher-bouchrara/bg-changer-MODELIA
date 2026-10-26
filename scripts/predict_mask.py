"""Run BiRefNet on one photo and save its alpha matte as a greyscale PNG.

Run:  uv run python scripts/predict_mask.py photo.jpg -o outputs/photo_mask.png

This is a temporary script used to check the model before the real CLI exists.
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
from bgchange.segmenters import BiRefNetSegmenter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", type=Path, help="input photo")
    parser.add_argument("-o", "--output", type=Path, help="where to save the mask PNG")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    output = args.output or Path("outputs") / f"{args.image.stem}_mask.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        loaded = load_image(args.image)
    except ImageLoadError as error:
        raise SystemExit(f"error  : {error}") from None
    image = loaded.rgb
    print(f"image  : {args.image} ({image.width}x{image.height})")
    for note in loaded.notes:  # every fix the loader applied, e.g. EXIF rotation
        print(f"  note : {note}")

    start = time.perf_counter()
    segmenter = BiRefNetSegmenter(device=args.device)
    print(f"loaded : {segmenter.name} on {segmenter.device} in {time.perf_counter() - start:.1f}s")

    # The first call includes one-off GPU warm-up, so time a second call too.
    for run in ("first", "second"):
        start = time.perf_counter()
        alpha = segmenter.predict(image)
        if segmenter.device.type == "cuda":
            torch.cuda.synchronize()
        print(f"predict: {run} call {time.perf_counter() - start:.2f}s")

    if segmenter.device.type == "cuda":
        print(f"VRAM   : peak {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")

    Image.fromarray((alpha * 255).round().astype(np.uint8), mode="L").save(output)
    print(f"saved  : {output}")


if __name__ == "__main__":
    main()
