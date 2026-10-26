"""Print what PyTorch sees: version, CUDA build, GPU name, and a tiny GPU test.

Run:  uv run python scripts/check_gpu.py

On an RTX 50xx (Blackwell) card, a PyTorch build older than CUDA 12.8 fails the
test with "no kernel image is available for execution on the device". That
means the wrong torch wheel was installed, not that the GPU is broken.
"""

import torch

print(f"torch          : {torch.__version__}")
print(f"built for CUDA : {torch.version.cuda}")
print(f"CUDA available : {torch.cuda.is_available()}")

if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    print(f"GPU            : {props.name}")
    print(f"VRAM           : {props.total_memory / 1024**3:.1f} GB")
    print(f"compute cap.   : sm_{props.major}{props.minor}")

    # A real computation on the GPU; this is what fails on a mismatched build.
    x = torch.randn(1024, 1024, device="cuda", dtype=torch.float16)
    y = (x @ x).sum().item()
    print(f"GPU matmul test: OK ({y:.1f})")
else:
    print("Running on CPU only.")
