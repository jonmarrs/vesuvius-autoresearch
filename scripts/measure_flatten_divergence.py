"""How far apart are two flattens of the same meshes, and what does it cost in ink?

`reports/the_render_is_the_noise_floor.md` established that re-rendering one mesh
set on one pinned tree moves `total_fg_pixels` by 3.04%. This measures the
geometric cause: the lasagna flatten is a stochastic optimisation, and two runs
land on different surfaces.

**Nearest-neighbour surface distance, not index-wise.** The two flattens need not
share a grid -- the outer pair came out (426, 8266) and (425, 8266) -- so
comparing cell [i,j] to cell [i,j] compares different material points. Doing that
reports 20.9 vx for the outer pair where the true surface separation is 7.2 vx;
the difference is parameterization offset, not movement. Index-wise happens to be
valid for the inner pair only because its grids matched exactly, and there it
agrees with NN to three decimals (0.533 vs 0.535).

Usage: measure_flatten_divergence.py --a <flat_dir> --b <flat_dir> [--ink-pct X]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.spatial import cKDTree


def points(flat_dir: str) -> np.ndarray:
    d = Path(flat_dir)
    x, y, z = (tifffile.imread(d / f"{c}.tif").astype(np.float64) for c in "xyz")
    m = ((x != 0) | (y != 0) | (z != 0)) & (z > 0)
    return np.column_stack([x[m], y[m], z[m]])


def nn_distance(
    a: str, b: str, sample: int = 200_000, seed: int = 20260920
) -> np.ndarray:
    PA, PB = points(a), points(b)
    rng = np.random.default_rng(seed)
    sub = PB[rng.choice(len(PB), size=min(sample, len(PB)), replace=False)]
    d, _ = cKDTree(PA).query(sub, k=1)
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument(
        "--ink-pct",
        type=float,
        default=None,
        help="measured |dT| in percent, to report a per-voxel figure",
    )
    ap.add_argument("--sample", type=int, default=200_000)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    d = nn_distance(args.a, args.b, args.sample)
    out = {
        "mean": float(d.mean()),
        "p50": float(np.percentile(d, 50)),
        "p90": float(np.percentile(d, 90)),
        "p99": float(np.percentile(d, 99)),
        "max": float(d.max()),
        "frac_gt_1vx": float(np.mean(d > 1)),
        "frac_gt_16vx": float(np.mean(d > 16)),
    }
    print("flatten divergence, nearest-neighbour surface distance (voxels)\n")
    for k in ("mean", "p50", "p90", "p99", "max"):
        print(f"  {k:<6}{out[k]:>10.3f}")
    print(f"  >1vx  {out['frac_gt_1vx']:>9.2%}")
    print(f"  >16vx {out['frac_gt_16vx']:>9.2%}   (one winding gap is ~16.17 vx)")

    if args.ink_pct is not None:
        per = args.ink_pct / out["mean"]
        out["ink_pct"], out["pct_per_voxel"] = args.ink_pct, per
        print(f"\n  ink change {args.ink_pct:.2f}%  ->  {per:.2f}% per voxel")
        print("  NOT a constant: measured 2.65 %/vx on the inner pair and 0.43 on the")
        print(
            "  outer. A two-point agreement with the gap fix's 2.61 looked like a law"
        )
        print("  and the third point refuted it 6x. Do not extrapolate this ratio.")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
