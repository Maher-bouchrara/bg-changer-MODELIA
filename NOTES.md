# Working notes

A running log of time spent, decisions in progress and how AI tools were used.
Kept honest and short; the polished version of the decisions lives in the README.

## Time log

| Date | Hours | What |
|---|---|---|
| 2026-10-26 | 0.5 | Read the brief, planned the pipeline, repo baseline |
| 2026-10-26 | 1.0 | Researched the 5 candidate models; PyTorch on the RTX 5050; BiRefNet segmenter (most of the time was the ~13 min PyTorch download) |

| 2026-10-26 | 0.5 | Checked each model's license, gating and files; download script; downloaded all 5 models |

| 2026-10-26 | 1.0 | Step 3: image loader and hex parser, 43 tests, README sections 3.1 and 3.2 |

| 2026-10-26 | 0.5 | Split io/ and color/ into one file per step |
| 2026-10-26 | 2.0 | Step 4: 3 adapters, registry, check script (slow network: OpenCV took 8.5 min) |

| 2026-10-27 | 1.0 | Chose benchmark sets (checked BiRefNet's training list), test_data/ README, download script. The download itself took about 1.5 h at 0.13 MB/s (unattended) |

**Total so far:** 6.5 h

## Decisions in progress

- **Model step before input handling.** The riskiest part (new GPU + model loading) goes first.
- **Pinned BiRefNet revision** (`e2bf8e44...`). transformers warns that remote model code is
  re-downloaded unpinned otherwise.
- **Models in `./models/<name>/`, not the hidden Hugging Face cache.** It's easy to see what is
  on disk and to delete one model. A script downloads every model pinned to an exact version.
- **Only inference files are downloaded.** BEN2's repo is 1.76 GB, but `model.safetensors` (381 MB)
  is enough. The 1.1 GB `.pth` holds the same weights, and ONNX exports and demo images are skipped.
  The same goes for RMBG-2.0: 5.4 GB in the repo, 885 MB needed.
- **InSPyReNet comes from a GitHub release**, not Hugging Face. The script verifies its MD5 checksum.
- **RMBG-2.0 is gated.** I accepted BRIA's terms and logged in to Hugging Face myself.
- **Two input packages, `io/` and `color/`, one file per step.** The two inputs are independent and
  change for different reasons. I first wrote one file each, then split them into folders with one
  file per loading step, so each file can be read on its own. Tests mirror the same layout.
- **A test caught a wrong assumption.** I first listed `#FF00` as invalid, but it is valid
  `#RGBA` (transparent yellow). The test is now pinned and the README warns about it.
- **Read each model's code before wrapping it.** That's how the min-max stretching (BEN2 and
  InSPyReNet), BEN2's global settings change and InSPyReNet's heavy `__init__` came to light.
- **InSPyReNet in fp32.** fp16 autocast gave NaN masks. It was tested, not assumed.
- **Blank-image check in the smoke test.** It showed that RMBG-2.0 labels a plain grey image as
  95% subject. That's a lead to verify in the benchmark, not a conclusion.
- **Test sets: DIS-VD + P3M-500-NP, not P3M-500-P or AIM-500.** I first proposed P3M-500-P. Then
  BiRefNet's official README showed its general model *trained* on P3M-500-P and AIM-500, and kept
  DIS-VD and P3M-500-NP for testing. Testing on training images would inflate its score.
- **Only the test split is downloaded** (757 MB instead of about 12 GB), from Hugging Face copies
  that store each split as its own file. Pinned commit + SHA-256 check + official image count.
- **Custom resumable downloader.** huggingface_hub's downloader stalled twice on the slow
  connection (Xet at 0 MB, plain HTTP at 10 MB). The script now resumes with HTTP Range requests
  and retries. It survived one timeout mid-download.
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
