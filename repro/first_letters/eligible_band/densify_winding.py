"""Subdivide a tifxyz winding grid: original nodes kept, bilinear midpoints added (finding 130).

A grid of H x W nodes becomes (F(H - 1) + 1) x (F(W - 1) + 1) for factor F. A new node exists only where every node
it is interpolated from exists. meta.json's scale is multiplied by F (more nodes per voxel), its area and bbox kept,
and the source noted.

usage: densify_winding.py IN_TIFXYZ OUT_TIFXYZ [--factor 2]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def densify(
    xyz: np.ndarray, valid: np.ndarray, factor: int
) -> tuple[np.ndarray, np.ndarray]:
    """(H, W, 3) nodes and their mask -> the subdivided grid and mask."""
    if factor < 1:
        raise ValueError("factor must be at least 1")
    h, w = valid.shape
    rows = np.linspace(0, h - 1, factor * (h - 1) + 1)
    cols = np.linspace(0, w - 1, factor * (w - 1) + 1)
    r0 = (
        np.minimum(np.floor(rows).astype(int), h - 2)
        if h > 1
        else np.zeros(len(rows), int)
    )
    c0 = (
        np.minimum(np.floor(cols).astype(int), w - 2)
        if w > 1
        else np.zeros(len(cols), int)
    )
    fr = (rows - r0)[:, None, None]
    fc = (cols - c0)[None, :, None]
    r1 = np.minimum(r0 + 1, h - 1)
    c1 = np.minimum(c0 + 1, w - 1)
    p = np.where(valid[..., None], xyz, 0.0)
    out = (
        (1 - fr) * (1 - fc) * p[r0][:, c0]
        + (1 - fr) * fc * p[r0][:, c1]
        + fr * (1 - fc) * p[r1][:, c0]
        + fr * fc * p[r1][:, c1]
    )
    # a node needs the corners it takes weight from
    need = lambda f: f > 1e-9  # noqa: E731
    ok = (
        (valid[r0][:, c0] | ~(need(1 - fr[..., 0]) & need(1 - fc[..., 0])))
        & (valid[r0][:, c1] | ~(need(1 - fr[..., 0]) & need(fc[..., 0])))
        & (valid[r1][:, c0] | ~(need(fr[..., 0]) & need(1 - fc[..., 0])))
        & (valid[r1][:, c1] | ~(need(fr[..., 0]) & need(fc[..., 0])))
    )
    return out, ok


def main(argv: list[str] | None = None) -> int:
    import tifffile

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--factor", type=int, default=2)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    xyz = np.stack(
        [tifffile.imread(args.src / f"{c}.tif").astype(np.float64) for c in "xyz"], -1
    )
    valid = np.isfinite(xyz).all(-1) & (xyz > -0.5).all(-1)
    dense, ok = densify(xyz, valid, args.factor)
    args.out.mkdir(parents=True)
    for i, c in enumerate("xyz"):
        tifffile.imwrite(
            args.out / f"{c}.tif", np.where(ok, dense[..., i], -1.0).astype(np.float32)
        )
    meta = json.loads((args.src / "meta.json").read_text())
    meta["scale"] = [float(s) * args.factor for s in meta.get("scale", [0.05, 0.05])]
    meta["source"] = (
        meta.get("source", "") + f" + densify_winding x{args.factor} (finding 130)"
    )
    (args.out / "meta.json").write_text(json.dumps(meta, indent=4) + "\n")
    print(f"{args.src.name}: {valid.shape} -> {ok.shape}, {int(ok.sum())} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
