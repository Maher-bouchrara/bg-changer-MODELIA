# Working notes

A running log of time spent, decisions in progress and how AI tools were used.
Kept honest and short; the polished version of the decisions lives in the README.

## Time log

| Date | Hours | What |
|---|---|---|
| 2026-10-26 | 0.5 | Read the brief, planned the pipeline, repo baseline |
| 2026-10-26 | 1.0 | Researched the 5 candidate models; PyTorch on the RTX 5050; BiRefNet segmenter (most of the time was the ~13 min PyTorch download) |

**Total so far:** 1.5 h

## Decisions in progress

- **Model step before input handling.** The riskiest part (new GPU + model loading) goes first.
- **Pinned BiRefNet revision** (`e2bf8e44...`). transformers warns that remote model code is
  re-downloaded unpinned otherwise.
- **fp16 on GPU.** Peak VRAM is 1.6 GB, far under the 8 GB available, which leaves room to try
  larger input sizes later.

## Use of AI tools

| Tool | What I used it for | What I checked / changed myself |
|---|---|---|
| Claude Code | Planning, comparing segmentation models, scaffolding files and docs | Reviewed every file; decisions are mine |

## Environment

- Laptop GPU: NVIDIA RTX 5050 Laptop (8 GB, Blackwell sm_120), so PyTorch must be a CUDA 12.8+ build.
  Verified working: torch 2.11.0+cu128, `scripts/check_gpu.py` passes.
- Python 3.12, pinned in `.python-version`. The system Python is 3.14, which ML wheels may not support yet.
- Package manager: `uv`.
