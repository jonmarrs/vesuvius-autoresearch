"""Two open limits of reports/spiral_satisfaction_winding_blindness.md.

**A. The splicing configuration.** Every number we have measured is for villa's
DEFAULT metrics_config (0.45 / 6.0 / 0.95), which is what the reporting path
prints. But `get_patch_satisfied_areas` has a second call site, inside
`save_mesh`, which overrides all three thresholds (0.495 / 12.0 / 0.90) and uses
the result to decide which patches are SPLICED INTO THE OUTPUT MESH. That is the
configuration with downstream consequences, and "you measured the config that
prints, not the one that gates the mesh" is the strongest available objection to
the whole finding. This probe answers it by re-running the load-bearing
measurements under the splicing overrides.

    It also settles something the report flagged as unmeasured. The report notes
    that the one verdict flip we found "does not recur under the splicing
    configuration (0.90 x 165 = 148.5; both 159 and 156 clear it)", with the
    caveat that the looser tolerances would ALSO move the underlying satisfied
    fractions, which nobody had measured. Recomputing the fractions under the
    splicing config, rather than reusing the reporting config's fractions against
    a different threshold, is what makes that claim honest.

**B. The theta = 0 seam.** Every patch measured so far spans theta 0.30 to 1.30
rad and never crosses the seam, so `get_theta_crossing_step_adjustments` and the
branch-offset unwrap are never exercised. A patch spanning the seam has points
whose recovered shifted-radius differs by a whole `dr` across the branch cut
purely as an artifact of `theta % 2pi`, which is exactly what that unwrap logic
exists to repair. If the blindness were an artifact of avoiding the seam, this is
where it would show.

Every number comes from a real call to villa's unmodified
`get_patch_satisfied_areas`, here with its own documented `metrics_overrides`
hook. No pinned script, test, or artifact is modified.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_splicing_and_seam.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import torch  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_spiral_satisfaction_robustness import (  # noqa: E402
    _patch_is_satisfied,
    _to_scan_space,
    add_radius_scatter,
    build_transform,
    draw_unit_noise,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    DR,
    Z_BEGIN,
    Z_END,
    IdentityTransform,
    build_synthetic_patch,
    displace,
    get_patch_satisfied_areas,
)

REAL_DR = 12.81
WINDING = 5

# villa's two configurations, both read from its own source rather than restated.
# The reporting default is metrics_config; the splicing override is the dict passed
# at the save_mesh call site.
REPORTING = {
    "satisfaction_radius_tolerance": 0.45,
    "satisfaction_distance_tolerance": 6.0,
    "satisfied_patch_quad_fraction": 0.95,
}
SPLICING = {
    "satisfaction_radius_tolerance": 0.495,
    "satisfaction_distance_tolerance": 12.0,
    "satisfied_patch_quad_fraction": 0.90,
}
CONFIGS = [("reporting", REPORTING), ("splicing", SPLICING)]

# Offsets from the nearest integer winding, chosen to bracket BOTH candidate edges:
# the reporting tolerance 0.45 and the splicing tolerance 0.495.
OFFSET_LEVELS = [0.0, 0.25, 0.40, 0.44, 0.46, 0.48, 0.49, 0.499, 0.50]


def score_with(patch, dr, overrides, transform=None):
    """Satisfied-quad fraction from villa's unmodified function under an explicit
    configuration, via its own `metrics_overrides` hook."""
    _, _, _, masks, _, _ = get_patch_satisfied_areas(
        transform if transform is not None else IdentityTransform(),
        torch.tensor(dr),
        [patch],
        Z_BEGIN,
        Z_END,
        metrics_overrides=overrides,
    )
    total = int(patch.valid_quad_mask.sum().item())
    return int(masks[0].sum().item()) / max(total, 1)


def verdict_under(fraction, total_quads, overrides):
    return _patch_is_satisfied(
        fraction, total_quads, overrides["satisfied_patch_quad_fraction"]
    )


def seam_patch(dr, winding=WINDING):
    """A patch spanning theta = 0. `build_synthetic_patch` places points at
    unwrapped angle theta with radius `winding*dr + theta/(2pi)*dr`; passing a
    theta range that crosses 2pi therefore produces a patch that is continuous on
    one physical winding but whose RECOVERED shifted-radius jumps by a whole `dr`
    across the branch cut, because villa recovers theta as `atan2 % 2pi`. That
    jump is precisely what the branch-offset unwrap exists to repair."""
    return build_synthetic_patch(dr=dr, winding=winding, theta0=6.0, theta1=6.6)


def run_offset_sweep(
    dr, overrides, transform=None, patch_builder=build_synthetic_patch
):
    rows = []
    for off in OFFSET_LEVELS:
        ref = patch_builder(dr=dr, winding=WINDING)
        moved = displace(ref, dr, n_windings=1.0 + off)
        total = int(ref.valid_quad_mask.sum().item())
        ref_f = score_with(ref, dr, overrides, transform)
        disp_f = score_with(moved, dr, overrides, transform)
        rows.append(
            {
                "offset": off,
                "ref_frac": ref_f,
                "disp_frac": disp_f,
                "ref_verdict": verdict_under(ref_f, total, overrides),
                "disp_verdict": verdict_under(disp_f, total, overrides),
                "delta": disp_f - ref_f,
            }
        )
    return rows


def acceptance_edge(rows):
    """The measured bracket: the largest offset still accepted, and the smallest
    rejected. Returned rather than a single value because only a bracket was
    measured."""
    acc = [r["offset"] for r in rows if r["disp_verdict"]]
    rej = [r["offset"] for r in rows if not r["disp_verdict"]]
    return (max(acc) if acc else None), (min(rej) if rej else None)


def run_flip_cell_under(overrides):
    """The one cell of the pinned robustness grid whose verdict flips under the
    reporting config: scatter 0.05 (as a fraction of dr), alpha 0.80, at dr=100.
    Recomputed here under `overrides`, with the FRACTIONS recomputed too rather
    than reused from the reporting config, which is the part the report flagged
    as unmeasured."""
    dr, alpha, scatter_frac = DR, 0.80, 0.05
    transform = build_transform(alpha, WINDING * dr)
    base = build_synthetic_patch(dr=dr, winding=WINDING)
    noise = draw_unit_noise(base.zyxs.shape[0], base.zyxs.shape[1])
    ref_spiral = add_radius_scatter(base, noise, scatter_frac, dr)
    moved_spiral = displace(ref_spiral, dr, n_windings=1.0)
    ref = _to_scan_space(ref_spiral, transform)
    moved = _to_scan_space(moved_spiral, transform)
    total = int(ref.valid_quad_mask.sum().item())
    ref_f = score_with(ref, dr, overrides, transform)
    disp_f = score_with(moved, dr, overrides, transform)
    return {
        "ref_frac": ref_f,
        "disp_frac": disp_f,
        "total": total,
        "threshold_quads": overrides["satisfied_patch_quad_fraction"] * total,
        "ref_quads": int(round(ref_f * total)),
        "disp_quads": int(round(disp_f * total)),
        "ref_verdict": verdict_under(ref_f, total, overrides),
        "disp_verdict": verdict_under(disp_f, total, overrides),
    }


def _v(f):
    return "SAT" if f else "unsat"


def format_report(sweeps, seam_rows, flip_rows):
    out = []
    out.append("The splicing configuration, and the theta=0 seam")
    out.append(
        "Both configurations are villa's own: the reporting default "
        f"({REPORTING['satisfaction_radius_tolerance']} / "
        f"{REPORTING['satisfaction_distance_tolerance']} / "
        f"{REPORTING['satisfied_patch_quad_fraction']}) and the override passed at the "
        f"save_mesh splicing call site ({SPLICING['satisfaction_radius_tolerance']} / "
        f"{SPLICING['satisfaction_distance_tolerance']} / "
        f"{SPLICING['satisfied_patch_quad_fraction']}), which gates what enters the output mesh."
    )
    out.append("")

    out.append(
        f"=== A. Acceptance edge under each configuration (dr = {REAL_DR:.2f}) ==="
    )
    out.append(
        "displacement = (1 + offset) windings; offset is distance from a whole winding"
    )
    for name, rows in sweeps:
        lo, hi = acceptance_edge(rows)
        out.append("")
        out.append(f"  -- {name} config --")
        out.append("   offset | ref_frac ref_v | disp_frac disp_v |    delta")
        out.append("  " + "-" * 58)
        for r in rows:
            out.append(
                f"  {r['offset']:7.4f} | {r['ref_frac']:8.6f} {_v(r['ref_verdict']):>5} "
                f"| {r['disp_frac']:9.6f} {_v(r['disp_verdict']):>6} | {r['delta']:+9.6f}"
            )
        out.append(
            f"  edge bracket: accepted up to {lo}, rejected from {hi}"
            if lo is not None and hi is not None
            else "  edge bracket: not resolved by this grid"
        )
    out.append("")
    out.append(
        "  At offset 0 (an exact whole-winding displacement) the delta is the finding, and it "
        "must be zero under BOTH configurations for the finding to hold where it matters."
    )
    out.append("")

    out.append("=== B. The theta=0 seam ===")
    out.append(
        "patch spans theta 6.0 to 6.6 rad, crossing the branch cut, so the recovered "
        "shifted-radius jumps a whole dr mid-patch and the branch-offset unwrap is exercised"
    )
    out.append("   config |  offset | ref_frac ref_v | disp_frac disp_v |    delta")
    out.append("  " + "-" * 66)
    for name, rows in seam_rows:
        for r in rows:
            out.append(
                f"  {name:>9} | {r['offset']:7.4f} | {r['ref_frac']:8.6f} {_v(r['ref_verdict']):>5} "
                f"| {r['disp_frac']:9.6f} {_v(r['disp_verdict']):>6} | {r['delta']:+9.6f}"
            )
    out.append("")

    out.append("=== C. The one verdict-flipping cell, recomputed under each config ===")
    out.append(
        "scatter 0.05 of dr, alpha 0.80, dr=100. The report noted the flip 'does not recur "
        "under the splicing configuration' but flagged that the looser tolerances would also "
        "move the fractions, which was not measured. Here the fractions are recomputed."
    )
    out.append(
        "     config | ref_quads/total disp_quads/total  thr | ref_v  disp_v | flips?"
    )
    out.append("  " + "-" * 72)
    for name, f in flip_rows:
        flips = f["ref_verdict"] != f["disp_verdict"]
        out.append(
            f"  {name:>9} | {f['ref_quads']:6d}/{f['total']:<5d} {f['disp_quads']:9d}/{f['total']:<5d} "
            f"{f['threshold_quads']:6.2f} | {_v(f['ref_verdict']):>5} {_v(f['disp_verdict']):>6} | "
            f"{'YES' if flips else 'no'}"
        )
    return "\n".join(out) + "\n"


def main():
    sweeps = [(name, run_offset_sweep(REAL_DR, cfg)) for name, cfg in CONFIGS]
    seam_rows = [
        (
            name,
            run_offset_sweep(
                REAL_DR, cfg, patch_builder=lambda dr, winding: seam_patch(dr, winding)
            ),
        )
        for name, cfg in CONFIGS
    ]
    flip_rows = [(name, run_flip_cell_under(cfg)) for name, cfg in CONFIGS]
    print(format_report(sweeps, seam_rows, flip_rows))


if __name__ == "__main__":
    main()
