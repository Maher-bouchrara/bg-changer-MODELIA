"""Benchmark the segmentation models on the test sets.

Run:
    uv run python scripts/run_benchmark.py --model birefnet --limit 20   # quick check
    uv run python scripts/run_benchmark.py --model birefnet              # all 970 photos
    uv run python scripts/run_benchmark.py --model all                   # all 5 models
    uv run python scripts/run_benchmark.py --report-only                 # just rebuild the report

Results (gitignored) go to benchmarks/results/:
    <model>/scores.csv           one row per photo
    <model>/masks/<set>/*.png    every predicted mask
    summary.md                   tables comparing every model that has results
    contact_sheet_<set>.png      hardest photos, all models side by side

An interrupted run continues where it stopped when run again.
"""

from __future__ import annotations

import argparse

from bgchange.benchmark.dataset import SETS
from bgchange.benchmark.report import write_report
from bgchange.benchmark.runner import RESULTS_DIR, run
from bgchange.s3_ai_models import MODELS, unload


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the segmentation models.")
    parser.add_argument("--model", nargs="+", default=[], help=f"'all' or any of: {', '.join(MODELS)}")
    parser.add_argument("--set", nargs="+", default=list(SETS), choices=SETS, help="test sets (default: both)")
    parser.add_argument("--limit", type=int, help="at most N photos per set, spread evenly (quick runs)")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--report-only", action="store_true", help="skip running, just rebuild the report")
    args = parser.parse_args()

    models = list(MODELS) if args.model == ["all"] else args.model
    unknown = [m for m in models if m not in MODELS]
    if unknown:
        parser.error(f"unknown model(s) {unknown}; choose from {list(MODELS)} or 'all'")
    if not models and not args.report_only:
        parser.error("give --model (or --report-only)")

    if not args.report_only:
        for model in models:
            run(model, args.set, limit=args.limit, device=args.device)
            unload()  # free the GPU before the next model

    print()
    print(write_report())
    print(f"\nFull results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
