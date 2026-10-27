"""Does batchgeneratorsv2 beat the unchanged config, not only the loop's other tweaks? Registered before either arm ran
(docs/preregistration/2026-10-27_loop_unchanged_control.md).

Since the 2026-10-27 promotion (#262) the loop's base config trains with batchgeneratorsv2. Its no-change control
(#259), control_unchanged, fine-tunes the incumbent with config.json as it is; its aug_mode tweak now offers
albumentations, the old recipe. Both arms fine-tune the same incumbent at the same budget, interleaved by the loop's
sampler. The confirmation (#254) could only set batchgeneratorsv2 against the other tweaks; this sets the old recipe
against the new one directly.

It reads cycles.jsonl, one record per cycle with its result (#245): no join to the run logs. Until the window is
complete it prints the arms' cycle counts and nothing they measured.

    python3 scripts/loop_unchanged_control.py status --cycles cycles.jsonl
    python3 scripts/loop_unchanged_control.py read --cycles cycles.jsonl \
        --steps reports/loop_steps_vs_ranking_2026-10-26.json --out reports/X.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

REGISTERED = {
    "since": "2026-10-27T16:00:00",
    "deadline": "2026-11-03T16:00:00",
    # best_model.pt as promoted on 2026-10-27 (#262): the incumbent both arms fine-tune
    "incumbent_sha256": "c80885969cc5b3d4c1dfeebc46d1c0c4c62f55fbe758ce48b263050dc293f18d",
    "budget_s": 900,
    "control": "control_unchanged",
    "reverse": "aug_mode_albumentations",
    "cut_at": 10,
    "min_each": 6,
    # the reverse arm minus the control: about half the confirmation's effects, with the sign reversed
    "Q1_val_f1": -0.002,
    "Q2_roc_auc": -0.005,
    "Q3_ap_lift": -0.015,
}
MEASURES = {"val_f1": "val_f1", "roc_auc": "roc_auc", "ap_lift": "ap_prevalence_lift"}
SCORED = ("REVERTED", "SUCCESS")


def _scored(record: dict) -> bool:
    result = record.get("result")
    if record.get("status") not in SCORED or not isinstance(result, dict):
        return False
    if result.get("promotion_blocked"):
        return False
    return all(
        isinstance(result.get(k), (int, float)) and math.isfinite(result[k])
        for k in MEASURES.values()
    )


def window(
    records: list[dict], reg: dict = REGISTERED
) -> tuple[list[dict], str | None]:
    """The window's scored cycles in run order, and what ended it: from `since`, on the registered incumbent, in the
    code epoch of its first cycle (commit and code_changes); a promotion ends it with that cycle, as does a cycle on
    another incumbent or code, or one started at the deadline."""
    out, epoch = [], None
    for r in records:
        if r.get("started", "") < reg["since"]:
            continue
        if r["started"] >= reg["deadline"]:
            return out, "the deadline"
        if r.get("incumbent_sha256") != reg["incumbent_sha256"]:
            return out, "another incumbent"
        code = json.dumps([r.get("commit"), r.get("code_changes")])
        if epoch is None:
            epoch = code
        elif code != epoch:
            return out, "another code epoch"
        if r.get("budget_s") == reg["budget_s"] and _scored(r):
            out.append(r)
        if r.get("status") == "SUCCESS":
            return out, "a promotion"
    return out, None


def arms(rows: list[dict], reg: dict = REGISTERED) -> tuple[list[dict], list[dict]]:
    """Each arm's first cut_at cycles."""
    control = [r for r in rows if r["tweak"] == reg["control"]][: reg["cut_at"]]
    reverse = [r for r in rows if r["tweak"] == reg["reverse"]][: reg["cut_at"]]
    return control, reverse


def status(records: list[dict], reg: dict = REGISTERED, now: str | None = None) -> dict:
    """Cycle counts only: what may be read before the window is complete."""
    rows, ended = window(records, reg)
    control, reverse = arms(rows, reg)
    if (
        ended is None
        and len(control) >= reg["cut_at"]
        and len(reverse) >= reg["cut_at"]
    ):
        ended = f"both arms reached {reg['cut_at']} cycles"
    if ended is None and now is not None and now >= reg["deadline"]:
        ended = "the deadline"
    return {
        "control_cycles": len(control),
        "reverse_cycles": len(reverse),
        "window_cycles": len(rows),
        "ended_by": ended,
        "complete": ended is not None,
    }


def _welch(xs: list[float], ys: list[float]) -> dict:
    from scipy import stats

    d = statistics.mean(xs) - statistics.mean(ys)
    se = math.sqrt(
        statistics.variance(xs) / len(xs) + statistics.variance(ys) / len(ys)
    )
    test = stats.ttest_ind(xs, ys, equal_var=False)
    return {"diff": d, "se": se, "t": float(test.statistic), "p": float(test.pvalue)}


def read(records: list[dict], steps_record: dict, reg: dict = REGISTERED, now: str | None = None) -> dict:  # fmt: skip
    """The registered reading, once the window is complete."""
    st = status(records, reg, now)
    if not st["complete"]:
        raise SystemExit(
            "the window is not complete: run status, which reads the counts only"
        )
    rows, _ = window(records, reg)
    control, reverse = arms(rows, reg)
    if len(control) < reg["min_each"] or len(reverse) < reg["min_each"]:
        return dict(st, verdict={"status": "INCOMPLETE", "reading": None})
    effects = {}
    for name, key in MEASURES.items():
        xs, ys = (
            [r["result"][key] for r in reverse],
            [r["result"][key] for r in control],
        )
        effects[name] = {
            "reverse_mean": statistics.mean(xs),
            "control_mean": statistics.mean(ys),
            **_welch(xs, ys),
        }
    predictions = {
        "Q1": effects["val_f1"]["diff"] <= reg["Q1_val_f1"],
        "Q2": effects["roc_auc"]["diff"] <= reg["Q2_roc_auc"],
        "Q3": effects["ap_lift"]["diff"] <= reg["Q3_ap_lift"],
    }
    reading = (
        "BEATS_UNCHANGED"
        if predictions["Q1"] and predictions["Q2"]
        else "F1_ONLY"
        if predictions["Q1"]
        else "NOT_SHOWN"
    )
    # Reported, changes no reading: the arms' step counts, at #250's within-tweak slopes, and each arm against the
    # window's other tweaks (the confirmation's comparison).
    gap = statistics.mean(r["result"]["steps"] for r in reverse) - statistics.mean(r["result"]["steps"] for r in control)  # fmt: skip
    steps = {"reverse_minus_control": gap}
    for name in MEASURES:
        steps[name] = {"from_the_step_gap": steps_record["measures"][name]["per_100_steps"] * gap / 100}  # fmt: skip
    others = [r for r in rows if r["tweak"] not in (reg["control"], reg["reverse"])]
    against_others = {
        name: {
            arm: statistics.mean(r["result"][key] for r in cycles)
            - statistics.mean(r["result"][key] for r in others)
            for arm, cycles in (("control", control), ("reverse", reverse))
        }
        for name, key in MEASURES.items()
        if others
    }
    return dict(
        st,
        verdict={"status": "OK", "predictions": predictions, "reading": reading},
        effects=effects,
        steps=steps,
        against_other_tweaks=against_others,
        cycles={
            "control": [r["started"] for r in control],
            "reverse": [r["started"] for r in reverse],
        },
    )


def _records(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    return [json.loads(line) for line in raw.decode().splitlines() if line.strip()], raw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="the arms' cycle counts only")
    r = sub.add_parser(
        "read", help="the registered reading, once the window is complete"
    )
    for p in (s, r):
        p.add_argument("--cycles", type=Path, required=True)
    r.add_argument(
        "--steps",
        type=Path,
        required=True,
        help="loop_steps_vs_ranking's record (#250's slopes)",
    )
    r.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    now = dt.datetime.now().isoformat(timespec="seconds")
    records, raw = _records(args.cycles)
    if args.cmd == "status":
        print(json.dumps(status(records, now=now), indent=1))
        return 0
    steps_raw = args.steps.read_bytes()
    out = read(records, json.loads(steps_raw), now=now)
    out["registered"] = REGISTERED
    out["sources"] = {
        "cycles": {
            "path": str(args.cycles),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": len(records),
        },
        "steps": {
            "path": str(args.steps),
            "sha256": hashlib.sha256(steps_raw).hexdigest(),
        },
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "ended_by")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
