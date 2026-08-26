"""Tests for the matched-correlation onset sweep.

The point of this probe is that the two sides of a comparison were previously
measured at different correlation lengths. The tests pin the things that make the
corrected comparison meaningful: that correlation length actually moves the onset
(otherwise the mismatch never mattered), that the fitted sigma is in the swept
set, and that the min-over-rays and per-ray-median statistics are not confused.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_correlated_scatter import run_level  # noqa: E402
from probe_onset_at_matched_correlation import (  # noqa: E402
    RMS_LEVELS,
    SIGMA_GRID,
    onset_for,
)
from probe_scatter_estimator_calibration import WINDOW, matched_sigma  # noqa: E402
from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    load_shard,
    usable_rays,
)


def _rays(n=40):
    return usable_rays(load_shard(), n_rays=n)


def test_correlation_length_actually_moves_the_onset():
    """If it did not, the mismatch this probe exists to fix would not have
    mattered, and the whole exercise would be empty."""
    rays = _rays()
    lo, _, _ = onset_for(rays, 0.0, np.random.default_rng(20260825))
    hi, _, _ = onset_for(rays, 2.0, np.random.default_rng(20260825))
    assert lo is not None and hi is not None
    assert hi < lo


def test_more_correlation_flips_more_rays():
    """The monotone direction the comparison relies on: at a fixed rms, a longer
    correlation length should catch at least as many rays."""
    rays = _rays()
    rms = 2.5
    _, few = run_level(rays, rms, 0.0, np.random.default_rng(1))
    _, many = run_level(rays, rms, 2.0, np.random.default_rng(1))
    assert many > few


def test_the_fitted_sigma_is_inside_the_swept_range():
    """The probe's purpose is to report the onset AT the calibration's sigma. If
    that value fell outside the grid the headline row would be interpolated
    rather than measured."""
    fitted = matched_sigma(WINDOW)
    assert min(SIGMA_GRID) <= fitted <= max(SIGMA_GRID)


def test_min_over_rays_is_never_above_the_per_ray_median():
    """These two statistics are easy to confuse, and the report previously
    compared a min-over-rays onset against a median scatter. By construction the
    min cannot exceed the median; pinning it makes the distinction visible."""
    rays = _rays()
    first, med, n = onset_for(rays, 0.65, np.random.default_rng(20260825))
    assert first is not None and med is not None
    assert first <= med
    assert 0 < n <= len(rays)


def test_the_swept_range_reaches_the_corrected_scatter_band():
    """Relevance guard: the sweep has to cover the region where the corrected
    real-patch scatter sits (about 1.3 to 3.8 voxels) or it says nothing about
    real patches."""
    assert min(RMS_LEVELS) <= 1.30
    assert max(RMS_LEVELS) >= 3.80
