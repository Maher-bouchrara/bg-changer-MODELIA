"""Shared helpers for the input-handling tests.

pytest loads this file automatically for every test in tests/io/. Fixtures
defined here can be used by any test just by naming them as an argument.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image


@pytest.fixture
def encode():
    """Return a function that saves a Pillow image to in-memory file bytes.

    The bytes are exactly what would be on disk (or in an upload), so tests can
    build a hard-case file in code instead of committing binary test images.

        data = encode(Image.new("RGB", (10, 10)), "JPEG")
    """

    def _encode(image: Image.Image, fmt: str, **save_options) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format=fmt, **save_options)
        return buffer.getvalue()

    return _encode
