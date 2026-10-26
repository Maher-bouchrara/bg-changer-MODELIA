# Working notes

A running log of time spent, decisions in progress and how AI tools were used.
Kept honest and short; the polished version of the decisions lives in the README.

## Time log

| Date | Hours | What |
|---|---|---|
| 2026-10-26 | 0.5 | Read the brief, planned the pipeline, repo baseline |

**Total so far:** 0.5 h

## Use of AI tools

| Tool | What I used it for | What I checked / changed myself |
|---|---|---|
| Claude Code | Planning, comparing segmentation models, scaffolding files and docs | Reviewed every file; decisions are mine |

## Environment

- Laptop GPU: NVIDIA RTX 5050 Laptop (8 GB, Blackwell sm_120), so PyTorch must be a CUDA 12.8+ build.
- Python 3.12, pinned in `.python-version`. The system Python is 3.14, which ML wheels may not support yet.
- Package manager: `uv`.
