# Commands

Open a terminal in the project folder: in File Explorer, type `powershell` in
the address bar and press Enter. Paste a command, press Enter. **Ctrl + C** stops it.

## 1. Setup (first time only)

```
uv sync
uv run python scripts/download_models.py
uv run python scripts/download_test_data.py
```

## 2. Run a model on one photo

```
uv run python scripts/predict_mask.py "C:\path\to\photo.jpg" --model birefnet
```

Result: `outputs\photo_birefnet_mask.png` (white = subject, black = background).
Tip: drag the photo into the terminal to paste its path.

## 3. Run a model on all 970 test photos

One model (~15 min):

```
uv run python scripts/run_benchmark.py --model birefnet
```

All 5 models (~1.5 h):

```
uv run python scripts/run_benchmark.py --model all
```

Results: `benchmarks\results\summary.md` (scores) and `benchmarks\results\<model>\masks\` (every mask).

## 4. Compare the models side by side on a folder of photos

```
uv run python scripts/compare_models.py test_data/real-photos/images
```

Any folder works (also your own photos). Results: `comparisons\<folder>\sheet_01.png`, ...
Each row = one photo, each column = one model's cut-out on pink.
Photos where the models disagree most come first.
Choose models: add `--model birefnet ben2`.

## Models

`birefnet` (default), `birefnet-matting`, `rmbg-2.0`, `ben2`, `inspyrenet`

## Check everything works

```
uv run python scripts/check_gpu.py
uv run python scripts/check_models.py
uv run pytest
```
