import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import BPB_NOISE_TOLERANCE, TOPO_MIN_GAIN, is_model_improvement

# Stored best as of 2026-06-09: production resenc_unet on the fixed validation set.
BEST_BPB = 0.262564
BEST_CDICE = 0.0734


def test_topology_gain_not_vetoed_by_bpb_noise():
    # Real cycle 2026-06-09 18:57: +58% centerline_dice, val_bpb 8e-6 worse.
    # The old bpb-first rule rejected this; it must count as an improvement.
    assert is_model_improvement(0.262572, 0.1142, BEST_BPB, BEST_CDICE)


def test_bpb_noise_cannot_swap_in_topologically_worse_model():
    # Marginally lower val_bpb but centerline_dice down well past noise.
    assert not is_model_improvement(0.262560, 0.060, BEST_BPB, BEST_CDICE)


def test_real_bpb_gain_with_topology_held():
    assert is_model_improvement(
        0.25, BEST_CDICE - 0.5 * TOPO_MIN_GAIN, BEST_BPB, BEST_CDICE
    )


def test_topology_gain_with_real_bpb_regression_rejected():
    # Real cycle 2026-06-09 11:33: cdice up but val_bpb 0.2746 — a genuine
    # regression (>> noise tolerance), not noise.
    assert not is_model_improvement(0.274578, 0.104067, BEST_BPB, BEST_CDICE)


def test_noise_level_cdice_gain_alone_is_not_improvement():
    assert not is_model_improvement(
        BEST_BPB + 1e-6, BEST_CDICE + 0.5 * TOPO_MIN_GAIN, BEST_BPB, BEST_CDICE
    )


def test_nan_val_bpb_rejected():
    assert not is_model_improvement(float("nan"), 0.5, BEST_BPB, BEST_CDICE)


def test_initial_state_accepts_first_finite_model():
    # Fresh history: stored best is the (1.0, 0.0) sentinel.
    assert is_model_improvement(0.9, 0.0, 1.0, 0.0)


def test_tolerances_separate_observed_noise_from_regression():
    # Observed run-to-run bpb band is ~2e-4; the genuine regression was ~1.2e-2.
    assert 2e-4 < BPB_NOISE_TOLERANCE < 1.2e-2
