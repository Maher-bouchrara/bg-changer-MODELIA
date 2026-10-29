"""Where the result goes, and how it is written.

    photo.jpg + #FF0066  ->  outputs/photo_on_FF0066.png

Always PNG: it is lossless, so the soft edges the model worked for are not
blurred by JPEG compression, and it can hold transparency.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from bgchange.color import Color

#: Default output folder (gitignored), relative to where the command is run.
OUTPUT_DIR = Path("outputs")


def default_output_path(photo_path: Path, color: Color) -> Path:
    """outputs/<photo name>_on_<HEX>.png, so different colours never overwrite each other."""
    return OUTPUT_DIR / f"{Path(photo_path).stem}_on_{color.to_hex().lstrip('#')}.png"


def save_png(image: Image.Image, path: Path) -> Path:
    """Save `image` as PNG at `path` (creates the folder). Returns the path."""
    path = Path(path).with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
