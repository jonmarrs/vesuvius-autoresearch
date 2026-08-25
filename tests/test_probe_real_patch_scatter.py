"""Tests for the real-patch-scatter probe.

The headline number is only meaningful because the window is matched to the
synthetic patch's real-space extent. The first version of this measurement used a
window five to fifteen times too large and got an answer that pointed the opposite
way, so the tests here are mostly about that: that the sensitivity is real, that
the matched window is chosen by extent rather than by convenience, and that the
radius is measured from the umbilicus rather than from an arbitrary origin.
"""

import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_real_patch_scatter import (  # noqa: E402
    SYNTHETIC_EXTENT_VOX,
    WINDOWS,
    closest_window,
    collect,
    load_umbilicus,
    patch_dirs,
    radius_field,
    window_residuals,
)


def test_patches_are_present():
    """Guard on the premise: without real patches this probe measures nothing."""
    assert len(patch_dirs()) >= 5


def test_scatter_grows_monotonically_with_window_extent():
    """The central methodological claim, and the reason a single number would be
    misleading. If residual did NOT grow with window size, the first attempt's
    8.1-voxel median and this one's 0.85 would have to be reconciled some other
    way, and the 'curvature not roughness' explanation would be wrong."""
    _, cells = collect()
    medians = [
        np.median(cells[(h, w, 1)])
        for h, w in WINDOWS
        if (h, w, 1) in cells and cells[(h, w, 1)].size
    ]
    assert len(medians) >= 3
    assert medians == sorted(medians)
    assert medians[-1] > 3 * medians[0]


def test_the_comparable_window_is_chosen_by_real_extent():
    """The matched window must be the one whose voxel extent is closest to the
    synthetic patch, not the largest or the first. With a ~20 voxel grid step the
    synthetic patch's ~22x64 voxels lands on the smallest window in the sweep."""
    per_patch, _ = collect()
    best, med_step = closest_window(per_patch)
    assert best in WINDOWS
    extent = (best[0] * med_step[0], best[1] * med_step[1])
    for h, w in WINDOWS:
        if (h, w) == best:
            continue
        other = (h * med_step[0], w * med_step[1])
        cost_best = sum(
            abs(np.log(e / t))
            for e, t in zip(extent, SYNTHETIC_EXTENT_VOX, strict=False)
        )
        cost_other = sum(
            abs(np.log(e / t))
            for e, t in zip(other, SYNTHETIC_EXTENT_VOX, strict=False)
        )
        assert cost_best <= cost_other


def test_radius_is_measured_from_the_umbilicus_not_the_origin():
    """A radius taken from the volume origin instead of the scroll axis would be
    wrong by the axis offset, which is thousands of voxels here."""
    umb = load_umbilicus()
    uz, ux, uy = umb
    zs = np.full((4, 4), float(np.median(uz)))
    xs = np.full((4, 4), float(np.interp(np.median(uz), uz, ux)) + 100.0)
    ys = np.full((4, 4), float(np.interp(np.median(uz), uz, uy)))
    r = radius_field(xs, ys, zs, umb)
    assert np.allclose(r, 100.0, atol=1e-6)
    assert float(np.hypot(xs[0, 0], ys[0, 0])) > 1000.0


def test_residuals_use_only_fully_valid_windows():
    """A window containing an invalid (-1) cell would contribute a spurious
    residual of thousands of voxels."""
    rng = np.random.default_rng(0)
    r = np.zeros((8, 8))
    r[4, 4] = 10_000.0
    valid = np.ones((8, 8), dtype=bool)
    valid[4, 4] = False
    res = window_residuals(r, valid, 3, 4, 1, rng, n_samples=50)
    assert res.size > 0
    assert res.max() == pytest.approx(0.0, abs=1e-9)


def test_a_flat_surface_has_no_scatter():
    """Anchor: a perfectly smooth radius field must give a zero residual, or the
    fit is not removing the trend it claims to."""
    rng = np.random.default_rng(1)
    ii, jj = np.mgrid[0:12, 0:12]
    r = 500.0 + 3.0 * ii + 1.5 * jj
    res = window_residuals(r, np.ones_like(r, dtype=bool), 3, 4, 1, rng, n_samples=20)
    assert res.size > 0
    assert res.max() == pytest.approx(0.0, abs=1e-6)
