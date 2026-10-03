"""Subsample a tifxyz mesh's grid by an integer stride: keep every STRIDE-th grid point in both directions.

The kept points are unchanged (same 3D positions, same -1 invalid marker), so the surface passes through
the same points; only the grid gets coarser. meta.json's `scale` is divided by STRIDE so renderers keep
the same output size per unit of surface. Used to test whether grid cell size drives the linear/smooth
render difference (docs/preregistration/2026-10-03_coarse_grid_interpolation.md).

Usage: .venv/bin/python scripts/subsample_mesh.py SRC_TIFXYZ DST_TIFXYZ STRIDE
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import tifffile


def subsample(src: Path, dst: Path, stride: int) -> None:
    if dst.exists():
        sys.exit(f"{dst} exists")
    dst.mkdir(parents=True)
    shapes = set()
    for c in "xyz":
        a = tifffile.imread(src / f"{c}.tif")
        b = np.ascontiguousarray(a[::stride, ::stride])
        tifffile.imwrite(dst / f"{c}.tif", b)
        shapes.add(b.shape)
    assert len(shapes) == 1
    meta = json.loads((src / "meta.json").read_text())
    meta["scale"] = [s / stride for s in meta["scale"]]
    meta["subsampled_from"] = {"src": str(src), "stride": stride}
    (dst / "meta.json").write_text(json.dumps(meta, indent=4) + "\n")
    print(f"{dst}: grid {shapes.pop()}, scale {meta['scale']}")


if __name__ == "__main__":
    subsample(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
