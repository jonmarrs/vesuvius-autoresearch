"""Does ink agree less where the two fitted surfaces sit further apart?

Implements `docs/preregistration/2026-09-13_normal_separation_vs_agreement.md`,
committed before this file computed anything.

`reports/ink_offsets_are_not_coherent.md` ruled out a tangential slide between
seeds and was blind, by construction, to a NORMAL displacement -- which is what
the ~24 vx point-to-surface figure actually measures. A normal displacement moves
the sheet through the volume without rotating it, so the detector samples
different voxels and finds different ink, with no angular shift to detect.

Per (z, theta) bin this pairs:

  separation   |mean radius of A's surface - mean radius of B's|  (radius stands
               in for the normal: a spiral's sheet normal is predominantly radial)
  disagreement |ink_A - ink_B| / (ink_A + ink_B)                  (bounded, and
               independent of the arms' absolute ink totals)

and correlates them by Spearman, against a null that shuffles bin labels so the
pairing breaks while both distributions survive exactly.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import NTHETA, NZ, ink_per_cell, load_xyz  # noqa: E402

N_SHUFFLE = 1000
Z_RANGE = (13056.0, 18432.0)


def binned(arm_dir: str, axis):
    """(mean radius, ink) per (z, theta) bin, plus the axis used."""
    xyz = load_xyz(arm_dir)
    if xyz is None:
        return None, None, axis
    x, y, z = xyz
    ink = ink_per_cell(arm_dir, x.shape)
    if ink is None:
        return None, None, axis
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not m.any():
        return None, None, axis
    if axis is None:
        axis = (float(x[m].mean()), float(y[m].mean()))
    cx, cy = axis
    dx, dy = x[m] - cx, y[m] - cy
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    rng = [list(Z_RANGE), [-np.pi, np.pi]]
    cnt, _, _ = np.histogram2d(z[m], th, bins=[NZ, NTHETA], range=rng)
    rsum, _, _ = np.histogram2d(z[m], th, bins=[NZ, NTHETA], range=rng, weights=r)
    isum, _, _ = np.histogram2d(
        z[m], th, bins=[NZ, NTHETA], range=rng, weights=ink[m].astype(np.float64)
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_r = np.where(cnt > 0, rsum / np.maximum(cnt, 1), np.nan)
    return mean_r, isum, axis


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    from scipy import stats

    return float(stats.spearmanr(a, b).statistic)


def analyse(rA, iA, rB, iB, rng: np.random.Generator) -> dict:
    # a bin counts only if BOTH arms have surface there and SOMETHING has ink
    ok = np.isfinite(rA) & np.isfinite(rB) & ((iA + iB) > 0)
    n = int(ok.sum())
    if n < 100:
        return {"n_bins": n, "rho": float("nan"), "p": float("nan")}
    sep = np.abs(rA[ok] - rB[ok])
    dis = np.abs(iA[ok] - iB[ok]) / (iA[ok] + iB[ok])
    obs = spearman(sep, dis)
    null = np.array([spearman(sep, rng.permutation(dis)) for _ in range(N_SHUFFLE)])
    p = float((np.abs(null) >= abs(obs)).mean())
    return {
        "n_bins": n,
        "rho": obs,
        "p": p,
        "sep_median": float(np.median(sep)),
        "sep_p90": float(np.percentile(sep, 90)),
        "dis_median": float(np.median(dis)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--arms", nargs="+", default=["curbase_s1", "curbase_s2", "curbase_s3"]
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    data, axis = {}, None
    for tag in args.arms:
        r, i, axis = binned(f"{args.spiral_out}/outer_{tag}", axis)
        if r is None:
            print(f"{tag}: unusable, skipped")
            continue
        data[tag] = (r, i)
        print(
            f"{tag:<20} bins with surface {int(np.isfinite(r).sum()):>6,}  ink {i.sum():>12,.0f}"
        )

    tags = list(data)
    if len(tags) < 2:
        raise SystemExit("need two usable arms")

    rng = np.random.default_rng(0)
    print(f"\nseparation (vx) vs ink disagreement, Spearman, {N_SHUFFLE} shuffles")
    print(f"{'pair':<30}{'bins':>7}{'sep med':>9}{'rho':>8}{'p':>8}  verdict")
    rows = []
    for a, b in [
        (tags[i], tags[j]) for i in range(len(tags)) for j in range(i + 1, len(tags))
    ]:
        res = analyse(*data[a], *data[b], rng)
        res.update(a=a, b=b)
        rows.append(res)
        if res["p"] == res["p"] and res["p"] < 0.05:
            v = "SUPPORTED" if res["rho"] > 0 else "OPPOSITE (surprise)"
        else:
            v = "not supported"
        print(
            f"{a + ' vs ' + b:<30}{res['n_bins']:>7,}{res['sep_median']:>9.1f}"
            f"{res['rho']:>8.3f}{res['p']:>8.3f}  {v}"
        )

    sup = [r for r in rows if r["p"] == r["p"] and r["p"] < 0.05 and r["rho"] > 0]
    print(
        f"\n{len(sup)} of {len(rows)} pairs support the normal-displacement mechanism"
    )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {"n_shuffle": N_SHUFFLE, "bins": [NZ, NTHETA], "pairs": rows}, indent=1
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
