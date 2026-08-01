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


def run(stem: str) -> dict:
    size = size_from_stem(stem)
    shape = (size, size, size)
    skel = parse_nml(SRC / f"{stem}.nml", origin_zyx=origin_from_stem(stem))
    prob = np.load(SRC / f"{stem}_fiberprob.npy")
    if prob.shape != shape:
        raise SystemExit(f"{stem}: expected {shape}, got {prob.shape}")

    J, _ = hessian(prob.copy(), gauss_sigma=2, sigma=3)
    dirs, valid = fiber_direction(J)
    res = analyse_cube(skel, np.asarray(dirs), np.asarray(valid), shape)

    err = res["error_deg"]
    dis = res["estimator_disagreement_deg"]
    row = {
        "cube": stem,
        "n_fibers": res["n_fibers"],
        "n_scored": res["n_scored"],
        "field_undefined_frac": round(res["field_undefined_frac"], 4),
        "median_deg": round(_pct(err, 50), 2),
        "p90_deg": round(_pct(err, 90), 2),
        "p99_deg": round(_pct(err, 99), 2),
        "frac_over_25": round(res["frac_over_25"], 4),
        "median_curvature_deg": (
            round(float(np.nanmedian(res["curvature_deg"])), 2)
            if len(res["curvature_deg"])
            else float("nan")
        ),
        "median_spacing_vox": (
            round(float(np.median(res["spacing"])), 2)
            if len(res["spacing"])
            else float("nan")
        ),
        "median_estimator_disagreement_deg": (
            round(float(np.nanmedian(dis)), 3) if len(dis) else float("nan")
        ),
        "p90_estimator_disagreement_deg": (
            round(float(np.nanpercentile(dis, 90)), 3) if len(dis) else float("nan")
        ),
        "node_kinds": res["node_kinds"],
        "offset_median_deg": {
            str(k): (round(v, 2) if np.isfinite(v) else None)
            for k, v in res["offset_error"].items()
        },
    }
    print(
        f"{stem}: median {row['median_deg']}deg  p90 {row['p90_deg']}deg  "
        f"over-{int(TURN_LIMIT_DEG)}deg {row['frac_over_25']:.1%}  "
        f"undefined {row['field_undefined_frac']:.1%}  n={row['n_scored']}"
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
