"""Build the STRIPMATCH control: a random draw matched to BOOTSTRAP on total
area AND on area inside the scored strip.

Registered in `docs/preregistration/2026-09-04_stripmatch_followup.md`. The parent
study's RANDOM control matches BOOTSTRAP globally but not inside w120-w129, where
`total_fg_pixels` is actually measured and where BOOTSTRAP carries ~11% less
relative area. STRIPMATCH removes that difference so a remaining effect is
selection quality alone.

**In-strip weight is apportioned, never point-assigned.** Each patch contributes
the fraction of its radial extent that falls inside the strip's calibrated support
(radius 1,593-3,311 from `calibrate_radius_to_winding.py`). The median patch spans
602 vx of radius against 149 vx bands, so assigning a patch to one radius would
measure almost nothing -- the bug corrected in `check_patch_spatial_balance.py`.

The selection is a two-pool greedy: patches are shuffled once under a fixed seed
and then drawn from an above-target or below-target pool according to whether the
running in-strip share currently sits above or below BOOTSTRAP's. That converges
on both constraints at once without ever choosing a patch for its satisfaction,
which would defeat the control.

The registration requires `check_patch_selection.py` and
`check_patch_spatial_balance.py` to pass on the built dataset before any fit runs.
"""

import argparse
import os
import random
import sys
from pathlib import Path

STRIP_LO, STRIP_HI = 1593.0, 3311.0
CX, CY = 3644.0, 4621.0

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_patch_spatial_balance import radial_extent
from scripts.patch_dataset_artifacts import (
    MANIFEST,
    bootstrap_ids,
    dataset_links,
    fingerprint,
    geometry,
    publish_dataset,
    reference_patches,
    verify_geometry,
)


def strip_weight(extent, lo=STRIP_LO, hi=STRIP_HI):
    """Fraction of a patch's radial extent lying inside the scored strip."""
    r0, r1 = extent
    span = r1 - r0
    if span <= 0:
        return 1.0 if lo <= r0 <= hi else 0.0
    return max(0.0, min(r1, hi) - max(r0, lo)) / span


def profile(ids, area, weight):
    # Set iteration order varies across Python processes. Keep target sums stable.
    ids = sorted(ids)
    a = sum(area[i] for i in ids)
    if a == 0:
        return 0.0, 0.0
    return a, sum(area[i] * weight[i] for i in ids) / a


def select(pool, area, weight, target_area, target_share, seed=0):
    """Draw patches until total area reaches target_area, steering the running
    in-strip share toward target_share."""
    rng = random.Random(seed)
    order = sorted(pool)
    rng.shuffle(order)
    above = [i for i in order if weight[i] >= target_share]
    below = [i for i in order if weight[i] < target_share]

    keep, acc_a, acc_s, ai, bi = [], 0.0, 0.0, 0, 0
    while acc_a < target_area and (ai < len(above) or bi < len(below)):
        cur = acc_s / acc_a if acc_a > 0 else target_share
        want_below = cur >= target_share
        src, idx = (below, bi) if want_below else (above, ai)
        if idx >= len(src):  # that pool is exhausted; take from the other
            src, idx = (above, ai) if want_below else (below, bi)
            if idx >= len(src):
                break
            want_below = not want_below
        i = src[idx]
        if want_below:
            bi += 1
        else:
            ai += 1
        keep.append(i)
        acc_a += area[i]
        acc_s += area[i] * weight[i]
    return keep


def draw_stability(pool, area, weight, target_area, target_share, seeds, frac=None):
    """Re-draw under the same constraints across seeds and report what moves.

    The registration inherits a single-draw limitation from the parent study. For
    RANDOM that was discharged by showing the draw tracked the full population;
    that argument does NOT transfer here, because STRIPMATCH is deliberately
    unrepresentative -- it is pinned to BOOTSTRAP's in-strip share, which is below
    the population's. The right question is instead whether independent draws
    under the same constraints agree on the quantities the comparison rests on.
    """
    rows = []
    first = None
    for seed in seeds:
        keep = select(pool, area, weight, target_area, target_share, seed=seed)
        a, sh = profile(set(keep), area, weight)
        row = {
            "seed": seed,
            "n": len(keep),
            "area_frac_of_target": a / target_area,
            "in_strip": sh,
        }
        if frac is not None:
            row["mean_satisfaction"] = sum(frac[i] for i in keep) / len(keep)
        if first is None:
            first = set(keep)
            row["overlap_with_first"] = 1.0
        else:
            row["overlap_with_first"] = len(first & set(keep)) / len(first)
        rows.append(row)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--bootstrap", required=True)
    ap.add_argument("--full", required=True, help="unfiltered source dataset")
    ap.add_argument("--out", required=True, help="dataset directory to create")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--stability",
        type=int,
        default=0,
        metavar="N",
        help="draw N times under the same constraints and report agreement "
        "instead of writing a dataset; tests the single-draw limitation",
    )
    args = ap.parse_args(argv)
    try:
        if args.stability != 0 and not 2 <= args.stability <= 1000:
            raise ValueError("--stability must be 0 (build) or 2..1000 draws")
        return build(args)
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        print(f"STRIPMATCH preparation failed: {exc}", file=sys.stderr)
        return 1


def build(args):
    reference, records = reference_patches(args.reference)
    area = {pid: value[1] for pid, value in records.items()}
    frac = {pid: value[0] for pid, value in records.items()}
    links = dataset_links(args.full, records)
    bootstrap, boot = bootstrap_ids(args.bootstrap, records)
    boxes, geometry_sources = geometry(links[0], area)
    weight = {i: strip_weight(radial_extent(boxes[i], CX, CY)) for i in boxes}

    ta, ts = profile(boot, area, weight)
    if ta <= 0:
        raise ValueError("bootstrap target area must be positive")

    def verify():
        reference.verify()
        verify_geometry(geometry_sources)
        if bootstrap_ids(bootstrap, records)[1] != boot:
            raise ValueError("bootstrap selection changed before publication")

    print(f"BOOTSTRAP  area {ta:,.0f}  in-strip share {ts:.4f}")

    if args.stability:
        rows = draw_stability(
            set(boxes), area, weight, ta, ts, range(args.stability), frac
        )
        verify()
        print(
            f"\n{'seed':<6}{'n':>9}{'area %target':>14}{'in-strip':>10}"
            f"{'mean satisf':>13}{'overlap':>10}"
        )
        for r in rows:
            print(
                f"{r['seed']:<6}{r['n']:>9,}{100 * r['area_frac_of_target']:>13.2f}%"
                f"{r['in_strip']:>10.4f}{r['mean_satisfaction']:>13.4f}"
                f"{100 * r['overlap_with_first']:>9.1f}%"
            )
        sh = [r["in_strip"] for r in rows]
        ms = [r["mean_satisfaction"] for r in rows]
        print(
            f"\nin-strip share spans {max(sh) - min(sh):.4f}; mean satisfaction spans "
            f"{max(ms) - min(ms):.4f}. Draw overlap with the first is "
            f"{100 * min(r['overlap_with_first'] for r in rows[1:]):.0f}-"
            f"{100 * max(r['overlap_with_first'] for r in rows[1:]):.0f}%. "
            "Compare these input diagnostics before fitting."
        )
        return 0

    keep = select(set(boxes), area, weight, ta, ts, seed=args.seed)
    ka, ks = profile(set(keep), area, weight)
    print(
        f"STRIPMATCH area {ka:,.0f} ({100 * ka / ta:.2f}% of target)  "
        f"in-strip {ks:.4f} (gap {abs(ks - ts):.4f})  {len(keep):,} patches"
    )
    if abs(ks - ts) > 0.005 or abs(ka - ta) / ta > 0.01:
        raise ValueError("did not converge on both constraints; refusing to write")

    publish_dataset(
        links,
        args.out,
        keep,
        {
            "mode": "stripmatch",
            "seed": args.seed,
            "reference": reference.provenance(),
            "scored_patches": len(records),
            "bootstrap": str(bootstrap),
            "bootstrap_ids": sorted(boot),
            "bootstrap_target_area": ta,
            "bootstrap_target_strip_share": ts,
            "selected_area": ka,
            "selected_strip_share": ks,
            "selected_count": len(keep),
            "strip_radius_bounds": [STRIP_LO, STRIP_HI],
            "center_xy": [CX, CY],
            "geometry_sources_sha256": fingerprint(geometry_sources),
            "matching_basis": "unchanged seeded greedy draw; 1% area and 0.005 strip-share tolerance",
        },
        inputs=(
            reference.path,
            bootstrap,
            bootstrap / "verified_patches",
            *(bootstrap / "verified_patches" / pid for pid in boot),
        ),
        verify=verify,
    )
    print(f"wrote {Path(args.out).resolve()} ({len(keep):,} patch symlinks)")
    print(f"selection record: {Path(args.out) / MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
