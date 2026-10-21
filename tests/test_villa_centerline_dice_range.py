"""Villa's centerline_dice, which the loop's topology threshold maximises (train.select_topology_threshold), is
2 |S_pred ∩ T(S_gt)| / (|S_gt| + |S_pred|): the prediction's skeleton pixels within the tolerance of the ground
truth's skeleton, over both skeletons' lengths. It is not the symmetric clDice, and it is not bounded by 1. A
prediction whose skeleton is longer than the ground truth's, inside the tolerance, scores above an exact copy.
METHOD.md states this; these cases pin it, so the statement fails here if villa's pinned metric changes."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "training"))

import train  # noqa: E402

pytestmark = pytest.mark.skipif(
    train.CENTERLINE_DICE_IMPORT_ERROR is not None,
    reason=f"villa's centerline_dice is unavailable: {train.CENTERLINE_DICE_IMPORT_ERROR}",
)


def _cd(gt, pred):
    return train.compute_centerline_dice(gt, pred, tolerance_radius=3.0)


def _stroke():
    """A 3-px-wide, 56-px-long stroke of ink in one 64 x 64 slice."""
    gt = np.zeros((1, 64, 64), bool)
    gt[0, 30:33, 4:60] = True
    return gt


def test_an_exact_copy_scores_one_and_a_distant_one_zero():
    gt = _stroke()
    assert _cd(gt, gt.copy())["centerline_dice"] == pytest.approx(1.0)
    far = np.zeros_like(gt)
    far[0, 5:8, 4:60] = True  # the same stroke, 25 px away
    assert _cd(gt, far)["centerline_dice"] == 0.0


def test_a_ragged_prediction_around_the_ink_outscores_an_exact_one():
    gt = _stroke()
    ragged = gt.copy()
    rng = np.random.default_rng(0)
    ragged[0, 27:36, 4:60] |= rng.random((9, 56)) < 0.35
    comb = gt.copy()
    for x in range(5, 59, 2):
        comb[0, 27:36, x] = True  # 3-px teeth either side of the stroke
    exact = _cd(gt, gt.copy())["centerline_dice"]
    for pred, above in ((ragged, 1.05), (comb, 1.25)):
        r = _cd(gt, pred)
        # Its skeleton is longer than the ground truth's and lies within the tolerance.
        assert r["centerline_length_pred"] > r["centerline_length_gt"]
        assert r["centerline_dice"] > above > exact
        # "sensitivity" is the same numerator over the ground truth's length, so it exceeds 1 too.
        assert r["centerline_sensitivity"] > 1.0
        assert r["centerline_dice"] < 2.0
