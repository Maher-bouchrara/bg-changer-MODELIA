"""Tests for bgchange/benchmark/metrics.py on tiny hand-made masks.

Each test builds masks whose correct score is known in advance, so a mistake
in the scoring code (which would silently distort the whole benchmark) shows up
here first.
"""

import numpy as np
import pytest

from bgchange.benchmark.metrics import boundary_f, f_measure, mae


def _square(size=100, top=30, left=30, side=40) -> np.ndarray:
    """A float mask with one filled square (the "subject")."""
    mask = np.zeros((size, size), dtype=np.float32)
    mask[top : top + side, left : left + side] = 1.0
    return mask


def test_perfect_prediction_gets_perfect_scores():
    truth = _square()
    assert mae(truth, truth) == 0.0
    assert f_measure(truth, truth) == 1.0
    assert boundary_f(truth, truth) == 1.0


def test_inverted_prediction_gets_worst_scores():
    truth = _square()
    inverted = 1.0 - truth
    assert mae(inverted, truth) == 1.0
    assert f_measure(inverted, truth) == 0.0


def test_empty_image_and_empty_prediction_is_perfect():
    """No subject in the image, and the model says so: nothing to punish."""
    nothing = np.zeros((50, 50), dtype=np.float32)
    assert f_measure(nothing, nothing) == 1.0
    assert boundary_f(nothing, nothing) == 1.0


def test_missing_everything_scores_zero():
    """The model finds no subject at all."""
    assert f_measure(np.zeros((100, 100)), _square()) == 0.0
    assert boundary_f(np.zeros((100, 100)), _square()) == 0.0


def test_half_the_subject_found():
    """Recall 0.5, precision 1.0 -> F = 2 * 0.5 * 1 / 1.5 = 0.667."""
    truth = _square(top=30, left=30, side=40)
    half = truth.copy()
    half[:, 50:] = 0.0  # the model cut off the right half
    assert f_measure(half, truth) == pytest.approx(2 / 3, abs=0.01)


def test_mae_counts_soft_values():
    """MAE uses soft values: predicting 0.5 where the truth is 1 costs 0.5 per pixel."""
    truth = np.ones((10, 10), dtype=np.float32)
    unsure = np.full((10, 10), 0.5, dtype=np.float32)
    assert mae(unsure, truth) == pytest.approx(0.5)


def test_small_shift_is_tolerated_by_boundary_f():
    """A 1-pixel shift of the outline is within tolerance: edges still count as right."""
    truth = _square(size=200, top=50, left=50, side=80)
    shifted = _square(size=200, top=51, left=51, side=80)
    assert boundary_f(shifted, truth) == pytest.approx(1.0)


def test_extra_blob_far_away_lowers_boundary_f_but_not_recall():
    """An invented blob far from the subject adds wrong edges (precision drops)."""
    truth = _square(size=200, top=20, left=20, side=60)
    with_blob = truth.copy()
    with_blob[150:190, 150:190] = 1.0  # a second "subject" that isn't there
    score = boundary_f(with_blob, truth)
    assert 0.4 < score < 0.9
    assert f_measure(with_blob, truth) < 1.0


def test_thin_structure_missed_hurts_boundary_more_than_region():
    """Missing a thin cable barely changes the region score but clearly hurts the edge score.

    This is why boundary F is in the benchmark: DIS-VD is full of cables, spokes and ladders.
    """
    truth = _square(size=200, top=20, left=20, side=100)
    truth[150:152, 0:200] = 1.0  # a 2-pixel cable across the image
    without_cable = _square(size=200, top=20, left=20, side=100)

    region = f_measure(without_cable, truth)
    edges = boundary_f(without_cable, truth)
    assert region > 0.97
    assert edges < region - 0.2
