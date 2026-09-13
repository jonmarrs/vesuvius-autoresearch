"""Tests for the seed-consensus measurement.

The result turned on a comparator choice, not on the decision rule: the
registration compared consensus against the BETTER of two singles, and max() of
two noisy correlations is biased upward, so the gain came out +0.016 where a
typical-single comparison gives +0.065. Both numbers are real; they answer
different questions. These tests pin that both are computed and that the
registered thresholds are not quietly edited to match whichever is convenient.
"""

import json
import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_seed_consensus_gain as mod  # noqa: E402


def test_the_registered_thresholds_are_constants():
    assert mod.WORTH_IT == 0.05
    assert mod.MARGINAL == 0.01


def test_max_of_two_noisy_estimates_is_biased_upward():
    """Why the registered comparator understates the gain. Two unbiased noisy
    measurements of the same value: their max is above the truth on average."""
    rng = np.random.default_rng(0)
    truth = 0.70
    draws = rng.normal(truth, 0.05, (20000, 2))
    assert draws.mean() == pytest.approx(truth, abs=0.002)
    assert draws.max(axis=1).mean() > truth + 0.02


def test_averaging_independent_noise_raises_correlation_toward_a_known_limit():
    """Positive control on the model the report extrapolates from: with signal
    plus independent noise, the consensus of two beats a single by the amount
    the variance algebra predicts."""
    rng = np.random.default_rng(1)
    n = 40000
    s = rng.normal(0, 1, n)
    ratio = 0.393
    a, b, c = (s + rng.normal(0, np.sqrt(ratio), n) for _ in range(3))
    r_single = np.corrcoef(a, c)[0, 1]
    r_cons = np.corrcoef((a + b) / 2, c)[0, 1]
    predicted = 1 / np.sqrt((1 + ratio / 2) * (1 + ratio))
    assert r_single == pytest.approx(1 / (1 + ratio), abs=0.02)
    assert r_cons == pytest.approx(predicted, abs=0.02)
    assert r_cons - r_single == pytest.approx(0.057, abs=0.02)


def test_the_k_seed_projection_matches_the_published_table():
    ratio = 1 / 0.718 - 1
    for k, want in ((1, 0.718), (2, 0.836), (3, 0.884), (5, 0.927)):
        assert 1 / (1 + ratio / k) == pytest.approx(want, abs=0.002)


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/seed_consensus_gain.json")),
    reason="consensus measurement not run",
)
def test_the_published_artifact_keeps_both_comparators_recoverable():
    d = json.load(open(os.path.join(_REPO, "reports/seed_consensus_gain.json")))
    assert len(d["rows"]) == 3
    singles = [v for r in d["rows"] for v in (r["single_a"], r["single_b"])]
    cons = [r["consensus"] for r in d["rows"]]
    # the report's +0.065 must be derivable from the artifact, not just asserted
    assert np.mean(cons) - np.mean(singles) == pytest.approx(0.065, abs=0.005)
    assert d["mean_gain"] == pytest.approx(0.016, abs=0.005)
    assert d["verdict"] == "MARGINAL"
