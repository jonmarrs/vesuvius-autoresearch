"""Does the detector's confidence predict which ink reproduces across seeds?

Implements `docs/preregistration/2026-09-13_does_confidence_predict_reproducibility.md`,
and is written before any probability map exists -- the arms have not been
re-scored yet, and cannot be while a render holds the box.

About 28% of a run's ink does not survive a change of RNG seed. If the detector's
own probability separates the reproducible part, raising the threshold is free,
where a 3-seed consensus costs 3x the compute.

The scorer discards its probabilities by default (saved masks hold exactly two
values). `repro/spiral_render/keep_probabilities.patch` preserves them behind
INK_METRIC_KEEP_PROB=1 as `<name>_flat_prob.npy`, float16.

**The gate that matters is bin-size dependence.** Agreement fractions in this
corpus move from 89.7% to 43.2% purely with binning, so a result at one binning
proves nothing. The conclusion must hold at all three or it is reported as
bin-dependent and not as a finding.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_ink_in_volume import ink_per_cell, load_xyz, tile_index  # noqa: E402

BINNINGS = ((48, 128), (96, 256), (192, 512))  # registered; all three must agree
N_SHUFFLE = 1000
DIFF_THRESHOLD = 0.05
Z_RANGE = (13056.0, 18432.0)
INK_TOLERANCE = 0.001  # re-scored total_fg_pixels must match to 0.1%


def load_prob(arm_dir: str, shape: tuple[int, int]) -> np.ndarray | None:
    """Per-cell mean detector probability, from the patched scorer's .npy tiles."""
    fs = sorted(
        glob.glob(f"{arm_dir}/ink_metric/predictions/*_prob.npy"), key=tile_index
    )
    if not fs:
        return None
    h, w = shape
    rows = []
    for f in fs:
        a = np.load(f).astype(np.float32)
        if a.shape[0] != h * 10:
            return None
        rows.append(a[: h * 10].reshape(h, 10, a.shape[1]).mean(axis=1))
    full = np.concatenate(rows, axis=1)
    if full.shape[1] != w * 10:
        return None
    return full.reshape(h, w, 10).mean(axis=2)


def binned_maps(arm_dir: str, axis, nz: int, nt: int):
    """(ink, probability-weighted ink, cell count) per (z, theta) bin."""
    xyz = load_xyz(arm_dir)
    if xyz is None:
        return None, axis
    x, y, z = xyz
    ink = ink_per_cell(arm_dir, x.shape)
    prob = load_prob(arm_dir, x.shape)
    if ink is None or prob is None:
        return None, axis
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not m.any():
        return None, axis
    if axis is None:
        axis = (float(x[m].mean()), float(y[m].mean()))
    cx, cy = axis
    th = np.arctan2(y[m] - cy, x[m] - cx)
    rng = [list(Z_RANGE), [-np.pi, np.pi]]
    i_sum, _, _ = np.histogram2d(
        z[m], th, bins=[nz, nt], range=rng, weights=ink[m].astype(np.float64)
    )
    p_sum, _, _ = np.histogram2d(
        z[m],
        th,
        bins=[nz, nt],
        range=rng,
        weights=(prob[m] * ink[m]).astype(np.float64),
    )
    return (i_sum, p_sum), axis


def one_binning(arms: dict, nz: int, nt: int, rng: np.random.Generator) -> dict:
    inks = np.stack([arms[t][0] for t in arms])
    probs = np.stack([arms[t][1] for t in arms])
    n_agree = (inks > 0).sum(axis=0)

    with np.errstate(invalid="ignore", divide="ignore"):
        mean_p = np.where(
            inks.sum(axis=0) > 0,
            probs.sum(axis=0) / np.maximum(inks.sum(axis=0), 1),
            np.nan,
        )

    unan = mean_p[(n_agree == len(arms)) & np.isfinite(mean_p)]
    lone = mean_p[(n_agree == 1) & np.isfinite(mean_p)]
    if len(unan) < 30 or len(lone) < 30:
        return {
            "bins": [nz, nt],
            "n_unanimous": int(len(unan)),
            "n_lone": int(len(lone)),
            "diff": float("nan"),
            "p": float("nan"),
        }
    obs = float(unan.mean() - lone.mean())

    pool = np.concatenate([unan, lone])
    k = len(unan)
    null = np.array(
        [
            (lambda s: s[:k].mean() - s[k:].mean())(rng.permutation(pool))
            for _ in range(N_SHUFFLE)
        ]
    )
    p = float((np.abs(null) >= abs(obs)).mean())
    return {
        "bins": [nz, nt],
        "n_unanimous": int(len(unan)),
        "n_lone": int(len(lone)),
        "mean_unanimous": float(unan.mean()),
        "mean_lone": float(lone.mean()),
        "diff": obs,
        "p": p,
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

    rng = np.random.default_rng(0)
    results, axis = [], None
    missing = []
    for nz, nt in BINNINGS:
        arms, axis_b = {}, axis
        for tag in args.arms:
            maps, axis_b = binned_maps(f"{args.spiral_out}/outer_{tag}", axis_b, nz, nt)
            if maps is None:
                missing.append(tag)
                continue
            arms[tag] = maps
        axis = axis_b
        if len(arms) < len(args.arms):
            break
        results.append(one_binning(arms, nz, nt, rng))

    if missing:
        raise SystemExit(
            f"no probability maps for: {', '.join(sorted(set(missing)))}. Re-score with "
            "INK_METRIC_KEEP_PROB=1 after applying keep_probabilities.patch. "
            "A partial sample is refused, not reported."
        )

    print("mean detector probability of ink, unanimous bins vs bins only one arm found")
    print(
        f"{'binning':>12}{'unanimous':>11}{'lone':>9}{'diff':>9}{'p':>8}{'n_u':>8}{'n_l':>7}"
    )
    for r in results:
        label = f"{r['bins'][0]}x{r['bins'][1]}"
        print(
            f"{label:>12}{r['mean_unanimous']:>11.4f}{r['mean_lone']:>9.4f}"
            f"{r['diff']:>+9.4f}{r['p']:>8.3f}{r['n_unanimous']:>8,}{r['n_lone']:>7,}"
        )

    sig = [r for r in results if r["p"] < 0.05 and r["diff"] > DIFF_THRESHOLD]
    neg = [r for r in results if r["p"] < 0.05 and r["diff"] < 0]
    if len(sig) == len(results):
        verdict, why = (
            "CONFIDENCE PREDICTS REPRODUCIBILITY",
            (
                "a higher threshold would preferentially discard the irreproducible ink; "
                "the trade against lost recall is now worth measuring."
            ),
        )
    elif neg:
        verdict, why = (
            "OPPOSITE (surprise)",
            ("reproducible ink is LESS confident, which no account predicts."),
        )
    elif sig:
        verdict, why = (
            "BIN-DEPENDENT",
            (
                f"significant at {len(sig)} of {len(results)} binnings. The registration "
                "requires all three; reported as bin-dependent, NOT as a finding."
            ),
        )
    else:
        verdict, why = (
            "CONFIDENCE DOES NOT PREDICT IT",
            (
                "the irreproducible ink is not distinguishable by confidence, so "
                "thresholding cannot separate it and averaging remains the only lever."
            ),
        )
    print(f"\nVERDICT: {verdict}\n  {why}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "binnings": [list(b) for b in BINNINGS],
                    "threshold": DIFF_THRESHOLD,
                    "results": results,
                    "verdict": verdict,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
