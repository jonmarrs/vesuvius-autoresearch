"""Robustness of the whole-winding-blindness finding (see
`probe_spiral_satisfaction_winding.py`) to two real-world conditions the
ideal probe does not exercise: patch scatter and a nonlinear scan<->spiral
transform.

Why the ideal probe's result is not automatically robust
----------------------------------------------------------
For a patch lying EXACTLY on a winding, the invariance is provably exact for
ANY invertible transform T (forward, scan->spiral) with inverse T_inv
(spiral->scan): the displaced patch is

    p' = T_inv(T(p) + delta)

and the metric's own snap-target for p' lands at exactly T(p) + delta (delta
= one winding's worth of spiral-space radius, at fixed theta/z), which
T_inv maps back to exactly p'. The scan-space distance the metric checks is
therefore 0 both before and after the displacement, and T cancels out of the
comparison entirely. This is why the original probe could use
`IdentityTransform` without loss of generality for that ideal case.

Real patches are not exact -- they sit at some nonzero spiral-space
scatter distance `d` from their true winding. After a one-winding
displacement the scan-space check instead compares

    ||T_inv(target + delta) - T_inv(T(p) + delta)||   vs   ||T_inv(target) - T_inv(T(p))||

and for a NONLINEAR T_inv these need not be equal, because the deformation
stretches space differently at different radii. This script measures how far
that comparison drifts from exact as scatter and nonlinearity both increase,
for the same synthetic patch geometry the ideal probe used.

Two independent knobs are swept, at fixed pre-registered `DR`, tolerances,
and base patch geometry (unchanged from the ideal probe):

1. Patch scatter: zero-mean Gaussian noise added to each point's spiral-space
   radius (see `add_radius_scatter`), with std = `scatter_std_frac * DR`.
   The SAME per-point unit-normal draw (fixed seed `SCATTER_SEED`) is reused
   across every scatter level, scaled by the level -- so the sweep varies
   only the noise magnitude, never its direction, keeping levels comparable.
   scatter_std_frac == 0.0 is a true no-op (see `add_radius_scatter`).

2. Nonlinearity: `RadialPowerLawTransform`, a purely radial warp with an
   exact closed-form inverse (see its docstring for the algebra).
   alpha == 1.0 dispatches to the real `IdentityTransform` from the ideal
   probe (not the power-law's own alpha=1 case), so the zero/zero cell is
   bit-exact with the original finding, not merely numerically close to it.

CAVEAT -- the alpha sweep is intentionally bounded at 0.60, and the finding
does NOT extrapolate past that bound
--------------------------------------------------------------------------
`ALPHA_LEVELS` stops at 0.60 (a fairly aggressive but not extreme radial
compression). That bound was a deliberate choice, not a discovery that
degradation vanishes beyond it. Informal probing below the pinned bound
(scatter_std_frac=0.02, alpha=0.2 -- one step past the sweep's most
aggressive cell) found the invariant break substantially more, with
delta_combined around -0.36, roughly 8x the pinned worst case of -0.042.
That number is NOT part of the pinned sweep grid and is NOT re-derived by
this script (no test pins it) -- it is reported here only so a reader of
this file, or of the generated report's footer, does not conclude the
whole-winding blindness is unconditional across realistic nonlinearity. It
survives comfortably within the pinned grid; it is not proven to survive
arbitrarily aggressive nonlinearity.

For each (scatter, alpha) cell we report the reference (winding=5) satisfied
fraction, the +1-winding-displaced satisfied fraction, their delta, and the
per-condition breakdown (spiral-space tolerance / scan-space tolerance) for
both, via `probe_spiral_satisfaction_winding.score_conditions`'s technique of
neutralizing one tolerance at a time through villa's own `metrics_overrides`
hook -- every number in the table comes from a real call to villa's
unmodified `get_patch_satisfied_areas`.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_robustness.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from probe_spiral_satisfaction_winding import (  # noqa: E402
    _NEUTRAL_TOLERANCE,
    DR,
    Z_BEGIN,
    Z_END,
    IdentityTransform,
    SyntheticPatch,
    build_synthetic_patch,
    displace,
    get_patch_satisfied_areas,
)

WINDING = 5
SCATTER_SEED = 20260824


class RadialPowerLawTransform:
    """A smooth, invertible, purely-radial warp: leaves theta = atan2(y, x)
    and z untouched, and maps radius r = sqrt(y^2 + x^2) by a power law
    anchored at a reference radius r0:

        s = r0 * (r / r0) ** alpha                       (forward, scan->spiral)
        r = r0 * (s / r0) ** (1 / alpha)                  (inverse, spiral->scan)

    These are exact algebraic inverses for any alpha != 0, r0 > 0, r > 0:

        T_inv(T(r)) = r0 * ( (r0 * (r/r0)**alpha) / r0 ) ** (1/alpha)
                    = r0 * ( (r/r0)**alpha ) ** (1/alpha)
                    = r0 * (r/r0)
                    = r

    alpha == 1.0 reduces algebraically to the identity map (though this
    class is never used for alpha == 1.0 in the sweep below -- see
    `build_transform`). alpha < 1 compresses radii above r0 (and expands
    below); alpha > 1 does the reverse. Either way the map stretches space
    by a DIFFERENT factor at different radii, which is exactly the property
    under test: the metric's spiral-space tolerance (a fraction of dr) and
    its scan-space tolerance (an absolute voxel count) are anchored at
    different radii after a one-winding displacement, so a radius-dependent
    stretch can decouple them.

    All arithmetic is done in float64 internally regardless of the input's
    dtype, then cast back to the input's dtype on return, to keep the
    round-trip error at float64 machine precision rather than compounding
    the caller's own working precision.
    """

    def __init__(self, alpha, r0):
        if alpha == 0.0:
            raise ValueError("alpha must be nonzero for the inverse to exist")
        self.alpha = float(alpha)
        self.r0 = float(r0)

    def __call__(self, zyxs):
        return self._map(zyxs, self.alpha)

    def inv(self, zyxs):
        return self._map(zyxs, 1.0 / self.alpha)

    def _map(self, zyxs, exponent):
        in_dtype = zyxs.dtype
        zyxs64 = zyxs.to(torch.float64)
        z = zyxs64[..., 0]
        y = zyxs64[..., 1]
        x = zyxs64[..., 2]
        r = torch.sqrt(y**2 + x**2)
        theta = torch.atan2(y, x)
        r_new = self.r0 * (r / self.r0) ** exponent
        out = torch.stack(
            [z, torch.sin(theta) * r_new, torch.cos(theta) * r_new], dim=-1
        )
        return out.to(in_dtype)


def build_transform(alpha, r0):
    """alpha == 1.0 dispatches to the real IdentityTransform (bit-exact, no
    float64 round trip) rather than RadialPowerLawTransform's own algebraic
    alpha=1 case, so the zero-nonlinearity sweep row is bit-exact with the
    original probe's pinned finding, not merely close to it."""
    if alpha == 1.0:
        return IdentityTransform()
    return RadialPowerLawTransform(alpha=alpha, r0=r0)


def draw_unit_noise(n_rows, n_cols, seed=SCATTER_SEED):
    """A fixed, reproducible (n_rows, n_cols) standard-normal draw, reused
    at every scatter level in the sweep (scaled by that level), so the sweep
    varies noise magnitude only, never its direction."""
    generator = torch.Generator().manual_seed(seed)
    return torch.randn(n_rows, n_cols, generator=generator, dtype=torch.float32)


def add_radius_scatter(patch, unit_noise, scatter_std_frac, dr):
    """Perturb each point's spiral-space radius by independent Gaussian
    noise (unit_noise * scatter_std_frac * dr), holding theta and z fixed.

    scatter_std_frac == 0.0 is a TRUE no-op: it returns `patch` itself
    without recomputing radius/theta from y/x, so the zero-scatter cells of
    the sweep cannot pick up any sqrt/atan2/sin/cos round-trip noise of
    their own -- only genuine scatter effects show up in nonzero rows.
    """
    if scatter_std_frac == 0.0:
        return patch
    zyxs = patch.zyxs.clone()
    ys = zyxs[..., 1]
    xs = zyxs[..., 2]
    radii = torch.sqrt(ys**2 + xs**2)
    thetas = torch.arctan2(ys, xs)
    noisy_radii = radii + unit_noise * scatter_std_frac * dr
    zyxs[..., 1] = torch.sin(thetas) * noisy_radii
    zyxs[..., 2] = torch.cos(thetas) * noisy_radii
    return SyntheticPatch(
        zyxs=zyxs, valid_quad_mask=patch.valid_quad_mask.clone(), area=patch.area
    )


def _to_scan_space(spiral_patch, transform):
    """Apply T_inv pointwise to a patch's geometry, treating `spiral_patch`
    as living in spiral space and producing the corresponding scan-space
    patch that `get_patch_satisfied_areas` expects as input (it applies the
    forward transform internally to recover spiral space)."""
    return SyntheticPatch(
        zyxs=transform.inv(spiral_patch.zyxs),
        valid_quad_mask=spiral_patch.valid_quad_mask.clone(),
        area=spiral_patch.area,
    )


def score_conditions_with_transform(patch, dr, transform):
    """Same technique as `probe_spiral_satisfaction_winding.score_conditions`
    (villa's own `metrics_overrides` hook neutralizes one tolerance at a
    time), generalized to an arbitrary transform instead of the hardcoded
    IdentityTransform. Returns (spiral_fraction, scan_fraction,
    combined_fraction); every number comes from a real call to villa's
    unmodified `get_patch_satisfied_areas`."""
    total = int(patch.valid_quad_mask.sum().item())

    def _fraction(overrides=None):
        _, _, _, masks, _, _ = get_patch_satisfied_areas(
            transform,
            torch.tensor(dr),
            [patch],
            Z_BEGIN,
            Z_END,
            metrics_overrides=overrides,
        )
        return int(masks[0].sum().item()) / max(total, 1)

    spiral_fraction = _fraction({"satisfaction_distance_tolerance": _NEUTRAL_TOLERANCE})
    scan_fraction = _fraction({"satisfaction_radius_tolerance": _NEUTRAL_TOLERANCE})
    combined_fraction = _fraction(None)
    return spiral_fraction, scan_fraction, combined_fraction


def run_cell(
    scatter_std_frac, alpha, unit_noise, dr=DR, winding=WINDING, n_windings=1.0
):
    """One (scatter, alpha) cell of the sweep. Builds the ideal spiral-space
    patch, adds scatter, derives the +n_windings-displaced spiral-space
    patch from the SAME noisy geometry (so both share the identical noise
    realization), maps both to scan space through T_inv for the chosen
    transform, and scores both through villa's unmodified metric.

    Returns a dict with the per-condition fractions for both the reference
    and displaced patch, plus their combined-fraction delta.
    """
    base = build_synthetic_patch(dr=dr, winding=winding)
    noisy_spiral = add_radius_scatter(base, unit_noise, scatter_std_frac, dr)
    displaced_spiral = displace(noisy_spiral, dr, n_windings=n_windings)

    transform = build_transform(alpha, r0=winding * dr)

    ref_scan = _to_scan_space(noisy_spiral, transform)
    disp_scan = _to_scan_space(displaced_spiral, transform)

    ref_spiral_f, ref_scan_f, ref_combined = score_conditions_with_transform(
        ref_scan, dr, transform
    )
    disp_spiral_f, disp_scan_f, disp_combined = score_conditions_with_transform(
        disp_scan, dr, transform
    )

    return {
        "scatter_std_frac": scatter_std_frac,
        "alpha": alpha,
        "ref_spiral": ref_spiral_f,
        "ref_scan": ref_scan_f,
        "ref_combined": ref_combined,
        "disp_spiral": disp_spiral_f,
        "disp_scan": disp_scan_f,
        "disp_combined": disp_combined,
        "delta_combined": disp_combined - ref_combined,
    }


SCATTER_LEVELS = [0.0, 0.01, 0.02, 0.05, 0.10]
ALPHA_LEVELS = [1.0, 0.95, 0.90, 0.80, 0.60]


def run_sweep():
    # build_synthetic_patch's defaults are n_rows=12, n_cols=16 -> zyxs shape
    # (12, 16, 3); unit_noise is per-POINT, matching that shape exactly.
    unit_noise = draw_unit_noise(12, 16)

    rows = []
    for scatter in SCATTER_LEVELS:
        for alpha in ALPHA_LEVELS:
            rows.append(run_cell(scatter, alpha, unit_noise))
    return rows


def format_report(rows):
    lines = []
    lines.append("Robustness sweep: patch scatter x nonlinear scan<->spiral transform")
    lines.append(
        f"seed = {SCATTER_SEED} (torch.Generator, one fixed (12,16) unit-normal "
        "draw reused at every scatter level, scaled by scatter_std_frac * dr)"
    )
    lines.append(
        f"dr = {DR}, winding = {WINDING} (unchanged from the ideal probe); "
        "scatter perturbs spiral-space radius only, before the +1-winding "
        "displacement, so reference and displaced share the identical noise draw"
    )
    lines.append(
        "transform: RadialPowerLawTransform  s = r0*(r/r0)**alpha, "
        f"r0 = winding*dr = {WINDING * DR:.1f}; exact closed-form inverse "
        "(see module docstring for the algebra); alpha=1.0 uses the real "
        "IdentityTransform, not the power-law's own alpha=1 case"
    )
    lines.append("")
    header = (
        f"{'scatter':>8} {'alpha':>6} | "
        f"{'ref_spiral':>10} {'ref_scan':>9} {'ref_comb':>9} | "
        f"{'disp_spiral':>11} {'disp_scan':>9} {'disp_comb':>9} | "
        f"{'delta_comb':>11}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        lines.append(
            f"{r['scatter_std_frac']:8.2f} {r['alpha']:6.2f} | "
            f"{r['ref_spiral']:10.6f} {r['ref_scan']:9.6f} {r['ref_combined']:9.6f} | "
            f"{r['disp_spiral']:11.6f} {r['disp_scan']:9.6f} {r['disp_combined']:9.6f} | "
            f"{r['delta_combined']:+11.6f}"
        )
    lines.append("")
    worst = max(rows, key=lambda r: abs(r["delta_combined"]))
    lines.append(
        "worst-case |delta_combined| = "
        f"{abs(worst['delta_combined']):.6f} at scatter_std_frac="
        f"{worst['scatter_std_frac']}, alpha={worst['alpha']}"
    )
    lines.append("")
    lines.append(
        "CAVEAT: alpha is intentionally bounded at 0.60 above. Informal, "
        "UNPINNED probing one step past this bound (scatter_std_frac=0.02, "
        "alpha=0.2) found delta_combined around -0.36 -- roughly 8x the "
        "worst-case above. This finding does not establish that the "
        "invariant survives nonlinearity more aggressive than alpha=0.60; "
        "it establishes only that it survives within the pinned grid."
    )
    return "\n".join(lines) + "\n"


def main():
    rows = run_sweep()
    report = format_report(rows)
    print(report)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(
        repo_root, "reports", "spiral_satisfaction_winding_robustness.txt"
    )
    with open(out_path, "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()
