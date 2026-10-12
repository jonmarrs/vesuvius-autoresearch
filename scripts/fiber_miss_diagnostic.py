"""docs/preregistration/2026-10-11_s5_heldout_miss_diagnostic.md -- why does ScrollGT's fiber mask (fiber_hz_vt, P >= 0.5)
miss the hand-traced fibers on the two new Scroll-5 cubes of finding 83?

Two instruments, run on all 21 ScrollGT fiber targets (the 11 in-sample ones are controls):
* a frame check: mask coverage of the ground truth under every integer shift of the skeleton within +-4 voxels;
* a threshold sweep: coverage when the mask is P >= t for t below 0.5, from the ball-max probability near each point.

Coverage is ScrollGT's (fiber scoring version 2, tolerance 2.0): the length-weighted fraction of in-bounds resampled
ground-truth points within 2 voxels of the mask. At zero shift and t = 0.5 it must equal the published connected-
components coverage, and P >= 0.5 must equal the shipped mask bit for bit (gates G1, G2).

Usage: .venv/bin/python scripts/fiber_miss_diagnostic.py [--out reports/fiber_miss_diagnostic.json] [--cubes C ...]
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

NEO = Path("/home/jon/openclaw-workspace/Neo-VM")
SG = NEO / "projects/scrollgt"
IN_PROB = NEO / "projects/vesuvius-autoresearch/local_data/fiber_skeletons"
HELD_PROB = NEO / "spiral_out/fiber_heldout/data"
TOL = 2.0
STEP = 0.5
MAX_SHIFT = 4
THRESHOLDS = (0.5, 0.3, 0.2, 0.1, 0.05)
SOFT_T = 0.1

NEW_S5 = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
IN_S5 = (
    "s5_03997_01497_03997_256",
    "s5_07997_02997_05497_256",
    "s5_14997_01497_01497_256",
    "s5_06494_01994_03994_512",
    "s5_06994_00994_04994_512",
    "s5_07994_01994_05494_512",
)
# Registered constants: the lowest published connected-components coverage on an in-sample Scroll-5 256^3 cube
# (ScrollGT 0.5.0, s5_14997_01497_01497_256), and the shift gains that decide P1 and the control check.
IN_S5_256_MIN_COV = 0.8185
SHIFT_GAIN_FLAG = 0.05
GATE_COV_ABS = 1e-4


def ball_offsets(radius: float = TOL) -> np.ndarray:
    """Integer offsets d with |d| <= radius: exactly the voxels ScrollGT's EDT tolerance reaches."""
    r = int(np.floor(radius))
    rng = range(-r, r + 1)
    return np.array(
        [
            d
            for d in itertools.product(rng, rng, rng)
            if sum(v * v for v in d) <= radius * radius + 1e-9
        ]
    )


def samples(skeleton) -> tuple[np.ndarray, np.ndarray]:
    """Every resampled ground-truth point (rounded voxel index, segment length), as ScrollGT's _fiber_runs walks them.

    Rounding is Python's round(), half to even, which np.rint matches.
    """
    from scrollgt.fibers.eval_trace import _resample_fiber

    pts, dls = [], []
    for fiber in skeleton.fibers:
        for p, dl in _resample_fiber(fiber.coords, fiber.edges, step=STEP):
            if p is not None:
                pts.append(p)
                dls.append(dl)
    return np.rint(np.asarray(pts, dtype=float)).astype(np.int64), np.asarray(
        dls, dtype=float
    )


def _inb(idx: np.ndarray, shape) -> np.ndarray:
    return np.all((idx >= 0) & (idx < np.asarray(shape)), axis=1)


def coverage_at(
    dist: np.ndarray, idx: np.ndarray, dl: np.ndarray, shift=(0, 0, 0)
) -> float:
    """Length-weighted fraction of in-bounds points within TOL of the mask, after shifting the skeleton by `shift`."""
    j = idx + np.asarray(shift, dtype=np.int64)
    inb = _inb(j, dist.shape)
    jj = j[inb]
    hit = dist[jj[:, 0], jj[:, 1], jj[:, 2]] <= TOL
    tot = float(dl[inb].sum())
    return float(dl[inb][hit].sum() / tot) if tot > 0 else 0.0


def shift_search(
    mask: np.ndarray, idx: np.ndarray, dl: np.ndarray, max_shift: int = MAX_SHIFT
) -> dict:
    from scipy import ndimage

    dist = ndimage.distance_transform_edt(~mask)
    rng = range(-max_shift, max_shift + 1)
    cov = {s: coverage_at(dist, idx, dl, s) for s in itertools.product(rng, rng, rng)}
    best = max(cov, key=lambda s: (cov[s], -sum(abs(v) for v in s)))
    axes = {}
    for a, name in enumerate("zyx"):
        axes[name] = [
            round(cov[tuple(k if i == a else 0 for i in range(3))], 4) for k in rng
        ]
    return {"zero": cov[(0, 0, 0)], "best_shift": list(best), "best": cov[best], "gain": cov[best] - cov[(0, 0, 0)],
            "axis_profiles": axes}  # fmt: skip


def ball_max(prob: np.ndarray, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For each in-bounds point: the max probability over voxels within TOL. Returns (values, in-bounds mask)."""
    inb = _inb(idx, prob.shape)
    p = idx[inb]
    m = np.full(len(p), -np.inf)
    for d in ball_offsets():
        q = p + d
        ok = _inb(q, prob.shape)
        v = np.full(len(p), -np.inf)
        v[ok] = prob[q[ok, 0], q[ok, 1], q[ok, 2]]
        np.maximum(m, v, out=m)
    return m, inb


def threshold_sweep(prob: np.ndarray, idx: np.ndarray, dl: np.ndarray) -> dict:
    m, inb = ball_max(prob, idx)
    w = dl[inb]
    tot = float(w.sum())
    cov = {str(t): float(w[m >= t].sum() / tot) for t in THRESHOLDS}
    dens = {str(t): float((prob >= t).mean()) for t in THRESHOLDS}
    c5, cs = cov["0.5"], cov[str(SOFT_T)]
    soft = (cs - c5) / (1.0 - c5) if c5 < 1.0 else float("nan")
    missed = m < 0.5
    q = np.quantile(m[missed], [0.25, 0.5, 0.75]).tolist() if missed.any() else None
    return {
        "coverage": cov,
        "density": dens,
        "soft_miss_fraction": soft,
        "missed_ballmax_quartiles": q,
    }


def prob_path(cube: str) -> Path:
    p = IN_PROB / f"{cube}_fiberprob.npy"
    return p if p.exists() else HELD_PROB / f"{cube}_fiberprob.npy"


def diagnose(cube: str) -> dict:
    sys.path.insert(0, str(SG / "src"))
    from scrollgt.fibers.target import load_fiber_target

    skel, mask, meta = load_fiber_target(SG / "data" / f"fibers_{cube}")
    prob = np.load(prob_path(cube))
    idx, dl = samples(skel)
    published = meta["floors"]["floor_connected_components"]["coverage"]
    shift = shift_search(mask, idx, dl)
    sweep = threshold_sweep(prob, idx, dl)
    return {
        "split": meta["split"],
        "g1_prob_threshold_equals_shipped_mask": bool(
            np.array_equal(prob >= 0.5, mask)
        ),
        "published_cc_coverage": published,
        "g2_zero_shift_coverage": shift["zero"],
        "g2_ballmax_coverage_at_0.5": sweep["coverage"]["0.5"],
        "shift": shift,
        "sweep": sweep,
    }


def verdict(res: dict) -> dict:
    """res: cube -> diagnose() output, for all 21 targets. Gates first; a failed gate emits no verdict."""
    missing = [c for c in (*NEW_S5, *IN_S5) if c not in res]
    if missing:
        raise ValueError(f"refusing a partial sample: missing {missing}")
    g1 = [c for c, r in res.items() if not r["g1_prob_threshold_equals_shipped_mask"]]
    g2 = [c for c, r in res.items()
          if abs(r["g2_zero_shift_coverage"] - r["published_cc_coverage"]) > GATE_COV_ABS
          or abs(r["g2_ballmax_coverage_at_0.5"] - r["published_cc_coverage"]) > GATE_COV_ABS]  # fmt: skip
    if g1 or g2:
        return {"status": "INSTRUMENT_FAILED", "g1_failed": g1, "g2_failed": g2}
    ctrl = [
        c
        for c, r in res.items()
        if r["split"] != "held_out" and r["shift"]["gain"] >= SHIFT_GAIN_FLAG
    ]
    if ctrl:
        return {"status": "CONTROL_FAILED", "in_sample_cubes_with_shift_gain": ctrl}
    new = {c: res[c] for c in NEW_S5}
    p1_offset = {c: r["shift"]["gain"] >= SHIFT_GAIN_FLAG for c, r in new.items()}
    in_soft = max(res[c]["sweep"]["soft_miss_fraction"] for c in IN_S5)
    p2 = all(
        r["sweep"]["coverage"][str(SOFT_T)] < IN_S5_256_MIN_COV for r in new.values()
    )
    p3 = all(r["sweep"]["soft_miss_fraction"] <= in_soft for r in new.values())
    if any(p1_offset.values()):
        recovered = {
            c: res[c]["shift"]["best"] >= IN_S5_256_MIN_COV
            for c, hit in p1_offset.items()
            if hit
        }
        conclusion = ("FRAME_OFFSET_EXPLAINS" if all(recovered.values()) and all(p1_offset.values())
                      else "FRAME_OFFSET_PARTIAL")  # fmt: skip
    elif not p2:
        conclusion = "THRESHOLD_RESCUES"
    elif not p3:
        conclusion = "SOFTER_BUT_NOT_RESCUED"
    else:
        conclusion = "HARD_MISS"
    return {"status": "OK", "conclusion": conclusion, "frame_offset_flag": p1_offset,
            "in_sample_s5_max_soft_miss": in_soft,
            "predictions": {"P2_threshold_0.1_does_not_rescue": p2, "P3_misses_no_softer_than_in_sample": p3}}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/fiber_miss_diagnostic.json")
    )
    ap.add_argument("--cubes", nargs="*", help="default: every ScrollGT fiber target")
    args = ap.parse_args()
    cubes = args.cubes or sorted(
        p.name.removeprefix("fibers_") for p in (SG / "data").glob("fibers_*")
    )
    res = {}
    for c in cubes:
        r = diagnose(c)
        res[c] = r
        s, w = r["shift"], r["sweep"]
        print(f"{c} {r['split']:12s} G1 {r['g1_prob_threshold_equals_shipped_mask']} cov0 {s['zero']:.4f} "
              f"(pub {r['published_cc_coverage']:.4f}) best {s['best']:.4f} @ {s['best_shift']} | "
              f"C(0.1) {w['coverage']['0.1']:.4f} soft {w['soft_miss_fraction']:.3f}", flush=True)  # fmt: skip
    out = {
        "tolerance": TOL,
        "max_shift": MAX_SHIFT,
        "thresholds": list(THRESHOLDS),
        "cubes": res,
    }
    if not args.cubes:
        out["verdict"] = verdict(res)
        print(json.dumps(out["verdict"], indent=1))
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
