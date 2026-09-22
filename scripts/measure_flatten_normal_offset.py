"""How far apart are two surfaces ALONG THE SURFACE NORMAL, not merely point to point?

`scripts/measure_flatten_divergence.py` reports nearest-neighbour distance between
two flattened tifxyz surfaces. That number cannot separate two different things:

* the surface MOVED (a displacement along its normal), and
* the same surface was RE-SAMPLED on a grid offset within the sheet.

The flat tifxyz grid is spaced ~20 vx, so two samplings of ONE sheet with a random
in-plane offset read ~7.7-8.0 vx apart by nearest neighbour. Two stock flattens of
identical meshes read 7.15 vx apart that way and were reported as landing on
"different surfaces"; along the normal they are 0.25 vx apart
(reports/the_flatten_moves_the_grid_not_the_surface.md).

This splits each nearest-neighbour vector into its component along A's own grid
normal (a displacement) and the remainder in the sheet's plane (a re-sampling).

Run:
    python scripts/measure_flatten_normal_offset.py <A flat tifxyz dir> <B flat tifxyz dir> [--json out]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def load_grid(flat_dir: str) -> tuple[np.ndarray, np.ndarray]:
    import tifffile

    d = Path(flat_dir)
    P = np.stack(
        [tifffile.imread(d / f"{c}.tif").astype(np.float64) for c in "xyz"], -1
    )
    m = (P != 0).any(-1) & (P[..., 2] > 0)
    return P, m


def grid_normals(P: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Unit normals from central differences on the grid; NaN where a neighbour
    is invalid or on the border."""
    gu = np.full(P.shape, np.nan)
    gv = np.full(P.shape, np.nan)
    ok_u = m[:, 2:] & m[:, :-2]
    ok_v = m[2:] & m[:-2]
    gu[:, 1:-1][ok_u] = (P[:, 2:] - P[:, :-2])[ok_u]
    gv[1:-1][ok_v] = (P[2:] - P[:-2])[ok_v]
    n = np.cross(gu, gv)
    with np.errstate(invalid="ignore", divide="ignore"):
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


def normal_offset(
    PA: np.ndarray,
    mA: np.ndarray,
    PB: np.ndarray,
    mB: np.ndarray,
    frac: float = 1.0,
    seed: int = 0,
    axis: tuple[float, float] | None = None,
) -> dict[str, float]:
    """Statistics of B's points relative to surface A, split along A's normal.

    With `axis` = (cx, cy), also report the displacement along the OUTWARD normal
    (the grid normal flipped where it points toward the axis). The grid normal's
    own sign is arbitrary, so only the outward reading compares across surfaces."""
    n = grid_normals(PA, mA)
    good = mA & np.isfinite(n).all(-1)
    A, NA = PA[good], n[good]
    B = PB[mB]
    if frac < 1.0:
        keep = np.random.default_rng(seed).permutation(len(B))[
            : max(1, int(len(B) * frac))
        ]
        B = B[keep]
    dist, idx = cKDTree(A).query(B)
    v = B - A[idx]
    dn = (v * NA[idx]).sum(-1)
    dt = np.linalg.norm(v - dn[:, None] * NA[idx], axis=-1)
    extra: dict[str, float] = {}
    if axis is not None:
        q = A[idx]
        radial = np.stack([q[:, 0] - axis[0], q[:, 1] - axis[1]], -1)
        outward = np.sign((NA[idx][:, :2] * radial).sum(-1))
        extra["normal_outward_median"] = float(np.median(dn * outward))
    return extra | {
        "n_a": int(len(A)),
        "n_b": int(len(B)),
        "nn_p50": float(np.median(dist)),
        "nn_mean": float(dist.mean()),
        "normal_abs_p50": float(np.median(np.abs(dn))),
        "normal_abs_p90": float(np.percentile(np.abs(dn), 90)),
        "normal_signed_median": float(np.median(dn)),
        "in_plane_p50": float(np.median(dt)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument(
        "--frac", type=float, default=0.125, help="share of B's points queried"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    PA, mA = load_grid(a.a)
    PB, mB = load_grid(a.b)
    r = normal_offset(PA, mA, PB, mB, frac=a.frac)
    print(f"A {a.a}\nB {a.b}")
    print(
        f"  nearest neighbour p50 {r['nn_p50']:.2f} vx (mean {r['nn_mean']:.2f})\n"
        f"  ALONG A's NORMAL  |d| p50 {r['normal_abs_p50']:.2f}  p90 {r['normal_abs_p90']:.2f}"
        f"  signed median {r['normal_signed_median']:+.2f}\n"
        f"  IN-PLANE          p50 {r['in_plane_p50']:.2f}"
    )
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
