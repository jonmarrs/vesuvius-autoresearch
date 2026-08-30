"""The frozen detector's rule is a property, so it is pinned rather than trusted.

This project's recorded failure mode is a property measured once and never
re-checked. The thresholds here are frozen in
`docs/preregistration/2026-08-29_sheet_switch_detector.md`, and a threshold that
drifts silently would invalidate every number reported against it, including the
5.02%-versus-5% verdict that the whole September bet currently turns on.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)

import detect_sheet_switches as det  # noqa: E402


def cache(arrays):
    """arrays: list of (winding_idx, satisfied) pairs."""
    return {
        "patches": [(f"p{i}", a) for i, (a, _) in enumerate(arrays)],
        "satisfied": [(f"p{i}", m) for i, (_, m) in enumerate(arrays)],
    }


def test_frozen_thresholds_have_not_drifted():
    """If either constant changes, every reported number becomes incomparable."""
    assert det.MIN_MINORITY_FRACTION == 0.10
    assert det.MIN_MINORITY_QUADS == 16


def test_a_single_winding_patch_is_never_flagged():
    a = np.full((20, 20), 7, dtype=np.int32)
    flagged, _ = det.flag_patches(cache([(a, np.ones_like(a, bool))]))
    assert flagged == []


def test_a_half_and_half_split_is_flagged():
    """The signature the baseline work found: two large regions, adjacent windings."""
    a = np.full((20, 20), 7, dtype=np.int32)
    a[:, 10:] = 8
    flagged, recs = det.flag_patches(cache([(a, np.ones_like(a, bool))]))
    assert flagged == ["p0"]
    assert recs[0]["minority_fraction"] == pytest.approx(0.5)


def test_a_few_stray_quads_are_not_flagged():
    """Below the fraction threshold: noise must stay quiet, or the detector is not
    conservative in the sense the wish list asks for."""
    a = np.full((20, 20), 7, dtype=np.int32)
    a.reshape(-1)[:20] = 8  # 20/400 = 5%, under 10%
    flagged, _ = det.flag_patches(cache([(a, np.ones_like(a, bool))]))
    assert flagged == []


def test_the_quad_floor_binds_on_small_patches():
    """A large FRACTION on a tiny patch is still too few quads to be a switch."""
    a = np.full((6, 6), 7, dtype=np.int32)
    a[:, 3:] = (
        8  # 50% minority, but only 18 quads total and 18 minority... too small overall
    )
    flagged, _ = det.flag_patches(cache([(a, np.ones_like(a, bool))]))
    assert flagged == ["p0"]  # 18 >= 16, so this one does flag
    b = np.full((4, 4), 7, dtype=np.int32)
    b[:, 2:] = 8  # 8 minority quads, under the 16 floor
    flagged2, _ = det.flag_patches(cache([(b, np.ones_like(b, bool))]))
    assert flagged2 == []


def test_unsatisfied_quads_are_excluded_from_the_statistic():
    """A winding index is meaningless where the metric rejected the quad. If the
    minority region is entirely unsatisfied, the patch must not flag."""
    a = np.full((20, 20), 7, dtype=np.int32)
    a[:, 10:] = 8
    m = np.ones_like(a, bool)
    m[:, 10:] = False  # the whole minority region is rejected
    flagged, _ = det.flag_patches(cache([(a, m)]))
    assert flagged == []


def test_untargeted_quads_are_excluded():
    """-1 marks a quad with no assigned target and must not count as a winding."""
    a = np.full((20, 20), 7, dtype=np.int32)
    a[:, 10:] = -1
    flagged, _ = det.flag_patches(cache([(a, np.ones_like(a, bool))]))
    assert flagged == []
