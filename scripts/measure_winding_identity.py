"""Does a winding NAME denote the same papyrus in two fits?

The anchor-count ablation is blocked on exactly this. The ink strip is selected
by winding name (w120-w129), and `abs_winding.json` is the only thing pinning the
absolute index (`fit_spiral.py:1577`). Thin the anchors and index 120 may denote
a different physical wrap, which would make any ink comparison between the arms
meaningless -- comparing different papyrus and calling the difference an effect.

The blocking measurement so far used **median radius**, which cannot settle it:
`calibrate_radius_to_winding.py` established that one winding sweeps ~1,683 vx of
radius and overlaps its neighbours entirely, so radius orders windings but does
not identify one.

This matches windings by **surface proximity** instead, which does identify them:
for each winding in the reference fit, find the nearest winding in the other fit
by median point-to-surface distance, and report the INDEX OFFSET.

    offset 0 everywhere -> numbering preserved, the ablation is interpretable
    offset +/-1         -> the strip is different papyrus, the study is dead

Center-free, so it needs no cx/cy convention, and it answers the question asked
rather than a proxy for it.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import tifffile
    from scipy.spatial import cKDTree
except ImportError:  # pragma: no cover
    tifffile = cKDTree = None

MAX_PTS = 40_000  # per surface; plenty for a median at these scales


def load_points(mesh_root: str, tag: str, w: int, rng: np.random.Generator):
    """Valid (x,y,z) mesh points for one winding. -1 / non-positive is no-data."""
    d = Path(mesh_root) / f"w{w:03d}_{tag}"
    if not d.is_dir():
        return None
    try:
        x, y, z = (
            tifffile.imread(str(d / f"{c}.tif")).astype(np.float64) for c in "xyz"
        )
    except (FileNotFoundError, ValueError):
        return None
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not m.any():
        return None
    p = np.column_stack([x[m], y[m], z[m]])
    if len(p) > MAX_PTS:
        p = p[rng.choice(len(p), MAX_PTS, replace=False)]
    return p


def median_surface_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Median nearest-neighbour distance from points of A to the surface of B.

    Asymmetric by construction; the caller compares one reference winding against
    several candidates, so the reference side is held fixed and only B varies.
    """
    return float(np.median(cKDTree(b).query(a, k=1)[0]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ref-meshes", required=True, help="meshes/fitted_<tag> of the reference fit"
    )
    ap.add_argument("--ref-tag", required=True)
    ap.add_argument("--alt-meshes", required=True)
    ap.add_argument("--alt-tag", required=True)
    ap.add_argument("--strip", default="120-129", help="reference windings to check")
    ap.add_argument(
        "--search", type=int, default=3, help="+/- windings to search in alt"
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if tifffile is None or cKDTree is None:
        raise SystemExit("needs tifffile and scipy")

    lo, hi = (int(v) for v in args.strip.split("-"))
    rng = np.random.default_rng(args.seed)

    rows = []
    print(
        f"{'ref':>6}{'best alt':>10}{'offset':>8}{'dist':>10}{'runner-up':>11}{'margin':>9}"
    )
    for w in range(lo, hi + 1):
        a = load_points(args.ref_meshes, args.ref_tag, w, rng)
        if a is None:
            print(f"w{w:03d}   reference winding missing, skipped")
            continue
        cand = {}
        for v in range(w - args.search, w + args.search + 1):
            b = load_points(args.alt_meshes, args.alt_tag, v, rng)
            if b is not None:
                cand[v] = median_surface_distance(a, b)
        if not cand:
            print(f"w{w:03d}   no candidate windings found, skipped")
            continue
        order = sorted(cand.items(), key=lambda kv: kv[1])
        best, d0 = order[0]
        second, d1 = order[1] if len(order) > 1 else (None, float("nan"))
        rows.append(
            {
                "ref": w,
                "best": best,
                "offset": best - w,
                "dist": d0,
                "runner_up": second,
                "runner_up_dist": d1,
            }
        )
        label = f"w{second:03d}" if second is not None else "-"
        print(f"w{w:03d}{best:>10}{best - w:>+8}{d0:>10.2f}{label:>11}{d1 - d0:>9.2f}")

    if not rows:
        raise SystemExit("nothing compared")

    offs = [int(r["offset"]) for r in rows]
    n0 = sum(o == 0 for o in offs)
    print(
        f"\n{n0}/{len(offs)} windings keep their number; offsets seen: {sorted(set(offs))}"
    )
    verdict = "NUMBERING PRESERVED" if all(o == 0 for o in offs) else "RENUMBERED"
    print(f"VERDICT: {verdict}")
    if verdict == "RENUMBERED":
        print(
            "  A name-selected strip is NOT the same papyrus in both fits, so an ink\n"
            "  comparison between them would be uninterpretable."
        )
    else:
        med = float(np.median([r["dist"] for r in rows]))
        margin = float(np.median([r["runner_up_dist"] - r["dist"] for r in rows]))
        print(
            f"  median self-distance {med:.2f} vx, median margin to the next winding "
            f"{margin:.2f} vx"
        )
        if margin < med:
            print(
                "  WARNING: the margin is smaller than the self-distance; the match is\n"
                "  not comfortable and this verdict should not be leaned on."
            )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "verdict": verdict,
                    "rows": rows,
                    "ref": args.ref_tag,
                    "alt": args.alt_tag,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
