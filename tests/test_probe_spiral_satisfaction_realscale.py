"""Real-scale/real-shape robustness of the whole-winding-blindness finding (see
probe_spiral_satisfaction_winding.py). The harness's own arithmetic must be
correct before its real-scale numbers mean anything -- these tests anchor the
new module to the pinned Task-3 result and check its own displacement math
directly, before trusting anything it reports about DR=12.81."""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import re

import pytest
import torch
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_realscale import (
    RATIO_LEVELS,
    REAL_DR,
    SCALE_DRS,
    WINDING,
    format_report,
    max_ratio_deviation,
    run_cell,
)
from probe_spiral_satisfaction_winding import (
    build_synthetic_patch,
    displace,
    score,
)

restore_cuda_env()  # do not leave the mask for other test modules


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


# --- Fix round 1: CRITICAL -- a hand-typed narrative statistic ("about
# 0.28-0.38 of a winding") that did not actually track RATIO_LEVELS (the
# original text was wrong even at the time it was written: the true max
# deviation across the pinned grid is 0.38 at ratio=1.38, not a "0.28-0.38"
# range -- 0.28 was the deviation of a DIFFERENT row, ratio=0.72). The tests
# below anchor the fix: the helper's own arithmetic, and that the rendered
# report text agrees with what RATIO_LEVELS actually implies.


def test_max_ratio_deviation_matches_hand_computed_values():
    """max_ratio_deviation must return the (deviation, ratio) pair for
    whichever row's n_windings sits FARTHEST from the nearest integer
    winding -- checked against a small hand-built rows_b, not against
    RATIO_LEVELS itself."""
    rows_b = [{"n_windings": v} for v in [0.72, 0.9985, 1.38]]
    dev, ratio = max_ratio_deviation(rows_b)
    # |0.72-1|=0.28, |0.9985-1|=0.0015, |1.38-1|=0.38 -- 1.38 is farthest.
    assert dev == pytest.approx(0.38, abs=1e-9)
    assert ratio == pytest.approx(1.38, abs=1e-9)


def test_max_ratio_deviation_on_pinned_ratio_levels():
    """Sanity anchor on the actual pinned RATIO_LEVELS grid: the true
    farthest-from-integer point is ratio=1.38 (deviation 0.38), which is
    coincidentally one of the two numbers the original hand-typed text used
    -- but the text wrongly implied a RANGE (0.28-0.38) rather than the
    single correct max-deviation value."""
    rows_b = [{"n_windings": r} for r in RATIO_LEVELS]
    dev, ratio = max_ratio_deviation(rows_b)
    assert ratio == pytest.approx(1.38, abs=1e-9)
    assert dev == pytest.approx(0.38, abs=1e-9)


def _synthetic_rows(drs_or_ratios, dr_key_is_ratio, fixed_dr=None):
    """Build minimal synthetic row dicts carrying only the fields
    format_report() reads, all pinned to the "everything satisfied, zero
    delta" case -- used to render the report text WITHOUT re-deriving the
    fields from a real get_patch_satisfied_areas call, since this helper
    exists only to test format_report()'s TEXT RENDERING, which is already
    covered elsewhere by tests that go through the real metric."""
    rows = []
    for v in drs_or_ratios:
        dr = fixed_dr if dr_key_is_ratio else v
        n_windings = v if dr_key_is_ratio else 1.0
        rows.append(
            {
                "dr": dr,
                "n_windings": n_windings,
                "ref_spiral": 1.0,
                "ref_scan": 1.0,
                "ref_combined": 1.0,
                "disp_spiral": 1.0,
                "disp_scan": 1.0,
                "disp_combined": 1.0,
                "delta_combined": 0.0,
            }
        )
    return rows


def test_narrative_deviation_matches_ratio_levels_not_hardcoded():
    """Drift guard for the CRITICAL fix: the Experiment B Result paragraph's
    quoted 'largest observed deviation ... of a winding' figure must match
    what RATIO_LEVELS actually implies. The expected value is computed here
    INDEPENDENTLY of max_ratio_deviation (by hand, from RATIO_LEVELS
    directly) and then compared against what is parsed out of the rendered
    report TEXT -- exactly what a reviewer reading only the .txt file would
    have to redo by hand, automated. This is the same technique
    measure_real_winding_nonlinearity.py's sibling drift-guard test uses."""
    rows_a = _synthetic_rows(SCALE_DRS, dr_key_is_ratio=False)
    rows_b = _synthetic_rows(RATIO_LEVELS, dr_key_is_ratio=True, fixed_dr=REAL_DR)
    report = format_report(rows_a, rows_b)

    expected_ratio = max(RATIO_LEVELS, key=lambda r: abs(r - round(r)))
    expected_dev = abs(expected_ratio - round(expected_ratio))

    m = re.search(r"quantiles is ([\d.]+) of a winding \(at ratio=([\d.]+)\)", report)
    assert m is not None, "expected deviation sentence not found in rendered report"
    parsed_dev = float(m.group(1))
    parsed_ratio = float(m.group(2))
    assert parsed_dev == pytest.approx(expected_dev, abs=5e-5)
    assert parsed_ratio == pytest.approx(expected_ratio, abs=5e-5)


def test_report_column_header_does_not_overclaim_rejection():
    """IMPORTANT fix guard: the scale-sweep table's tolerance-comparison
    column must be headed something that states it is a tolerance-magnitude
    comparison (e.g. 'tighter_tol'), never the unqualified 'binds', and the
    report must state near that table that scatter is zero so nothing was
    empirically observed to reject anything there."""
    rows_a = _synthetic_rows(SCALE_DRS, dr_key_is_ratio=False)
    rows_b = _synthetic_rows(RATIO_LEVELS, dr_key_is_ratio=True, fixed_dr=REAL_DR)
    report = format_report(rows_a, rows_b)

    assert "tighter_tol" in report
    assert "binds" not in report
    assert "scatter is held at zero" in report.lower()
