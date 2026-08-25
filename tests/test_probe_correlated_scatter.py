"""Tests for the correlated-scatter probe.

The claim this probe exists to establish is that the noise SHAPE matters at equal
magnitude, and that the earlier onset was measured with the wrong shape. Two ways
that could be an artifact rather than a finding: the arms not actually having
equal RMS, and the real residual not actually being correlated. Both are pinned.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_correlated_scatter import (  # noqa: E402
    RMS_LEVELS,
    SIGMAS,
    measure_real_autocorrelation,
    noise_field,
    run_level,
)
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)


def test_all_arms_have_identical_rms():
    """If the correlated arms carried more RMS than the independent one, their
    earlier break would be a magnitude effect masquerading as a shape effect,
    and the whole probe would be circular."""
    rng = np.random.default_rng(0)
    for rms in (1.5, 3.0, 6.0):
        for sigma in SIGMAS:
            f = noise_field((12, 16), rms, sigma, rng)
            assert float(f.std()) == pytest.approx(rms, rel=1e-9)


def test_smoothing_actually_induces_correlation():
    """sigma>0 must produce a field that is measurably correlated, or the
    'correlated' arms are not correlated and the comparison is empty."""
    rng = np.random.default_rng(1)

    def lag1(f):
        return float(np.corrcoef(f[:, :-1].ravel(), f[:, 1:].ravel())[0, 1])

    indep = np.mean([lag1(noise_field((12, 16), 3.0, 0.0, rng)) for _ in range(40)])
    corr = np.mean([lag1(noise_field((12, 16), 3.0, 2.0, rng)) for _ in range(40)])
    assert abs(indep) < 0.2
    assert corr > 0.6


def test_real_patch_residuals_are_correlated_not_white():
    """The fact that decides which arm is the relevant comparison. If real
    residuals were white, the independent arm would be right and the earlier
    conclusion would stand unchanged."""
    a = measure_real_autocorrelation(n_windows=200)
    assert a.size >= 100
    assert float(np.median(a)) > 0.15
    assert float((a > 0).mean()) > 0.6


def test_correlated_noise_breaks_the_metric_earlier_than_independent():
    """The finding. At an RMS where independent noise flips nothing, correlated
    noise of the SAME RMS flips several verdicts."""
    rays = usable_rays(load_shard(), n_rays=40)
    rng = np.random.default_rng(20260825)
    _, indep_flips = run_level(rays, 2.5, 0.0, rng)
    _, corr_flips = run_level(rays, 2.5, 2.0, rng)
    assert indep_flips == 0
    assert corr_flips >= 3


def test_the_rms_grid_covers_real_patch_scatter():
    """Guard on relevance: real patches measure median 0.846 and p95 2.179
    voxels, so the swept range has to reach down to that neighbourhood or the
    probe says nothing about them."""
    assert min(RMS_LEVELS) <= 2.179
