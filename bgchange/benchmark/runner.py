"""The benchmark loop: for each test photo, predict a mask and score it.

    for each photo:
        1. load the photo        (bgchange.io, the same loader as the real tool)
        2. model predicts        (GPU) -> saved to results/<model>/masks/<set>/<name>.png
        3. compare with answer   (metrics.py) -> one row appended to results/<model>/scores.csv

Rows are written as soon as each photo is done, so an interrupted run loses
nothing: running the same command again skips the photos already in
scores.csv and continues where it stopped.
"""

from __future__ import annotations

import csv
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image

from bgchange.benchmark.dataset import Sample, list_samples
from bgchange.benchmark.metrics import boundary_f, f_measure, mae
from bgchange.io import load_image
from bgchange.paths import PROJECT_ROOT

#: Where results go (gitignored): results/<model>/scores.csv and masks/.
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"

#: Columns of scores.csv, one row per photo.
FIELDS = [
    "set", "image", "group", "category", "product_like",
    "mae", "f_measure", "boundary_f", "predict_s", "width", "height", "note",
]  # fmt: skip


def run(
    model_name: str,
    set_names: list[str],
    limit: int | None = None,
    device: str = "auto",
    results_dir: Path = RESULTS_DIR,
    log: Callable[[str], None] = print,
) -> Path:
    """Benchmark one model on the given test sets. Returns the scores.csv path.

    Args:
        model_name: a name from the registry, e.g. "birefnet".
        set_names: e.g. ["dis-vd", "p3m-500-np"].
        limit: at most this many photos per set (spread evenly), for quick runs.
        device: "auto", "cuda" or "cpu".
        results_dir: parent folder of the per-model results.
        log: where progress lines go (print by default).
    """
    import torch

    from bgchange.segmenters import get_segmenter

    out_dir = results_dir / model_name
    scores_path = out_dir / "scores.csv"
    done = _already_scored(scores_path)

    samples = [s for name in set_names for s in list_samples(name, limit) if (s.set_name, s.name) not in done]
    if not samples:
        log(f"[{model_name}] nothing to do: all photos already scored in {scores_path}")
        return scores_path

    log(f"[{model_name}] loading model...")
    model = get_segmenter(model_name, device)
    on_gpu = torch.cuda.is_available() and device != "cpu"

    def sync() -> None:
        # GPU work runs in the background; wait for it so the timer is honest.
        if on_gpu:
            torch.cuda.synchronize()

    # Warm-up on a small dummy image: the very first GPU call includes one-off
    # setup that would otherwise make the first photo look slow.
    model.predict(Image.new("RGB", (64, 64)))
    sync()

    out_dir.mkdir(parents=True, exist_ok=True)
    is_new_file = not scores_path.exists()
    started = time.perf_counter()

    with scores_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()

        for index, sample in enumerate(samples, start=1):
            writer.writerow(_score_one(model, sample, out_dir, sync))
            f.flush()  # on disk right away: an interrupted run loses nothing

            if index % 25 == 0 or index == len(samples):
                elapsed = time.perf_counter() - started
                remaining = elapsed / index * (len(samples) - index)
                log(f"[{model_name}] {index}/{len(samples)} photos, ~{remaining / 60:.0f} min left")

    return scores_path


def _score_one(model, sample: Sample, out_dir: Path, sync: Callable[[], None]) -> dict:
    """Steps 1-3 for one photo. Returns its scores.csv row."""
    row = {
        "set": sample.set_name,
        "image": sample.name,
        "group": sample.group,
        "category": sample.category,
        "product_like": sample.product_like,
    }

    # 1. Load the photo with the real loader (EXIF rotation, colour modes...).
    photo = load_image(sample.image_path).rgb

    # 2. Predict, timing only the model itself.
    sync()
    start = time.perf_counter()
    alpha = model.predict(photo)
    sync()
    row["predict_s"] = round(time.perf_counter() - start, 4)

    mask_path = out_dir / "masks" / sample.set_name / f"{sample.name}.png"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((alpha * 255).round().astype(np.uint8), mode="L").save(mask_path)

    # 3. Compare with the answer key (stored as 0-255 greyscale).
    truth = np.asarray(Image.open(sample.mask_path).convert("L"), dtype=np.float32) / 255.0
    row["width"], row["height"] = truth.shape[1], truth.shape[0]

    if alpha.shape != truth.shape:
        # Should not happen; recorded instead of crashing, and visible in the report.
        row["note"] = f"size mismatch: prediction {alpha.shape}, answer key {truth.shape}"
        row["mae"] = row["f_measure"] = row["boundary_f"] = math.nan
        return row

    row["mae"] = round(mae(alpha, truth), 5)
    row["f_measure"] = round(f_measure(alpha, truth), 5)
    row["boundary_f"] = round(boundary_f(alpha, truth), 5)
    row["note"] = ""
    return row


def _already_scored(scores_path: Path) -> set[tuple[str, str]]:
    """(set, image) pairs already in scores.csv, so a re-run can skip them."""
    if not scores_path.exists():
        return set()
    with scores_path.open(newline="", encoding="utf-8") as f:
        return {(row["set"], row["image"]) for row in csv.DictReader(f)}
