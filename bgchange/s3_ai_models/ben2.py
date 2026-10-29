"""BEN2 ("Background Erase Network 2", https://huggingface.co/PramaLLC/BEN2), MIT.

What makes BEN2 different: it looks at the photo as 4 zoomed-in tiles plus 1
zoomed-out overview, all at once, and combines them. The tiles give fine edge
detail (hair), the overview gives context (which object is the subject).

    1024x1024 image
      -> 4 local tiles (512x512 each) + 1 global view (512x512)
      -> Swin Transformer backbone on all 5
      -> decoder merges them into one mask, 1024x1024, already in [0, 1]

Where the network code comes from: models/ben2/BEN2.py, downloaded at a pinned
commit with the weights. It is loaded straight from that file instead of
`pip install git+https://github.com/PramaLLC/BEN2`, as their README suggests,
because the file is already pinned and on disk.

Three things this adapter does differently from BEN2's own inference() helper:

1. BEN2.py changes global PyTorch settings when imported (random seeds and
   matmul precision "highest", which is the slowest). The precision is set
   back to "high" after importing, so other models don't slow down.
2. BEN2's helper stretches every mask so its minimum becomes 0 and its maximum
   becomes 1. On an uncertain photo, that turns noise into a fake subject. This
   adapter returns the model's real probabilities instead.
3. Weights are read from model.safetensors (381 MB), a format that cannot run
   code when loaded, instead of the 1.1 GB .pth pickle.
"""

from __future__ import annotations

import functools
import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from bgchange.device import pick_device
from bgchange.paths import model_dir
from bgchange.s3_ai_models.base import Segmenter

# Same normalisation BEN2.py uses (ImageNet statistics).
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# BEN2 is trained at 1024x1024; its tile layout assumes exactly this size.
_INPUT_SIZE = 1024


@functools.cache
def _load_ben2_code(code_file: Path) -> ModuleType:
    """Import models/ben2/BEN2.py as a Python module (only once per process).

    functools.cache means the file's top-level code (which changes global
    settings) runs a single time, even if BEN2 is loaded several times.
    """
    spec = importlib.util.spec_from_file_location("ben2_network", code_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Undo BEN2.py's global "highest" precision (see point 1 in the docstring).
    torch.set_float32_matmul_precision("high")
    return module


class BEN2Segmenter(Segmenter):
    """Segmenter backed by BEN2 base, loaded from models/ben2/."""

    name = "ben2"

    def __init__(self, device: str = "auto") -> None:
        """Build the network, load the weights, move it to the GPU (or CPU).

        Args:
            device: "auto", "cuda" or "cpu".

        Raises:
            FileNotFoundError: BEN2 is not downloaded (the message gives the command).
        """
        from safetensors.torch import load_file

        folder = model_dir("ben2")
        self.device = pick_device(device)

        # 1. Build the empty network from BEN2's own code.
        network = _load_ben2_code(folder / "BEN2.py").BEN_Base()

        # 2. Fill it with the trained weights. strict=True fails loudly if even
        #    one weight is missing or unexpected, instead of silently giving a
        #    half-random model.
        network.load_state_dict(load_file(folder / "model.safetensors"), strict=True)

        # 3. Move to the device. The weights stay fp32: BEN2's forward() already
        #    switches itself to fp16 on CUDA (torch.autocast), so it gets the
        #    fp16 speed-up without us converting anything.
        self.model = network.to(self.device).eval()

    def _to_tensor(self, image: Image.Image) -> torch.Tensor:
        """PIL RGB image -> normalised (1, 3, 1024, 1024) float32 tensor."""
        # LANCZOS, like BEN2's own loader: match the preprocessing it was trained with.
        resized = image.resize((_INPUT_SIZE, _INPUT_SIZE), Image.LANCZOS)
        array = np.asarray(resized, dtype=np.float32) / 255.0  # (H, W, 3) in [0, 1]
        array = (array - _IMAGENET_MEAN) / _IMAGENET_STD
        tensor = torch.from_numpy(array.astype(np.float32)).permute(2, 0, 1)  # (3, H, W)
        return tensor.unsqueeze(0).to(self.device)

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> np.ndarray:
        """See `Segmenter.predict`."""
        width, height = image.size

        # BEN2's forward() already applies the sigmoid: values are in [0, 1].
        probs = self.model(self._to_tensor(image)).float()  # (1, 1, 1024, 1024)

        # Back to the photo's own size. No min/max stretching (see point 2 above).
        probs = F.interpolate(probs, size=(height, width), mode="bilinear", align_corners=False)
        return probs[0, 0].clamp(0, 1).cpu().numpy()
