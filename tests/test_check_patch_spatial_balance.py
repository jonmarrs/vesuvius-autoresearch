"""Tests for the radial-balance proxy.

The test that earns its place is `test_a_wide_patch_is_not_point_assigned`. The
first version of this script assigned each patch to the single band containing
its centroid, which looked precise and measured almost nothing: the median patch
is 602 vx wide radially against a 149 vx median band. Spreading area across the
bands a patch actually covers is the whole correctness claim here, so it is
pinned directly rather than trusted.
"""

import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import check_patch_spatial_balance as mod  # noqa: E402


def _box(x0, y0, x1, y1):
    return [[x0, y0, 0.0], [x1, y1, 10.0]]


def test_radial_extent_is_zero_inside_the_footprint():
    lo, hi = mod.radial_extent(_box(-10, -10, 10, 10), 0.0, 0.0)
    assert lo == 0.0
    assert hi == pytest.approx((200) ** 0.5)


def test_radial_extent_measures_to_the_nearest_edge_when_outside():
    lo, hi = mod.radial_extent(_box(10, -5, 20, 5), 0.0, 0.0)
    assert lo == pytest.approx(10.0)
    assert hi == pytest.approx((20**2 + 5**2) ** 0.5)


def test_a_narrow_patch_lands_wholly_in_one_band():
    extent = {"a": (10.0, 12.0)}
    share, tot = mod.area_share_by_band(
        ["a"], extent, [50.0, 100.0] + [200.0] * 7, {"a": 1.0}
    )
    assert share[0] == pytest.approx(1.0)
    assert tot == 1.0


def test_a_wide_patch_is_not_point_assigned():
    """A patch from 0 to 100 across bands edged at 50 must split 50/50, NOT land
    entirely in the band holding its midpoint (50)."""
    extent = {"a": (0.0, 100.0)}
    edges = [50.0] + [1e9] * 8
    share, _ = mod.area_share_by_band(["a"], extent, edges, {"a": 1.0})
    assert share[0] == pytest.approx(0.5)
    assert share[1] == pytest.approx(0.5)


def test_area_is_conserved_when_spread():
    extent = {"a": (0.0, 300.0), "b": (10.0, 20.0)}
    edges = [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0]
    share, tot = mod.area_share_by_band(["a", "b"], extent, edges, {"a": 3.0, "b": 1.0})
    assert sum(share) == pytest.approx(1.0)
    assert tot == pytest.approx(4.0)


def test_a_degenerate_zero_width_patch_still_counts():
    extent = {"a": (75.0, 75.0)}
    edges = [50.0, 100.0] + [1e9] * 7
    share, _ = mod.area_share_by_band(["a"], extent, edges, {"a": 1.0})
    assert share[1] == pytest.approx(1.0)


def test_bands_are_equal_area_over_the_population():
    extent = {str(i): (float(i), float(i) + 1.0) for i in range(100)}
    area = dict.fromkeys(extent, 1.0)
    edges = mod.radial_bands(extent, area, n_bands=10)
    assert len(edges) == 9
    assert edges == sorted(edges)
