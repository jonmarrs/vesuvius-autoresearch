import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import F1_NOISE_TOLERANCE, LIFT_MARGIN, is_f1_improvement


def test_clear_f1_gain_with_signal_is_improvement():
    # ap_lift well above 1, f1 up well past tolerance, vs a fresh -inf baseline.
    assert is_f1_improvement(0.40, 2.0, float("-inf"))


def test_f1_gain_over_existing_best_is_improvement():
    assert is_f1_improvement(0.50, 1.5, 0.40)


def test_no_signal_lift_at_or_below_one_is_rejected():
    # Constant-prediction guard: high f1 but no real signal (lift ~1.0).
    assert not is_f1_improvement(0.60, 1.0, 0.40)
    assert not is_f1_improvement(0.60, 1.0 + LIFT_MARGIN, 0.40)  # exactly at margin


def test_f1_within_noise_tolerance_is_not_improvement():
    assert not is_f1_improvement(0.40 + 0.5 * F1_NOISE_TOLERANCE, 2.0, 0.40)


def test_nan_f1_rejected():
    assert not is_f1_improvement(float("nan"), 2.0, 0.40)


def test_nan_lift_rejected():
    assert not is_f1_improvement(0.50, float("nan"), 0.40)


def test_tolerances_are_positive_and_small():
    assert 0.0 < F1_NOISE_TOLERANCE < 0.1
    assert 0.0 < LIFT_MARGIN < 0.5
