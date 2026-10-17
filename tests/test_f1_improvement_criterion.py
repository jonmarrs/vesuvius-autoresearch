import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import F1_NOISE_TOLERANCE, LIFT_MARGIN, is_f1_improvement

ROOT = Path(__file__).resolve().parents[1]
# The protocol-v3 noise probe (2026-10-16): four identical-config trials from the incumbent.
V3_PROBE = json.loads((ROOT / "reports/noise_probe_v3_2026-10-16.json").read_text())
V3_INCUMBENT = 0.249348  # best_model.pt's stored val_f1 re-scored under v3


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


def test_every_v3_probe_trial_would_be_promoted():
    # The owner's 2026-10-17 decision: a one-cycle gain the size the v3 probe measured
    # (+0.012 to +0.018 over the incumbent, 4.8-6.9 SDs) must be promotable.
    for run in V3_PROBE["runs"]:
        m = run["metrics"]
        assert is_f1_improvement(m["val_f1"], m["ap_prevalence_lift"], V3_INCUMBENT)


def test_false_promotion_at_the_v3_sigma_is_under_one_percent():
    # A promotion compares two draws, so a no-change cycle clears the tolerance with
    # probability P(N(0, 2 sigma^2) > tol).
    sigma = V3_PROBE["f1_spread"]["sample_std"]
    z = F1_NOISE_TOLERANCE / (math.sqrt(2) * sigma)
    assert 0.5 * math.erfc(z / math.sqrt(2)) < 0.01
