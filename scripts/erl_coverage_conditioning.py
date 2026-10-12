"""Post hoc, not registered (finding 85): ScrollGT's fiber ERL is conditional on coverage.

ScrollGT scores ERL as sum(r^2) / sum(r) over the runs a labelling covers, so uncovered ground truth never enters the
denominator, and deleting any run shorter than the current ERL raises it. Two outputs:

* a control on a real labelling: our tracer on one in-sample target, with instances under N voxels deleted;
* the AFV generator entrant's rows and their comparators (reports/afv_generator_entrant.json) with ground-truth-
  normalized ERL, sum(r^2) / ground-truth length, which equals ERL x coverage exactly because sum(r) is the covered
  length.

Usage: .venv/bin/python scripts/erl_coverage_conditioning.py [--out reports/erl_coverage_conditioning.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

NEO = Path("/home/jon/openclaw-workspace/Neo-VM")
SG = NEO / "projects/scrollgt"
TRACER = NEO / "spiral_out/tracer_rescore"
CONTROL_CUBE = "s1_00497_01497_03997_256"  # unrevised since finding 80, so its shipped GT is what the tracer was scored on
MIN_VOXELS = (0, 100, 200, 400)


def gt_normalized(row: dict) -> dict:
    return {
        "erl_gt": row["erl"] * row["coverage"],
        "erl_pen_gt": row["erl_merge_penalized"] * row["coverage"],
    }


def deletion_control() -> list[dict]:
    sys.path.insert(0, str(SG / "src"))
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target

    skel, _, meta = load_fiber_target(SG / "data" / f"fibers_{CONTROL_CUBE}")
    lab = np.load(TRACER / f"{CONTROL_CUBE}_instances.npy")
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    out = []
    for n in MIN_VOXELS:
        keep = ids[counts >= n]
        s = score_tracing(
            skel, np.where(np.isin(lab, keep), lab, 0), tolerance=2.0
        ).as_row()
        out.append({"min_voxels": n, "instances": int(len(keep)), **{k: s[k] for k in ("erl", "erl_merge_penalized", "coverage")},
                    **gt_normalized(s)})  # fmt: skip
    pub = meta["floors"]["tracer_strict_relink"]
    if (out[0]["erl"], out[0]["erl_merge_penalized"], out[0]["coverage"]) != (
        pub["erl"],
        pub["erl_merge_penalized"],
        pub["coverage"],
    ):
        raise SystemExit("fidelity: the unfiltered labelling does not reproduce the published tracer row")  # fmt: skip
    return out


def entrant_table(result: dict) -> dict:
    rows = {}
    for c, g in result["generator_rows"].items():
        comp = result["comparators"][c]
        rows[c] = {"generator": {**gt_normalized(g), "coverage": g["coverage"]},
                   "tracer": {**gt_normalized(comp["tracer"]), "coverage": comp["tracer"]["coverage"]},
                   "cc": {**gt_normalized(comp["cc"]), "coverage": comp["cc"]["coverage"]}}  # fmt: skip
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--entrant", type=Path, default=Path("reports/afv_generator_entrant.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/erl_coverage_conditioning.json")
    )
    args = ap.parse_args()
    out = {"control_cube": CONTROL_CUBE, "deletion_control": deletion_control(),
           "entrant_gt_normalized": entrant_table(json.loads(args.entrant.read_text()))}  # fmt: skip
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    for r in out["deletion_control"]:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
