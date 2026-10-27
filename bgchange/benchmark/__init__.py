"""Benchmark: grade the segmentation models on test photos with known answers.

One file per job (see the README section on the benchmark):

    dataset.py   list the (photo, answer key) pairs of each test set
    metrics.py   the 3 scores: MAE, F-measure, boundary F
    runner.py    the loop: load photo -> model predicts -> save mask -> score
    report.py    summary table + contact sheet from the saved scores

Run it with:  uv run python scripts/run_benchmark.py --model birefnet
"""
