"""Are the between-seed ink offsets spatially coherent, or independent noise?

Implements `docs/preregistration/2026-09-13_ink_offset_coherence.md`, committed
before this file computed anything.

A continuous sheet displaced between two fits moves neighbouring regions of the
scroll together. Independent detector noise does not. So the discriminator is
COHERENCE along z, which needs no convention about direction and no assumption
about which component of the surface displacement matters.

Per z-slice, the angular shift that best aligns one arm's ink to the other's;
then the lag-1 autocorrelation of those shifts ordered by z. The null shuffles
the slice ORDER, destroying adjacency while preserving the shift distribution
exactly -- so a significant result cannot come from the shifts merely being
large or skewed.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import volume_map  # noqa: E402

N_SLICES = 24  # registered, not swept
MAX_SHIFT_DEG = 15.0
N_SHUFFLE = 1000
NTHETA = 256


def slice_shift(a: np.ndarray, b: np.ndarray, max_bins: int) -> float | None:
    """Angular shift (in bins) best aligning b to a, by cross-correlation."""
    if a.sum() <= 0 or b.sum() <= 0:
        return None
    a = a - a.mean()
    b = b - b.mean()
    if a.std() == 0 or b.std() == 0:
        return None
    best, best_k = -2.0, 0
    for k in range(-max_bins, max_bins + 1):
        r = float(np.corrcoef(a, np.roll(b, k))[0, 1])
        if np.isfinite(r) and r > best:
            best, best_k = r, k
    return float(best_k)


def lag1(x: np.ndarray) -> float:
    if len(x) < 3 or x.std() == 0:
        return float("nan")
    return float(np.corrcoef(x[:-1], x[1:])[0, 1])


def coherence(H_a: np.ndarray, H_b: np.ndarray, rng: np.random.Generator) -> dict:
    nz = H_a.shape[0]
    per = max(1, nz // N_SLICES)
    max_bins = int(round(MAX_SHIFT_DEG / 360.0 * H_a.shape[1]))
    shifts = []
    for i in range(N_SLICES):
        sl = slice(i * per, (i + 1) * per)
        s = slice_shift(H_a[sl].sum(axis=0), H_b[sl].sum(axis=0), max_bins)
        if s is not None:
            shifts.append(s)
    shifts = np.array(shifts, dtype=float)
    if len(shifts) < 5:
        return {"n_slices": int(len(shifts)), "lag1": float("nan"), "p": float("nan")}
    obs = lag1(shifts)
    null = np.array([lag1(rng.permutation(shifts)) for _ in range(N_SHUFFLE)])
    null = null[np.isfinite(null)]
    p = float((null >= obs).mean()) if len(null) else float("nan")
    return {
        "n_slices": int(len(shifts)),
        "lag1": obs,
        "p": p,
        "null_mean": float(null.mean()) if len(null) else float("nan"),
        "shift_range_bins": [float(shifts.min()), float(shifts.max())],
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

    maps, axis = {}, None
    for tag in args.arms:
        H, axis = volume_map(f"{args.spiral_out}/outer_{tag}", axis)
        if H is None:
            print(f"{tag}: unusable, skipped")
            continue
        maps[tag] = H
    tags = list(maps)
    if len(tags) < 2:
        raise SystemExit("need two usable arms")

    rng = np.random.default_rng(0)
    print(
        f"coherence of between-seed ink offsets, {N_SLICES} z-slices, "
        f"+/-{MAX_SHIFT_DEG:.0f} deg, {N_SHUFFLE} shuffles"
    )
    print(f"{'pair':<30}{'slices':>7}{'lag-1':>9}{'null':>8}{'p':>8}  verdict")
    rows = []
    for i, a in enumerate(tags):
        for b in tags[i + 1 :]:
            r = coherence(maps[a], maps[b], rng)
            r.update(a=a, b=b)
            rows.append(r)
            v = (
                "COHERENT"
                if (r["p"] == r["p"] and r["p"] < 0.05)
                else "not significant"
            )
            print(
                f"{a + ' vs ' + b:<30}{r['n_slices']:>7}{r['lag1']:>9.3f}"
                f"{r['null_mean']:>8.3f}{r['p']:>8.3f}  {v}"
            )

    ok = [r for r in rows if r["p"] == r["p"] and r["p"] < 0.05]
    print(f"\n{len(ok)} of {len(rows)} pairs coherent at p < 0.05")
    print("registered rule: coherent -> consistent with ink moving with a continuous")
    print("surface, and inconsistent with independent detector noise.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "n_slices": N_SLICES,
                    "max_shift_deg": MAX_SHIFT_DEG,
                    "n_shuffle": N_SHUFFLE,
                    "pairs": rows,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
