"""Test the registered confidence/bin-agreement association with validity gates.

Version 2 measures saved ink pixels directly, requires three distinct arms and
the registered re-score count gate, and emits finite, versioned reports. This
association does not establish ink correctness or a benefit from thresholding.
See docs/CONFIDENCE_REPRODUCIBILITY.md for inputs, interpretation and limits.
"""

import argparse
import re
import stat
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

from compare_ink_in_volume import load_xyz

from scripts.confidence_inputs import (
    SCALE,
    ArmData,
    count_gate,
    file_state,
    mask_paths,
    probability_path,
    probability_sums,
)
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths
from vesuvius_autoresearch.fibers.provenance import write_json

ANALYSIS_VERSION = 2
BINNINGS = ((48, 128), (96, 256), (192, 512))
N_SHUFFLE = 1000
DIFF_THRESHOLD = 0.05
Z_RANGE = (13056.0, 18432.0)
INK_TOLERANCE = 0.001
MIN_BINS = 30


def load_prob(arm_dir, shape):
    """Mean probability of saved ink pixels per cell (zero in empty cells)."""
    path = probability_path(arm_dir)
    if path is None:
        return None
    # Retain the old helper's absent/bad-shape sentinel for research callers.
    a = np.load(path, mmap_mode="r", allow_pickle=False)
    if a.shape != tuple(n * SCALE for n in shape):
        return None
    del a
    ink, sums = probability_sums(path, mask_paths(path), shape)
    return np.divide(sums, ink, out=np.zeros_like(sums), where=ink > 0)


def load_arm(arm_dir):
    root = Path(arm_dir)
    probability = probability_path(root)
    if probability is None:
        raise ValueError(
            f"{root}: no probability maps; re-score with INK_METRIC_KEEP_PROB=1. A partial sample is refused."
        )
    masks = mask_paths(probability)
    paths = [
        probability,
        *masks,
        root / "ink_metric/metrics.json",
        root / "ink_metric_prob/metrics.json",
        *(root / "meshes/concat/w120-129_flat" / f"{axis}.tif" for axis in "xyz"),
    ]
    sources = {str(path.absolute()): file_state(path) for path in paths}
    xyz = load_xyz(str(root))
    if xyz is None or len({a.shape for a in xyz}) != 1 or xyz[0].ndim != 2:
        raise ValueError(f"{root}: missing or mismatched coordinate grids")
    ink, sums = probability_sums(probability, masks, xyz[0].shape)
    gate = count_gate(root, ink.size * SCALE**2, int(ink.sum()), INK_TOLERANCE)
    arm = ArmData(xyz, ink, sums, gate, sources)
    arm.verify()
    return arm


def bin_arm(arm, axis, nz, nt):
    x, y, z = arm.xyz
    valid = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if not valid.any():
        raise ValueError("coordinate grid has no valid volume locations")
    if axis is None:
        axis = (float(x[valid].mean()), float(y[valid].mean()))
    if not np.isfinite(axis).all():
        raise ValueError("shared volume axis must be finite")
    theta = np.arctan2(y[valid] - axis[1], x[valid] - axis[0])
    bounds = [list(Z_RANGE), [-np.pi, np.pi]]
    ink = np.histogram2d(
        z[valid], theta, bins=[nz, nt], range=bounds, weights=arm.ink[valid]
    )[0]
    probabilities = np.histogram2d(
        z[valid], theta, bins=[nz, nt], range=bounds, weights=arm.probability_sum[valid]
    )[0]
    return (ink, probabilities), axis


def binned_maps(arm_dir, axis, nz, nt):
    """Compatibility helper; the CLI loads each arm once for all three binnings."""
    return bin_arm(load_arm(arm_dir), axis, nz, nt)


def one_binning(arms, nz, nt, rng):
    if len(arms) != 3 or type(nz) is not int or type(nt) is not int or min(nz, nt) < 1:
        raise ValueError(
            "a binning requires three distinct arms and positive integer dimensions"
        )
    for ink, probability in arms.values():
        if (
            ink.shape != (nz, nt)
            or probability.shape != (nz, nt)
            or not np.isfinite(ink).all()
            or not np.isfinite(probability).all()
            or np.any(ink < 0)
            or np.any(probability < 0)
            or np.any(probability > ink + np.maximum(1, ink) * 1e-12)
        ):
            raise ValueError(
                "binned ink counts/probability sums must match shape and be finite in [0, ink]"
            )
    inks = np.stack([value[0] for value in arms.values()])
    probabilities = np.stack([value[1] for value in arms.values()])
    agreement = (inks > 0).sum(axis=0)
    total = inks.sum(axis=0)
    means = np.divide(
        probabilities.sum(axis=0),
        total,
        out=np.zeros_like(total, dtype=float),
        where=total > 0,
    )
    unanimous, lone = means[agreement == 3], means[agreement == 1]
    row = {
        "bins": [nz, nt],
        "n_unanimous": int(unanimous.size),
        "n_lone": int(lone.size),
        "status": "INDETERMINATE",
        "reason": None,
        "mean_unanimous": None,
        "mean_lone": None,
        "diff": None,
        "p": None,
    }
    if min(unanimous.size, lone.size) < MIN_BINS:
        row["reason"] = (
            f"need at least {MIN_BINS} unanimous and {MIN_BINS} lone-arm bins"
        )
        return row
    observed = float(unanimous.mean() - lone.mean())
    pool = np.concatenate([unanimous, lone])
    k = unanimous.size
    exceedances = 0
    for _ in range(N_SHUFFLE):
        shuffled = rng.permutation(pool)
        null = float(shuffled[:k].mean() - shuffled[k:].mean())
        exceedances += abs(null) >= abs(observed) - 1e-14
    row.update(
        status="MEASURED",
        mean_unanimous=float(unanimous.mean()),
        mean_lone=float(lone.mean()),
        diff=observed,
        p=(int(exceedances) + 1) / (N_SHUFFLE + 1),
    )
    return row


def decide(results):
    if (
        len(results) != len(BINNINGS)
        or [row.get("bins") for row in results] != [list(b) for b in BINNINGS]
        or any(
            row.get("status") != "MEASURED"
            or any(
                type(row.get(key)) not in (int, float) or not np.isfinite(row[key])
                for key in ("diff", "p")
            )
            for row in results
        )
        or any(not 0 < row["p"] <= 1 or abs(row["diff"]) > 1 for row in results)
    ):
        return (
            "INDETERMINATE",
            "All three registered binnings need complete, finite comparisons.",
        )
    positive = [row["p"] < 0.05 and row["diff"] > DIFF_THRESHOLD for row in results]
    negative = [row["p"] < 0.05 and row["diff"] < 0 for row in results]
    if all(positive):
        return (
            "CONFIDENCE ASSOCIATES WITH BIN AGREEMENT",
            "A bin-level association was detected at all three binnings; thresholding efficacy and ink correctness were not tested.",
        )
    if all(negative):
        return (
            "OPPOSITE ASSOCIATION",
            "Unanimous bins were less confident at all three binnings.",
        )
    if any(positive) or any(negative):
        return (
            "BIN-DEPENDENT",
            "The association does not hold in one direction at all three registered binnings.",
        )
    return (
        "NO REGISTERED EFFECT DETECTED",
        "The registered effect rule was not met; this does not establish absence of an effect.",
    )


def _report_output(path, roots, inputs=()):
    if path is None:
        return
    path = Path(path)
    validate_plan_paths(
        [(path, "confidence report")],
        [(p, "analysis input") for p in [*roots, *inputs]],
    )
    if path.is_symlink() or path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("report must be a nonsymlink regular file")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--arms", nargs="+", default=["curbase_s1", "curbase_s2", "curbase_s3"]
    )
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    if (
        len(args.arms) != 3
        or len(set(args.arms)) != 3
        or any(
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", tag) for tag in args.arms
        )
    ):
        ap.error("--arms requires exactly three distinct arm names")
    roots = [Path(args.spiral_out) / f"outer_{tag}" for tag in args.arms]
    if len({root.resolve() for root in roots}) != 3:
        ap.error("--arms must refer to three distinct directories")
    try:
        _report_output(args.json, roots)
        data = {tag: load_arm(root) for tag, root in zip(args.arms, roots, strict=True)}
        inputs = [path for arm in data.values() for path in arm.sources]
        _report_output(args.json, roots, inputs)
        axis = None
        results = []
        rng = np.random.default_rng(0)
        for nz, nt in BINNINGS:
            maps = {}
            for tag, arm in data.items():
                maps[tag], axis = bin_arm(arm, axis, nz, nt)
            results.append(one_binning(maps, nz, nt, rng))
        verdict, reason = decide(results)
        status = "INDETERMINATE" if verdict == "INDETERMINATE" else "MEASURED"
        report = {
            "analysis_version": ANALYSIS_VERSION,
            "status": status,
            "statistic_kind": "ink_pixel_probability_sum_over_ink_count_per_bin",
            "binnings": [list(b) for b in BINNINGS],
            "threshold": DIFF_THRESHOLD,
            "n_shuffle": N_SHUFFLE,
            "p_method": "two_sided_shuffle_plus_one",
            "arms": args.arms,
            "shared_axis": list(axis),
            "z_range": list(Z_RANGE),
            "validity_gate": {tag: arm.gate for tag, arm in data.items()},
            "input_file_states": {tag: arm.sources for tag, arm in data.items()},
            "results": results,
            "verdict": verdict,
            "reason": reason,
            "ink_correctness_tested": False,
            "thresholding_benefit_tested": False,
        }
        for arm in data.values():
            arm.verify()
        if args.json:
            _report_output(args.json, roots, inputs)
            write_json(args.json, report)
    except (OSError, ValueError) as exc:
        ap.exit(1, f"confidence analysis: {exc}\n")
    print("mean probability of saved ink pixels: unanimous vs lone-arm bins")
    for row in results:
        if row["status"] == "MEASURED":
            print(
                f"{row['bins']}: diff={row['diff']:+.4f} p={row['p']:.4f} n_u={row['n_unanimous']} n_l={row['n_lone']}"
            )
        else:
            print(f"{row['bins']}: INDETERMINATE — {row['reason']}")
    print(f"VERDICT: {verdict}\n  {reason}")
    return 0 if status == "MEASURED" else 1


if __name__ == "__main__":
    sys.exit(main())
