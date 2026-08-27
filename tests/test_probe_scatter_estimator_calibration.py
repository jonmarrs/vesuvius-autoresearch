"""Tests for the scatter-estimator calibration.

The correction this probe produces is only as good as two things: that the
injected field's correlation matches the real residual's, and that the
calibration curve is monotone enough to invert. Both are pinned. An earlier
version used an arbitrary sigma whose lag-1 was roughly double the real one,
which would have roughly doubled the correction.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402
from probe_scatter_estimator_calibration import (  # noqa: E402
    INJECT_RMS,
    REAL_LAG1,
    WINDOW,
    collect,
    correlated_field,
    field_lag1,
    invert,
    matched_sigma,
)

needs_data = pytest.mark.skipif(
    not patch_dirs(),
    reason="real patch data absent; see local_data/spiral_patches_phercparis4",
)

from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules


def test_matched_sigma_bisection_converges():
    """This pins ONLY that the bisection converges on its own target. It does NOT
    show the surrogate matches the real field: the fit targets lag-1 on the raw
    injected field, while the real +0.357 was measured on a plane-fit residual,
    and that residual statistic is unreachable for any isotropic sigma. An
    earlier docstring here claimed the stronger thing."""
    sig = matched_sigma(WINDOW)
    got = field_lag1(WINDOW, sig, np.random.default_rng(5), trials=800)
    assert got == pytest.approx(REAL_LAG1, abs=0.06)


def test_an_arbitrary_sigma_would_have_been_wrong():
    """Pins the specific error that was caught: sigma=1.0 over-correlates this
    window by roughly 2x against the real residual."""
    got = field_lag1(WINDOW, 1.0, np.random.default_rng(6), trials=800)
    assert got > REAL_LAG1 + 0.25


def test_injected_field_has_exactly_the_requested_rms():
    """A change-detector on `correlated_field`'s final line, kept only because a
    silent regression there would corrupt every ratio. It does NOT prevent
    confounding shape with magnitude: that confound lives in the PER-WINDOW rms
    (about 0.79 for the fitted sigma against 0.93 for white), which this does not
    touch and which the report now accounts for explicitly."""
    rng = np.random.default_rng(7)
    for rms in (0.25, 2.0):
        for sigma in (0.0, matched_sigma(WINDOW)):
            f = correlated_field((12, 16), rms, sigma, rng)
            assert float(f.std()) == pytest.approx(rms, rel=1e-9)


@needs_data
def test_the_calibration_curve_is_monotone_and_invertible():
    """`invert` interpolates the curve, which is only meaningful if reported
    scatter rises with injected scatter."""
    _, rows, sig, _ = collect()
    reported = [
        float(np.median(rows[(1, rms, sig)]))
        for rms in INJECT_RMS
        if rows.get((1, rms, sig))
    ]
    assert len(reported) >= 3
    assert reported == sorted(reported)
    mid = 0.5 * (reported[0] + reported[-1])
    est, _ = invert(rows, 1, sig, mid)
    assert INJECT_RMS[0] <= est <= INJECT_RMS[-1]


@needs_data
def test_the_plane_estimator_under_reports_correlated_scatter():
    """The finding, and the reason the report's bracket points the wrong way.
    At the largest injected level the plane returns materially less than was put
    in, so the real-patch figures are low rather than high."""
    _, rows, sig, _ = collect()
    largest = INJECT_RMS[-1]
    got = float(np.median(rows[(1, largest, sig)]))
    assert got < 0.8 * largest


@needs_data
def test_the_quadratic_eats_most_of_the_signal():
    """Why the quadratic column must not be read as a tighter estimate: it
    recovers well under half of what is injected."""
    _, rows, sig, _ = collect()
    for rms in INJECT_RMS:
        v = rows.get((2, rms, sig))
        if v:
            assert float(np.median(v)) < 0.5 * rms


@needs_data
def test_plane_carries_curvature_contamination_and_quadratic_does_not():
    """The two failure modes are real and opposite, which is why neither order is
    simply correct."""
    floors, _, _, _ = collect()
    assert float(np.median(floors[1])) > 0.1
    assert float(np.median(floors[2])) < 0.05
