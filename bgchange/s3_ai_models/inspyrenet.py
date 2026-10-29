"""InSPyReNet ("Inverse Saliency Pyramid Reconstruction Network"), MIT.

Paper: Kim et al., ACCV 2022. Code: https://github.com/plemeri/transparent-background

What makes InSPyReNet different: it builds the mask like an image pyramid.
It first predicts a rough, low-resolution mask, then repeatedly adds back only
the missing detail (the edges) at higher resolutions:

    rough mask (1/32 size) --+ edge detail --> 1/16 --+ detail --> ... --> full size

Each level only has to predict "what is missing", which keeps edges sharp on
large images.

Where the pieces come from:
    weights        models/inspyrenet/ckpt_base.pth  (GitHub release, MD5-checked)
    network code   the `transparent-background` package, installed WITHOUT its
                   24 extra dependencies (see pyproject.toml)

Two things this adapter does differently from the package's own Remover:

1. The package's front door (transparent_background/__init__.py) imports its GUI
   and its Remover tool, which need those 24 extras. This adapter registers the
   package folder by hand, so only the network files are imported and the front
   door is never executed.
2. The network's own forward() stretches every mask so its minimum becomes 0
   and its maximum becomes 1, which turns an uncertain prediction into a
   confident-looking one. This adapter calls the inner step (forward_inspyre)
   and applies only the sigmoid: the same computation, minus the stretch.
"""

from __future__ import annotations

import functools
import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from bgchange.device import pick_device
from bgchange.paths import model_dir
from bgchange.s3_ai_models.base import Segmenter

# Same preprocessing as the package's "base" mode (static 1024x1024 resize,
# bilinear, ImageNet normalisation).
_INPUT_SIZE = 1024
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

_PACKAGE = "transparent_background"


@functools.cache
def _network_builder():
    """Return the InSPyReNet_SwinB function without running the package's __init__.py.

    Python normally runs a package's __init__.py before any file inside it. To
    skip it, an empty module with the package's folder as its search path is
    put into sys.modules first: Python then sees "package already imported" and
    goes straight to the file we ask for.
    """
    spec = importlib.util.find_spec(_PACKAGE)  # finds the folder, imports nothing
    if spec is None or not spec.submodule_search_locations:
        raise ImportError(
            "The transparent-background package is not installed. Run:  uv sync"
        )

    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = list(spec.submodule_search_locations)
        sys.modules[_PACKAGE] = package

    from transparent_background.InSPyReNet import InSPyReNet_SwinB

    return InSPyReNet_SwinB


class InSPyReNetSegmenter(Segmenter):
    """Segmenter backed by InSPyReNet (Swin-B backbone, "base" checkpoint)."""

    name = "inspyrenet"

    def __init__(self, device: str = "auto") -> None:
        """Build the network, load the weights, move it to the GPU (or CPU).

        Args:
            device: "auto", "cuda" or "cpu".

        Raises:
            FileNotFoundError: the weights are not downloaded (the message gives the command).
        """
        checkpoint: Path = model_dir("inspyrenet") / "ckpt_base.pth"
        self.device = pick_device(device)

        # 1. Build the empty network, exactly as the package's Remover does for
        #    mode "base": 64 channels per layer, trained at 1024x1024.
        #    threshold=None means "one pass at the input size" (no extra
        #    low-resolution pass), which is what forward_inspyre does below.
        build = _network_builder()
        network = build(depth=64, pretrained=False, base_size=[_INPUT_SIZE, _INPUT_SIZE], threshold=None)

        # 2. Fill it with the weights. weights_only=True: the .pth file is a
        #    Python pickle, and this setting refuses anything that is not plain
        #    tensors, so a tampered file cannot run code. strict=True fails
        #    loudly if a single weight is missing.
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        network.load_state_dict(state, strict=True)

        # 3. Move to the device. The network overrides .to() with a version that
        #    only accepts a device (it also moves its internal pyramid kernels),
        #    so the weights stay fp32 (see predict() for why fp16 is not used).
        self.model = network.to(self.device).eval()

    def _to_tensor(self, image: Image.Image) -> torch.Tensor:
        """PIL RGB image -> normalised (1, 3, 1024, 1024) float32 tensor."""
        resized = image.resize((_INPUT_SIZE, _INPUT_SIZE), Image.BILINEAR)
        array = np.asarray(resized, dtype=np.float32) / 255.0  # (H, W, 3) in [0, 1]
        array = (array - _IMAGENET_MEAN) / _IMAGENET_STD
        tensor = torch.from_numpy(array.astype(np.float32)).permute(2, 0, 1)  # (3, H, W)
        return tensor.unsqueeze(0).to(self.device)

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> np.ndarray:
        """See `Segmenter.predict`."""
        width, height = image.size
        batch = self._to_tensor(image)

        # Full precision (fp32) on purpose. Tested: running this network in
        # fp16 (torch.autocast) makes the output NaN ("not a number"), because
        # some internal values are too large for fp16. So InSPyReNet is slower
        # and uses more memory than the others; the benchmark reports it as is.
        #
        # The last entry of the saliency pyramid is the full-resolution result,
        # as raw scores. See point 2 in the module docstring.
        logits = self.model.forward_inspyre(batch)["saliency"][-1]
        probs = torch.sigmoid(logits.float())  # (1, 1, 1024, 1024) in [0, 1]

        probs = F.interpolate(probs, size=(height, width), mode="bilinear", align_corners=False)
        return probs[0, 0].clamp(0, 1).cpu().numpy()
