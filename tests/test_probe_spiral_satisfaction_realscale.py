"""Real-scale/real-shape robustness of the whole-winding-blindness finding (see
probe_spiral_satisfaction_winding.py). The harness's own arithmetic must be
correct before its real-scale numbers mean anything -- these tests anchor the
new module to the pinned Task-3 result and check its own displacement math
directly, before trusting anything it reports about DR=12.81."""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import pytest
import torch
from probe_spiral_satisfaction_realscale import (
    RATIO_LEVELS,
    REAL_DR,
    SCALE_DRS,
    WINDING,
    run_cell,
)
from probe_spiral_satisfaction_winding import (
    build_synthetic_patch,
    displace,
    score,
)


def test_run_cell_at_dr100_ratio1_reproduces_pinned_finding():
    """Anchor: at DR=100, n_windings=1.0 (the original probe's exact setup),
    run_cell must reproduce the pinned Task-3 exact-zero delta bit-for-bit,
    cross-checked against a direct call to the ORIGINAL probe's own score()
    (not reimplemented arithmetic)."""
    result = run_cell(dr=100.0, n_windings=1.0)
    assert result["ref_combined"] == pytest.approx(1.0, abs=1e-9)
    assert result["disp_combined"] == pytest.approx(1.0, abs=1e-9)
    assert result["delta_combined"] == pytest.approx(0.0, abs=1e-6)

    ref = build_synthetic_patch(dr=100.0, winding=WINDING)
    whole = displace(ref, 100.0, n_windings=1.0)
    assert result["ref_combined"] == pytest.approx(score(ref, 100.0), abs=1e-9)
    assert result["disp_combined"] == pytest.approx(score(whole, 100.0), abs=1e-9)


def test_scale_sweep_grid_covers_required_dr_values():
    """The task pins this exact grid: the original value, two intermediates,
    the real median, and the real p05."""
    assert SCALE_DRS == [100.0, 50.0, 25.0, 12.81, 8.04]


def test_scale_invariance_holds_at_every_pinned_dr():
    """The pre-registered algebra says the whole-winding invariance is exact
    for ANY dr under IdentityTransform with no scatter (both the transform
    and the scale cancel). If this fails at any grid point, that is itself
    the major finding this task exists to surface -- do not weaken this
    assertion to make it pass; if it fails, the report must say so loudly."""
    for dr in SCALE_DRS:
        result = run_cell(dr=dr, n_windings=1.0)
        assert result["ref_combined"] == pytest.approx(1.0, abs=1e-9), dr
        assert result["disp_combined"] == pytest.approx(1.0, abs=1e-9), dr
        assert result["delta_combined"] == pytest.approx(0.0, abs=1e-6), dr
        assert result["ref_spiral"] == pytest.approx(1.0, abs=1e-9), dr
        assert result["ref_scan"] == pytest.approx(1.0, abs=1e-9), dr
        assert result["disp_spiral"] == pytest.approx(1.0, abs=1e-9), dr
        assert result["disp_scan"] == pytest.approx(1.0, abs=1e-9), dr


def test_realistic_ratio_grid_matches_measured_quantiles():
    """The task pins this exact grid: p05, the [0.8,1.25] band edges, p50,
    p75, the other band edge, and p95 of the measured real adjacent-gap
    ratio distribution (reports/real_winding_nonlinearity.txt section 2)."""
    assert RATIO_LEVELS == [0.72, 0.80, 0.8939, 0.9985, 1.1155, 1.25, 1.38]


def test_ratio_one_at_real_dr_matches_whole_winding_invariance():
    """Sanity anchor: ratio == 1.0 at the real dr is exactly the whole-winding
    displacement case, so it must reproduce the same zero-delta invariance as
    the DR=100 pinned result -- not a new, different computation."""
    result = run_cell(dr=REAL_DR, n_windings=1.0)
    assert result["delta_combined"] == pytest.approx(0.0, abs=1e-6)
    assert result["ref_combined"] == pytest.approx(1.0, abs=1e-9)
    assert result["disp_combined"] == pytest.approx(1.0, abs=1e-9)


def test_run_cell_displacement_is_dr_times_ratio_not_flat_dr():
    """run_cell's displacement for a fractional ratio must move the patch's
    shifted radius by exactly ratio * dr, not by a flat dr -- this is the
    conceptual correction this task makes over the idealized sweep (moving
    to the adjacent wrap means moving by the LOCAL gap, which varies)."""
    sys.path.insert(
        0, os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
    )
    from sample_spiral import get_theta_and_radii

    ratio = 0.72
    ref = build_synthetic_patch(dr=REAL_DR, winding=WINDING)
    moved = displace(ref, REAL_DR, n_windings=ratio)

    dr_t = torch.tensor(REAL_DR)
    _, _, before = get_theta_and_radii(ref.zyxs[..., 1:], dr_t)
    _, _, after = get_theta_and_radii(moved.zyxs[..., 1:], dr_t)
    assert torch.allclose(
        after - before, torch.full_like(before, ratio * REAL_DR), atol=1e-4
    )


def test_half_winding_control_still_rejected_at_real_dr():
    """Sanity control at the real scale: the harness must still be capable of
    reporting dissatisfaction (a half-winding offset sits outside the
    0.45*dr spiral tolerance), or the real-scale numbers below are not
    exercising the metric at all."""
    result = run_cell(dr=REAL_DR, n_windings=0.5)
    assert result["disp_combined"] < 0.5
