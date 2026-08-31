"""Are two spiral-fit runs geometrically comparable?

Backs the control in `reports/spiral_ink_objective_reachability.md`.
Usage: measure_spiral_comparability.py tag=<meshes_dir> [tag=<meshes_dir> ...]

Original question: Estimate radial sheet spacing
directly from the meshes: median radial distance from the umbilicus axis, per
winding, then the median step between consecutive windings.

If smoke01's spacing is wildly different from the converged runs, its zero
far-overlap is apples-to-oranges and says nothing.
"""

import os
import sys

import numpy as np
import tifffile


def radii(d):
    xyz = [tifffile.imread(os.path.join(d, f"{c}.tif")) for c in "xyz"]
    ok = np.ones(xyz[0].shape, bool)
    for a in xyz:
        ok &= a > -0.5
    return xyz[0][ok], xyz[1][ok]


for tag, base in [(t, p) for t, p in (a.split("=") for a in sys.argv[1:])]:
    ws, meds = [], []
    names = sorted(n for n in os.listdir(base) if "_spliced" in n)
    xs, ys = [], []
    for n in names:
        x, y = radii(os.path.join(base, n))
        xs.append(x)
        ys.append(y)
        ws.append(int(n[1:4]))
    cx = np.median(np.concatenate(xs))
    cy = np.median(np.concatenate(ys))
    for x, y in zip(xs, ys, strict=True):
        meds.append(float(np.median(np.hypot(x - cx, y - cy))))
    meds = np.array(meds)
    ws = np.array(ws)
    o = np.argsort(ws)
    meds, ws = meds[o], ws[o]
    step = np.diff(meds)
    print(
        f"{tag:<12} centre ({cx:7.1f},{cy:7.1f})  radius {meds.min():7.1f}..{meds.max():7.1f}  "
        f"median inter-winding step {np.median(step):6.2f}  monotone {int((step > 0).sum())}/{step.size}"
    )
