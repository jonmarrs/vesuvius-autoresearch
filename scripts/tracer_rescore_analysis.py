"""docs/preregistration/2026-10-05_tracer_rescore.md -- score the re-run tracer's labellings with ScrollGT.

* Version 2 (current ScrollGT, published v2 floors): `score_fiber_prediction`.
* Version 1 (ScrollGT 0.3.2's scorer, read from its git tag) on the same labellings, for the fidelity check
  against the published `tracer_strict_relink` rows.

Usage: .venv/bin/python scripts/tracer_rescore_analysis.py --work DIR [--out PATH]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

SG = Path("/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt")
sys.path.insert(0, str(SG / "src"))
from scrollgt.fibers.target import (  # noqa: E402
    load_fiber_target,
    score_fiber_prediction,
)

CUBES = ["s1_00497_01497_03997_256", "s1_00497_02497_02997_256", "s1_00997_02497_02997_256",
         "s1_08997_02997_02497_256", "s1_10997_02997_02997_256", "s5_03997_01497_03997_256",
         "s5_07997_02997_05497_256", "s5_14997_01497_01497_256", "s5_06494_01994_03994_512",
         "s5_06994_00994_04994_512", "s5_07994_01994_05494_512"]  # fmt: skip
FIDELITY_TOL = 0.05
KEYS = (
    "erl",
    "erl_merge_penalized",
    "coverage",
    "precision",
    "splits",
    "merges",
    "n_pred_instances",
)


def v1_scorer():
    """ScrollGT 0.3.2's eval_trace, executed as a module next to the current skeleton_io (unchanged since)."""
    src = subprocess.run(["git", "-C", str(SG), "show", "v0.3.2:src/scrollgt/fibers/eval_trace.py"],
                         capture_output=True, text=True, check=True).stdout  # fmt: skip
    src = src.replace(
        "from .skeleton_io import", "from scrollgt.fibers.skeleton_io import"
    )
    path = Path(tempfile.mkdtemp()) / "eval_trace_v1.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location("eval_trace_v1", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eval_trace_v1"] = (
        mod  # dataclasses resolve annotations through sys.modules
    )
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/tracer_rescore.json"))
    args = ap.parse_args()
    v1 = v1_scorer()
    cubes: dict[str, dict] = {}
    for c in CUBES:
        inst = args.work / f"{c}_instances.npy"
        target = SG / "data" / f"fibers_{c}"
        if not inst.exists():
            cubes[c] = {"ran": False}
            print(f"{c}: NOT RUN")
            continue
        card = score_fiber_prediction(inst, target)
        t2, cc2 = card["metrics"], card["floors"]["floor_connected_components"]
        sk, mask, meta = load_fiber_target(target)
        labels = np.load(inst)
        t1 = v1.score_tracing(sk, labels, tolerance=float(meta["tolerance"])).as_row()
        pub = meta["floors"].get("tracer_strict_relink")
        fid = None
        if pub:
            fid = {k: (pub[k], t1[k]) for k in KEYS}
            fid["erl_rel"] = t1["erl"] / pub["erl"] - 1
            fid["erl_pen_rel"] = (
                t1["erl_merge_penalized"] / pub["erl_merge_penalized"] - 1
            )
        cubes[c] = {"ran": True, "size_class": int(meta["size_class"]), "tracer_v2": {k: t2[k] for k in KEYS},
                    "cc_v2": {k: cc2[k] for k in KEYS}, "oracle_v2_erl": card["class_oracle_erl"],
                    "tracer_v1": {k: t1[k] for k in KEYS}, "published_v1": pub, "fidelity": fid}  # fmt: skip
        f = (
            ""
            if fid is None
            else f"  fidelity v1 ERL {pub['erl']} -> {t1['erl']} ({100 * fid['erl_rel']:+.1f}%)"
        )
        print(f"{c}: tracer ERL {t2['erl']} vs cc {cc2['erl']} | ERLpen {t2['erl_merge_penalized']} vs cc "
              f"{cc2['erl_merge_penalized']} | coverage {t2['coverage']}{f}", flush=True)  # fmt: skip
    ran = {c: v for c, v in cubes.items() if v["ran"]}
    small = [v for v in ran.values() if v["size_class"] == 256]
    big = [v for v in ran.values() if v["size_class"] == 512]
    pred = {
        "P1_raw_erl_below_cc_all_11": len(ran) == 11 and all(v["tracer_v2"]["erl"] < v["cc_v2"]["erl"] for v in ran.values()),
        "P2_pen_below_cc_all_8_256": len(small) == 8 and all(
            v["tracer_v2"]["erl_merge_penalized"] < v["cc_v2"]["erl_merge_penalized"] for v in small),
        "P3_pen_above_cc_2_of_3_512": len(big) == 3 and sum(
            v["tracer_v2"]["erl_merge_penalized"] > v["cc_v2"]["erl_merge_penalized"] for v in big) >= 2,
    }  # fmt: skip
    fid_fail = [
        c
        for c, v in ran.items()
        if v["fidelity"] and abs(v["fidelity"]["erl_rel"]) > FIDELITY_TOL
    ]
    res = {
        "cubes": cubes,
        "n_ran": len(ran),
        "predictions": pred,
        "fidelity_failed": fid_fail,
    }
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print("ran", len(ran), "of 11; predictions", pred, "; fidelity failed on", fid_fail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
