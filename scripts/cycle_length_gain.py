"""Do longer loop cycles score higher? val_f1 of 60- against 15-minute cycles on one incumbent.

Every cycle fine-tunes best_model.pt for its budget: 15 minutes by day, 60 by night. This
takes the sprint logs' cycles that started at or after --since, up to and including the
first promotion (SUCCESS), since later cycles start from another checkpoint. In time order,
each run of shifts with one budget is an arm, and each 60-minute arm is compared with the
15-minute arm beside it: the difference of means, with Welch's 95% interval. The secondary
comparison leaves out the tweaks that change how many steps a budget buys (STEP_TWEAKS).
With --run-log, each cycle gets its run's step count, matched by val_f1 as in
epoch_boundary_overhead.py. Pre-registered in reports/cycle_length_gain_prereg_2026-10-18.md.

    python3 scripts/cycle_length_gain.py --since 2026-10-17T21:17:25 \
        --sprint-logs 'sprint_logs/sprint_log_2026-10-1[78]_*.md' \
        --run-log run.log.old run.log --out reports/X.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import re
import statistics
import sys
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epoch_boundary_overhead as ebo  # noqa: E402

STEP_TWEAKS = re.compile(r"^(use_uamt_|batch_size_)")
TOLERANCE = 0.01  # train.py's F1_NOISE_TOLERANCE


def reading(lo: float | None, hi: float | None) -> str | None:
    """What a 95% interval for (60-minute mean - 15-minute mean) says, fixed in advance."""
    if lo is None:
        return None
    if lo > 0:
        return "higher"
    if hi < 0:
        return "lower"
    return "no measurable gain" if hi < TOLERANCE else "inconclusive"


def welch(long: list[float], short: list[float]) -> dict:
    diff = statistics.mean(long) - statistics.mean(short)
    out = {"n_long": len(long), "n_short": len(short), "diff": diff}
    if len(long) < 2 or len(short) < 2:
        return dict(out, df=None, lo=None, hi=None, reading=None)
    v1, v2 = (
        statistics.variance(long) / len(long),
        statistics.variance(short) / len(short),
    )
    df = (v1 + v2) ** 2 / (v1**2 / (len(long) - 1) + v2**2 / (len(short) - 1))
    half = stats.t.ppf(0.975, df) * math.sqrt(v1 + v2)
    lo, hi = diff - half, diff + half
    return dict(out, df=df, lo=lo, hi=hi, reading=reading(lo, hi))


def _arm(cycles: list[dict]) -> dict:
    f1 = [c["val_f1"] for c in cycles if c["val_f1"] is not None]
    steps = [c["steps"] for c in cycles if c.get("steps") is not None]
    return {
        "budget": cycles[0]["budget"],
        "first_start": cycles[0]["start"],
        "scored": len(f1),
        "crashed": sum(c["result"] == "CRASHED" for c in cycles),
        "mean": statistics.mean(f1) if f1 else None,
        "sd": statistics.stdev(f1) if len(f1) > 1 else None,
        "median_steps": statistics.median(steps) if steps else None,
        "cycles": cycles,
    }


def analyse(
    patterns: str | list[str], since: str, run_logs: list[str] | None = None
) -> dict:
    if isinstance(patterns, str):
        patterns = [patterns]
    # Each log once, however many patterns name it; a pattern that names none
    # is an error, not a missing arm.
    paths = set()
    for pattern in patterns:
        found = glob.glob(pattern)
        if not found:
            raise SystemExit(f"no sprint log matches {pattern}")
        paths.update(found)
    kept = sorted(
        (
            c
            for path in sorted(paths)
            for c in ebo.cycles(glob.escape(path))
            if dt.datetime.fromisoformat(c["start"]) >= dt.datetime.fromisoformat(since)
        ),
        key=lambda c: c["start"],
    )
    promotion = next((c for c in kept if c["result"] == "SUCCESS"), None)
    if promotion is not None:
        kept = kept[: kept.index(promotion) + 1]
    if run_logs:
        scored, _ = ebo.runs(run_logs)
        for c in kept:
            steps = (
                scored.get(round(c["val_f1"], 6), []) if c["val_f1"] is not None else []
            )
            c["steps"] = steps[0] if len(steps) == 1 else None
    blocks: list[list[dict]] = []
    for c in kept:
        if blocks and blocks[-1][0]["budget"] == c["budget"]:
            blocks[-1].append(c)
        else:
            blocks.append([c])
    arms = [_arm(b) for b in blocks]
    comparisons: dict[str, list[dict]] = {"all": [], "steps_held": []}
    for i in range(len(arms) - 1):
        pair = sorted((i, i + 1), key=lambda k: -arms[k]["budget"])
        long, short = (arms[k]["cycles"] for k in pair)
        for name, keep in (("all", lambda c: True), ("steps_held", _steps_held)):
            a = [c["val_f1"] for c in long if c["val_f1"] is not None and keep(c)]
            b = [c["val_f1"] for c in short if c["val_f1"] is not None and keep(c)]
            comparisons[name].append(dict(welch(a, b), long=pair[0], short=pair[1]))
    return {
        "since": since,
        "tolerance": TOLERANCE,
        "promotion": None
        if promotion is None
        else {"cycle": promotion["cycle"], "start": promotion["start"]},
        "arms": arms,
        "comparisons": comparisons,
    }


def _steps_held(c: dict) -> bool:
    return not STEP_TWEAKS.match(c["cycle"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sprint-logs", nargs="+", required=True, help="sprint-log paths or globs"
    )
    ap.add_argument("--since", required=True)
    ap.add_argument("--run-log", nargs="+", help="run.log.old run.log")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = analyse(args.sprint_logs, args.since, args.run_log)
    result["sources"] = {"sprint_logs": args.sprint_logs, "run_log": args.run_log}
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    summary = {
        "arms": [{k: a[k] for k in a if k != "cycles"} for a in result["arms"]],
        "comparisons": result["comparisons"],
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
