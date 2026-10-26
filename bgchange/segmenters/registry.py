"""The registry: pick a segmentation model by name.

Like a phone's contact list: you ask for "ben2" and the registry knows which
code builds it. Everything else (CLI, API, UI, benchmark) uses only this file:

    from bgchange.segmenters.registry import get_segmenter, MODELS

    model = get_segmenter("ben2")        # builds it (or reuses the loaded one)
    alpha = model.predict(image)

Memory rule: only ONE model is kept loaded at a time. Asking for a different
one first removes the previous one from the GPU, so 8 GB of VRAM is always
enough, whatever the order the models are used in.
"""

from __future__ import annotations

import gc
import threading
from collections.abc import Callable
from dataclasses import dataclass

from bgchange.segmenters.base import Segmenter


@dataclass(frozen=True)
class ModelInfo:
    """One entry of the list: how to build a model, plus facts shown to users."""

    #: Function that builds the model; it receives the device ("auto", "cuda", "cpu").
    build: Callable[[str], Segmenter]
    #: One line shown in --help and in the UI dropdown.
    description: str
    #: License of the weights.
    license: str
    #: False for weights that may not be used commercially (shown as a warning).
    commercial_use: bool


# Each `build` imports its file only when called, so asking for one model never
# loads the code (or the extra packages) of the others.


def _birefnet(variant: str) -> Callable[[str], Segmenter]:
    def build(device: str) -> Segmenter:
        from bgchange.segmenters.birefnet import BiRefNetSegmenter

        return BiRefNetSegmenter(variant, device=device)

    return build


def _ben2(device: str) -> Segmenter:
    from bgchange.segmenters.ben2 import BEN2Segmenter

    return BEN2Segmenter(device=device)


def _inspyrenet(device: str) -> Segmenter:
    from bgchange.segmenters.inspyrenet import InSPyReNetSegmenter

    return InSPyReNetSegmenter(device=device)


#: The list. The order here is the order shown in menus and benchmark tables.
MODELS: dict[str, ModelInfo] = {
    "birefnet": ModelInfo(
        _birefnet("birefnet"), "BiRefNet general: people and products", "MIT", True
    ),
    "birefnet-matting": ModelInfo(
        _birefnet("birefnet-matting"), "BiRefNet matting: soft edges, hair", "MIT", True
    ),
    "rmbg-2.0": ModelInfo(
        _birefnet("rmbg-2.0"), "BRIA RMBG-2.0: strong on products", "CC BY-NC 4.0", False
    ),
    "ben2": ModelInfo(_ben2, "BEN2: tiles + overview, fine edges", "MIT", True),
    "inspyrenet": ModelInfo(_inspyrenet, "InSPyReNet: coarse-to-fine pyramid", "MIT", True),
}

#: Used when no model is given. Provisional: the benchmark (step 5) decides.
DEFAULT_MODEL = "birefnet"


# --- The one-model-at-a-time cache ------------------------------------------

# The model currently loaded, and the (name, device) it was built with.
_loaded: Segmenter | None = None
_loaded_key: tuple[str, str] | None = None

# The API (later) can receive several requests at the same time. The lock makes
# sure two requests never load or unload a model simultaneously.
_lock = threading.Lock()


def get_segmenter(name: str = DEFAULT_MODEL, device: str = "auto") -> Segmenter:
    """Return the model called `name`, loading it if needed.

    Calling it again with the same name and device returns the already loaded
    model instantly. A different name unloads the previous model first.

    Raises:
        ValueError: unknown name (the message lists the valid names).
        FileNotFoundError: the model is not downloaded (the message gives the command).
    """
    global _loaded, _loaded_key

    if name not in MODELS:
        raise ValueError(f"Unknown model '{name}'. Choose from: {', '.join(MODELS)}.")

    with _lock:
        if _loaded is not None and _loaded_key == (name, device):
            return _loaded  # already loaded: reuse it

        _unload_locked()  # free the GPU before loading the next model
        _loaded = MODELS[name].build(device)
        _loaded_key = (name, device)
        return _loaded


def unload() -> None:
    """Remove the currently loaded model from memory (GPU and RAM)."""
    with _lock:
        _unload_locked()


def _unload_locked() -> None:
    """Unload without taking the lock (the caller already holds it)."""
    global _loaded, _loaded_key

    if _loaded is None:
        return
    _loaded = None
    _loaded_key = None

    # Dropping the last reference is not always enough: Python frees memory
    # when it gets around to it, and PyTorch keeps freed GPU memory reserved
    # for reuse. These two calls make the memory really available again.
    gc.collect()
    import torch

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
