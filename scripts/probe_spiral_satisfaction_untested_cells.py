"""Close the two cells `reports/spiral_satisfaction_winding_blindness.md` names as
its weakest points (Limits 4 and 5).

Cell 1 -- scatter crossed with the real scale. The pinned scatter sweep ran at
dr=100; the real-scale run held scatter at zero. The cross was untested. The
question the report poses: if real scatter at dr~12.81 already pushes the
REFERENCE below villa's 0.95 patch threshold, the practical question stops being
"can the metric detect a wrong wrap" and becomes "does it accept anything at all
at this scale".

    Scatter is swept TWO ways on purpose. As a fraction of dr (the pinned
    parameterization) it is not comparable across scales: 0.05*dr is 0.64 voxels
    at dr=12.81 but 5 voxels at dr=100, against a 6.0-voxel tolerance in both
    cases. Real patch scatter is physical and does not shrink because the winding
    spacing does, so the absolute-voxel sweep is the one that compares the two
    scales honestly. Reporting only the fractional sweep would make the real
    scale look safe for a definitional reason rather than a physical one.

Cell 2 -- displacement ratios beyond the p05-p95 grid. Experiment B swept only
0.72..1.38. The measured real distribution runs 0.0446..23.8006. Because villa
snaps to the NEAREST winding, acceptance is expected to be PERIODIC rather than
monotonic -- a displacement passes or fails according to where it lands modulo 1,
not according to how large it is. That is a prediction under test here, not an
assumption.

Both cells report villa's patch-level VERDICT (satisfaction_metrics.py:317, the
integer-count rule), not only the satisfied-quad fraction. The verdict is what
the report's question is actually about; the fraction alone does not answer it.

Every number comes from a real call to villa's unmodified `get_patch_satisfied_areas`
via the pinned probes. No pinned script, test, or artifact is modified.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_untested_cells.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_spiral_satisfaction_robustness import (  # noqa: E402
    _patch_is_satisfied,
    add_radius_scatter,
    draw_unit_noise,
    total_valid_quads,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    DR,
    build_synthetic_patch,
    displace,
    score_conditions,
)

# The real measured median inter-winding gap, voxels
# (reports/real_winding_nonlinearity.txt section 1).
REAL_DR = 12.81
WINDING = 5

# villa's own patch-level threshold (satisfaction_metrics.py metrics_config).
PATCH_THRESHOLD = 0.95

# Cell 1a: the pinned fractional levels, now at the real scale.
SCATTER_FRAC_LEVELS = [0.0, 0.01, 0.02, 0.05, 0.10]

# Cell 1b: scatter in ABSOLUTE VOXELS, the parameterization that is comparable
# across scales. 6.0 is villa's own scan tolerance, included as the reference point.
SCATTER_VOXEL_LEVELS = [0.0, 0.5, 1.0, 2.0, 4.0, 6.0]
SCALES = [REAL_DR, DR]

# Cell 2: the full observed span of the measured adjacent-gap ratio distribution
# (min 0.0446, max 23.8006), with half-integers and integers included so the
# periodicity prediction can be resolved rather than assumed.
RATIO_TAIL_LEVELS = [
    0.0446,
    0.25,
    0.50,
    0.75,
    1.00,
    1.25,
    1.50,
    1.75,
    2.00,
    2.50,
    3.00,
    3.50,
    5.00,
    5.50,
    23.8006,
    # Boundary resolution. The first pass accepted every offset up to 0.2500 and
    # rejected only 0.5000, leaving the acceptance edge unlocated between them.
    # villa's spiral tolerance is 0.45*dr and, at dr=12.81, spiral is the tighter
    # of the two conditions (5.7645 vox vs the 6.0-vox scan tolerance), so the edge
    # is predicted at an offset of 0.45. These points bracket that prediction.
    0.40,
    0.44,
    0.46,
    0.48,
]


def _verdict(fraction, total_quads):
    return _patch_is_satisfied(fraction, total_quads, PATCH_THRESHOLD)


def run_cell(dr, n_windings, scatter_voxels=0.0, winding=WINDING):
    """One grid point. Build a patch exactly on `winding` at scale `dr`, apply
    `scatter_voxels` of absolute-voxel radial scatter, displace by
    `n_windings * dr`, and score both arms through villa's unmodified metric.

    Scatter is applied via the pinned `add_radius_scatter`, which scales its
    noise by `scatter_std_frac * dr`; passing `scatter_voxels / dr` therefore
    yields exactly `scatter_voxels` of absolute noise without touching that
    function. Reference and displaced arms share one noise draw, so the delta
    measures displacement alone and never a difference in noise.
    """
    ref = build_synthetic_patch(dr=dr, winding=winding)
    if scatter_voxels != 0.0:
        noise = draw_unit_noise(ref.zyxs.shape[0], ref.zyxs.shape[1])
        ref = add_radius_scatter(ref, noise, scatter_voxels / dr, dr)
    moved = displace(ref, dr, n_windings=n_windings)

    ref_spiral, ref_scan, ref_combined = score_conditions(ref, dr)
    disp_spiral, disp_scan, disp_combined = score_conditions(moved, dr)
    total = total_valid_quads(dr=dr, winding=winding)

    return {
        "dr": dr,
        "n_windings": n_windings,
        "scatter_voxels": scatter_voxels,
        "ref_spiral": ref_spiral,
        "ref_scan": ref_scan,
        "ref_combined": ref_combined,
        "disp_spiral": disp_spiral,
        "disp_scan": disp_scan,
        "disp_combined": disp_combined,
        "delta_combined": disp_combined - ref_combined,
        "total_quads": total,
        "ref_verdict": _verdict(ref_combined, total),
        "disp_verdict": _verdict(disp_combined, total),
    }


def nearest_winding_offset(ratio):
    """How far a displacement of `ratio` windings lands from the nearest integer
    winding. This is the quantity villa's snap-to-nearest logic actually sees,
    and the one the periodicity prediction is about."""
    return abs(ratio - round(ratio))


def run_cell1_fractional():
    return [
        run_cell(REAL_DR, 1.0, scatter_voxels=frac * REAL_DR)
        for frac in SCATTER_FRAC_LEVELS
    ]


def run_cell1_absolute():
    return [
        run_cell(dr, 1.0, scatter_voxels=vox)
        for dr in SCALES
        for vox in SCATTER_VOXEL_LEVELS
    ]


def run_cell2():
    return [run_cell(REAL_DR, ratio) for ratio in RATIO_TAIL_LEVELS]


def verdict_disagreements(rows):
    """Rows where villa's patch verdict differs between the two arms -- i.e. the
    metric actually notices the displacement. Returns the rows themselves so the
    narrative can never quote a count that disagrees with the table."""
    return [r for r in rows if r["ref_verdict"] != r["disp_verdict"]]


def reference_failures(rows):
    """Rows where the CORRECTLY PLACED patch already fails villa's verdict. This
    is the report's question for Cell 1: past this point the metric is not
    accepting a wrong wrap, it is rejecting everything."""
    return [r for r in rows if not r["ref_verdict"]]


def _v(flag):
    return "SAT" if flag else "unsat"


def format_report(rows_1a, rows_1b, rows_2):
    out = []
    out.append(
        "Closing the two untested cells of reports/spiral_satisfaction_winding_blindness.md"
    )
    out.append(
        f"villa patch verdict = integer satisfied-quad count >= "
        f"{PATCH_THRESHOLD} * {rows_2[0]['total_quads']} valid quads = "
        f"{PATCH_THRESHOLD * rows_2[0]['total_quads']:.2f} quads "
        f"(satisfaction_metrics.py:317)"
    )
    out.append("")

    out.append("=== Cell 1a: scatter as a FRACTION of dr, at the real scale ===")
    out.append(
        f"dr = {REAL_DR} (real measured median gap); exact whole-winding displacement; "
        "identity transform"
    )
    out.append("  frac    vox | ref_comb ref_v | disp_comb disp_v |  delta_comb")
    out.append("-" * 66)
    for frac, r in zip(SCATTER_FRAC_LEVELS, rows_1a, strict=False):
        out.append(
            f"  {frac:4.2f} {r['scatter_voxels']:6.3f} | {r['ref_combined']:8.6f} {_v(r['ref_verdict']):>5} "
            f"| {r['disp_combined']:9.6f} {_v(r['disp_verdict']):>6} | {r['delta_combined']:+11.6f}"
        )
    out.append("")
    out.append(
        f"Note the voxel column: the pinned fractional levels correspond to only "
        f"{min(r['scatter_voxels'] for r in rows_1a):.3f}-"
        f"{max(r['scatter_voxels'] for r in rows_1a):.3f} voxels at this dr, against villa's "
        "6.0-voxel scan tolerance. The same fractions at dr=100 span "
        f"{min(f * DR for f in SCATTER_FRAC_LEVELS):.1f}-{max(f * DR for f in SCATTER_FRAC_LEVELS):.1f} voxels. "
        "This is why the fractional parameterization alone cannot compare the two scales, "
        "and why Cell 1b sweeps absolute voxels instead."
    )
    out.append("")

    out.append("=== Cell 1b: scatter in ABSOLUTE VOXELS, both scales ===")
    out.append(
        "the comparable parameterization: real patch scatter is physical and does not "
        "shrink with winding spacing"
    )
    out.append("      dr    vox | ref_comb ref_v | disp_comb disp_v |  delta_comb")
    out.append("-" * 70)
    for r in rows_1b:
        out.append(
            f"  {r['dr']:6.2f} {r['scatter_voxels']:6.2f} | {r['ref_combined']:8.6f} {_v(r['ref_verdict']):>5} "
            f"| {r['disp_combined']:9.6f} {_v(r['disp_verdict']):>6} | {r['delta_combined']:+11.6f}"
        )
    out.append("")

    flips_1b = verdict_disagreements(rows_1b)
    ref_fail_1b = reference_failures(rows_1b)
    out.append(
        f"Verdict disagreements in Cell 1b: {len(flips_1b)} of {len(rows_1b)} cells"
        + (
            " -- "
            + ", ".join(
                f"dr={r['dr']:.2f}/{r['scatter_voxels']:.2f}vox" for r in flips_1b
            )
            if flips_1b
            else " (the metric never notices the displacement)"
        )
    )
    out.append(
        f"Cells where the CORRECTLY PLACED patch already fails villa's verdict: "
        f"{len(ref_fail_1b)} of {len(rows_1b)}"
        + (
            " -- "
            + ", ".join(
                f"dr={r['dr']:.2f}/{r['scatter_voxels']:.2f}vox" for r in ref_fail_1b
            )
            if ref_fail_1b
            else ""
        )
    )
    out.append("")

    out.append("=== Cell 2: displacement ratios across the full measured span ===")
    out.append(
        f"dr = {REAL_DR}; no scatter; ratios span the measured real distribution "
        f"({min(RATIO_TAIL_LEVELS)} to {max(RATIO_TAIL_LEVELS)}), with half-integers and "
        "integers included to resolve the periodicity prediction"
    )
    out.append("   ratio  off_int | ref_comb ref_v | disp_comb disp_v |  delta_comb")
    out.append("-" * 72)
    for r in rows_2:
        off = nearest_winding_offset(r["n_windings"])
        out.append(
            f"  {r['n_windings']:7.4f} {off:8.4f} | {r['ref_combined']:8.6f} {_v(r['ref_verdict']):>5} "
            f"| {r['disp_combined']:9.6f} {_v(r['disp_verdict']):>6} | {r['delta_combined']:+11.6f}"
        )
    out.append("")

    accepted = [r for r in rows_2 if r["disp_verdict"]]
    rejected = [r for r in rows_2 if not r["disp_verdict"]]
    out.append(
        f"Displaced patch accepted in {len(accepted)} of {len(rows_2)} ratio cells; "
        f"rejected in {len(rejected)}."
    )
    if accepted:
        out.append(
            f"  accepted offsets from the nearest integer winding: "
            f"{min(nearest_winding_offset(r['n_windings']) for r in accepted):.4f} to "
            f"{max(nearest_winding_offset(r['n_windings']) for r in accepted):.4f}"
        )
    if rejected:
        out.append(
            f"  rejected offsets from the nearest integer winding: "
            f"{min(nearest_winding_offset(r['n_windings']) for r in rejected):.4f} to "
            f"{max(nearest_winding_offset(r['n_windings']) for r in rejected):.4f}"
        )
    out.append(
        "  Read the off_int column, not the ratio column: if acceptance tracks distance "
        "from the nearest integer winding rather than the size of the displacement, the "
        "metric's blindness is PERIODIC -- an arbitrarily large displacement passes "
        "whenever it lands near some winding."
    )
    return "\n".join(out) + "\n"


def main():
    rows_1a = run_cell1_fractional()
    rows_1b = run_cell1_absolute()
    rows_2 = run_cell2()
    print(format_report(rows_1a, rows_1b, rows_2))


if __name__ == "__main__":
    main()
