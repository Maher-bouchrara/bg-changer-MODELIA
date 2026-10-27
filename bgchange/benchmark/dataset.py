"""List the test samples: each photo paired with its answer key (correct mask).

The files come from scripts/download_test_data.py:

    test_data/<set>/images/<name>.jpg   the photo
    test_data/<set>/masks/<name>.png    the answer key (same name)

DIS-VD file names carry the object's category, which lets the report give a
separate score for product-like objects:

    1#Accessories#1#Bag#3811492306_4ae60c73b6_o.jpg
      ^ group       ^ category
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bgchange.paths import TEST_DATA_DIR

#: The test sets, in the order they appear in reports.
SETS = ("dis-vd", "p3m-500-np")

#: DIS-VD groups that look like things a shop would sell. Chosen by hand from
#: the 22 groups in DIS-VD; the rest are buildings, vehicles, animals, weapons,
#: diagrams, etc. (see test_data/README.md).
PRODUCT_LIKE_GROUPS = frozenset(
    {
        "Accessories",
        "Electrical",
        "Electronics",
        "Entertainment",
        "Frame",
        "Furniture",
        "Kitchenware",
        "Music Instrument",
        "Sports",
        "Tool",
    }
)


@dataclass(frozen=True)
class Sample:
    """One test photo and its answer key."""

    set_name: str  # "dis-vd" or "p3m-500-np"
    image_path: Path
    mask_path: Path
    group: str  # e.g. "Furniture"; "People" for P3M
    category: str  # e.g. "Chair"; "Portrait" for P3M

    @property
    def name(self) -> str:
        """File name without extension, shared by the photo and its mask."""
        return self.image_path.stem

    @property
    def product_like(self) -> bool:
        return self.group in PRODUCT_LIKE_GROUPS


def _group_and_category(set_name: str, stem: str) -> tuple[str, str]:
    """Read the group and category from the file name (DIS-VD only)."""
    if set_name == "p3m-500-np":
        return "People", "Portrait"
    parts = stem.split("#")
    if len(parts) >= 4:
        return parts[1], parts[3]
    return "Unknown", "Unknown"


def list_samples(set_name: str, limit: int | None = None, root: Path = TEST_DATA_DIR) -> list[Sample]:
    """All samples of one test set, sorted by name.

    Args:
        set_name: one of SETS.
        limit: if given, keep only this many samples, spread evenly over the
            sorted list. DIS-VD is sorted by group, so taking the first 20
            would give 20 accessories; spreading gives a mix of groups.
        root: folder holding the sets (test_data/ by default).

    Raises:
        FileNotFoundError: the set is not downloaded (the message gives the command).
    """
    images_dir = root / set_name / "images"
    masks_dir = root / set_name / "masks"
    if not images_dir.is_dir():
        raise FileNotFoundError(
            f"Test set '{set_name}' not found in {images_dir}.\n"
            f"Download it with:  uv run python scripts/download_test_data.py {set_name}"
        )

    samples = []
    for image_path in sorted(images_dir.iterdir()):
        mask_path = masks_dir / f"{image_path.stem}.png"
        if not mask_path.exists():
            continue  # a photo without an answer key can't be graded
        group, category = _group_and_category(set_name, image_path.stem)
        samples.append(Sample(set_name, image_path, mask_path, group, category))

    if limit is not None and limit < len(samples):
        step = len(samples) / limit
        samples = [samples[int(i * step)] for i in range(limit)]
    return samples
