"""Turn an Automated Fiber Volume (.afv, villa volume-cartographer/docs/fiber-collections.md) into an instance labelling
ScrollGT can score.

An .afv stores each fiber as a polyline in native L0 XYZ voxels, split into blocks of at most 256 segments that share
their boundary point. ScrollGT scores a (Z, Y, X) integer labelling, 0 = background. Each polyline is sampled every
`step` voxels; each sampled voxel takes the id of the fiber whose sample lies nearest its centre (ties: lower fiber
id). ScrollGT's tolerance then grows the labelling by nearest-label, so a thin centreline is a valid entrant.

Optionally an affine (4x4, native XYZ -> cube frame XYZ) and a translation are applied before the cube origin is
subtracted, for collections on another scan of the same scroll.

Usage: .venv/bin/python scripts/afv_to_labels.py AFV --origin-zyx Z Y X --size N --out labels.npy
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np


def read_afv(
    path: Path, bbox_xyz: tuple[np.ndarray, np.ndarray] | None = None
) -> dict[int, np.ndarray]:
    """fiber id -> (N, 3) float64 XYZ polyline. With bbox_xyz=(lo, hi), only fibers with a block intersecting it."""
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        if con.execute("PRAGMA application_id").fetchone()[0] != 0x56434643:
            raise ValueError(f"{path}: not an Automated Fiber Volume (application_id)")
        if con.execute(
            "SELECT value FROM metadata WHERE key = 'complete'"
        ).fetchone() != ("true",):
            raise ValueError(f"{path}: incomplete .afv")
        if bbox_xyz is None:
            ids = [r[0] for r in con.execute("SELECT id FROM fibers")]
        else:
            # Python floats: sqlite3 binds a numpy integer as a BLOB, and the RTree comparison then silently
            # matches nothing.
            lo, hi = ([float(v) for v in np.asarray(b, dtype=float)] for b in bbox_xyz)
            ids = sorted({r[0] for r in con.execute(
                "SELECT DISTINCT b.fiber_id FROM block_bounds r JOIN blocks b ON b.id = r.id WHERE r.max_x >= ? AND "
                "r.min_x <= ? AND r.max_y >= ? AND r.min_y <= ? AND r.max_z >= ? AND r.min_z <= ?",
                (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))})  # fmt: skip
        out = {}
        for fid in ids:
            pts = []
            for (blob,) in con.execute(
                "SELECT points FROM blocks WHERE fiber_id = ? ORDER BY first_segment",
                (fid,),
            ):
                p = np.frombuffer(blob, dtype="<f8").reshape(-1, 3)
                pts.append(
                    p if not pts else p[1:]
                )  # consecutive blocks share their boundary point
            out[int(fid)] = np.concatenate(pts)
        return out
    finally:
        con.close()


def to_cube_zyx(
    xyz: np.ndarray,
    origin_zyx,
    affine: np.ndarray | None = None,
    shift_zyx=(0.0, 0.0, 0.0),
) -> np.ndarray:
    """Native XYZ -> cube-local ZYX: optional affine (to the cube's frame), minus a translation, minus the origin."""
    if affine is not None:
        xyz = xyz @ affine[:3, :3].T + affine[:3, 3]
    return xyz[:, ::-1] - np.asarray(shift_zyx, float) - np.asarray(origin_zyx, float)


def rasterize(
    fibers_zyx: dict[int, np.ndarray], shape, step: float = 0.25
) -> np.ndarray:
    """Thin centreline labelling: label = 1 + rank of the fiber id; nearest sample wins a voxel, ties to the lower id."""
    vox, dist, lab = [], [], []
    for rank, fid in enumerate(sorted(fibers_zyx)):
        p = fibers_zyx[fid]
        if len(p) == 0:
            continue
        seg = np.diff(p, axis=0)
        n = np.maximum(np.ceil(np.linalg.norm(seg, axis=1) / step).astype(int), 1)
        t = np.concatenate([np.arange(k) / k for k in n]) if len(n) else np.zeros(0)
        start = np.repeat(p[:-1], n, axis=0)
        samples = np.concatenate(
            [start + np.repeat(seg, n, axis=0) * t[:, None], p[-1:]]
        )
        idx = np.rint(samples).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < np.asarray(shape)), axis=1)
        vox.append(idx[ok])
        dist.append(np.linalg.norm(samples[ok] - idx[ok], axis=1))
        lab.append(np.full(int(ok.sum()), rank + 1, dtype=np.int64))
    out = np.zeros(shape, dtype=np.int32)
    if not vox:
        return out
    v, d, lb = np.concatenate(vox), np.concatenate(dist), np.concatenate(lab)
    flat = np.ravel_multi_index(v.T, shape)
    order = np.lexsort((lb, d, flat))  # by voxel, then distance, then label
    flat, lb = flat[order], lb[order]
    first = np.ones(len(flat), bool)
    first[1:] = flat[1:] != flat[:-1]
    out.ravel()[flat[first]] = lb[first]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("afv", type=Path)
    ap.add_argument("--origin-zyx", type=float, nargs=3, required=True)
    ap.add_argument("--size", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    shape = (args.size,) * 3
    o = np.asarray(args.origin_zyx)[::-1]
    fibers = read_afv(args.afv, (o - 2, o + args.size + 2))
    labels = rasterize(
        {k: to_cube_zyx(v, args.origin_zyx) for k, v in fibers.items()}, shape
    )
    np.save(args.out, labels)
    print(f"{len(fibers)} fibers near the cube; {int((labels > 0).sum())} labelled voxels; "
          f"{len(np.unique(labels)) - 1} instances")  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
