"""Tests for the strip-periodicity estimator.

This file exists because its absence is what produced a retracted finding. The
analysis it replaces lived in a shell heredoc, ran once, and had no control; every
committed tool in this project has known-input tests and none of them failed that
way.

The tests that matter are the calibration ones: an estimator that always returns
*a* peak is useless unless you know what its output looks like when there is
nothing to find.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import measure_strip_periodicity as mod  # noqa: E402

INNER, OUTER = 8810, 82670


def sine(length, period, noise=0.5, seed=0):
    r = np.random.default_rng(seed)
    t = np.arange(length)
    return np.sin(2 * np.pi * t / period) + noise * r.normal(size=length)


@pytest.mark.parametrize("length", [INNER, OUTER])
@pytest.mark.parametrize("period", [300.0, 850.0, 945.0])
def test_it_recovers_a_known_period_at_both_real_strip_lengths(length, period):
    """The control the retracted analysis lacked. 850 vs 945 at inner length is
    the specific discrimination that analysis got wrong."""
    got, _ = mod.dominant_period(sine(length, period))
    assert abs(got - period) / period < 0.03


def test_the_bundled_validate_passes():
    assert mod.validate(verbose=False)


def test_a_real_line_scores_far_above_pure_noise():
    """Calibration. Without this the share number is meaningless."""
    _, line = mod.dominant_period(sine(INNER, 850.0))
    _, noise = mod.dominant_period(np.random.default_rng(1).normal(size=INNER))
    assert line > 5 * noise
    assert line > 0.05  # a genuine line carries >5% of band power
    assert noise < 0.02  # pure noise carries <2%


def test_it_still_finds_the_line_at_low_signal_to_noise():
    got, share = mod.dominant_period(sine(INNER, 850.0, noise=3.0))
    assert abs(got - 850.0) / 850.0 < 0.03
    assert share > 0.05


def test_no_moving_average_high_pass_is_used():
    """The retracted version used `hp = min(2500, size//8)`, which trimmed 5000 of
    8810 points on an inner strip and filtered inner and outer strips
    differently. Pinning its absence, since reintroducing it would silently
    recreate the defect."""
    import inspect

    src = inspect.getsource(mod.dominant_period)
    assert "convolve" not in src, "moving-average high-pass is back"
    assert "//" not in src, "length-proportional window is back"


def test_the_estimator_does_not_trim_the_series():
    """A peak that scales with input length is the signature of an artefact. If
    the estimator ever starts trimming, this catches it: the recovered period for
    a fixed true period must not move with length."""
    a, _ = mod.dominant_period(sine(6000, 850.0))
    b, _ = mod.dominant_period(sine(12000, 850.0))
    assert abs(a - b) / 850.0 < 0.05
