"""Are the patch-bootstrap arms balanced WHERE THE ENDPOINT IS MEASURED?

`scripts/check_patch_selection.py` establishes that BOOTSTRAP and RANDOM hold the
same total patch area (76.36% vs 76.37%). That is a GLOBAL match, and the ink
endpoint is not global: `total_fg_pixels` is scored only on windings w120-w129,
the outer strip.

So a global match can hide the confound it exists to remove. If the 0.90
satisfaction threshold preferentially drops OUTER patches -- plausible, since
outer windings are longer, thinner and harder to reconcile -- then BOOTSTRAP
would carry less evidence exactly where the ink is read, while still matching on
area overall. An ink deficit would then be a quantity artefact in the measured
region, not the quality effect the study is trying to detect.

`satisfied_fitted.json` carries no spatial field and `abs_winding.json` is a
handful of correction anchors, not a patch->winding map, so winding is not
directly available. This uses a RADIAL PROXY built from each patch's meta.json
bbox: distance from the area-weighted centre of the full population in XY.

**A centroid will not do, and the first version of this script used one.** The
median patch has an XY bbox diagonal of 829 voxels while the equal-area radial
bands are 115-300 voxels wide, so the typical patch spans three to seven bands
and 37.9% span more than a thousand voxels. Assigning such a patch to the single
band holding its centre-point produces a table that looks precise and measures
almost nothing. Each patch's area is therefore SPREAD across the radial interval
its bbox actually covers, from the nearest point of the footprint to the farthest
corner.

That spreading is itself approximate -- it assumes area is uniform in radius
across the footprint, which for a curved sheet it is not exactly -- so the proxy
is monotone in winding, uncalibrated to it, and this script REPORTS rather than
gates.

**There is deliberately no pass/fail threshold.** No spatial balance criterion was
pre-registered, and choosing one after seeing these numbers is how a null becomes
a finding. The comparison offered instead is internal: per-band area gaps against
the 0.01-point global gap the same build achieved.
"""

import argparse
import json
import os
import statistics as st
import sys

N_BANDS = 10


def load_boxes(dataset_dir, ids):
    """id -> bbox, read once per id from the symlink farm."""
    out = {}
    root = os.path.join(dataset_dir, "verified_patches")
    for i in ids:
        p = os.path.join(root, i, "meta.json")
        if os.path.exists(p):
            out[i] = json.load(open(p))["bbox"]
    return out


def radial_extent(box, cx, cy):
    """(r_min, r_max) of an axis-aligned XY footprint about (cx, cy).

    r_min is 0 when the centre lies inside the footprint; otherwise it is the
    distance to the nearest edge or corner. r_max is always a corner.
    """
    (x0, y0, _), (x1, y1, _) = box
    dx = max(x0 - cx, 0.0, cx - x1)
    dy = max(y0 - cy, 0.0, cy - y1)
    r_min = (dx * dx + dy * dy) ** 0.5
    r_max = max(
        ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x in (x0, x1) for y in (y0, y1)
    )
    return r_min, r_max


def radial_bands(extent, area, n_bands=N_BANDS):
    """Equal-area radial bands over the full population, innermost first.

    Edges are taken on the AREA-WEIGHTED distribution of patch midpoint radius,
    which only has to place the band boundaries sensibly; the per-band accounting
    below does not use midpoints.
    """
    mid = {i: 0.5 * (lo + hi) for i, (lo, hi) in extent.items()}
    tot_a = sum(area[i] for i in extent)
    order = sorted(mid, key=lambda i: mid[i])
    edges, acc, step = [], 0.0, tot_a / n_bands
    for i in order:
        acc += area[i]
        if acc >= step * (len(edges) + 1) and len(edges) < n_bands - 1:
            edges.append(mid[i])
    return edges


def area_share_by_band(ids, extent, edges, area, n_bands=N_BANDS):
    """Spread each patch's area across every band its footprint covers.

    A patch reaching from r_min to r_max contributes to each band in proportion
    to the fraction of [r_min, r_max] that band holds. A patch narrower than one
    band lands wholly inside it, as it should.
    """
    bounds = [0.0, *edges, float("inf")]
    per = [0.0] * n_bands
    tot = 0.0
    for i in ids:
        if i not in extent:
            continue
        lo, hi = extent[i]
        a = area[i]
        tot += a
        span = hi - lo
        if span <= 0:
            per[min(sum(1 for e in edges if lo > e), n_bands - 1)] += a
            continue
        for b in range(n_bands):
            ov = min(hi, bounds[b + 1]) - max(lo, bounds[b])
            if ov > 0:
                per[b] += a * ov / span
    return [p / tot for p in per], tot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--bootstrap", required=True)
    ap.add_argument("--random", required=True, dest="random_dir")
    ap.add_argument(
        "--full",
        default=None,
        help="the UNFILTERED source dataset. When given, the full patch "
        "population is added as a third row, which is how a single RANDOM draw "
        "is checked for spatial representativeness.",
    )
    args = ap.parse_args()

    ref = json.load(open(args.reference))["patches"]
    area = {p["id"]: p["total_area"] for p in ref}

    boot = set(os.listdir(os.path.join(args.bootstrap, "verified_patches")))
    rand = set(os.listdir(os.path.join(args.random_dir, "verified_patches")))
    both = (boot | rand) & area.keys()

    boxes = load_boxes(args.bootstrap, boot & area.keys())
    boxes.update(load_boxes(args.random_dir, (rand - boot) & area.keys()))
    missing = both - boxes.keys()
    if missing:
        print(f"WARNING: {len(missing)} patch(es) had no readable meta.json")

    tot_a = sum(area[i] for i in boxes)
    cx = sum(0.5 * (boxes[i][0][0] + boxes[i][1][0]) * area[i] for i in boxes) / tot_a
    cy = sum(0.5 * (boxes[i][0][1] + boxes[i][1][1]) * area[i] for i in boxes) / tot_a
    extent = {i: radial_extent(boxes[i], cx, cy) for i in boxes}

    widths = sorted(hi - lo for lo, hi in extent.values())
    med_w = widths[len(widths) // 2]
    edges = radial_bands(extent, area)
    band_w = st.median([edges[i + 1] - edges[i] for i in range(len(edges) - 1)])

    print(f"radial centre (area-weighted, XY): ({cx:,.0f}, {cy:,.0f})")
    print(f"patches with geometry: {len(boxes):,} of {len(both):,}")
    print(
        f"median patch radial WIDTH {med_w:,.0f} vx vs median band width "
        f"{band_w:,.0f} vx -- the reason area is spread, not point-assigned\n"
    )

    sb, _ = area_share_by_band(boot & extent.keys(), extent, edges, area)
    sr, _ = area_share_by_band(rand & extent.keys(), extent, edges, area)

    # Band edges stay derived from BOOTSTRAP | RANDOM even when --full is given.
    # That union is 93.6% of patches, so the edges barely move, and holding them
    # fixed keeps these numbers comparable with
    # reports/patch_bootstrap_outer_evidence_deficit.md rather than silently
    # restating a published table on a new axis.
    sa = None
    if args.full:
        full_boxes = load_boxes(args.full, set(area))
        full_extent = {i: radial_extent(full_boxes[i], cx, cy) for i in full_boxes}
        sa, _ = area_share_by_band(set(full_extent), full_extent, edges, area)

    print(
        f"{'band':<6}{'radius <=':>12}{'BOOT area%':>12}{'RAND area%':>12}{'gap pts':>10}"
        + (f"{'ALL area%':>11}{'RAND-ALL':>10}" if sa else "")
    )
    gaps, gaps_ra = [], []
    for b in range(N_BANDS):
        lim = f"{edges[b]:,.0f}" if b < len(edges) else "outermost"
        g = 100 * (sb[b] - sr[b])
        gaps.append(abs(g))
        row = f"{b:<6}{lim:>12}{100 * sb[b]:>12.2f}{100 * sr[b]:>12.2f}{g:>+10.2f}"
        if sa:
            d = 100 * (sr[b] - sa[b])
            gaps_ra.append(abs(d))
            row += f"{100 * sa[b]:>11.2f}{d:>+10.2f}"
        print(row)

    print(
        f"\nlargest per-band gap: {max(gaps):.2f} points "
        f"(global area gap for the same build: 0.01 points)"
    )
    print(
        f"outermost band: BOOT {100 * sb[-1]:.2f}% vs RAND {100 * sr[-1]:.2f}% "
        f"of own area -- this is the region w120-w129 is scored on"
    )
    mb = st.mean([0.5 * (extent[i][0] + extent[i][1]) for i in boot & extent.keys()])
    mr = st.mean([0.5 * (extent[i][0] + extent[i][1]) for i in rand & extent.keys()])
    print(f"\nmean midpoint radius  BOOT {mb:,.0f}  RAND {mr:,.0f}")

    if sa:
        print(
            f"\nRANDOM vs FULL population: largest band gap {max(gaps_ra):.2f} points, "
            f"against {max(gaps):.2f} for BOOTSTRAP vs RANDOM. A draw that tracks the "
            "population across every radial band is not spatially extreme -- the "
            "dimension reports/patch_bootstrap_selection_verified.md left unchecked."
        )
    print(
        "\nREPORTED, NOT GATED: no spatial balance criterion was pre-registered, and "
        "picking one now would be choosing a threshold after seeing the data. The "
        "radial proxy is monotone in winding but not calibrated to it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
