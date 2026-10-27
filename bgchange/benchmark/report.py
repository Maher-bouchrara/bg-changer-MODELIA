"""Turn the saved scores into a summary table and contact sheets.

Reads every results/<model>/scores.csv that exists, so it works after one model
or after all five, and never needs the GPU.

    summary.md                   one table per subset, models as rows, best value in bold
    contact_sheet_<set>.png      the hardest photos: photo | answer key | each model's mask

The three subsets:

    Objects        all of DIS-VD (470)
    Product-like   the DIS-VD groups a shop would sell (see dataset.PRODUCT_LIKE_GROUPS)
    People         all of P3M-500-NP (500)
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from bgchange.benchmark.runner import RESULTS_DIR
from bgchange.paths import TEST_DATA_DIR

# (title, which rows belong to it)
SUBSETS = [
    ("Objects (DIS-VD)", lambda r: r["set"] == "dis-vd"),
    ("Product-like objects (DIS-VD subset)", lambda r: r["set"] == "dis-vd" and r["product_like"] == "True"),
    ("People (P3M-500-NP)", lambda r: r["set"] == "p3m-500-np"),
]

# (column title, csv field, True if higher is better)
METRICS = [("MAE ↓", "mae", False), ("F-measure ↑", "f_measure", True), ("Boundary F ↑", "boundary_f", True)]


def load_scores(results_dir: Path = RESULTS_DIR) -> dict[str, list[dict]]:
    """{model name: list of scores.csv rows} for every model that has results."""
    scores = {}
    for path in sorted(results_dir.glob("*/scores.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            scores[path.parent.name] = list(csv.DictReader(f))
    return scores


def _mean(rows: list[dict], field: str) -> float:
    values = [float(r[field]) for r in rows if r[field] not in ("", "nan")]
    values = [v for v in values if not math.isnan(v)]
    return statistics.fmean(values) if values else math.nan


def summary_markdown(scores: dict[str, list[dict]]) -> str:
    """The summary as Markdown tables (also printed to the console)."""
    lines = ["# Benchmark results", ""]
    for title, belongs in SUBSETS:
        per_model = {m: [r for r in rows if belongs(r)] for m, rows in scores.items()}
        per_model = {m: rows for m, rows in per_model.items() if rows}
        if not per_model:
            continue

        means = {m: {field: _mean(rows, field) for _, field, _ in METRICS} for m, rows in per_model.items()}
        best = {
            field: (max if higher else min)(v[field] for v in means.values())
            for _, field, higher in METRICS
        }

        lines += [f"## {title}", ""]
        lines.append("| Model | Photos | " + " | ".join(t for t, _, _ in METRICS) + " | Time per photo |")
        lines.append("|---|---|" + "---|" * len(METRICS) + "---|")
        for model, rows in per_model.items():
            cells = []
            for _, field, _ in METRICS:
                value = means[model][field]
                text = f"{value:.4f}"
                cells.append(f"**{text}**" if len(per_model) > 1 and value == best[field] else text)
            median_s = statistics.median(float(r["predict_s"]) for r in rows)
            lines.append(f"| {model} | {len(rows)} | " + " | ".join(cells) + f" | {median_s:.2f} s |")
        lines.append("")

    problems = [(m, r) for m, rows in scores.items() for r in rows if r.get("note")]
    if problems:
        lines += ["## Problems", ""] + [f"- {m}: {r['set']}/{r['image']}: {r['note']}" for m, r in problems] + [""]
    return "\n".join(lines)


def contact_sheet(
    scores: dict[str, list[dict]], set_name: str, count: int = 8, cell_height: int = 180, results_dir: Path = RESULTS_DIR
) -> Image.Image | None:
    """The `count` hardest photos of a set, one row each.

    Columns: photo | answer key | one column per model. "Hardest" = lowest
    boundary F averaged over the models, among photos every model has scored,
    so the sheet shows where the models struggle and how differently they fail.
    """
    models = list(scores)
    by_model = {m: {r["image"]: r for r in rows if r["set"] == set_name and not r.get("note")} for m, rows in scores.items()}
    common = set.intersection(*(set(d) for d in by_model.values())) if by_model else set()
    if not common:
        return None

    def difficulty(image: str) -> float:
        return statistics.fmean(float(by_model[m][image]["boundary_f"]) for m in models)

    hardest = sorted(common, key=difficulty)[:count]
    headers = ["photo", "answer key", *models]

    # Each cell is scaled to the same height; width follows the photo's shape.
    rows_of_cells = []
    for image in hardest:
        photo_path = next((TEST_DATA_DIR / set_name / "images").glob(f"{_glob_escape(image)}.*"))
        paths = [photo_path, TEST_DATA_DIR / set_name / "masks" / f"{image}.png"]
        paths += [results_dir / m / "masks" / set_name / f"{image}.png" for m in models]
        cells = [_thumbnail(p, cell_height) for p in paths]
        labels = ["", ""] + [f"BF {float(by_model[m][image]['boundary_f']):.2f}" for m in models]
        rows_of_cells.append((cells, labels))

    widths = [max(cells[c].width for cells, _ in rows_of_cells) for c in range(len(headers))]
    pad, header_h = 6, 22
    sheet = Image.new(
        "RGB",
        (sum(widths) + pad * (len(widths) + 1), header_h + len(rows_of_cells) * (cell_height + pad) + pad),
        (255, 255, 255),
    )
    draw = ImageDraw.Draw(sheet)

    x = pad
    for title, width in zip(headers, widths):
        draw.text((x, 5), title, fill=(0, 0, 0))
        x += width + pad

    y = header_h
    for cells, labels in rows_of_cells:
        x = pad
        for cell, label, width in zip(cells, labels, widths):
            sheet.paste(cell, (x, y))
            if label:  # model's boundary F on this photo, in a corner of its mask
                draw.rectangle((x, y, x + 52, y + 14), fill=(255, 255, 255))
                draw.text((x + 2, y + 1), label, fill=(200, 0, 0))
            x += width + pad
        y += cell_height + pad
    return sheet


def _thumbnail(path: Path, height: int) -> Image.Image:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        width = max(1, round(image.width * height / image.height))
        return image.resize((width, height), Image.BILINEAR)


def _glob_escape(name: str) -> str:
    """DIS-VD names contain '#', '[' etc.; escape the characters glob treats specially."""
    return "".join(f"[{c}]" if c in "[]*?" else c for c in name)


def write_report(results_dir: Path = RESULTS_DIR) -> str:
    """Write summary.md and the contact sheets; return the summary text."""
    scores = load_scores(results_dir)
    if not scores:
        return "No results yet."

    text = summary_markdown(scores)
    (results_dir / "summary.md").write_text(text, encoding="utf-8")
    for set_name in ("dis-vd", "p3m-500-np"):
        sheet = contact_sheet(scores, set_name, results_dir=results_dir)
        if sheet is not None:
            sheet.save(results_dir / f"contact_sheet_{set_name}.png")
    return text
