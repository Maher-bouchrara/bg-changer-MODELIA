"""Download the benchmark test sets into test_data/<set>/images + masks.

Run:
    uv run python scripts/download_test_data.py               # all sets
    uv run python scripts/download_test_data.py dis-vd        # only some

What it does, for each set (see test_data/README.md for what the sets are):

    1. download ONE Parquet file from a pinned Hugging Face commit
       (Parquet = a compact table file; each row holds one photo + its mask)
       -> test_data/_downloads/<file>.parquet
       The download resumes where it stopped and retries on network errors
       (huggingface_hub's own downloader stalled twice on a slow connection),
       and the finished file must match its official SHA-256 fingerprint.
    2. unpack every row into two normal image files with the same name:
       -> test_data/<set>/images/<name>.jpg   the photo
       -> test_data/<set>/masks/<name>.png    the correct mask
    3. check the number of pairs matches the official count (470 / 500),
       so a broken or modified copy is noticed immediately

Only the test split is downloaded. Each dataset copy also has training files
(several GB) that we never fetch.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from bgchange.paths import TEST_DATA_DIR

DOWNLOADS_DIR = TEST_DATA_DIR / "_downloads"


@dataclass(frozen=True)
class TestSet:
    """One test set stored as a Parquet file in a Hugging Face dataset repo."""

    repo_id: str
    revision: str  # exact commit hash, never a branch name
    filename: str  # the single file holding the test split
    size: int  # exact size in bytes, from the Hub's file listing
    sha256: str  # fingerprint from the Hub's file listing; checked after download
    expected_count: int  # official number of images; checked after unpacking

    @property
    def url(self) -> str:
        return f"https://huggingface.co/datasets/{self.repo_id}/resolve/{self.revision}/{self.filename}"


TEST_SETS: dict[str, TestSet] = {
    "dis-vd": TestSet(
        repo_id="not-lain/DIS5K",
        revision="e007e9a3af50dec16d0fca3c0856793d20b9a448",
        filename="data/DIS_VD-00000-of-00001-87c0cab31f89a0a6.parquet",
        size=478_010_664,
        sha256="9b3afd69caf78c014b7d5ac23883b2ed5e5eacb49abc34392b2cb80ce50fb85a",
        expected_count=470,
    ),
    "p3m-500-np": TestSet(
        repo_id="nobg/P3M-10K",
        revision="a239de9297bd56e372cf3c9c82f7085d59e71219",
        filename="data/P3M_500_NP-00000-of-00001.parquet",
        size=278_540_465,
        sha256="6af9c2dd7f4df7f0730dd41db9685033505f3b22a2e5aadcac0bc1b982220c79",
        expected_count=500,
    ),
}

# Network behaviour: give up on a silent connection after 60 s, then retry.
_TIMEOUT_S = 60
_MAX_RETRIES = 50
_CHUNK = 1 << 20  # read 1 MB at a time


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(name: str, spec: TestSet) -> Path:
    """Step 1: fetch the Parquet file, resuming and retrying as needed.

    The file is first written as <file>.part. After every network error the
    next attempt asks the server only for the missing bytes (an HTTP "Range"
    request), so a dropped connection never restarts from zero.
    """
    target = DOWNLOADS_DIR / Path(spec.filename).name
    partial = target.with_suffix(target.suffix + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and target.stat().st_size == spec.size:
        print(f"[{name}] already downloaded")
        return target

    for attempt in range(1, _MAX_RETRIES + 1):
        have = partial.stat().st_size if partial.exists() else 0
        if have >= spec.size:
            break
        request = urllib.request.Request(spec.url, headers={"Range": f"bytes={have}-"})
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response, partial.open("ab") as out:
                last_print = 0.0
                while chunk := response.read(_CHUNK):
                    out.write(chunk)
                    have += len(chunk)
                    if time.monotonic() - last_print > 5:  # progress every 5 s
                        print(f"[{name}] {have / 1e6:6.0f} / {spec.size / 1e6:.0f} MB ({100 * have / spec.size:4.1f}%)")
                        last_print = time.monotonic()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            print(f"[{name}] network error ({error}); retry {attempt}/{_MAX_RETRIES} from {have / 1e6:.0f} MB")
            time.sleep(min(30, 2 * attempt))

    if not partial.exists() or partial.stat().st_size != spec.size:
        sys.exit(f"[{name}] download incomplete after {_MAX_RETRIES} retries; run the script again to resume")

    print(f"[{name}] checking SHA-256 fingerprint...")
    actual = _sha256(partial)
    if actual != spec.sha256:
        partial.unlink()
        sys.exit(f"[{name}] SHA-256 mismatch (expected {spec.sha256}, got {actual}); file deleted")
    partial.replace(target)
    print(f"[{name}] downloaded and verified")
    return target


def _image_columns(table) -> list[str]:
    """Names of the columns that hold images.

    Hugging Face stores an image column as a struct {bytes, path}: the encoded
    file (JPEG/PNG bytes) plus its original file name.
    """
    import pyarrow as pa

    return [
        field.name
        for field in table.schema
        if pa.types.is_struct(field.type) and "bytes" in [f.name for f in field.type]
    ]


def unpack(name: str, spec: TestSet, parquet_file: Path) -> int:
    """Step 2: write every row as images/<stem>.<ext> + masks/<stem>.png."""
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_file)
    columns = _image_columns(table)
    if len(columns) != 2:
        sys.exit(
            f"[{name}] expected 2 image columns (photo + mask), found {columns} "
            f"in schema:\n{table.schema}"
        )
    # The photo column comes first in both copies (e.g. "image", then "mask"/"label").
    photo_column, mask_column = columns

    images_dir = TEST_DATA_DIR / name / "images"
    masks_dir = TEST_DATA_DIR / name / "masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    photos = table.column(photo_column).to_pylist()
    masks = table.column(mask_column).to_pylist()
    for index, (photo, mask) in enumerate(zip(photos, masks, strict=True)):
        # Keep the original file name when the copy recorded it, so results can
        # be traced back to the official dataset; otherwise number the rows.
        original = photo.get("path") or f"{index:04d}.jpg"
        stem = Path(original).stem

        # The photo is written as-is (no re-encoding, so no quality loss).
        suffix = Path(original).suffix.lower() or ".jpg"
        (images_dir / f"{stem}{suffix}").write_bytes(photo["bytes"])

        # Masks are always saved as 8-bit greyscale PNG (lossless), whatever
        # format the copy used, so the benchmark can read them all the same way.
        Image.open(io.BytesIO(mask["bytes"])).convert("L").save(masks_dir / f"{stem}.png")

    return len(photos)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the benchmark test sets.")
    parser.add_argument("names", nargs="*", help=f"sets to fetch (default: all): {', '.join(TEST_SETS)}")
    parser.add_argument(
        "--download-only", action="store_true", help="fetch the Parquet files but don't unpack them"
    )
    args = parser.parse_args()

    unknown = [n for n in args.names if n not in TEST_SETS]
    if unknown:
        parser.error(f"unknown set(s) {unknown}; choose from {list(TEST_SETS)}")

    for name in args.names or TEST_SETS:
        spec = TEST_SETS[name]
        print(f"[{name}] downloading {spec.repo_id}/{spec.filename}")
        parquet_file = download(name, spec)
        if args.download_only:
            continue

        count = unpack(name, spec, parquet_file)
        status = "OK" if count == spec.expected_count else "MISMATCH"
        print(f"[{name}] {count} image/mask pairs (official count {spec.expected_count}): {status}")
        if count != spec.expected_count:
            sys.exit(1)

    print(f"\nDone. Test data is in {TEST_DATA_DIR}")


if __name__ == "__main__":
    main()
