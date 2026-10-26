"""BiRefNet: the model suggested in the brief (https://huggingface.co/ZhengPeng7/BiRefNet).

BiRefNet ("Bilateral Reference Network") is trained for high-resolution
dichotomous segmentation: it decides, for every pixel, whether it belongs to the
main subject. It works on both people and products and is MIT licensed.

How one prediction works:

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
from bgchange.segmenters.base import Segmenter

# Mean / std of the ImageNet dataset. BiRefNet's backbone was trained on images
# normalised this way, so inputs must be normalised identically.
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# Exact Hub commit of ZhengPeng7/BiRefNet that was tested. Pinning it means the
# model's Python code (executed via trust_remote_code) and weights cannot change
# underneath us if the repository is updated later.
_BIREFNET_REVISION = "e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4"


class BiRefNetSegmenter(Segmenter):
    """Segmenter backed by a BiRefNet checkpoint from the Hugging Face Hub."""

    name = "birefnet"

    def __init__(
        self,
        repo_id: str = "ZhengPeng7/BiRefNet",
        revision: str | None = _BIREFNET_REVISION,
        input_size: int = 1024,
        device: str = "auto",
    ) -> None:
        """Download (first time only) and load the model.

        Args:
            repo_id: Hugging Face repository holding the weights. Other BiRefNet
                variants (e.g. the matting one) reuse this class with another id.
            revision: Hub commit to load; pinned by default (see _BIREFNET_REVISION).
            input_size: side length the image is resized to. 1024 is what the
                general model was trained at.
            device: "auto", "cuda" or "cpu".
        """
        # Imported here so that `import bgchange` stays fast and does not need
        # transformers unless a model is actually used.
        from transformers import AutoModelForImageSegmentation

        self.input_size = input_size
        self.device = pick_device(device)
        self.dtype = pick_dtype(self.device)

        # trust_remote_code=True: BiRefNet's architecture is defined by Python
        # code stored in its Hub repository, not inside transformers itself.
        # That code is executed locally, which is why the repo id and revision
        # are fixed here and not taken from user input.
        model = AutoModelForImageSegmentation.from_pretrained(
            repo_id, revision=revision, trust_remote_code=True
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
