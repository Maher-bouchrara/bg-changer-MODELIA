"""Download the segmentation models into ./models/<name>/.

Run:
    uv run python scripts/download_models.py              # all models
    uv run python scripts/download_models.py birefnet ben2  # only some

Every model is pinned to an exact version (a Hugging Face commit, or a GitHub
release file checked with its MD5), so everyone benchmarks the same weights.
Only the files needed for inference are fetched; demo images, ONNX exports and
duplicate checkpoint formats are skipped.

Resulting layout (all gitignored except models/README.md):

    models/
    ├── birefnet/          BiRefNet general         (HF, MIT)
    ├── birefnet-matting/  BiRefNet matting variant (HF, MIT)
    ├── rmbg-2.0/          BRIA RMBG-2.0            (HF, gated, non-commercial)
    ├── ben2/              BEN2 base                (HF, MIT)
    └── inspyrenet/        InSPyReNet base          (GitHub release, MIT)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# Shared with the loading code, so both always agree on where models live.
from bgchange.paths import MODELS_DIR


@dataclass(frozen=True)
class HubModel:
    """A model stored in a Hugging Face repository."""

    repo_id: str
    revision: str  # exact commit hash, never a branch name
    files: list[str] = field(default_factory=list)  # only these are downloaded
    gated: bool = False  # True: you must accept the terms on the website first


@dataclass(frozen=True)
class UrlModel:
    """A single checkpoint file published at a fixed URL."""

    url: str
    filename: str
    md5: str


# The code files (*.py, config.json) are needed because these models define
# their architecture in Python stored next to the weights.
MODELS: dict[str, HubModel | UrlModel] = {
    "birefnet": HubModel(
        repo_id="ZhengPeng7/BiRefNet",
        revision="e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4",
        files=["birefnet.py", "BiRefNet_config.py", "config.json", "model.safetensors", "README.md"],
    ),
    "birefnet-matting": HubModel(
        repo_id="ZhengPeng7/BiRefNet-matting",
        revision="eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9",
        files=["birefnet.py", "BiRefNet_config.py", "config.json", "model.safetensors", "README.md"],
    ),
    "rmbg-2.0": HubModel(
        repo_id="briaai/RMBG-2.0",
        revision="2fd7b4b0f2393ddb39a267fb62df6c010928a6c6",
        files=["birefnet.py", "BiRefNet_config.py", "config.json", "model.safetensors", "README.md"],
        gated=True,
    ),
    "ben2": HubModel(
        repo_id="PramaLLC/BEN2",
        revision="e48a20765fb421d19dcdb0bf3cc61e802ca5ec8f",
        # model.safetensors (381 MB) holds the same weights as BEN2_Base.pth (1.1 GB).
        files=["BEN2.py", "config.json", "model.safetensors", "README.md"],
    ),
    "inspyrenet": UrlModel(
        url="https://github.com/plemeri/transparent-background/releases/download/1.2.12/ckpt_base.pth",
        filename="ckpt_base.pth",
        md5="d692e3dd5fa1b9658949d452bebf1cda",
    ),
}


def _md5(path: Path) -> str:
    """MD5 of a file, read in chunks so large checkpoints don't fill the RAM."""
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_hub(name: str, spec: HubModel) -> None:
    """Download the listed files of a pinned Hugging Face commit."""
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import GatedRepoError

    try:
        snapshot_download(
            repo_id=spec.repo_id,
            revision=spec.revision,
            allow_patterns=spec.files,
            local_dir=MODELS_DIR / name,
        )
    except GatedRepoError:
        sys.exit(
            f"\n{spec.repo_id} is gated. To download it:\n"
            f"  1. Open https://huggingface.co/{spec.repo_id} and accept the terms.\n"
            f"  2. Log in on this machine:  uv run hf auth login\n"
            f"  3. Run this script again:   uv run python scripts/download_models.py {name}\n"
        )


def download_url(name: str, spec: UrlModel) -> None:
    """Download one file and refuse it if its MD5 does not match."""
    target = MODELS_DIR / name / spec.filename
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and _md5(target) == spec.md5:
        print(f"  already present, checksum OK: {target}")
        return

    partial = target.with_suffix(target.suffix + ".part")
    urllib.request.urlretrieve(spec.url, partial)
    actual = _md5(partial)
    if actual != spec.md5:
        partial.unlink()
        sys.exit(f"  checksum mismatch for {spec.url}: expected {spec.md5}, got {actual}")
    partial.replace(target)
    print(f"  checksum OK: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the segmentation models.")
    parser.add_argument("names", nargs="*", help=f"models to fetch (default: all): {', '.join(MODELS)}")
    args = parser.parse_args()

    unknown = [n for n in args.names if n not in MODELS]
    if unknown:
        parser.error(f"unknown model(s) {unknown}; choose from {list(MODELS)}")

    for name in args.names or MODELS:
        spec = MODELS[name]
        print(f"[{name}]")
        if isinstance(spec, HubModel):
            download_hub(name, spec)
        else:
            download_url(name, spec)

    print(f"\nDone. Models are in {MODELS_DIR}")


if __name__ == "__main__":
    main()
