"""Segmentation models: each one turns an RGB photo into an alpha matte.

"Segment" = split the image into subject and background. This folder holds the
CODE that runs the models; the downloaded weights live in models/.

    base.py         the rule every model follows: predict(image) -> alpha
    birefnet.py     BiRefNet, BiRefNet-matting and RMBG-2.0 (one shared network)
    ben2.py         BEN2
    inspyrenet.py   InSPyReNet
    registry.py     pick a model by name: get_segmenter("ben2")

Other code should only need the registry:

    from bgchange.segmenters import get_segmenter
    alpha = get_segmenter("birefnet").predict(image)
"""

from bgchange.segmenters.base import Segmenter
from bgchange.segmenters.registry import DEFAULT_MODEL, MODELS, get_segmenter, unload

__all__ = ["DEFAULT_MODEL", "MODELS", "Segmenter", "get_segmenter", "unload"]
