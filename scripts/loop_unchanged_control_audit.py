"""Checks beside the unchanged-control reading (docs/preregistration/2026-10-27_loop_unchanged_control.md) that change
no reading: written after the registered `read`, on the same window.

The arms ran at different times (the sampler places them), so a score that drifted over the window could make one arm
look better. This reports, for each measure: the other tweaks' drift over the window; each arm cycle against the mean
of its `nearest` other-tweak cycles in time (the arms' difference with any drift matched out); a rank test; and the
raw difference with each cycle left out in turn.

    python3 scripts/loop_unchanged_control_audit.py --cycles cycles.jsonl --out reports/X.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop_unchanged_control as U  # noqa: E402

NEAREST = 6
THRESHOLD = {"val_f1": "Q1_val_f1", "roc_auc": "Q2_roc_auc", "ap_lift": "Q3_ap_lift"}


def _hours(record: dict) -> float:
    return dt.datetime.fromisoformat(record["started"]).timestamp() / 3600


def audit(
    records: list[dict], reg: dict = U.REGISTERED, nearest: int = NEAREST
) -> dict:
    from scipy import stats

    rows, ended = U.window(records, reg)
    control, reverse = U.arms(rows, reg)
    others = [r for r in rows if r["tweak"] not in (reg["control"], reg["reverse"])]
    if min(len(control), len(reverse)) < reg["min_each"] or len(others) < nearest:
        raise SystemExit("too few cycles to audit")
    t0 = _hours(rows[0])

    def near(record):
        return sorted(others, key=lambda o: abs(_hours(o) - _hours(record)))[:nearest]

    measures = {}
    for name, key in U.MEASURES.items():
        xs = [r["result"][key] for r in reverse]
        ys = [r["result"][key] for r in control]
        drift = stats.linregress([_hours(r) - t0 for r in others], [r["result"][key] for r in others])  # fmt: skip
        rr, rc = (
            [
                r["result"][key] - statistics.mean(o["result"][key] for o in near(r))
                for r in arm
            ]
            for arm in (reverse, control)
        )
        matched = stats.ttest_ind(rr, rc, equal_var=False)
        loo = [statistics.mean(xs[:i] + xs[i + 1 :]) - statistics.mean(ys) for i in range(len(xs))] + [
            statistics.mean(xs) - statistics.mean(ys[:i] + ys[i + 1 :]) for i in range(len(ys))
        ]  # fmt: skip
        measures[name] = {
            "threshold": reg[THRESHOLD[name]],
            "reverse": xs,
            "control": ys,
            "raw_diff": statistics.mean(xs) - statistics.mean(ys),
            "others_drift_per_day": float(drift.slope) * 24,
            "others_drift_p": float(drift.pvalue),
            "time_matched_diff": statistics.mean(rr) - statistics.mean(rc),
            "time_matched_t": float(matched.statistic),
            "time_matched_p": float(matched.pvalue),
            "mann_whitney_p": float(
                stats.mannwhitneyu(xs, ys, alternative="two-sided").pvalue
            ),
            "leave_one_out": [min(loo), max(loo)],
        }
    return {
        "ended_by": ended,
        "window": [rows[0]["started"], rows[-1]["started"]],
        "cycles": {
            "control": len(control),
            "reverse": len(reverse),
            "others": len(others),
        },
        "nearest": nearest,
        "measures": measures,
        "steps": {
            arm: [r["result"]["steps"] for r in cycles]
            for arm, cycles in (("control", control), ("reverse", reverse))
        },  # fmt: skip
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cycles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    raw = args.cycles.read_bytes()
    records = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    out = audit(records)
    out["sources"] = {"cycles": {"path": str(args.cycles), "sha256": hashlib.sha256(raw).hexdigest(), "records": len(records)}}  # fmt: skip
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: {m: round(v["time_matched_diff"], 5) for m, v in out["measures"].items()} for k in ("measures",)}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
