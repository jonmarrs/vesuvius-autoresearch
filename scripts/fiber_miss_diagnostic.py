"""docs/preregistration/2026-10-11_s5_heldout_miss_diagnostic.md -- why does ScrollGT's fiber mask (fiber_hz_vt, P >= 0.5)
miss the hand-traced fibers on the two new Scroll-5 cubes of finding 83?

Two instruments, run on all 21 ScrollGT fiber targets (the 11 in-sample ones are controls):
* a frame check: mask coverage of the ground truth under every integer shift of the skeleton within +-4 voxels;
* a threshold sweep: coverage when the mask is P >= t for t below 0.5, from the ball-max probability near each point.

Coverage is ScrollGT's (fiber scoring version 2, tolerance 2.0): the length-weighted fraction of in-bounds resampled
ground-truth points within 2 voxels of the mask. At zero shift and t = 0.5 it must equal the published connected-
components coverage, and P >= 0.5 must equal the shipped mask bit for bit (gates G1, G2).

Usage: .venv/bin/python scripts/fiber_miss_diagnostic.py --scrollgt-root DIR --prob-dir DIR
       [--prob-dir DIR ...] --out NEW.json [--cubes C ...]
"""

from __future__ import annotations

import argparse
import importlib
import itertools
import json
import math
import sys
from numbers import Integral, Real
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.labeling.label_artifacts import new_output, publish_new_file

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
IN_S1 = (
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
)
NEW_S3 = (
    "s3_00994_00494_01994_512",
    "s3_00994_01994_00494_512",
    "s3_00994_02494_01494_512",
    "s3_01994_01494_00994_512",
    "s3_01994_01994_01494_512",
    "s3_02994_02494_01994_512",
    "s3_03494_01494_00494_512",
    "s3_04494_00994_01494_512",
)
EXPECTED_SPLITS = {
    **dict.fromkeys(IN_S1, "primary"),
    **dict.fromkeys(IN_S5, "cross_scroll"),
    **dict.fromkeys((*NEW_S3, *NEW_S5), "held_out"),
}
CUBES = tuple(sorted(EXPECTED_SPLITS))
# Registered constants: the lowest published connected-components coverage on an in-sample Scroll-5 256^3 cube
# (ScrollGT 0.5.0, s5_14997_01497_01497_256), and the shift gains that decide P1 and the control check.
IN_S5_256_MIN_COV = 0.8185
SHIFT_GAIN_FLAG = 0.05
GATE_COV_ABS = 1e-4


def ball_offsets(radius: float = TOL) -> np.ndarray:
    """Integer offsets d with |d| <= radius: exactly the voxels ScrollGT's EDT tolerance reaches."""
    if (
        isinstance(radius, (bool, np.bool_))
        or not isinstance(radius, Real)
        or not math.isfinite(radius)
        or not 0 <= radius <= TOL
    ):
        raise ValueError(f"radius must be finite and between 0 and {TOL}")
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
    coords = np.asarray(pts, dtype=float)
    if not coords.size or not np.isfinite(coords).all():
        raise ValueError("skeleton must supply finite resampled points")
    if np.any(np.abs(coords) >= 2**63 - MAX_SHIFT):
        raise ValueError("skeleton coordinates exceed supported integer indices")
    return sample_arrays(np.rint(coords).astype(np.int64), np.asarray(dls, dtype=float))


def sample_indices(idx):
    idx = np.asarray(idx)
    if (
        idx.ndim != 2
        or idx.shape[1] != 3
        or not len(idx)
        or idx.dtype.kind not in "iu"
        or np.any(idx >= 2**63 - MAX_SHIFT)
        or np.any(idx <= -(2**63) + MAX_SHIFT)
    ):
        raise ValueError(
            "sample indices must be nonempty supported integer (N, 3) ZYX coordinates"
        )
    return idx.astype(np.int64, copy=False)


def sample_arrays(idx, dl):
    idx, dl = sample_indices(idx), np.asarray(dl)
    if (
        dl.shape != (len(idx),)
        or dl.dtype.kind not in "iuf"
        or not np.isfinite(dl).all()
        or np.any(dl < 0)
        or not math.isfinite(float(dl.sum()))
        or dl.sum() <= 0
    ):
        raise ValueError(
            "sample lengths must be aligned, finite, nonnegative and have positive total"
        )
    return idx, dl


def volume_array(values, name):
    values = np.asarray(values)
    if values.ndim != 3 or not values.size:
        raise ValueError(f"{name} must be a nonempty 3D ZYX array")
    return values


def probability_array(values):
    values = volume_array(values, "probability")
    if values.dtype.kind not in "biuf":
        raise ValueError("probability values must be real numbers in [0, 1]")
    # Validate slabs rather than allocate validation masks for an entire 512^3 cube.
    for start in range(0, values.shape[0], 16):
        slab = values[start : start + 16]
        if not np.isfinite(slab).all() or np.any(slab < 0) or np.any(slab > 1):
            raise ValueError("probability values must be finite and in [0, 1]")
    return values


def in_bounds_length(idx, dl, shape):
    inb = _inb(idx, shape)
    total = float(dl[inb].sum())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("samples must have positive in-bounds length")
    return inb, total


def _inb(idx: np.ndarray, shape) -> np.ndarray:
    return np.all((idx >= 0) & (idx < np.asarray(shape)), axis=1)


def coverage_at(
    dist: np.ndarray, idx: np.ndarray, dl: np.ndarray, shift=(0, 0, 0)
) -> float:
    """Length-weighted fraction of in-bounds points within TOL of the mask, after shifting the skeleton by `shift`."""
    idx, dl = sample_arrays(idx, dl)
    if len(shift) != 3 or any(
        isinstance(v, (bool, np.bool_))
        or not isinstance(v, Integral)
        or abs(v) > MAX_SHIFT
        for v in shift
    ):
        raise ValueError(f"shift must contain three integers within +/-{MAX_SHIFT}")
    return _coverage_at(dist, idx, dl, shift)


def _coverage_at(dist, idx, dl, shift):
    j = idx + np.asarray(shift, dtype=np.int64)
    inb, tot = in_bounds_length(j, dl, dist.shape)
    jj = j[inb]
    hit = dist[jj[:, 0], jj[:, 1], jj[:, 2]] <= TOL
    return float(dl[inb][hit].sum() / tot)


def shift_search(
    mask: np.ndarray, idx: np.ndarray, dl: np.ndarray, max_shift: int = MAX_SHIFT
) -> dict:
    from scipy import ndimage

    mask = volume_array(mask, "mask")
    if mask.dtype.kind != "b":
        raise ValueError("mask must be boolean")
    idx, dl = sample_arrays(idx, dl)
    if (
        isinstance(max_shift, (bool, np.bool_))
        or not isinstance(max_shift, Integral)
        or not 0 <= max_shift <= MAX_SHIFT
    ):
        raise ValueError(f"max_shift must be an integer in [0, {MAX_SHIFT}]")
    # SciPy's all-background EDT measures a virtual point outside the array.
    # There is no foreground to hit when the actual mask is empty.
    dist = (
        ndimage.distance_transform_edt(~mask)
        if mask.any()
        else np.full(mask.shape, np.inf)
    )
    rng = range(-max_shift, max_shift + 1)
    cov = {s: _coverage_at(dist, idx, dl, s) for s in itertools.product(rng, rng, rng)}
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
    return _ball_max(probability_array(prob), sample_indices(idx))


def _ball_max(prob, idx):
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
    prob = probability_array(prob)
    idx, dl = sample_arrays(idx, dl)
    _, tot = in_bounds_length(idx, dl, prob.shape)
    m, inb = _ball_max(prob, idx)
    w = dl[inb]
    cov = {str(t): float(w[m >= t].sum() / tot) for t in THRESHOLDS}
    dens = {
        str(t): sum(
            np.count_nonzero(prob[start : start + 16] >= t)
            for start in range(0, prob.shape[0], 16)
        )
        / prob.size
        for t in THRESHOLDS
    }
    c5, cs = cov["0.5"], cov[str(SOFT_T)]
    soft = (cs - c5) / (1.0 - c5) if c5 < 1.0 else None
    missed = m < 0.5
    q = np.quantile(m[missed], [0.25, 0.5, 0.75]).tolist() if missed.any() else None
    return {
        "coverage": cov,
        "density": dens,
        "soft_miss_fraction": soft,
        "missed_ballmax_quartiles": q,
    }


def prob_path(cube: str, probability_dirs) -> Path:
    matches = {
        (Path(directory) / f"{cube}_fiberprob.npy").resolve()
        for directory in probability_dirs
        if (Path(directory) / f"{cube}_fiberprob.npy").is_file()
    }
    if len(matches) != 1:
        raise ValueError(
            f"expected one probability file for {cube}, found {len(matches)}"
        )
    return matches.pop()


def diagnose(cube: str, *, scrollgt_root, probability_dirs) -> dict:
    from scrollgt.fibers.target import load_fiber_target

    skel, mask, meta = load_fiber_target(
        Path(scrollgt_root) / "data" / f"fibers_{cube}"
    )
    prob = probability_array(
        np.load(prob_path(cube, probability_dirs), mmap_mode="r", allow_pickle=False)
    )
    mask = volume_array(mask, "mask")
    if mask.dtype.kind != "b" or mask.shape != prob.shape:
        raise ValueError(
            f"{cube}: mask must be boolean and match the probability shape"
        )
    if meta["split"] != EXPECTED_SPLITS[cube]:
        raise ValueError(f"{cube}: target split disagrees with the registered sample")
    idx, dl = samples(skel)
    published = meta["floors"]["floor_connected_components"]["coverage"]
    shift = shift_search(mask, idx, dl)
    sweep = threshold_sweep(prob, idx, dl)
    return {
        "split": meta["split"],
        "g1_prob_threshold_equals_shipped_mask": all(
            np.array_equal(prob[start : start + 16] >= 0.5, mask[start : start + 16])
            for start in range(0, prob.shape[0], 16)
        ),
        "published_cc_coverage": published,
        "g2_zero_shift_coverage": shift["zero"],
        "g2_ballmax_coverage_at_0.5": sweep["coverage"]["0.5"],
        "shift": shift,
        "sweep": sweep,
    }


def fraction(value):
    return (
        not isinstance(value, (bool, np.bool_))
        and isinstance(value, Real)
        and math.isfinite(value)
        and 0 <= value <= 1
    )


def valid_row(cube, row):
    """Reject invalid evidence before floating comparisons can turn NaN into a verdict."""
    try:
        if (
            row["split"] != EXPECTED_SPLITS[cube]
            or type(row["g1_prob_threshold_equals_shipped_mask"]) is not bool
        ):
            return False
        values = [
            row["published_cc_coverage"],
            row["g2_zero_shift_coverage"],
            row["g2_ballmax_coverage_at_0.5"],
            row["shift"]["best"],
            row["shift"]["gain"],
            row["sweep"]["coverage"][str(SOFT_T)],
        ]
        if not all(fraction(v) for v in values):
            return False
        c5, cs = (
            row["g2_ballmax_coverage_at_0.5"],
            row["sweep"]["coverage"][str(SOFT_T)],
        )
        if (
            cs < c5
            or abs(
                row["shift"]["best"]
                - row["g2_zero_shift_coverage"]
                - row["shift"]["gain"]
            )
            > 1e-12
        ):
            return False
        soft = row["sweep"]["soft_miss_fraction"]
        if c5 == 1:
            return soft is None
        return fraction(soft) and abs(soft - (cs - c5) / (1 - c5)) <= 1e-12
    except (KeyError, TypeError, AttributeError):
        return False


def instrument_status(res):
    invalid = [c for c, r in res.items() if not valid_row(c, r)]
    if invalid:
        return {"status": "INSTRUMENT_FAILED", "invalid_rows": invalid}
    g1 = [c for c, r in res.items() if not r["g1_prob_threshold_equals_shipped_mask"]]
    g2 = [c for c, r in res.items()
          if abs(r["g2_zero_shift_coverage"] - r["published_cc_coverage"]) > GATE_COV_ABS
          or abs(r["g2_ballmax_coverage_at_0.5"] - r["published_cc_coverage"]) > GATE_COV_ABS]  # fmt: skip
    if g1 or g2:
        return {"status": "INSTRUMENT_FAILED", "g1_failed": g1, "g2_failed": g2}
    return {"status": "OK"}


def verdict(res: dict) -> dict:
    """res: cube -> diagnose() output, for all 21 targets. Gates first; a failed gate emits no verdict."""
    missing = [c for c in CUBES if c not in res]
    if missing:
        raise ValueError(f"refusing a partial sample: missing {missing}")
    extra = sorted(set(res) - set(CUBES))
    if extra:
        raise ValueError(f"unexpected cubes outside the registered sample: {extra}")
    status = instrument_status(res)
    if status["status"] != "OK":
        return status
    # No missed length is legitimate in a descriptive subset, but cannot supply
    # the soft-miss comparison required for this full registered verdict.
    undefined = [
        c for c in (*IN_S5, *NEW_S5) if res[c]["sweep"]["soft_miss_fraction"] is None
    ]
    if undefined:
        return {"status": "INSTRUMENT_FAILED", "undefined_soft_comparison": undefined}
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
    elif all(
        r["sweep"]["coverage"][str(SOFT_T)] >= IN_S5_256_MIN_COV for r in new.values()
    ):
        conclusion = "THRESHOLD_RESCUES"
    elif not p2:
        conclusion = "THRESHOLD_PARTIAL"
    elif not p3:
        conclusion = "SOFTER_BUT_NOT_RESCUED"
    else:
        conclusion = "HARD_MISS"
    return {"status": "OK", "conclusion": conclusion, "frame_offset_flag": p1_offset,
            "in_sample_s5_max_soft_miss": in_soft,
            "predictions": {"P2_threshold_0.1_does_not_rescue": p2, "P3_misses_no_softer_than_in_sample": p3}}  # fmt: skip


def configure_scrollgt(root):
    root = Path(root).resolve()
    source = root / "src"
    for relative in ("scrollgt/fibers/target.py", "scrollgt/fibers/eval_trace.py"):
        if not (source / relative).is_file():
            raise ValueError(f"ScrollGT checkout lacks {relative}: {root}")
    sys.path.insert(0, str(source))
    for name in ("scrollgt.fibers.target", "scrollgt.fibers.eval_trace"):
        module = importlib.import_module(name)
        if not Path(module.__file__).resolve().is_relative_to(source):
            raise ValueError(
                "a different ScrollGT checkout is already imported; use a fresh process"
            )
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--scrollgt-root",
        type=Path,
        required=True,
        help="explicit ScrollGT checkout with src/ and data/",
    )
    ap.add_argument(
        "--prob-dir",
        type=Path,
        action="append",
        required=True,
        help="probability directory; repeat for separate caches",
    )
    ap.add_argument(
        "--out", type=Path, required=True, help="new JSON artifact outside every source"
    )
    ap.add_argument(
        "--cubes",
        nargs="+",
        choices=CUBES,
        help="descriptive subset only; no registered verdict",
    )
    args = ap.parse_args(argv)
    try:
        root = args.scrollgt_root.resolve()
        dirs = [p.resolve() for p in args.prob_dir]
        output = new_output(args.out, root, *dirs)
        if output.suffix.lower() != ".json":
            raise ValueError("output must have a .json suffix")
        if not all(p.is_dir() for p in dirs):
            raise ValueError("every probability directory must exist")
        cubes = args.cubes if args.cubes is not None else list(CUBES)
        if len(cubes) != len(set(cubes)):
            raise ValueError("duplicate cube selection")
        # Resolve the complete workload before any expensive distance transforms.
        for cube in cubes:
            if not (root / "data" / f"fibers_{cube}").is_dir():
                raise ValueError(f"missing target in registered sample: {cube}")
            prob_path(cube, dirs)
        configure_scrollgt(root)
        res = {}
        for cube in cubes:
            res[cube] = diagnose(cube, scrollgt_root=root, probability_dirs=dirs)
            print(f"{cube}: completed", flush=True)
        out = {
            "diagnostic_contract": 2,
            "mode": "descriptive_subset"
            if args.cubes is not None
            else "registered_full",
            "scrollgt_root": str(root),
            "probability_dirs": [str(p) for p in dirs],
            "tolerance": TOL,
            "max_shift": MAX_SHIFT,
            "thresholds": list(THRESHOLDS),
            "cubes": res,
        }
        if args.cubes is None:
            result = verdict(res)
            out["verdict"] = result
            print(json.dumps(result, indent=1, allow_nan=False))
        else:
            result = instrument_status(res)
            out["instrument"] = result
        status = result["status"]
        payload = json.dumps(out, indent=1, allow_nan=False) + "\n"
        with publish_new_file(output, root, *dirs) as staging:
            staging.write_text(payload)
        return 0 if status == "OK" else 1
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(f"[fiber diagnostic] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
