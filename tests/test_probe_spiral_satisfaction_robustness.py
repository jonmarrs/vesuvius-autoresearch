"""The robustness sweep's own transform and noise machinery must be correct
before its degradation numbers mean anything."""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import re

import pytest
import torch
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_robustness import (
    DR,
    WINDING,
    RadialPowerLawTransform,
    add_radius_scatter,
    build_transform,
    format_report,
    run_cell,
    run_sweep,
    total_valid_quads,
    verdict_flips,
)
from probe_spiral_satisfaction_winding import IdentityTransform, build_synthetic_patch

restore_cuda_env()  # do not leave the mask for other test modules


def test_radial_power_law_round_trips_to_near_machine_epsilon():
    """T_inv(T(r)) must recover r to within float64 machine epsilon, or the
    'exact closed-form inverse' claim in the docstring is false and every
    downstream delta is contaminated by transform error, not scatter/
    nonlinearity error."""
    transform = RadialPowerLawTransform(alpha=0.6, r0=500.0)
    torch.manual_seed(0)
    z = torch.zeros(200, dtype=torch.float64)
    y = torch.empty(200, dtype=torch.float64).uniform_(-800, 800)
    x = torch.empty(200, dtype=torch.float64).uniform_(-800, 800)
    zyxs = torch.stack([z, y, x], dim=-1)

    spiral = transform(zyxs)
    back = transform.inv(spiral)

    r_before = torch.sqrt(zyxs[..., 1] ** 2 + zyxs[..., 2] ** 2)
    r_after = torch.sqrt(back[..., 1] ** 2 + back[..., 2] ** 2)
    torch.testing.assert_close(r_after, r_before, atol=1e-9, rtol=1e-9)


def test_radial_power_law_round_trips_for_several_alphas():
    """Same round-trip property must hold for expansion (alpha>1) as well as
    compression (alpha<1), not just the one value exercised above."""
    torch.manual_seed(1)
    z = torch.zeros(50, dtype=torch.float64)
    y = torch.empty(50, dtype=torch.float64).uniform_(-800, 800)
    x = torch.empty(50, dtype=torch.float64).uniform_(100, 800)
    zyxs = torch.stack([z, y, x], dim=-1)
    for alpha in [0.4, 0.8, 1.3, 2.0]:
        transform = RadialPowerLawTransform(alpha=alpha, r0=500.0)
        back = transform.inv(transform(zyxs))
        torch.testing.assert_close(back, zyxs, atol=1e-8, rtol=1e-8)


def test_radial_power_law_is_not_a_no_op():
    """Sanity check that the transform actually deforms space for alpha != 1
    -- otherwise a 'no degradation' result at nonzero alpha would be
    meaningless (the transform, not the invariance, would be inert)."""
    transform = RadialPowerLawTransform(alpha=0.5, r0=500.0)
    zyx = torch.tensor([[0.0, 0.0, 600.0]], dtype=torch.float64)
    out = transform(zyx)
    r_in = 600.0
    r_out = torch.sqrt(out[..., 1] ** 2 + out[..., 2] ** 2).item()
    assert abs(r_out - r_in) > 1.0


def test_build_transform_alpha_one_is_the_real_identity_transform():
    """alpha == 1.0 must dispatch to the actual IdentityTransform used by the
    original probe, not a power-law special case that merely approximates
    identity -- this is what keeps the zero-scatter/zero-nonlinearity cell
    bit-exact with the pinned finding."""
    transform = build_transform(1.0, r0=500.0)
    assert isinstance(transform, IdentityTransform)


def test_add_radius_scatter_is_a_true_noop_at_zero_std():
    """scatter_std_frac == 0.0 must return the identical patch object (not a
    recomputed-but-numerically-close one), so the zero-scatter row of the
    sweep cannot pick up any transform round-trip noise of its own."""
    patch = build_synthetic_patch(dr=DR, winding=WINDING)
    unit_noise = torch.ones(patch.zyxs.shape[:2])
    out = add_radius_scatter(patch, unit_noise, 0.0, DR)
    assert out is patch


def test_add_radius_scatter_changes_radius_not_theta_or_z():
    patch = build_synthetic_patch(dr=DR, winding=WINDING)
    unit_noise = torch.ones(patch.zyxs.shape[:2])
    out = add_radius_scatter(patch, unit_noise, 0.1, DR)

    z_before, y_before, x_before = patch.zyxs.unbind(-1)
    z_after, y_after, x_after = out.zyxs.unbind(-1)
    theta_before = torch.arctan2(y_before, x_before)
    theta_after = torch.arctan2(y_after, x_after)
    r_before = torch.sqrt(y_before**2 + x_before**2)
    r_after = torch.sqrt(y_after**2 + x_after**2)

    torch.testing.assert_close(z_after, z_before)
    torch.testing.assert_close(theta_after, theta_before, atol=1e-5, rtol=1e-5)
    # unit_noise is all +1.0, so every point's radius grows by exactly
    # 0.1 * DR.
    torch.testing.assert_close(
        r_after - r_before, torch.full_like(r_before, 0.1 * DR), atol=1e-3, rtol=0
    )


def test_zero_scatter_zero_nonlinearity_reproduces_pinned_finding():
    """The regression this whole task is built on top of: at scatter=0.0,
    alpha=1.0, the +1-winding delta must still be exactly zero (the original
    Task 3 result), because both new knobs are true no-ops at their zero
    settings."""
    unit_noise = torch.zeros(12, 16)  # shape of the default synthetic patch's rows/cols
    result = run_cell(scatter_std_frac=0.0, alpha=1.0, unit_noise=unit_noise)
    assert result["delta_combined"] == pytest.approx(0.0, abs=1e-6)
    assert result["ref_combined"] == pytest.approx(1.0, abs=1e-9)


def test_a_half_winding_offset_control_still_rejected_at_zero_knobs():
    """Sanity: run_cell's machinery must still be capable of reporting
    dissatisfaction when the two new knobs are off, matching the original
    probe's control."""
    unit_noise = torch.zeros(12, 16)
    result = run_cell(
        scatter_std_frac=0.0, alpha=1.0, unit_noise=unit_noise, n_windings=0.5
    )
    assert result["disp_combined"] < 0.5


def _fake_row(scatter, alpha, ref_combined, disp_combined):
    """A minimal sweep row for the drift guard. Only the fields
    format_report/verdict_flips read are populated; the per-condition columns
    are filled with the combined value because they are not under test here."""
    return {
        "scatter_std_frac": scatter,
        "alpha": alpha,
        "ref_spiral": 1.0,
        "ref_scan": ref_combined,
        "ref_combined": ref_combined,
        "disp_spiral": 1.0,
        "disp_scan": disp_combined,
        "disp_combined": disp_combined,
        "delta_combined": disp_combined - ref_combined,
    }


def test_verdict_flip_is_not_predicted_by_delta_magnitude():
    """The reasoning error this guard exists to prevent: using |delta| as a
    proxy for 'does villa's verdict change'. Two hand-built cells, one with a
    LARGE delta whose arms both sit far below threshold (no flip) and one with
    a SMALLER delta straddling it (flip). If verdict_flips ever starts ranking
    by delta magnitude, this fails."""
    total = total_valid_quads()
    threshold = 0.95
    big_delta_no_flip = _fake_row(0.10, 0.60, 0.60, 0.20)
    small_delta_flip = _fake_row(0.05, 0.80, 159 / total, 156 / total)
    assert abs(big_delta_no_flip["delta_combined"]) > abs(
        small_delta_flip["delta_combined"]
    )

    flips = verdict_flips(
        [big_delta_no_flip, small_delta_flip], total_quads=total, threshold=threshold
    )
    assert len(flips) == 1
    assert flips[0]["scatter_std_frac"] == 0.05
    assert flips[0]["ref_satisfied"] is True
    assert flips[0]["disp_satisfied"] is False


def test_report_verdict_flip_line_matches_the_rows_not_a_literal():
    """Drift guard in the style of the realscale probe's: render the report
    from known rows and re-derive the expected flip count HERE, independently
    of verdict_flips, straight from villa's rule applied to integer quad
    counts. Then compare it against what is parsed out of the rendered report
    TEXT -- the arithmetic a reviewer reading only the .txt would have to redo
    by hand, automated."""
    total = total_valid_quads()
    rows = [
        _fake_row(0.00, 1.00, 1.0, 1.0),
        _fake_row(0.10, 0.60, 0.60, 0.20),
        _fake_row(0.05, 0.80, 159 / total, 156 / total),
    ]
    expected = sum(
        1
        for r in rows
        if (int(round(r["ref_combined"] * total)) >= 0.95 * total)
        != (int(round(r["disp_combined"] * total)) >= 0.95 * total)
    )
    assert expected == 1

    report = format_report(rows)
    m = re.search(r"^\s*(\d+) of (\d+) cells flip\.", report, re.MULTILINE)
    assert m is not None, "expected verdict-flip count sentence in rendered report"
    assert int(m.group(1)) == expected
    assert int(m.group(2)) == len(rows)


def test_pinned_sweep_has_exactly_one_verdict_flip():
    """Pins the measured finding itself: on the pinned grid, villa's
    patch-level verdict differs between the correctly-placed and the
    one-winding-displaced patch in exactly one cell -- scatter 0.05,
    alpha 0.80. This is the narrow counterexample to unconditional blindness
    under combined scatter and nonlinearity, and it must not silently move."""
    flips = verdict_flips(run_sweep())
    assert len(flips) == 1
    flip = flips[0]
    assert flip["scatter_std_frac"] == pytest.approx(0.05)
    assert flip["alpha"] == pytest.approx(0.80)
    assert flip["ref_satisfied"] is True
    assert flip["disp_satisfied"] is False
    assert flip["ref_quads"] == 159
    assert flip["disp_quads"] == 156
    assert flip["total_quads"] == 165
