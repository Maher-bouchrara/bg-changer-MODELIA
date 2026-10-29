"""The single interface every segmentation model implements.

The rest of the pipeline only ever calls `predict(image) -> alpha`. Adding a new
model therefore means writing one small class, with no changes anywhere else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from PIL import Image


class Segmenter(ABC):
    """Base class for a model that separates the subject from the background."""

    #: Short name used on the command line, e.g. `--model birefnet`.
    name: str = ""

    @abstractmethod
    def predict(self, image: Image.Image) -> np.ndarray:
        """Predict the alpha matte of the subject.

        Args:
            image: an upright 8-bit RGB image of any size.

        Returns:
            A float32 array of shape (height, width) with values in [0, 1], at the
            same size as `image`. 1 means "fully subject", 0 means "fully
            background", and values in between are soft edges (hair, motion blur,
            semi-transparent material).
        """
