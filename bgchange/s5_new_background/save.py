"""Where the result goes, and how it is written.

    photo.jpg + #FF0066    ->  outputs/photo_on_FF0066.png
    photo.jpg + beach.jpg  ->  outputs/photo_on_beach.png

Always PNG: it is lossless, so the soft edges the model worked for are not
blurred by JPEG compression, and it can hold transparency.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from bgchange.s2_read_color import Color

#: Default output folder (gitignored), relative to where the command is run.
OUTPUT_DIR = Path("outputs")


def default_output_path(photo_path: Path, background: Color | Path) -> Path:
    """outputs/<photo name>_on_<HEX>.png, or _on_<picture name>.png for a background
    picture, so different backgrounds never overwrite each other."""
    name = background.to_hex().lstrip("#") if isinstance(background, Color) else Path(background).stem
    return OUTPUT_DIR / f"{Path(photo_path).stem}_on_{name}.png"


def save_png(image: Image.Image, path: Path) -> Path:
    """Save `image` as PNG at `path` (creates the folder). Returns the path."""
    path = Path(path).with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
