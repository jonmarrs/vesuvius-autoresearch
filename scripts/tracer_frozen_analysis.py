"""docs/preregistration/2026-10-09_tracer_frozen_config_v2.md -- does the tracer's frozen "improved" configuration
(--tangent-window 5) still beat the baseline under fiber scoring version 2?

Scores both labellings per cube with ScrollGT (`score_fiber_prediction`, version 2): the frozen configuration from
--work, and the baseline from --baseline (finding 80's re-run). Fidelity: the frozen labellings, scored with version 1,
against the frozen-configuration numbers reports/fiber_tracer_improvement.md published (its Task 6 table).

Usage: .venv/bin/python scripts/tracer_frozen_analysis.py --work DIR --baseline DIR [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrollgt.fibers.target import (  # noqa: E402
    load_fiber_target,
    score_fiber_prediction,
)
from tracer_rescore_analysis import CUBES, SG, v1_scorer  # noqa: E402

# reports/fiber_tracer_improvement.md, "Did the dev-cube gain generalize?": frozen-configuration ERL and ERLpen
# (scoring version 1) on the six cubes that study scored.
PUBLISHED_FROZEN_V1 = {
    "s1_00497_01497_03997_256": (29.97, 25.61),
    "s1_00497_02497_02997_256": (45.47, 35.84),
    "s1_00997_02497_02997_256": (38.44, 33.00),
    "s1_08997_02997_02497_256": (33.62, 31.04),
    "s1_10997_02997_02997_256": (36.64, 36.19),
    "s5_03997_01497_03997_256": (31.57, 31.18),
}
KEYS = (
    "erl",
    "erl_merge_penalized",
    "coverage",
    "splits",
    "merges",
    "n_pred_instances",
)


def pen_up(v: dict) -> bool:
    return (
        v["frozen_v2"]["erl_merge_penalized"] > v["baseline_v2"]["erl_merge_penalized"]
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/tracer_frozen_v2.json"))
    args = ap.parse_args()
    v1 = v1_scorer()
    cubes: dict[str, dict] = {}
    for c in CUBES:
        fz, bl = args.work / f"{c}_instances.npy", args.baseline / f"{c}_instances.npy"
        if not (fz.exists() and bl.exists()):
            cubes[c] = {"ran": False}
            print(f"{c}: NOT RUN")
            continue
        target = SG / "data" / f"fibers_{c}"
        f2 = score_fiber_prediction(fz, target)
        b2 = score_fiber_prediction(bl, target)
        cc = f2["floors"]["floor_connected_components"]
        entry = {"ran": True, "size_class": int(f2["size_class"]),
                 "frozen_v2": {k: f2["metrics"][k] for k in KEYS}, "baseline_v2": {k: b2["metrics"][k] for k in KEYS},
                 "cc_v2": {k: cc[k] for k in KEYS}, "fidelity": None}  # fmt: skip
        if c in PUBLISHED_FROZEN_V1:
            sk, _, meta = load_fiber_target(target)
            r1 = v1.score_tracing(
                sk, np.load(fz), tolerance=float(meta["tolerance"])
            ).as_row()
            pub = PUBLISHED_FROZEN_V1[c]
            entry["fidelity"] = {"published_v1": pub, "rerun_v1": (r1["erl"], r1["erl_merge_penalized"]),
                                 "exact": (r1["erl"], r1["erl_merge_penalized"]) == pub}  # fmt: skip
        cubes[c] = entry
        f, b = entry["frozen_v2"], entry["baseline_v2"]
        fid = (
            ""
            if entry["fidelity"] is None
            else f"  fidelity v1 {entry['fidelity']['published_v1']} -> {entry['fidelity']['rerun_v1']}"
        )
        print(f"{c}: ERLpen frozen {f['erl_merge_penalized']} vs baseline {b['erl_merge_penalized']} (cc {cc['erl_merge_penalized']}) | "
              f"ERL frozen {f['erl']} vs baseline {b['erl']}{fid}", flush=True)  # fmt: skip
    ran = {c: v for c, v in cubes.items() if v["ran"]}
    six = [ran[c] for c in PUBLISHED_FROZEN_V1 if c in ran]
    pred = {
        "P1_pen_up_on_5_of_6_study_cubes": len(six) == 6 and sum(pen_up(v) for v in six) >= 5,
        "P2_pen_up_on_9_of_11": len(ran) == 11 and sum(pen_up(v) for v in ran.values()) >= 9,
        "P3_erl_within_10pct_on_9_of_11": len(ran) == 11 and sum(
            abs(v["frozen_v2"]["erl"] / v["baseline_v2"]["erl"] - 1) <= 0.10 for v in ran.values()) >= 9,
    }  # fmt: skip
    desc = {
        "frozen_pen_above_cc": sum(v["frozen_v2"]["erl_merge_penalized"] > v["cc_v2"]["erl_merge_penalized"] for v in ran.values()),
        "baseline_pen_above_cc": sum(v["baseline_v2"]["erl_merge_penalized"] > v["cc_v2"]["erl_merge_penalized"] for v in ran.values()),
        "fidelity_exact": [c for c, v in ran.items() if v["fidelity"] and v["fidelity"]["exact"]],
        "fidelity_inexact": [c for c, v in ran.items() if v["fidelity"] and not v["fidelity"]["exact"]],
    }  # fmt: skip
    res = {"cubes": cubes, "n_ran": len(ran), "predictions": pred, "descriptive": desc}
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print("ran", len(ran), "of 11; predictions", pred, "; descriptive", desc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
