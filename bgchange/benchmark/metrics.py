"""The 3 scores that compare a model's mask with the answer key.

Both masks are float arrays of the same size, values in [0, 1]
(1 = subject, 0 = background).

    score         question it answers                          best   range
    MAE           on average, how wrong is each pixel?          0     0 .. 1
    F-measure     right shape? nothing missing, nothing extra   1     0 .. 1
    boundary F    are the edges in the right place?             1     0 .. 1

MAE uses the soft values directly, so it rewards getting hair "40% subject"
right. F-measure and boundary F need a yes/no answer per pixel, so both masks
are cut at 0.5 first ("more subject than not").
"""

from __future__ import annotations

import cv2
import numpy as np

#: Pixels above this value count as "subject" for F-measure and boundary F.
THRESHOLD = 0.5

#: How far (as a share of the image diagonal) an edge may be from the true edge
#: and still count as correct. 0.75% is the usual choice for boundary F; on a
#: 1000x1000 photo that is about 10 pixels.
BOUNDARY_TOLERANCE = 0.0075


def mae(pred: np.ndarray, truth: np.ndarray) -> float:
    """Mean absolute error: the average per-pixel difference (0 = perfect).

    Example: a mask that is right everywhere except 10% of the pixels, where
    it is completely wrong, has MAE 0.10.
    """
    return float(np.abs(pred.astype(np.float32) - truth.astype(np.float32)).mean())


def f_measure(pred: np.ndarray, truth: np.ndarray) -> float:
    """F-measure (also called F1 or Dice) of the subject region (1 = perfect).

        precision = of the pixels the model called subject, how many really are?
        recall    = of the real subject pixels, how many did the model find?
        F         = 2 * precision * recall / (precision + recall)

    F is high only when BOTH are high: cutting off part of the subject lowers
    recall, and including background lowers precision.
    """
    p = pred > THRESHOLD
    t = truth > THRESHOLD
    return _f_from_counts(true_pos=np.count_nonzero(p & t), predicted=np.count_nonzero(p), actual=np.count_nonzero(t))


def boundary_f(pred: np.ndarray, truth: np.ndarray) -> float:
    """F-measure computed on the outlines only (1 = perfect edges).

    Region scores are dominated by the large, easy inside of the subject. This
    score looks only at the 1-pixel outline of each mask:

        precision = share of the model's outline lying near the true outline
        recall    = share of the true outline lying near the model's outline

    "Near" = within BOUNDARY_TOLERANCE of the image diagonal, so a 1-2 pixel
    shift is not punished but a missing cable or a blob over the background is.
    """
    p_edge = _outline(pred > THRESHOLD)
    t_edge = _outline(truth > THRESHOLD)

    height, width = truth.shape
    tolerance = max(1.0, BOUNDARY_TOLERANCE * float(np.hypot(height, width)))

    # Distance from every pixel to the nearest outline pixel of the other mask.
    near_true = _distance_to(t_edge) <= tolerance
    near_pred = _distance_to(p_edge) <= tolerance

    matched_pred = np.count_nonzero(p_edge & near_true)  # model's edges that are right
    matched_true = np.count_nonzero(t_edge & near_pred)  # true edges the model found
    n_pred, n_true = np.count_nonzero(p_edge), np.count_nonzero(t_edge)

    if n_pred == 0 and n_true == 0:
        return 1.0  # no subject, and the model agrees: perfect
    if n_pred == 0 or n_true == 0:
        return 0.0
    precision = matched_pred / n_pred
    recall = matched_true / n_true
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _f_from_counts(true_pos: int, predicted: int, actual: int) -> float:
    if predicted == 0 and actual == 0:
        return 1.0  # no subject, and the model agrees: perfect
    if predicted == 0 or actual == 0:
        return 0.0
    precision = true_pos / predicted
    recall = true_pos / actual
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _outline(mask: np.ndarray) -> np.ndarray:
    """1-pixel outline of a yes/no mask: the mask minus its shrunk (eroded) self."""
    as_uint8 = mask.astype(np.uint8)
    eroded = cv2.erode(as_uint8, np.ones((3, 3), np.uint8), borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return (as_uint8 - eroded).astype(bool)


def _distance_to(edge: np.ndarray) -> np.ndarray:
    """For every pixel, the distance (in pixels) to the nearest pixel of `edge`."""
    if not edge.any():
        return np.full(edge.shape, np.inf, dtype=np.float32)
    # distanceTransform measures the distance to the nearest ZERO pixel, so the
    # edge pixels are passed as zeros and everything else as ones.
    return cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
