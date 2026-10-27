"""Where things live on disk.

Kept in one place so the code and the download script always agree, and so
Docker can point to another folder without code changes.
"""

from __future__ import annotations

import os
from pathlib import Path

#: The project root (the folder containing pyproject.toml).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Where the model weights are, one sub-folder per model (models/birefnet/, ...).
#: Override with the BGCHANGE_MODELS_DIR environment variable, e.g. in Docker
#: where the weights are mounted as a volume at another path.
MODELS_DIR = Path(os.environ.get("BGCHANGE_MODELS_DIR", PROJECT_ROOT / "models"))


#: Where the benchmark test images are (test_data/dis-vd/, ...). See test_data/README.md.
TEST_DATA_DIR = Path(os.environ.get("BGCHANGE_TEST_DATA_DIR", PROJECT_ROOT / "test_data"))


def model_dir(name: str) -> Path:
    """Folder of one model, checked to exist.

    Raises:
        FileNotFoundError: with the exact command that downloads the model.
    """
    folder = MODELS_DIR / name
    if not folder.is_dir():
        raise FileNotFoundError(
            f"Model '{name}' is not downloaded (expected folder {folder}).\n"
            f"Download it with:  uv run python scripts/download_models.py {name}"
        )
    return folder
