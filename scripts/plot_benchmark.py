"""Draw the benchmark results as a dot chart: docs/images/benchmark_results.png.

Run:  uv run python scripts/plot_benchmark.py

Reads benchmarks/results/<model>/scores.csv (made by run_benchmark.py), so the
picture always matches the saved results. Drawn with Pillow only (no plotting
library needed).

Why a dot chart and not bars: the scores sit between 0.70 and 1.00. Bars must
start at 0, which would make 0.92 and 0.99 look almost the same; dots can use
a zoomed axis honestly because nothing is "filled up" from zero.

Encoding:
    filled dot  = fair score (the model did NOT train on this test set)
    hollow dot  = the model trained, or is claimed to have trained, on this test set
                  (score not trustworthy), with a short label saying so
"""

from __future__ import annotations

import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bgchange.benchmark.report import SUBSETS, load_scores
from bgchange.paths import PROJECT_ROOT

OUTPUT = PROJECT_ROOT / "docs" / "images" / "benchmark_results.png"

# Same order in every panel so a model is always on the same row.
MODELS = ["birefnet", "birefnet-matting", "ben2", "rmbg-2.0", "inspyrenet"]

# (subset title, model) -> why its score on that subset is not trustworthy.
# Sources: InSPyReNet's model zoo (Plus_Ultra lists DIS-VD) and BEN2's README
# ("RMBG 2.0 did not preserve the DIS 5k validation dataset"). See docs/05-benchmark.md.
CONTAMINATED = {
    ("Objects (DIS-VD)", "inspyrenet"): "trained on DIS-VD",
    ("Product-like objects (DIS-VD subset)", "inspyrenet"): "trained on DIS-VD",
    ("Objects (DIS-VD)", "rmbg-2.0"): "maybe trained on it",
    ("Product-like objects (DIS-VD subset)", "rmbg-2.0"): "maybe trained on it",
}

PANEL_TITLES = {
    "Objects (DIS-VD)": "Objects (470)",
    "Product-like objects (DIS-VD subset)": "Product-like objects (248)",
    "People (P3M-500-NP)": "People (500)",
}

# Reference light palette (dataviz skill): one series hue + neutral ink.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"

X_MIN, X_MAX = 0.65, 1.00
SCALE = 2  # draw at 2x for crisp text, then halve


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["segoeuib.ttf" if bold else "segoeui.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            if (folder / name).exists():
                return ImageFont.truetype(str(folder / name), size * SCALE)
    return ImageFont.load_default()


def main() -> None:
    scores = load_scores()
    missing = [m for m in MODELS if m not in scores]
    if missing:
        raise SystemExit(f"No results for {missing}. Run scripts/run_benchmark.py first.")

    # Mean boundary F per (subset, model).
    means = {}
    for title, belongs in SUBSETS:
        for model in MODELS:
            values = [float(r["boundary_f"]) for r in scores[model] if belongs(r) and r["boundary_f"] not in ("", "nan")]
            means[(title, model)] = statistics.fmean(values)

    s = SCALE
    width, height = 1400 * s, 520 * s
    image = Image.new("RGB", (width, height), SURFACE)
    draw = ImageDraw.Draw(image)

    draw.text((40 * s, 24 * s), "Edge accuracy (boundary F) of the 5 models", font=_font(22, True), fill=INK)
    draw.text(
        (40 * s, 58 * s),
        "Higher is better. Filled dot = fair test. Hollow dot = the model trained (or may have trained) on that test set.",
        font=_font(14),
        fill=INK_2,
    )

    label_w = 150 * s
    left = 40 * s + label_w
    panel_gap = 40 * s
    panel_w = (width - left - 40 * s - 2 * panel_gap) // 3
    top, row_h = 140 * s, 64 * s

    def x_of(value: float, x0: int) -> int:
        return x0 + round((value - X_MIN) / (X_MAX - X_MIN) * panel_w)

    # Model names once, on the left.
    for i, model in enumerate(MODELS):
        y = top + i * row_h + row_h // 2
        draw.text((40 * s, y), model, font=_font(15), fill=INK, anchor="lm")

    for p, (title, _) in enumerate(SUBSETS):
        x0 = left + p * (panel_w + panel_gap)
        draw.text((x0, top - 34 * s), PANEL_TITLES[title], font=_font(16, True), fill=INK)

        # Recessive grid + tick labels.
        for tick in (0.70, 0.80, 0.90, 1.00):
            x = x_of(tick, x0)
            draw.line((x, top, x, top + len(MODELS) * row_h), fill=GRID, width=s)
            draw.text((x, top + len(MODELS) * row_h + 10 * s), f"{tick:.2f}", font=_font(12), fill=MUTED, anchor="mt")
        draw.line((x0, top + len(MODELS) * row_h, x0 + panel_w, top + len(MODELS) * row_h), fill=AXIS, width=s)

        # Best FAIR score of the panel gets a bold value label.
        fair = {m: means[(title, m)] for m in MODELS if (title, m) not in CONTAMINATED}
        best = max(fair, key=fair.get)

        for i, model in enumerate(MODELS):
            y = top + i * row_h + row_h // 2
            value = means[(title, model)]
            x = x_of(value, x0)
            r = 7 * s
            note = CONTAMINATED.get((title, model))
            if note:
                draw.ellipse((x - r, y - r, x + r, y + r), outline=MUTED, width=3 * s, fill=SURFACE)
                draw.text((x - r - 8 * s, y), f"{value:.3f}", font=_font(12), fill=MUTED, anchor="rm")
                draw.text((x - r - 8 * s, y + 16 * s), note, font=_font(11), fill=MUTED, anchor="rm")
            else:
                draw.ellipse((x - r, y - r, x + r, y + r), fill=BLUE, outline=SURFACE, width=2 * s)
                bold = model == best
                draw.text(
                    (x - r - 8 * s, y),
                    f"{value:.3f}" + ("  best" if bold else ""),
                    font=_font(12, bold),
                    fill=INK if bold else INK_2,
                    anchor="rm",
                )

    draw.text(
        (40 * s, height - 30 * s),
        "Test sets: DIS-VD (objects) and P3M-500-NP (people). Axis starts at 0.65. Source: benchmarks/results/*/scores.csv",
        font=_font(12),
        fill=MUTED,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((width // s, height // s), Image.LANCZOS).save(OUTPUT)
    print(f"saved {OUTPUT}")


if __name__ == "__main__":
    main()
