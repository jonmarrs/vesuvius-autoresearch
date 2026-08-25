"""Locate the scatter onset at which the winding-blindness starts to break.

`reports/spiral_satisfaction_winding_blindness.md` Limits 7 now records that the
invariance holds under warps built from real measured winding spacings while the
patch is well placed, and breaks once the patch carries scatter: nothing at 2.0
voxels, 5 of 40 rays disagreeing at 4.0, 8 of 40 at 6.0. "Somewhere between 2 and
4 voxels" is too loose to qualify a headline with, so this locates it.

Two questions, and the second decides how the result should be phrased.

**Where is the onset?** Swept at 0.25-voxel resolution, reporting the first level
at which any ray's patch-level verdict differs between the correctly placed and
displaced arms, and separately the first level at which the satisfied fraction
moves at all. Those are different thresholds and the gap between them matters: a
fraction that has started moving is a metric already degrading, while a verdict
that has flipped is a decision already wrong.

**Is the onset absolute or relative?** villa's two tolerances scale differently:
`satisfaction_distance_tolerance` is 6.0 voxels ABSOLUTE, while
`satisfaction_radius_tolerance` is 0.45 x dr, RELATIVE. If the onset tracks
absolute voxels it is a property of the scan-space check and will not move with
winding spacing; if it tracks a fraction of dr it is a property of the
spiral-space check and will.

    Binning real rays by their own dr does NOT answer this, and the first version
    of this probe wrongly assumed it did. In the real population dr is strongly
    anti-correlated with knot count (pearson -0.882, mechanically: a longer mean
    gap means fewer gaps along a ray of given length) and mildly correlated with
    local irregularity (+0.147). The bins therefore move several things at once,
    and their apparent trend is largely confound. The bin table is still printed,
    labelled as confounded, because it is what a reader would otherwise compute
    themselves and reach the wrong conclusion from.

    The clean version rescales each ray's warp SHAPE to a target dr, which holds
    every relative irregularity fixed and moves only the spacing.

Every number comes from a real call to villa's unmodified
`get_patch_satisfied_areas`. No pinned script, test, or artifact is modified.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_onset.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_spiral_satisfaction_empirical_transform import (  # noqa: E402
    MIN_CROSSINGS,
    N_RAYS,
    RAY_SEED,
    load_shard,
    run_ray,
    usable_rays,
)
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    SPLICING,
)

# 0.25-voxel resolution across the interval Limits 7 leaves open, extended a
# little either side so the onset is bracketed rather than clipped at an endpoint.
FINE_SCATTER = [round(1.5 + 0.25 * i, 2) for i in range(12)]  # 1.50 .. 4.25
# Bins over each ray's own dr, to separate an absolute-voxel onset from a
# fraction-of-dr onset without rescaling anything synthetically.
DR_BINS = [(0, 12.0), (12.0, 16.0), (16.0, 100.0)]
# Target dr values for the RESCALED sweep. Binning real rays by their own dr does
# not isolate dr: across the selected population dr is strongly anti-correlated
# with knot count (pearson -0.882, mechanically, since a longer mean gap means
# fewer gaps along a ray of given length) and mildly correlated with local
# irregularity (+0.147; bin medians 0.547 / 0.605 / 0.653). Rescaling each ray's
# warp SHAPE to a target dr holds the irregularity fixed and moves only dr.
RESCALE_DR = [10.0, 13.0, 16.0, 20.0, 25.0]


def sweep(rays, overrides):
    """rows[scatter][ray] for the fine grid."""
    return {
        vox: [run_ray(radii, overrides, scatter_voxels=vox) for _, radii in rays]
        for vox in FINE_SCATTER
    }


def first_where(grid, predicate):
    """The lowest scatter level satisfying `predicate` over its rows, or None."""
    for vox in FINE_SCATTER:
        if predicate(grid[vox]):
            return vox
    return None


def per_ray_onsets(grid, n_rays):
    """The onset for EACH ray separately, so the summary is not a min over the
    sample.

    The headline onset below is `min` over rays: the first level at which ANY ray
    flips. That is sample-size dependent by construction -- draw more rays and it
    can only fall -- so it is a property of the sample as much as of the metric.
    The median per-ray onset is stable under sample size and is reported beside it.
    """
    out = []
    for i in range(n_rays):
        hit = next(
            (
                vox
                for vox in FINE_SCATTER
                if grid[vox][i]["ref_verdict"] != grid[vox][i]["disp_verdict"]
            ),
            None,
        )
        out.append(hit)
    return out


def onsets(grid):
    return {
        "fraction_moves": first_where(
            grid, lambda rows: any(abs(r["delta"]) > 1e-9 for r in rows)
        ),
        "verdict_flips": first_where(
            grid, lambda rows: any(r["ref_verdict"] != r["disp_verdict"] for r in rows)
        ),
        "reference_fails": first_where(
            grid, lambda rows: any(not r["ref_verdict"] for r in rows)
        ),
    }


def onset_by_dr_bin(rays, overrides):
    """The verdict onset computed separately within each dr bin.

    If the onset is set by the 6.0-voxel absolute scan tolerance it should be
    roughly constant across bins. If it is set by the 0.45*dr relative spiral
    tolerance it should rise with dr.
    """
    out = []
    for lo, hi in DR_BINS:
        subset = [
            (idx, radii)
            for idx, radii in rays
            if lo <= float(np.mean(np.diff(radii))) < hi
        ]
        if not subset:
            out.append(((lo, hi), 0, None, None))
            continue
        grid = sweep(subset, overrides)
        med_dr = float(np.median([np.mean(np.diff(r)) for _, r in subset]))
        o = onsets(grid)
        out.append(((lo, hi), len(subset), med_dr, o["verdict_flips"]))
    return out


def rescale_to(measured_radii, target_dr):
    """The same warp shape at a different winding spacing.

    Dividing by the ray's own mean gap makes the sequence unit-mean-gap, so
    multiplying by `target_dr` sets the spacing while leaving every relative
    irregularity untouched. This is what lets dr be varied without also varying
    the thing dr covaries with in the real population.
    """
    radii = np.asarray(measured_radii, dtype=np.float64)
    return radii / float(np.mean(np.diff(radii))) * float(target_dr)


def onset_by_rescaled_dr(rays, overrides):
    out = []
    for target in RESCALE_DR:
        grid = sweep([(i, rescale_to(r, target)) for i, r in rays], overrides)
        out.append((target, onsets(grid)["verdict_flips"]))
    return out


def format_report(per_config, per_bin, per_rescaled):
    out = []
    out.append("Where the winding-blindness starts to break, at 0.25-voxel resolution")
    out.append(
        f"Rays: {N_RAYS} drawn under seed {RAY_SEED} from shard_0, each carrying at least "
        f"{MIN_CROSSINGS} crossings at strictly consecutive winding levels. Warp is the "
        "empirical one: measured inter-winding spacing sequences read as radial knots (see "
        "reports/spiral_satisfaction_empirical_transform.txt for what that idealization is "
        "and is not)."
    )
    out.append(
        "Displacement is exactly one winding throughout; only the patch's scatter varies."
    )
    out.append("")

    for name, grid in per_config:
        o = onsets(grid)
        out.append(f"=== {name} configuration ===")
        out.append("  scatter |    max|delta| | verdict differs | reference fails")
        out.append("  " + "-" * 62)
        for vox in FINE_SCATTER:
            rows = grid[vox]
            md = max(abs(r["delta"]) for r in rows)
            dis = sum(1 for r in rows if r["ref_verdict"] != r["disp_verdict"])
            rf = sum(1 for r in rows if not r["ref_verdict"])
            out.append(
                f"  {vox:6.2f}v | {md:12.6f} | {dis:6d} of {len(rows):<5d} | {rf:6d} of {len(rows)}"
            )
        out.append("")
        out.append(
            f"  onset, satisfied fraction first moves : "
            f"{o['fraction_moves'] if o['fraction_moves'] is not None else 'not in range'}"
        )
        out.append(
            f"  onset, a patch VERDICT first flips    : "
            f"{o['verdict_flips'] if o['verdict_flips'] is not None else 'not in range'}"
        )
        out.append(
            f"  onset, the REFERENCE first fails      : "
            f"{o['reference_fails'] if o['reference_fails'] is not None else 'not in range'}"
        )
        n = len(grid[FINE_SCATTER[0]])
        hits = [v for v in per_ray_onsets(grid, n) if v is not None]
        out.append(f"  rays whose verdict flips anywhere in range: {len(hits)} of {n}")
        if hits:
            out.append(
                f"  per-ray onset, median {float(np.median(hits)):.2f}v, "
                f"range {min(hits):.2f}v to {max(hits):.2f}v"
            )
        out.append(
            "  The headline onset is a MIN over the sampled rays and can only fall as more "
            "rays are drawn, so it is a property of this sample as much as of the metric. "
            "The per-ray median is the sample-size-stable figure."
        )
        out.append("")

    out.append(
        "=== Is the onset absolute (scan tolerance) or relative (spiral tolerance)? ==="
    )
    out.append(
        "villa's scan tolerance is 6.0 voxels ABSOLUTE; its spiral tolerance is 0.45*dr "
        "RELATIVE. A verdict onset that is flat across dr bins points at the absolute check; "
        "one that rises with dr points at the relative check."
    )
    out.append("   dr bin (voxels) | rays | median dr | verdict onset")
    out.append("  " + "-" * 56)
    for (lo, hi), n, med, onset in per_bin:
        med_s = f"{med:9.3f}" if med is not None else "        -"
        on_s = f"{onset:.2f}v" if onset is not None else "not in range"
        out.append(f"  {lo:6.1f} - {hi:6.1f} | {n:4d} | {med_s} | {on_s}")
    out.append("")
    out.append(
        "  CONFOUNDED, do not read a dr effect off the table above. Across the selected rays "
        "dr is strongly anti-correlated with knot count (pearson -0.882) and mildly correlated "
        "with local irregularity (+0.147; bin medians 0.547 / 0.605 / 0.653), so these bins vary "
        "several things at once."
    )
    out.append("")
    out.append("=== The same question with dr isolated ===")
    out.append(
        "Each ray's warp SHAPE rescaled to a target dr, holding relative irregularity fixed and "
        "moving only the winding spacing."
    )
    out.append("   target dr | verdict onset | onset as fraction of dr")
    out.append("  " + "-" * 52)
    for target, onset in per_rescaled:
        on_s = f"{onset:.2f}v" if onset is not None else "not in range"
        frac = f"{onset / target:.3f}" if onset is not None else "-"
        out.append(f"  {target:10.1f} | {on_s:>13} | {frac:>23}")
    return "\n".join(out) + "\n"


def main():
    shard = load_shard()
    rays = usable_rays(shard)
    per_config = [
        (name, sweep(rays, cfg))
        for name, cfg in (("reporting", REPORTING), ("splicing", SPLICING))
    ]
    per_bin = onset_by_dr_bin(rays, REPORTING)
    per_rescaled = onset_by_rescaled_dr(rays, REPORTING)
    print(format_report(per_config, per_bin, per_rescaled))


if __name__ == "__main__":
    main()
