"""Choose where the model runs (GPU or CPU) and at what numeric precision.

The tool must work on the reviewers' machines too, which may have no NVIDIA
GPU. So the rule is: use CUDA if it is available, otherwise fall back to the
CPU, and never crash because a GPU is missing.
"""

from __future__ import annotations

import torch


def pick_device(requested: str = "auto") -> torch.device:
    """Return the torch device to run on.

    Args:
        requested: "auto" (GPU if available, else CPU), "cuda" or "cpu".

    Raises:
        RuntimeError: if "cuda" is requested explicitly but no GPU is usable.
    """
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA was requested but no usable GPU was found. "
            "Use --device cpu, or check that PyTorch was installed with CUDA support."
        )
    return torch.device(requested)


def pick_dtype(device: torch.device) -> torch.dtype:
    """Half precision (fp16) on GPU, full precision (fp32) on CPU.

    fp16 halves the VRAM use and is faster on GPUs, with no visible change in the
    mask. CPUs are slow at fp16, so they stay on fp32.
    """
    return torch.float16 if device.type == "cuda" else torch.float32
