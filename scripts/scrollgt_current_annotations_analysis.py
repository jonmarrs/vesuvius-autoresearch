"""docs/preregistration/2026-10-10_scrollgt_current_annotations.md -- do ScrollGT's published fiber conclusions hold
against villa's current annotations (fiber-skeletons Dataset004) on the three cubes it revised?

Each labelling (oracle, four floors, finding 80's tracer baseline, finding 81's frozen configuration) is scored with
ScrollGT (fiber scoring version 2) against the shipped ("old") ground truth and the Dataset004 ("current") one.
Fidelity gate: every old-ground-truth row must equal its published value exactly, or there is no verdict.

Usage: .venv/bin/python scripts/scrollgt_current_annotations_analysis.py --nml-dir DIR --baseline DIR --frozen DIR
       [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SG = Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt")

# cube -> Dataset004 NML (hash-checked against ScrollGT's source on 2026-10-10: these three differ, the other 8 match)
REVISED = {
    "s1_00497_02497_02997_256": "fibers_s1a_00497z_02497y_02997x_256_v01.nml",
    "s1_08997_02997_02497_256": "fibers_s1a_08997z_02997y_02497x_256_v01.nml",
    "s5_14997_01497_01497_256": "fibers_s5_14997z_01497y_01497x_256_v02.nml",
}
COMPUTED = (
    "oracle",
    "floor_single_instance",
    "floor_connected_components",
    "floor_voxel_instances",
    "floor_random_instances",
)
FROZEN_KEYS = (
    "erl",
    "erl_merge_penalized",
    "coverage",
    "splits",
    "merges",
    "n_pred_instances",
)
CC, TB, TF = "floor_connected_components", "tracer_baseline", "tracer_frozen"


def _strip(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "scoring_version"}


def fidelity_mismatches(
    old_rows: dict, published: dict, frozen_published: dict
) -> list[str]:
    """Old-ground-truth rows that do not equal their published values exactly.

    published: the target meta.json's `floors` (COMPUTED rows plus `tracer_strict_relink`).
    frozen_published: finding 81's `frozen_v2` entry for this cube (FROZEN_KEYS).
    """
    bad = []
    for k in COMPUTED:
        if _strip(old_rows[k]) != _strip(published[k]):
            bad.append(k)
    pub_t = _strip(published["tracer_strict_relink"])
    if {k: old_rows[TB].get(k) for k in pub_t} != pub_t:
        bad.append(TB)
    if {k: old_rows[TF][k] for k in FROZEN_KEYS} != {
        k: frozen_published[k] for k in FROZEN_KEYS
    }:
        bad.append(TF)
    return bad


def verdict(results: dict) -> dict:
    """results: cube -> {"old": rows, "current": rows, "mismatches": [...]}.

    Refuses a verdict on a partial sample or any fidelity mismatch: the returned dict then has no "predictions".
    """
    missing = sorted(set(REVISED) - set(results))
    if missing:
        return {"status": "INCOMPLETE", "missing": missing}
    bad = {c: r["mismatches"] for c, r in results.items() if r["mismatches"]}
    if bad:
        return {"status": "FIDELITY_FAILED", "mismatches": bad}
    o = {c: r["old"] for c, r in results.items()}
    n = {c: r["current"] for c, r in results.items()}
    pred = {
        "P1_cc_raw_erl_above_tracer_on_all_3": all(n[c][CC]["erl"] > n[c][TB]["erl"] for c in REVISED),
        "P2_precision_rises_cc_and_tracer_on_all_3": all(
            n[c][k]["precision"] > o[c][k]["precision"] for c in REVISED for k in (CC, TB)),
        "P3_merges_rise_cc_and_tracer_on_all_3": all(
            n[c][k]["merges"] > o[c][k]["merges"] for c in REVISED for k in (CC, TB)),
        "P4_s5_14997_tracer_pen_above_cc": n["s5_14997_01497_01497_256"][TB]["erl_merge_penalized"]
        > n["s5_14997_01497_01497_256"][CC]["erl_merge_penalized"],
    }  # fmt: skip
    desc = {
        c: {
            "coverage_old_to_current": {k: (o[c][k]["coverage"], n[c][k]["coverage"]) for k in (CC, TB, TF)},
            "oracle_splits_old_to_current": (o[c]["oracle"]["splits"], n[c]["oracle"]["splits"]),
            "tracer_pen_above_cc": {"old": o[c][TB]["erl_merge_penalized"] > o[c][CC]["erl_merge_penalized"],
                                    "current": n[c][TB]["erl_merge_penalized"] > n[c][CC]["erl_merge_penalized"]},
            "frozen_pen_above_cc": {"old": o[c][TF]["erl_merge_penalized"] > o[c][CC]["erl_merge_penalized"],
                                    "current": n[c][TF]["erl_merge_penalized"] > n[c][CC]["erl_merge_penalized"]},
            "frozen_pen_above_baseline": {
                "old": o[c][TF]["erl_merge_penalized"] > o[c][TB]["erl_merge_penalized"],
                "current": n[c][TF]["erl_merge_penalized"] > n[c][TB]["erl_merge_penalized"]},
        }
        for c in REVISED
    }  # fmt: skip
    return {"status": "OK", "predictions": pred, "descriptive": desc}


def current_skeleton(cube: str, nml_dir: Path):
    from scrollgt.fibers.skeleton_io import (
        Skeleton,
        origin_from_stem,
        parse_nml,
        size_from_stem,
    )

    shape = (size_from_stem(cube),) * 3
    full = parse_nml(nml_dir / REVISED[cube], origin_zyx=origin_from_stem(cube))
    return Skeleton(
        fibers=[f for f in full.fibers if f.in_bounds_mask(shape).sum() > 1],
        scale_um=full.scale_um,
        origin_zyx=full.origin_zyx,
    )


def score_rows(skeleton, mask, tol: float, baseline: Path, frozen: Path) -> dict:
    import numpy as np
    from scrollgt.fibers.eval_trace import oracle_from_skeleton, score_tracing
    from scrollgt.fibers.target import _floor_rows

    rows = {
        "oracle": score_tracing(
            skeleton, oracle_from_skeleton(skeleton, mask.shape), tolerance=tol
        ).as_row()
    }
    rows.update(_floor_rows(skeleton, mask, tol))
    rows[TB] = score_tracing(skeleton, np.load(baseline), tolerance=tol).as_row()
    rows[TF] = score_tracing(skeleton, np.load(frozen), tolerance=tol).as_row()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nml-dir", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--frozen", type=Path, required=True)
    ap.add_argument(
        "--frozen-json", type=Path, default=Path("reports/tracer_frozen_v2.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/scrollgt_current_annotations.json")
    )
    args = ap.parse_args()
    sys.path.insert(0, str(SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION
    from scrollgt.fibers.target import load_fiber_target

    frozen_pub = json.loads(args.frozen_json.read_text())["cubes"]
    results = {}
    for cube in REVISED:
        bl, fz = (
            args.baseline / f"{cube}_instances.npy",
            args.frozen / f"{cube}_instances.npy",
        )
        if not (bl.exists() and fz.exists()):
            print(f"{cube}: labelling missing, skipped", flush=True)
            continue
        old_sk, mask, meta = load_fiber_target(SG / "data" / f"fibers_{cube}")
        tol = float(meta["tolerance"])
        old = score_rows(old_sk, mask, tol, bl, fz)
        cur = score_rows(current_skeleton(cube, args.nml_dir), mask, tol, bl, fz)
        mism = fidelity_mismatches(old, meta["floors"], frozen_pub[cube]["frozen_v2"])
        results[cube] = {"old": old, "current": cur, "mismatches": mism}
        for k in (*COMPUTED, TB, TF):
            a, b = old[k], cur[k]
            print(f"{cube} {k}: ERL {a['erl']} -> {b['erl']} | ERLpen {a['erl_merge_penalized']} -> "
                  f"{b['erl_merge_penalized']} | cov {a['coverage']} -> {b['coverage']} | prec {a['precision']} -> "
                  f"{b['precision']} | merges {a['merges']} -> {b['merges']} | splits {a['splits']} -> {b['splits']} | "
                  f"n_gt {a['n_gt_fibers']} -> {b['n_gt_fibers']}", flush=True)  # fmt: skip
        print(
            f"{cube}: fidelity {'EXACT' if not mism else 'MISMATCH ' + str(mism)}",
            flush=True,
        )
    v = verdict(results)
    out = {
        "scoring_version": SCORING_VERSION,
        "revised": REVISED,
        "cubes": results,
        **v,
    }
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v[k] for k in v if k != "descriptive"}, indent=1))
    return 0 if v["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
