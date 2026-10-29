"""Run several models on a folder of photos and put the results side by side.

For photos WITHOUT an answer key: there's no score, so you judge by eye.

Run:
    uv run python scripts/compare_models.py test_data/real-photos/images
    uv run python scripts/compare_models.py test_data/products/eye-test/images --model birefnet ben2

What it does:

    1. every model cuts out every photo     -> comparisons/<folder>/<model>/<photo>.png  (masks)
    2. one sheet per 10 photos              -> comparisons/<folder>/sheet_01.png, ...
         each row: photo | each model's cut-out on a pink background
    3. rows sorted by how much the models DISAGREE, most first:
         where all 5 agree there's little to see; where they disagree, look closely

Already-made masks are reused, so a second run only does what's missing.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bgchange.paths import PROJECT_ROOT
from bgchange.s1_load_photo import ImageLoadError, load_image
from bgchange.s3_ai_models import MODELS, get_segmenter, unload

OUT_ROOT = PROJECT_ROOT / "comparisons"
BACKGROUND = (255, 0, 102)  # pink: makes leftover background and missing parts easy to see
CELL_H = 200  # height of each picture in the sheet
ROWS_PER_SHEET = 10
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def predict_all(photos: list[Path], models: list[str], out_dir: Path, device: str) -> None:
    """Step 1: save every model's mask for every photo (skips masks that already exist)."""
    for model_name in models:
        todo = [p for p in photos if not (out_dir / model_name / f"{p.stem}.png").exists()]
        if not todo:
            print(f"[{model_name}] all {len(photos)} masks already done")
            continue
        print(f"[{model_name}] loading model, then {len(todo)} photos...")
        model = get_segmenter(model_name, device)
        (out_dir / model_name).mkdir(parents=True, exist_ok=True)
        for photo in todo:
            try:
                rgb = load_image(photo).rgb
            except ImageLoadError as error:
                print(f"  skipped {photo.name}: {error}")
                continue
            alpha = model.predict(rgb)
            Image.fromarray((alpha * 255).round().astype(np.uint8), mode="L").save(out_dir / model_name / f"{photo.stem}.png")
        unload()  # free the GPU before the next model


def disagreement(photo: Path, models: list[str], out_dir: Path) -> float:
    """Average difference between every pair of models' masks (0 = all identical)."""
    masks = [np.asarray(Image.open(out_dir / m / f"{photo.stem}.png").resize((256, 256)), np.float32) / 255 for m in models]
    return float(np.mean([np.abs(a - b).mean() for a, b in itertools.combinations(masks, 2)]))


def cutout(rgb: Image.Image, mask_path: Path) -> Image.Image:
    """The photo's subject placed on the pink background, using a model's mask."""
    background = Image.new("RGB", rgb.size, BACKGROUND)
    return Image.composite(rgb, background, Image.open(mask_path).convert("L"))


def build_sheets(photos: list[Path], models: list[str], out_dir: Path) -> list[Path]:
    """Step 2-3: side-by-side sheets, rows sorted by disagreement (most first)."""
    scored = sorted(((disagreement(p, models, out_dir), p) for p in photos), reverse=True)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    sheets = []
    for page, start in enumerate(range(0, len(scored), ROWS_PER_SHEET), start=1):
        rows = []
        for score, photo in scored[start : start + ROWS_PER_SHEET]:
            rgb = load_image(photo).rgb
            width = round(rgb.width * CELL_H / rgb.height)
            small = rgb.resize((width, CELL_H))
            cells = [small] + [cutout(rgb, out_dir / m / f"{photo.stem}.png").resize((width, CELL_H)) for m in models]
            rows.append((photo.stem, score, cells))

        col_w = max(c.width for _, _, cells in rows for c in cells)
        pad, header, label = 8, 30, 22
        sheet = Image.new(
            "RGB",
            (pad + (col_w + pad) * (len(models) + 1), header + len(rows) * (CELL_H + label + pad)),
            "white",
        )
        draw = ImageDraw.Draw(sheet)
        for c, title in enumerate(["photo", *models]):
            draw.text((pad + c * (col_w + pad), 6), title, fill="black", font=font)
        y = header
        for name, score, cells in rows:
            draw.text((pad, y), f"{name}   (models disagree: {score:.3f})", fill=(90, 90, 90), font=font)
            for c, cell in enumerate(cells):
                sheet.paste(cell, (pad + c * (col_w + pad), y + label))
            y += CELL_H + label + pad

        path = out_dir / f"sheet_{page:02d}.png"
        sheet.save(path)
        sheets.append(path)

    print("\nMost disagreement (look at these first):")
    for score, photo in scored[:5]:
        print(f"  {score:.3f}  {photo.name}")
    return sheets


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare models side by side on a folder of photos.")
    parser.add_argument("folder", type=Path, help="folder of photos")
    parser.add_argument("--model", nargs="+", default=["all"], help=f"'all' (default) or any of: {', '.join(MODELS)}")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    models = list(MODELS) if args.model == ["all"] else args.model
    unknown = [m for m in models if m not in MODELS]
    if unknown:
        parser.error(f"unknown model(s) {unknown}; choose from {list(MODELS)} or 'all'")

    photos = sorted(p for p in args.folder.iterdir() if p.suffix.lower() in EXTENSIONS)
    if not photos:
        sys.exit(f"No photos found in {args.folder}")

    # comparisons/<parent>-<folder>, e.g. comparisons/real-photos-images
    out_dir = OUT_ROOT / f"{args.folder.resolve().parent.name}-{args.folder.resolve().name}"
    print(f"{len(photos)} photos, {len(models)} models -> {out_dir}")

    predict_all(photos, models, out_dir, args.device)
    sheets = build_sheets(photos, models, out_dir)
    print(f"\nSheets: {', '.join(s.name for s in sheets)} in {out_dir}")


if __name__ == "__main__":
    main()
