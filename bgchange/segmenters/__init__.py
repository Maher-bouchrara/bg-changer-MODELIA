"""Segmentation models. Each one turns an RGB image into an alpha matte.

For now only BiRefNet exists; a registry that picks a model by name
(`--model birefnet`, `--model rmbg2`, ...) is added in the model-registry step.
"""

from bgchange.segmenters.base import Segmenter
from bgchange.segmenters.birefnet import BiRefNetSegmenter

__all__ = ["Segmenter", "BiRefNetSegmenter"]
