"""Smoke test: does every model load and produce a sensible mask?

Run:  uv run python scripts/check_models.py            # all models
      uv run python scripts/check_models.py ben2       # only some

This is NOT the benchmark (that needs real photos with ground-truth masks).
It only checks that each model runs, and measures its speed and memory, on two
generated images:

    disc    a red disc on grey: the disc must come out as subject (~1),
            the corner as background (~0)
    blank   plain grey, no subject at all: a good model predicts ~0 everywhere
            instead of inventing a subject
"""

from __future__ import annotations

import argparse
import sys
import time

import torch
from PIL import Image, ImageDraw

from bgchange.s3_ai_models import MODELS, get_segmenter, unload


def _disc_image() -> Image.Image:
    image = Image.new("RGB", (800, 600), (200, 200, 200))
    ImageDraw.Draw(image).ellipse((250, 150, 550, 450), fill=(220, 30, 30))
    return image


def _sync() -> None:
    """Wait for the GPU to finish, so timings measure the real work.

    GPU calls return immediately and run in the background; without this the
    timer would stop before the prediction is actually done.
    """
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def check(name: str, device: str) -> dict:
    """Load one model, run both test images, return the measurements."""
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    start = time.perf_counter()
    model = get_segmenter(name, device)
    load_s = time.perf_counter() - start

    disc = _disc_image()
    model.predict(disc)  # warm-up: the first GPU call includes one-off setup
    _sync()
    start = time.perf_counter()
    alpha = model.predict(disc)
    _sync()
    predict_s = time.perf_counter() - start

    blank = model.predict(Image.new("RGB", (400, 300), (128, 128, 128)))
    vram_gb = torch.cuda.max_memory_allocated() / 1024**3 if torch.cuda.is_available() else 0.0

    centre, corner = float(alpha[300, 400]), float(alpha[10, 10])
    return {
        "load_s": load_s,
        "predict_s": predict_s,
        "vram_gb": vram_gb,
        "centre": centre,
        "corner": corner,
        "blank_max": float(blank.max()),
        "blank_mean": float(blank.mean()),
        # A mask is "OK" if it is a real number, the subject is clearly in and
        # the background clearly out.
        "ok": alpha.shape == (600, 800) and centre > 0.9 and corner < 0.1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the segmentation models.")
    parser.add_argument("names", nargs="*", help=f"models to check (default: all): {', '.join(MODELS)}")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    unknown = [n for n in args.names if n not in MODELS]
    if unknown:
        parser.error(f"unknown model(s) {unknown}; choose from {list(MODELS)}")

    header = f"{'model':18} {'mask':5} {'load':>7} {'predict':>8} {'VRAM':>8}  {'blank max':>9} {'blank mean':>10}"
    print(header)
    print("-" * len(header))

    failed = False
    for name in args.names or MODELS:
        try:
            r = check(name, args.device)
        except Exception as error:  # report and continue with the next model
            print(f"{name:18} ERROR  {type(error).__name__}: {error}")
            failed = True
            continue
        finally:
            unload()

        failed |= not r["ok"]
        print(
            f"{name:18} {'OK' if r['ok'] else 'BAD':5} {r['load_s']:6.1f}s {r['predict_s']:7.2f}s "
            f"{r['vram_gb']:6.2f}GB  {r['blank_max']:9.3f} {r['blank_mean']:10.3f}"
        )

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
