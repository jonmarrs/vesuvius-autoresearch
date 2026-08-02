"""Characterise the fiber_hz_vt orientation field against hand-traced ground truth.

Builds the field exactly as `bench_cli.cmd_trace` does -- hessian(P, gauss_sigma=2,
sigma=3) then fiber_direction -- so this measures the field the tracer consumes,
not a reimplementation of it.

Read-only: nothing here changes tracer behaviour.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from vesuvius_autoresearch.fibers.detection import fiber_direction, hessian
from vesuvius_autoresearch.fibers.field_quality import analyse_cube
from vesuvius_autoresearch.fibers.skeleton_io import (
    origin_from_stem,
    parse_nml,
    size_from_stem,
)

SRC = pathlib.Path("local_data/fiber_skeletons")
TURN_LIMIT_DEG = 25.0

CUBES = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
]


def _pct(a: np.ndarray, p: float) -> float:
    return float(np.percentile(a, p)) if len(a) else float("nan")


def _err_curv_r(err: np.ndarray, curv: np.ndarray) -> float | None:
    """Pearson r between angular error and genuine local curvature, node-aligned."""
    if len(err) != len(curv):
        return None
    ok = np.isfinite(err) & np.isfinite(curv)
    if ok.sum() < 3:
        return None
    return round(float(np.corrcoef(err[ok], curv[ok])[0, 1]), 3)


def _err_curv_split(
    err: np.ndarray, curv: np.ndarray
) -> tuple[float | None, float | None]:
    """Median error below and above the median-curvature node, node-aligned."""
    if len(err) != len(curv):
        return None, None
    ok = np.isfinite(err) & np.isfinite(curv)
    if ok.sum() < 4:
        return None, None
    e, c = err[ok], curv[ok]
    cut = float(np.median(c))
    lo, hi = e[c <= cut], e[c > cut]
    if not len(lo) or not len(hi):
        return None, None
    return round(float(np.median(lo)), 2), round(float(np.median(hi)), 2)


def run(stem: str) -> dict:
    size = size_from_stem(stem)
    shape = (size, size, size)
    skel = parse_nml(SRC / f"{stem}.nml", origin_zyx=origin_from_stem(stem))
    prob = np.load(SRC / f"{stem}_fiberprob.npy")
    if prob.shape != shape:
        raise SystemExit(f"{stem}: expected {shape}, got {prob.shape}")

    J, zero_mask = hessian(prob.copy(), gauss_sigma=2, sigma=3)
    dirs, valid = fiber_direction(J)
    res = analyse_cube(skel, np.asarray(dirs), np.asarray(valid), shape, prob=prob)

    err = res["error_deg"]
    dis = res["estimator_disagreement_deg"]
    curv = res["curvature_deg"]
    spacing = res["spacing"]
    self_consist = res["field_self_consistency_deg"]
    run_lengths = res["run_lengths"]
    prob_defined = res["prob_at_defined_nodes"]
    prob_undefined = res["prob_at_undefined_nodes"]

    median_curv = float(np.nanmedian(curv)) if len(curv) else float("nan")
    median_spacing = float(np.median(spacing)) if len(spacing) else float("nan")

    row = {
        "cube": stem,
        "n_fibers": res["n_fibers"],
        "n_scored": res["n_scored"],
        # CRITICAL 1: out-of-bounds (our annotation running past the cube edge)
        # and field-undefined (a fact about the model) are reported separately.
        "oob_frac": round(res["oob_frac"], 4),
        "field_undefined_frac": round(res["field_undefined_frac"], 4),
        "median_deg": round(_pct(err, 50), 2),
        "p90_deg": round(_pct(err, 90), 2),
        "p99_deg": round(_pct(err, 99), 2),
        "frac_over_25": round(res["frac_over_25"], 4),
        "median_curvature_deg": round(median_curv, 2)
        if np.isfinite(median_curv)
        else None,
        # Spec secondary cut 2: is field error EXPLAINED by genuine bending?
        # err and curv are node-aligned in analyse_cube, so this is a direct
        # comparison rather than an inference from their marginals.
        "err_vs_curvature_pearson_r": _err_curv_r(err, res["curvature_deg"]),
        "median_err_high_curv_deg": _err_curv_split(err, res["curvature_deg"])[1],
        "median_err_low_curv_deg": _err_curv_split(err, res["curvature_deg"])[0],
        "median_spacing_vox": (
            round(median_spacing, 2) if np.isfinite(median_spacing) else None
        ),
        # IMPORTANT 5: per-cube degrees-per-voxel, disclosing the spread the
        # single pooled figure previously hid. Note curvature is conditioned on
        # `defined` nodes while spacing is not -- see analyse_cube's docstring.
        "curvature_deg_per_spacing_vox": (
            round(median_curv / median_spacing, 3)
            if np.isfinite(median_curv)
            and np.isfinite(median_spacing)
            and median_spacing > 0
            else None
        ),
        "median_estimator_disagreement_deg": (
            round(float(np.nanmedian(dis)), 3) if len(dis) else float("nan")
        ),
        "p90_estimator_disagreement_deg": (
            round(float(np.nanpercentile(dis, 90)), 3) if len(dis) else float("nan")
        ),
        # IMPORTANT 3: field-vs-field turn between adjacent GT nodes -- what
        # actually gates the walker, unlike error_deg (field-vs-GT).
        "median_field_self_consistency_deg": (
            round(float(np.median(self_consist)), 2) if len(self_consist) else None
        ),
        "field_self_consistency_frac_over_25": (
            round(res["field_self_consistency_frac_over_25"], 4)
            if np.isfinite(res["field_self_consistency_frac_over_25"])
            else None
        ),
        # IMPORTANT 4: are over-25-degree nodes isolated or clustered along the
        # annotation chain?
        "mean_run_length": (
            round(res["mean_run_length"], 3)
            if np.isfinite(res["mean_run_length"])
            else None
        ),
        "independent_run_length_prediction": (
            round(res["independent_run_length_prediction"], 3)
            if np.isfinite(res["independent_run_length_prediction"])
            else None
        ),
        "frac_runs_ge_2": (
            round(res["frac_runs_ge_2"], 3)
            if np.isfinite(res["frac_runs_ge_2"])
            else None
        ),
        "max_run_length": (
            int(res["max_run_length"]) if np.isfinite(res["max_run_length"]) else None
        ),
        "n_runs": int(len(run_lengths)),
        # CRITICAL 2: fiber-probability at nodes where the field is genuinely
        # undefined (in-bounds, valid=False) vs. where it is defined.
        "median_prob_at_undefined_nodes": (
            round(float(np.median(prob_undefined)), 4) if len(prob_undefined) else None
        ),
        "median_prob_at_defined_nodes": (
            round(float(np.median(prob_defined)), 4) if len(prob_defined) else None
        ),
        "n_undefined_nodes": int(len(prob_undefined)),
        "zero_mask_any": bool(np.asarray(zero_mask).any()),
        "node_kinds": res["node_kinds"],
        "offset_median_deg": {
            str(k): (round(v, 2) if np.isfinite(v) else None)
            for k, v in res["offset_error"].items()
        },
    }
    print(
        f"{stem}: median {row['median_deg']}deg  p90 {row['p90_deg']}deg  "
        f"over-{int(TURN_LIMIT_DEG)}deg {row['frac_over_25']:.1%}  "
        f"undefined(in-bounds) {row['field_undefined_frac']:.1%}  "
        f"oob {row['oob_frac']:.1%}  n={row['n_scored']}"
    )
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cube", default=None, help="run one cube instead of all six")
    ap.add_argument(
        "--json-out", default="reports/fiber_orientation_field_quality.json"
    )
    args = ap.parse_args()

    stems = [args.cube] if args.cube else CUBES
    rows = [run(s) for s in stems]
    pathlib.Path(args.json_out).write_text(
        json.dumps({"turn_limit_deg": TURN_LIMIT_DEG, "cubes": rows}, indent=2) + "\n"
    )
    print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
