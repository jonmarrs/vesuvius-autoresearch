"""Calibrate the radial proxy against the winding meshes it stands in for.

`check_patch_spatial_balance.py` reports patch area by radial band and says, in
its own docstring, that the proxy is "monotone in winding but not calibrated to
it". This checks the first claim and supplies the second, using the fitted
winding meshes (`meshes/fitted_*/w<NNN>_*/{x,y}.tif`, tifxyz volume coordinates
in the same frame as the patch bboxes -- the documented 4x factor is between the
mesh frame and the ink VOLUME, a different pair).

Two things came out of running it, and the second corrects a published report:

1. **Radius is monotone in winding.** Median radius rises without exception from
   w010 to w129 over the sampled windings, so ordering patches by radius does
   order them by depth into the scroll. The proxy's direction is sound.

2. **A single winding sweeps a huge radial range, so radius does NOT identify a
   winding.** w129 runs from 1,715 at p5 to 3,358 at p95, overlapping w100
   entirely. The spiral is not a circle; radius varies around each turn. Any
   claim of the form "this radial band IS winding N" is therefore wrong, and
   `reports/patch_bootstrap_outer_evidence_deficit.md` originally made one by
   calling its outermost band "the region w120-w129 is scored on". That band is
   a SUBSET of the scored strip.

The strip's radial support is what should be quoted instead, and the deficit is
reported over several definitions of it so the number cannot rest on one cut.
"""

import argparse
import sys

import numpy as np

try:
    import tifffile
except ImportError:  # pragma: no cover - exercised only on a box without it
    tifffile = None

SAMPLE = (10, 20, 40, 60, 80, 100, 110, 120, 122, 124, 126, 128, 129)


def winding_radii(mesh_root, tag, w, cx, cy):
    """Radii of every valid mesh point in one winding. -1 is the no-data value."""
    x = tifffile.imread(f"{mesh_root}/w{w:03d}_{tag}/x.tif").astype(np.float64)
    y = tifffile.imread(f"{mesh_root}/w{w:03d}_{tag}/y.tif").astype(np.float64)
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    return np.hypot(x[m] - cx, y[m] - cy) if m.any() else None


def is_monotone(medians):
    return all(b >= a for a, b in zip(medians, medians[1:], strict=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meshes", required=True, help="meshes/fitted_<tag> directory")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cx", type=float, required=True)
    ap.add_argument("--cy", type=float, required=True)
    ap.add_argument("--strip", default="120-129")
    args = ap.parse_args()

    if tifffile is None:
        print("tifffile is not installed; cannot read the meshes")
        return 2

    print(f"{'winding':<9}{'median r':>10}{'p5':>9}{'p95':>9}{'n px':>10}")
    medians = []
    for w in SAMPLE:
        r = winding_radii(args.meshes, args.tag, w, args.cx, args.cy)
        if r is None:
            continue
        medians.append(float(np.median(r)))
        print(
            f"w{w:<8}{medians[-1]:>10,.0f}{np.percentile(r, 5):>9,.0f}"
            f"{np.percentile(r, 95):>9,.0f}{r.size:>10,}"
        )

    mono = is_monotone(medians)
    print(f"\nmedian radius monotone in winding: {mono}")
    if not mono:
        print("  the radial proxy does NOT order windings; band tables built on it")
        print("  cannot be read as inner-to-outer and should be withdrawn")

    lo_w, hi_w = (int(v) for v in args.strip.split("-"))
    parts = [
        r
        for r in (
            winding_radii(args.meshes, args.tag, w, args.cx, args.cy)
            for w in range(lo_w, hi_w + 1)
        )
        if r is not None
    ]
    strip = np.concatenate(parts)
    p5, med, p95 = (float(np.percentile(strip, q)) for q in (5, 50, 95))
    print(
        f"\nscored strip w{lo_w}-w{hi_w}: radius p5 {p5:,.0f}  median {med:,.0f}  "
        f"p95 {p95:,.0f}"
    )

    widths = []
    for w in range(lo_w, hi_w + 1):
        r = winding_radii(args.meshes, args.tag, w, args.cx, args.cy)
        if r is not None:
            widths.append(np.percentile(r, 95) - np.percentile(r, 5))
    print(
        f"a SINGLE winding spans {np.median(widths):,.0f} vx of radius (median p5-p95), "
        "so radius orders windings but does not identify one"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
