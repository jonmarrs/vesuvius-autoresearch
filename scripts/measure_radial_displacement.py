"""Did the gap-expander fix move the scored surface RADIALLY, or along the sheet?

`reports/the_gap_fix_does_not_remove_duplicated_coverage.md` established that the
fix costs 10.35% of the ink while leaving every coverage measure flat -- the same
canvas yields less ink -- and left one question open: does the surface RELOCATE
along the sheet, or RE-SAMPLE at a different depth across it?

For a spiral those are separable without any point correspondence, which matters
because the two arms' meshes are not point-comparable ((285,613) vs (285,612)):

  * **radial** displacement is normal to the sheet -- a depth change across layers;
  * **theta / z** displacement is along it -- lateral relocation.

Two rules this encodes, both of which change the answer:

* **ONE axis, derived, shared by both arms.** `analyse_placement_mechanism.py`
  records that a hardcoded axis "halved an effect once". Here a per-arm axis would
  be worse than wrong: any axis error is common-mode and cancels in the DELTA only
  if both arms use the same one.
* **Exclude sentinel points.** `z <= 0` marks invalid samples and they are 5.1% of
  the surface. Including them reports -4.65 vx; excluding them, -3.73 vx. The
  headline moves 20% on a mask choice.
"""

import argparse
import glob
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import stats

BASE = ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06")
GAP = ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6")
WINDINGS = tuple(f"w{i}" for i in range(120, 130))
DR_PER_WINDING = 16.17  # measure_winding_overlap.py docstring, this fit


def _points(spiral_out: str, tag: str, w: str):
    d = glob.glob(f"{spiral_out}/*patch_{tag}/meshes/*/{w}_spliced_*")
    if not d:
        return None
    x = tifffile.imread(f"{d[0]}/x.tif")
    y = tifffile.imread(f"{d[0]}/y.tif")
    z = tifffile.imread(f"{d[0]}/z.tif")
    m = ((x != 0) | (y != 0) | (z != 0)) & (z > 0) & np.isfinite(x) & np.isfinite(y)
    return x[m], y[m], z[m]


def shared_axis(spiral_out: str, tags) -> tuple[float, float]:
    xs, ys = [], []
    for t in tags:
        for w in WINDINGS:
            p = _points(spiral_out, t, w)
            if p is not None:
                xs.append(p[0])
                ys.append(p[1])
    return float(np.concatenate(xs).mean()), float(np.concatenate(ys).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    cx, cy = shared_axis(a.spiral_out, BASE + GAP)
    print(
        f"shared axis derived from all {len(BASE + GAP)} arms: cx={cx:.1f} cy={cy:.1f}"
    )
    print("sentinel points (z<=0) excluded\n")

    def r_of(tag: str, w: str):
        p = _points(a.spiral_out, tag, w)
        return None if p is None else float(np.hypot(p[0] - cx, p[1] - cy).mean())

    print(f"{'winding':<9}{'baseline r':>12}{'gap133 r':>12}{'delta_r':>10}{'p':>9}")
    out, deltas = {}, []
    for w in WINDINGS:
        b = [v for v in (r_of(t, w) for t in BASE) if v is not None]
        g = [v for v in (r_of(t, w) for t in GAP) if v is not None]
        if len(b) < 2 or len(g) < 2:
            continue
        d = st.mean(g) - st.mean(b)
        _, p = stats.ttest_ind(b, g, equal_var=False)
        deltas.append(d)
        out[w] = {
            "baseline": st.mean(b),
            "gap133": st.mean(g),
            "delta": d,
            "p": float(p),
        }
        print(f"{w:<9}{st.mean(b):>12.2f}{st.mean(g):>12.2f}{d:>+10.2f}{p:>9.4f}")

    mean_d = st.mean(deltas)
    frac = abs(mean_d) / DR_PER_WINDING
    print(f"\nmean radial shift over {len(deltas)} windings: {mean_d:+.2f} voxels")
    print(f"  = {frac:.1%} of one winding gap ({DR_PER_WINDING} vx)")
    print(
        f"  same direction in {sum(1 for d in deltas if d < 0)}/{len(deltas)} windings"
    )
    if a.json:
        Path(a.json).write_text(
            json.dumps(
                {
                    "axis": [cx, cy],
                    "per_winding": out,
                    "mean_delta": mean_d,
                    "fraction_of_winding_gap": frac,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
