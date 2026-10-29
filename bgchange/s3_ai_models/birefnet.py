"""BiRefNet and the two models built on the same network.

BiRefNet ("Bilateral Reference Network", https://huggingface.co/ZhengPeng7/BiRefNet)
decides, for every pixel, whether it belongs to the main subject. It looks at
the image twice: once small, to understand the whole scene ("this is a
person"), and once at full detail, to place the edges precisely.

Three of our five models use this exact network and differ only in the
weights, i.e. what they were trained on. Their config.json files all declare
the same "BiRefNet" architecture, so this one class serves all three:

    variant            folder              trained on                     license
    birefnet           models/birefnet/    general subjects (DIS5K, ...)  MIT
    birefnet-matting   models/birefnet-    matting data: soft, partly     MIT
                       matting/            transparent edges (hair)
    rmbg-2.0           models/rmbg-2.0/    BRIA's licensed product and    non-commercial
                                           people photos

How one prediction works (same for all three):

    RGB image (any size)
      -> resize to 1024x1024 and normalise like ImageNet  (what the model was trained on)
      -> network  -> raw scores (logits), 1024x1024
      -> sigmoid  -> probabilities in [0, 1]
      -> resize back to the original size  -> alpha matte
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from bgchange.device import pick_device, pick_dtype
from bgchange.paths import model_dir
from bgchange.s3_ai_models.base import Segmenter

# Mean / std of the ImageNet dataset. BiRefNet's backbone was trained on images
# normalised this way, so inputs must be normalised identically.
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

#: The variants this class can load. Each is a folder name under models/.
VARIANTS = ("birefnet", "birefnet-matting", "rmbg-2.0")


class BiRefNetSegmenter(Segmenter):
    """Segmenter for any BiRefNet-architecture model in models/<variant>/."""

    def __init__(self, variant: str = "birefnet", input_size: int = 1024, device: str = "auto") -> None:
        """Load the model from its local folder onto the GPU (or CPU).

        Args:
            variant: one of VARIANTS, i.e. which weights to load.
            input_size: side length the image is resized to. All three variants
                were trained at 1024.
            device: "auto", "cuda" or "cpu".

        Raises:
            ValueError: unknown variant.
            FileNotFoundError: the model was not downloaded yet (the message
                gives the download command).
        """
        if variant not in VARIANTS:
            raise ValueError(f"Unknown BiRefNet variant '{variant}'. Choose from {VARIANTS}.")

        # Imported here so that `import bgchange` stays fast and does not need
        # transformers unless a model is actually used.
        from transformers import AutoModelForImageSegmentation

        self.name = variant
        self.input_size = input_size
        self.device = pick_device(device)
        self.dtype = pick_dtype(self.device)

        # Load from the local folder, not from the internet. The folder was
        # filled by scripts/download_models.py at a pinned commit, so the
        # weights and code are exactly the ones that were tested.
        #
        # trust_remote_code=True: the network is defined by birefnet.py inside
        # that folder, not by transformers itself, and that file is executed.
        # It is safe here because it is the pinned file we downloaded, and the
        # folder name comes from VARIANTS, never from user input.
        model = AutoModelForImageSegmentation.from_pretrained(
            model_dir(variant), trust_remote_code=True
        )
        self.model = model.to(self.device, dtype=self.dtype).eval()

        # Allows faster TF32 matrix maths on recent GPUs; no visible quality change.
        torch.set_float32_matmul_precision("high")

    def _to_tensor(self, image: Image.Image) -> torch.Tensor:
        """PIL RGB image -> normalised (1, 3, input_size, input_size) tensor."""
        resized = image.resize((self.input_size, self.input_size), Image.BILINEAR)
        array = np.asarray(resized, dtype=np.float32) / 255.0  # (H, W, 3) in [0, 1]
        array = (array - _IMAGENET_MEAN) / _IMAGENET_STD
        tensor = torch.from_numpy(array.astype(np.float32)).permute(2, 0, 1)  # (3, H, W)
        return tensor.unsqueeze(0).to(self.device, dtype=self.dtype)

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> np.ndarray:
        """See `Segmenter.predict`."""
        width, height = image.size
        batch = self._to_tensor(image)

        # BiRefNet returns a list of predictions at several scales; the last one
        # is the final, full-resolution output.
        logits = self.model(batch)[-1]
        probs = logits.sigmoid().float()  # back to fp32 for the resize

        # Resize the 1024x1024 matte back to the photo's own size. Bilinear keeps
        # soft edges soft instead of making them blocky.
        probs = F.interpolate(probs, size=(height, width), mode="bilinear", align_corners=False)
        return probs[0, 0].clamp(0, 1).cpu().numpy()
