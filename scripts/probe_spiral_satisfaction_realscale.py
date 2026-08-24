"""Re-run the whole-winding-blindness measurement (see
`probe_spiral_satisfaction_winding.py`) at the REAL scroll's scale and with
the REAL kind of irregularity, fixing two mismatches between the earlier
sweeps and the measured PHercParis4 field.

Mismatch 1 -- scale
--------------------
`probe_spiral_satisfaction_robustness.py`'s sweep used `DR = 100.0` against
villa's fixed absolute scan-space tolerance of 6.0 voxels -- a 6% acceptance
band. The real field's inter-winding gap (measured in
`measure_real_winding_nonlinearity.py`, reports/real_winding_nonlinearity.txt
section 1) has p50 = 12.81 voxels, p05 = 8.04 voxels. At those real scales
the SAME 6.0-voxel absolute tolerance is 47%+ of a winding spacing -- roughly
8x looser, relative to the winding, than the earlier sweep tested. There is
also a knock-on: villa's spiral-space tolerance is `0.45 * dr`, so at
dr=100 it is 45 units versus a 6.0-voxel scan tolerance (scan dominates,
consistent with the earlier sweep, where the spiral condition read 1.0 in
every row); at dr=12.81 the spiral tolerance is 5.7645 voxels versus scan's
6.0 -- comparable. Which condition binds may flip, so Experiment A reports
both `spiral_tolerance` and `scan_tolerance` (read from villa's own
`metrics_config`, not hand-typed) at every grid point.

Mismatch 2 -- shape of the irregularity
-----------------------------------------
The earlier robustness sweep perturbed geometry SMOOTHLY (a radial power
law). The real field's adjacent-gap ratio (section 2 of the same report) is
instead locally noisy: pooled median 0.9985, p05/p95 = 0.72/1.38, 21.6% of
ratios outside [0.8, 1.25]. The conceptual correction that matters most: in
a real scroll, "move the patch to the adjacent wrap" means moving it by the
LOCAL gap `g = dr * ratio`, not by the nominal `dr` exactly. Experiment B
displaces by `dr * ratio` for `ratio` drawn from the measured quantiles,
using `displace(patch, dr, n_windings=ratio)` from the original probe --
that function already computes a radial offset of `n_windings * dr`, so no
new displacement arithmetic is written here; a realistic gap ratio is simply
a non-1.0 value of the same `n_windings` argument the original probe's own
fractional-winding control already exercised.

Both experiments reuse `build_synthetic_patch`, `displace`, `score`, and
`score_conditions` from `probe_spiral_satisfaction_winding.py` and
`IdentityTransform` from the same module, UNMODIFIED, and call villa's own
`get_patch_satisfied_areas` (via those functions) for every number reported.
Nothing under villa/ is edited or reimplemented; `metrics_config`'s
`satisfaction_radius_tolerance` (0.45) and `satisfaction_distance_tolerance`
(6.0) are read directly from villa's `satisfaction_metrics` module, not
hand-typed, so the report can never silently drift from the real constants
being characterized.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_realscale.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from probe_spiral_satisfaction_winding import (  # noqa: E402
    DR as ORIGINAL_DR,
    build_synthetic_patch,
    displace,
    score_conditions,
)

# satisfaction_metrics is guaranteed importable here: importing
# probe_spiral_satisfaction_winding already ran its villa-import-stub
# installation and inserted villa's spiral/ dir onto sys.path.
from satisfaction_metrics import metrics_config  # noqa: E402

WINDING = 5

# Experiment A: original value, two intermediates, the real median, the real
# p05 (reports/real_winding_nonlinearity.txt section 1: p50=12.81, p05=8.04).
SCALE_DRS = [100.0, 50.0, 25.0, 12.81, 8.04]
assert SCALE_DRS[0] == ORIGINAL_DR

REAL_DR = 12.81  # real median inter-winding gap, voxels

# Experiment B: measured real adjacent-gap ratio quantiles (section 2) --
# p05, the [0.8,1.25] band edges, p50, p75, the other band edge, p95.
RATIO_LEVELS = [0.72, 0.80, 0.8939, 0.9985, 1.1155, 1.25, 1.38]


def run_cell(dr, n_windings, winding=WINDING):
    """One grid point shared by both experiments: build a patch exactly on
    `winding` at scale `dr`, displace it by `n_windings * dr` (the real
    displacement `displace()` already computes), and score both the
    reference and displaced patch through villa's unmodified metric, broken
    out per satisfaction condition via `score_conditions`.

    In Experiment A, `n_windings` is held at 1.0 (exact whole-winding
    displacement) while `dr` sweeps the real scale range. In Experiment B,
    `dr` is held at `REAL_DR` while `n_windings` sweeps the measured real
    adjacent-gap ratio quantiles -- `n_windings` there IS the ratio: a
    displacement of `ratio * dr` is exactly what `displace(..., n_windings=
    ratio)` already computes, so no new displacement formula is introduced.
    """
    ref = build_synthetic_patch(dr=dr, winding=winding)
    moved = displace(ref, dr, n_windings=n_windings)

    ref_spiral, ref_scan, ref_combined = score_conditions(ref, dr)
    disp_spiral, disp_scan, disp_combined = score_conditions(moved, dr)

    return {
        "dr": dr,
        "n_windings": n_windings,
        "ref_spiral": ref_spiral,
        "ref_scan": ref_scan,
        "ref_combined": ref_combined,
        "disp_spiral": disp_spiral,
        "disp_scan": disp_scan,
        "disp_combined": disp_combined,
        "delta_combined": disp_combined - ref_combined,
    }


def tolerances_at(dr):
    """villa's two per-quad tolerances at a given dr, read directly from its
    own `metrics_config` (never hand-typed): the spiral-space shifted-radius
    tolerance (`satisfaction_radius_tolerance * dr`) and the absolute
    scan-space distance tolerance (`satisfaction_distance_tolerance`,
    unscaled by dr)."""
    spiral_tolerance = metrics_config["satisfaction_radius_tolerance"] * dr
    scan_tolerance = metrics_config["satisfaction_distance_tolerance"]
    return spiral_tolerance, scan_tolerance


def binding_condition(dr):
    """Which of the two tolerances is numerically tighter at this dr -- a
    magnitude comparison of villa's own constants, used only to describe the
    scale crossover the task calls out (spiral tolerance shrinks with dr,
    scan tolerance is fixed). Not itself a claim about which condition
    rejected anything in this experiment (both conditions read 1.0
    throughout, since there is no scatter here -- see module docstring)."""
    spiral_tolerance, scan_tolerance = tolerances_at(dr)
    if abs(spiral_tolerance - scan_tolerance) < 1e-6:
        return "comparable"
    return "spiral" if spiral_tolerance < scan_tolerance else "scan"


def run_experiment_a():
    return [run_cell(dr=dr, n_windings=1.0) for dr in SCALE_DRS]


def run_experiment_b():
    return [run_cell(dr=REAL_DR, n_windings=ratio) for ratio in RATIO_LEVELS]


def _fmt_row_a(r):
    spiral_tolerance, scan_tolerance = tolerances_at(r["dr"])
    return (
        f"{r['dr']:8.2f} {spiral_tolerance:9.4f} {scan_tolerance:9.4f} "
        f"{binding_condition(r['dr']):>9s} | "
        f"{r['ref_spiral']:9.6f} {r['ref_scan']:9.6f} {r['ref_combined']:9.6f} | "
        f"{r['disp_spiral']:9.6f} {r['disp_scan']:9.6f} {r['disp_combined']:9.6f} | "
        f"{r['delta_combined']:+11.6f}"
    )


def _fmt_row_b(r):
    displacement = r["n_windings"] * r["dr"]
    return (
        f"{r['n_windings']:8.4f} {displacement:12.4f} | "
        f"{r['ref_spiral']:9.6f} {r['ref_scan']:9.6f} {r['ref_combined']:9.6f} | "
        f"{r['disp_spiral']:9.6f} {r['disp_scan']:9.6f} {r['disp_combined']:9.6f} | "
        f"{r['delta_combined']:+11.6f}"
    )


def format_report(rows_a, rows_b):
    lines = []
    lines.append(
        "Real-scale re-run of the whole-winding-blindness measurement "
        "(see reports/spiral_satisfaction_winding_robustness.txt and "
        "reports/real_winding_nonlinearity.txt for background)"
    )
    lines.append("")

    lines.append("=== Experiment A: scale sweep ===")
    lines.append(
        "no scatter, IdentityTransform, exact whole-winding displacement "
        "(n_windings=1.0); dr swept from the original pinned value down to "
        "the real field's measured p05 gap"
    )
    lines.append(
        f"winding = {WINDING}; tolerances read from villa's own "
        f"metrics_config: satisfaction_radius_tolerance = "
        f"{metrics_config['satisfaction_radius_tolerance']}, "
        f"satisfaction_distance_tolerance = "
        f"{metrics_config['satisfaction_distance_tolerance']} voxels"
    )
    lines.append("")
    header_a = (
        f"{'dr':>8} {'spiral_tol':>9} {'scan_tol':>9} {'binds':>9} | "
        f"{'ref_spiral':>9} {'ref_scan':>9} {'ref_comb':>9} | "
        f"{'disp_spiral':>9} {'disp_scan':>9} {'disp_comb':>9} | "
        f"{'delta_comb':>11}"
    )
    lines.append(header_a)
    lines.append("-" * len(header_a))
    for r in rows_a:
        lines.append(_fmt_row_a(r))
    lines.append("")
    worst_a = max(rows_a, key=lambda r: abs(r["delta_combined"]))
    lines.append(
        "worst-case |delta_combined| across the scale sweep = "
        f"{abs(worst_a['delta_combined']):.6f} at dr={worst_a['dr']}"
    )
    all_exact_a = all(abs(r["delta_combined"]) < 1e-6 for r in rows_a)
    if all_exact_a:
        lines.append(
            "Result: the whole-winding invariance is EXACT at every scale "
            "tested, matching the pre-registered algebra (the transform and "
            "the scale both cancel for an ideal, unscattered patch under "
            "IdentityTransform). This CONFIRMS the earlier sweep's finding "
            "is not an artifact of the DR=100 scale it happened to be run "
            "at -- the blindness is scale-invariant."
        )
    else:
        lines.append(
            "*** MAJOR FINDING: the whole-winding invariance did NOT hold "
            "exactly at every scale tested, contrary to the pre-registered "
            "algebra (which predicts an exact cancellation for an ideal, "
            "unscattered patch under IdentityTransform at ANY dr). This is "
            "NOT explained away here -- see the non-zero delta_combined "
            "row(s) above and treat the scale-invariance claim as OPEN, "
            "pending investigation of why the algebra's prediction failed. "
            "***"
        )
    lines.append("")

    lines.append("=== Experiment B: realistic displacement at the real scale ===")
    lines.append(
        f"dr = {REAL_DR} (real measured median inter-winding gap, voxels); "
        "displacement = n_windings * dr where n_windings is drawn from the "
        "measured real adjacent-gap ratio quantiles "
        "(reports/real_winding_nonlinearity.txt section 2), via the "
        "original probe's own displace(patch, dr, n_windings=ratio) -- no "
        "new displacement formula"
    )
    spiral_tolerance_b, scan_tolerance_b = tolerances_at(REAL_DR)
    lines.append(
        f"at dr={REAL_DR}: spiral_tolerance = {spiral_tolerance_b:.4f} voxels, "
        f"scan_tolerance = {scan_tolerance_b:.4f} voxels ({binding_condition(REAL_DR)} "
        "is tighter)"
    )
    lines.append("")
    header_b = (
        f"{'ratio':>8} {'displacement':>12} | "
        f"{'ref_spiral':>9} {'ref_scan':>9} {'ref_comb':>9} | "
        f"{'disp_spiral':>9} {'disp_scan':>9} {'disp_comb':>9} | "
        f"{'delta_comb':>11}"
    )
    lines.append(header_b)
    lines.append("-" * len(header_b))
    for r in rows_b:
        lines.append(_fmt_row_b(r))
    lines.append("")
    worst_b = max(rows_b, key=lambda r: abs(r["delta_combined"]))
    lines.append(
        "worst-case |delta_combined| across the realistic-ratio sweep = "
        f"{abs(worst_b['delta_combined']):.6f} at ratio={worst_b['n_windings']}"
    )
    still_satisfied_b = [r for r in rows_b if r["disp_combined"] >= 0.95]
    lines.append(
        f"{len(still_satisfied_b)}/{len(rows_b)} of the measured real ratio "
        "quantiles leave the displaced patch scoring satisfied "
        f"(>=0.95) by villa's own combined criterion"
    )
    if len(still_satisfied_b) == len(rows_b):
        lines.append(
            "Result: the metric accepts a patch displaced by EVERY measured "
            "real adjacent-gap ratio quantile in this sweep (p05 through "
            "p95), not only an exact whole-winding offset -- because the "
            "largest observed deviation from an exact winding at these "
            "quantiles (about 0.28-0.38 of a winding) still sits inside "
            "villa's 0.45*dr spiral-space tolerance and its 6.0-voxel "
            "scan-space tolerance at this real dr. The blindness measured "
            "on the idealized sweep is NOT weaker in practice: at the real "
            "scale, a displaced patch does not need to land precisely on "
            "the adjacent wrap to be scored satisfied -- the real field's "
            "typical local gap noise already fits inside the metric's "
            "acceptance band."
        )
    else:
        lines.append(
            "Result: at least one measured real ratio quantile broke the "
            "metric's acceptance -- the blindness is NOT unconditional "
            "across the full measured range at this scale. See the "
            "per-row deltas above for exactly which quantile(s)."
        )
    lines.append("")
    lines.append(
        "CAVEAT: RATIO_LEVELS covers only the pinned quantile grid (p05 "
        "through p95 of the measured adjacent-gap ratio distribution). The "
        "measured distribution has real tails beyond this grid (min "
        "0.0446, max 23.8006, and 21.6% of all ratios fall outside "
        "[0.8, 1.25] -- see reports/real_winding_nonlinearity.txt section "
        "2); this sweep does not claim the invariance holds for those "
        "more extreme, less-typical local deviations."
    )
    return "\n".join(lines) + "\n"


def main():
    rows_a = run_experiment_a()
    rows_b = run_experiment_b()
    report = format_report(rows_a, rows_b)
    print(report)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(repo_root, "reports", "spiral_satisfaction_realscale.txt")
    with open(out_path, "w") as f:
        f.write(report)


if __name__ == "__main__":
    main()
