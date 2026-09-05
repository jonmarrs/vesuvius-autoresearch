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
import json
import os
import random
import sys

STRIP_LO, STRIP_HI = 1593.0, 3311.0
CX, CY = 3644.0, 4621.0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_patch_spatial_balance import load_boxes, radial_extent  # noqa: E402


def strip_weight(extent, lo=STRIP_LO, hi=STRIP_HI):
    """Fraction of a patch's radial extent lying inside the scored strip."""
    r0, r1 = extent
    span = r1 - r0
    if span <= 0:
        return 1.0 if lo <= r0 <= hi else 0.0
    return max(0.0, min(r1, hi) - max(r0, lo)) / span


def profile(ids, area, weight):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--bootstrap", required=True)
    ap.add_argument("--full", required=True, help="unfiltered source dataset")
    ap.add_argument("--out", required=True, help="dataset directory to create")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    ref = json.load(open(args.reference))["patches"]
    area = {p["id"]: p["total_area"] for p in ref}
    boot = (
        set(os.listdir(os.path.join(args.bootstrap, "verified_patches"))) & area.keys()
    )

    boxes = load_boxes(args.full, set(area))
    weight = {i: strip_weight(radial_extent(boxes[i], CX, CY)) for i in boxes}

    ta, ts = profile(boot, area, weight)
    print(f"BOOTSTRAP  area {ta:,.0f}  in-strip share {ts:.4f}")

    keep = select(set(boxes), area, weight, ta, ts, seed=args.seed)
    ka, ks = profile(set(keep), area, weight)
    print(
        f"STRIPMATCH area {ka:,.0f} ({100 * ka / ta:.2f}% of target)  "
        f"in-strip {ks:.4f} (gap {abs(ks - ts):.4f})  {len(keep):,} patches"
    )
    if abs(ks - ts) > 0.005 or abs(ka - ta) / ta > 0.01:
        raise SystemExit("did not converge on both constraints; refusing to write")

    src = os.path.abspath(args.full)
    dst = os.path.abspath(args.out)
    os.makedirs(os.path.join(dst, "verified_patches"), exist_ok=True)
    for entry in os.listdir(src):
        if entry == "verified_patches":
            continue
        link = os.path.join(dst, entry)
        if not os.path.lexists(link):
            os.symlink(os.path.join(src, entry), link)
    for i in keep:
        link = os.path.join(dst, "verified_patches", i)
        if not os.path.lexists(link):
            os.symlink(os.path.join(src, "verified_patches", i), link)
    print(f"wrote {dst} ({len(keep):,} patch symlinks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
