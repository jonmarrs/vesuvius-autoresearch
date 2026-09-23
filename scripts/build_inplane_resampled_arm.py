"""Re-sample one flattened surface IN-PLANE: same sheet, same grid, different sample points.

Question (`docs/preregistration/2026-09-23_resampling_or_distortion.md`): two flattens of
one surface are read ~13.5% differently per 2 kpx block, and the scorer is
translation-invariant, so the cause is either local DISTORTION of the layout or
RE-SAMPLING of the ink volume at different points. This builds a surface that
isolates re-sampling: every grid point is moved `t` of a cell along the strip
axis (u), ON the sheet. The render of it is the original, translated by ~t cell
(which the scorer ignores), and sampled at different points.

Catmull-Rom along u, not bilinear: bilinear at cell centres puts points ~0.9 vx
inside a curved sheet (measured), a normal displacement the offset sweep shows
already costs ink. Catmull-Rom stays on a smooth sheet to far below that.

Usage:
    build_inplane_resampled_arm.py <src flat tifxyz dir> <out flat tifxyz dir> --t 0.5
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np


def resample_u(P: np.ndarray, m: np.ndarray, t: float) -> tuple[np.ndarray, np.ndarray]:
    """Catmull-Rom between columns j and j+1 at fraction t, from the stencil
    j-1..j+2. A cell is valid only if all four stencil points are valid; the
    border columns without a full stencil are invalid. Invalid cells are zeroed
    (the tifxyz convention)."""
    P0, P1, P2, P3 = P[:, :-3], P[:, 1:-2], P[:, 2:-1], P[:, 3:]
    t2, t3 = t * t, t * t * t
    Q = 0.5 * (
        2 * P1
        + (-P0 + P2) * t
        + (2 * P0 - 5 * P1 + 4 * P2 - P3) * t2
        + (-P0 + 3 * P1 - 3 * P2 + P3) * t3
    )
    ok = m[:, :-3] & m[:, 1:-2] & m[:, 2:-1] & m[:, 3:]
    out = np.zeros_like(P)
    mo = np.zeros(m.shape, bool)
    out[:, 1:-2][ok] = Q[ok]
    mo[:, 1:-2] = ok
    return out, mo


def main() -> int:
    import tifffile

    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--t", type=float, required=True, help="fraction of a cell along u")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    x, y, z = (tifffile.imread(src / f"{c}.tif").astype(np.float64) for c in "xyz")
    m = ((x != 0) | (y != 0) | (z != 0)) & (z > 0)
    P = np.stack([x, y, z], -1)
    Q, mq = resample_u(P, m, a.t)
    out.mkdir(parents=True)
    for i, c in enumerate("xyz"):
        tifffile.imwrite(out / f"{c}.tif", Q[..., i].astype(np.float32))
    meta = json.loads((src / "meta.json").read_text())
    meta["bbox"] = [
        [float(Q[mq][:, k].min()) for k in range(3)],
        [float(Q[mq][:, k].max()) for k in range(3)],
    ]
    meta["source"] = f"in-plane Catmull-Rom resample, t={a.t} cell along u, of {src}"
    (out / "meta.json").write_text(json.dumps(meta, indent=4))
    print(f"wrote {out}: valid {int(mq.sum())} of source {int(m.sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
