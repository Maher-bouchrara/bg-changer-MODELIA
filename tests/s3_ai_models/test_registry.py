"""Tests for bgchange/s3_ai_models/registry.py.

These use a fake model instead of real ones, so they run in a fraction of a
second, without a GPU and without the downloaded weights.
"""

from __future__ import annotations

import numpy as np
import pytest

from bgchange.s3_ai_models import registry
from bgchange.s3_ai_models.base import Segmenter
from bgchange.s3_ai_models.registry import DEFAULT_MODEL, MODELS, ModelInfo, get_segmenter, unload


class FakeSegmenter(Segmenter):
    """Stands in for a real model: predicts "everything is subject"."""

    def __init__(self, name: str) -> None:
        self.name = name

    def predict(self, image):
        width, height = image.size
        return np.ones((height, width), dtype=np.float32)


@pytest.fixture
def fake_models(monkeypatch):
    """Replace the real list with two fake models, and count how often each is built."""
    built: list[str] = []

    def make(name: str) -> ModelInfo:
        def build(device: str) -> Segmenter:
            built.append(name)
            return FakeSegmenter(name)

        return ModelInfo(build, f"fake {name}", "MIT", True)

    monkeypatch.setattr(registry, "MODELS", {"fake-a": make("fake-a"), "fake-b": make("fake-b")})
    unload()  # start every test with nothing loaded
    yield built
    unload()


def test_the_five_models_are_listed():
    assert list(MODELS) == ["birefnet", "birefnet-matting", "rmbg-2.0", "ben2", "inspyrenet"]
    assert DEFAULT_MODEL in MODELS


def test_non_commercial_weights_are_flagged():
    """RMBG-2.0 is CC BY-NC 4.0; everything else is MIT."""
    assert not MODELS["rmbg-2.0"].commercial_use
    assert all(info.commercial_use for name, info in MODELS.items() if name != "rmbg-2.0")


def test_unknown_name_lists_the_valid_ones(fake_models):
    with pytest.raises(ValueError, match="Choose from: fake-a, fake-b"):
        get_segmenter("ben3")


def test_same_name_reuses_the_loaded_model(fake_models):
    first = get_segmenter("fake-a")
    second = get_segmenter("fake-a")

    assert first is second  # the very same object, not a new one
    assert fake_models == ["fake-a"]  # built only once


def test_switching_model_replaces_the_loaded_one(fake_models):
    get_segmenter("fake-a")
    model_b = get_segmenter("fake-b")
    model_a_again = get_segmenter("fake-a")

    assert model_b.name == "fake-b"
    assert model_a_again.name == "fake-a"
    # fake-a was unloaded when fake-b came in, so it had to be built again.
    assert fake_models == ["fake-a", "fake-b", "fake-a"]


def test_unload_forces_a_rebuild(fake_models):
    get_segmenter("fake-a")
    unload()
    get_segmenter("fake-a")

    assert fake_models == ["fake-a", "fake-a"]
