"""Exploratory, after finding 92: where thin predicted centrelines sit relative to ScrollGT's hand-traced fibers.

Finding 91's neural tracer and #1934's generator write thin centrelines; ScrollGT scores them at a tolerance of 2
voxels. Per cube, both polylines are sampled every 0.25 voxel, and each predicted sample within 6 voxels of the GT is
matched to its nearest GT sample. Recorded per cube and entrant:

* the share of matched samples within 2 voxels;
* the median displacement (z, y, x) from prediction to GT. The displacement to the nearest GT point is perpendicular
  to the GT fiber, so a shift between the GT and the CT shows only on fibers across it: a shift along z is invisible on
  a vertical fiber, and where those hold most samples the median misses it. So the median along each axis is also
  recorded over the samples on fibers within 30 degrees of perpendicular to it, which see at least 3/4 of a shift;
* that share separately for samples nearest a GT point within 1 voxel of an annotator's node, and at least 3 voxels
  from both: straight edges between sparse nodes would put a tracer that follows the true centre further off
  mid-edge;
* the GT's median edge length.

Writes reports/neural_tracer_placement.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402

STEP, RADIUS, TOL = 0.25, 6.0, 2.0
NEAR_NODE, MID_EDGE = 1.0, 3.0
PERPENDICULAR = (
    0.5  # |cos| of a fiber's angle to an axis: within 30 degrees of perpendicular to it
)
NEURAL = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/run")
GENERATOR = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/run")


def _samples(p: np.ndarray, step: float = STEP) -> np.ndarray:
    """A polyline (N, 3) sampled every `step` along each segment, both ends kept."""
    if len(p) < 2:
        return p
    seg = np.diff(p, axis=0)
    n = np.maximum(np.ceil(np.linalg.norm(seg, axis=1) / step).astype(int), 1)
    t = np.concatenate([np.arange(k) / k for k in n])
    return np.vstack(
        [np.repeat(p[:-1], n, axis=0) + np.repeat(seg, n, axis=0) * t[:, None], p[-1:]]
    )


def gt_samples(
    fibers, size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """GT edges sampled every STEP inside the cube: points (z, y, x), each one's edge length, its distance from the
    nearer of the edge's two nodes, and the edge's unit direction (NaN for an edge of length 0)."""
    P, length, node, direction = [], [], [], []
    for f in fibers:
        for a, b in f.edges:
            p0, p1 = f.coords[a], f.coords[b]
            e = float(np.linalg.norm(p1 - p0))
            n = max(int(np.ceil(e / STEP)), 1)
            t = np.arange(n + 1) / n
            P.append(p0 + (p1 - p0) * t[:, None])
            length.append(np.full(n + 1, e))
            node.append(np.minimum(t, 1 - t) * e)
            u = (p1 - p0) / e if e > 0 else np.full(3, np.nan)
            direction.append(np.tile(u, (n + 1, 1)))
    P, length, node = np.vstack(P), np.concatenate(length), np.concatenate(node)
    direction = np.vstack(direction)
    inside = np.all((P >= 0) & (size > P), axis=1)
    return P[inside], length[inside], node[inside], direction[inside]


def placement(
    pred: np.ndarray,
    P: np.ndarray,
    length: np.ndarray,
    node: np.ndarray,
    direction: np.ndarray,
) -> dict:
    """Predicted samples matched to their nearest GT sample within RADIUS, as recorded per cube."""
    from scipy.spatial import cKDTree

    d, i = cKDTree(P).query(pred, distance_upper_bound=RADIUS)
    ok = np.isfinite(d)
    d, i = d[ok], i[ok]
    near, mid = node[i] <= NEAR_NODE, node[i] >= MID_EDGE
    disp = P[i] - pred[ok]
    # On a fiber within 30 degrees of perpendicular to an axis (|cos| <= 1/2), the displacement keeps 1 - cos^2, at
    # least 3/4, of a shift along that axis.
    across = np.abs(direction[i]) <= PERPENDICULAR

    def share(m):
        return float((d[m] <= TOL).mean()) if m.any() else None

    return {
        "n_pred": int(len(pred)),
        "n_matched": int(ok.sum()),
        "matched_share": float(ok.mean()),
        "le2": share(np.ones(len(d), bool)),
        "median_disp_zyx": [float(v) for v in np.median(disp, axis=0)],
        "median_disp_perp_zyx": [
            float(np.median(disp[across[:, a], a])) if across[:, a].any() else None
            for a in range(3)
        ],
        "n_perp_zyx": [int(n) for n in across.sum(axis=0)],
        "n_near_node": int(near.sum()),
        "near_node_le2": share(near),
        "n_mid_edge": int(mid.sum()),
        "mid_edge_le2": share(mid),
        "median_gt_edge_of_matched": float(np.median(length[i])),
    }


def predicted(afv: Path, size: int) -> np.ndarray:
    """A .afv's fibers as cube (z, y, x) samples inside the cube, as finding 91 rasterised them."""
    fibers = afv_to_labels.read_afv(afv)
    pts = [
        _samples(afv_to_labels.to_cube_zyx(v, (0, 0, 0)))
        for v in fibers.values()
        if len(v)
    ]
    p = np.vstack(pts)
    return p[np.all((p >= 0) & (p < size), axis=1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--neural", type=Path, default=NEURAL, help="finding 91's work dir")
    ap.add_argument(
        "--generator",
        type=Path,
        default=GENERATOR,
        help="finding 85's generator work dir",
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_placement.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.target import load_fiber_target

    cubes = {}
    for c in f91.ALL:
        size = int(c.rsplit("_", 1)[1])
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
        gt = gt_samples(skel.fibers, size)
        edges = np.concatenate([np.linalg.norm(f.coords[f.edges[:, 1]] - f.coords[f.edges[:, 0]], axis=1)
                                for f in skel.fibers])  # fmt: skip
        edge = float(np.median(edges))
        neural = placement(predicted(args.neural / c / "fibers.afv", size), *gt)
        generator = placement(predicted(args.generator / f"{c}.afv", size), *gt)
        cubes[c] = {"gt_median_edge": edge, "neural": neural, "generator": generator}
        print(c, f"{edge:.2f}", neural["le2"], generator["le2"], flush=True)
    out = {
        "status": "exploratory, after finding 92's registered result",
        "step": STEP,
        "radius": RADIUS,
        "tolerance": TOL,
        "near_node": NEAR_NODE,
        "mid_edge": MID_EDGE,
        "perpendicular": PERPENDICULAR,
        "sources": {
            "neural": "/".join(args.neural.resolve().parts[-3:]),
            "generator": "/".join(args.generator.resolve().parts[-3:]),
        },  # fmt: skip
        "groups": {
            "in_sample": f91.IN_SAMPLE,
            "s3": f91.S3,
            "s5_held_out": f91.S5_HELDOUT,
        },
        "cubes": cubes,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
