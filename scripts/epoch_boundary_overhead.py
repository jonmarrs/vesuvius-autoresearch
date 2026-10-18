"""How much of a loop cycle's wall time the training budget does not count, per pass.

A cycle's overhead is the time between its sprint-log timestamp and the previous one's
(the shift's start for cycle 1), less the training budget. Each cycle is matched to its
run in run.log by val_f1 (6 decimals), which gives its step count; with the batch size
that is its number of passes over the training catalogue, so of epoch boundaries crossed.
Fits overhead = a + b * boundaries over the matched cycles, and reads the 60-minute cycle
the loop killed at its timeout (2026-10-16 night shift) from run.log.

    python3 scripts/epoch_boundary_overhead.py --run-log run.log \
        --sprint-logs 'sprint_logs/sprint_log_2026-10-1[67]_*.md' --out reports/X.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

CATALOGUE = 7345  # "Initialized Dataset: ... Valid Patches 7345" (Fr47)
TIMEOUT_MARGIN = 300  # run_autoresearch_loop.py: timeout=default_budget + 300
RUN_START = "Starting Gated UNet-Transformer Loop (Budget: "
V3 = "seeded-sample-400-v3"


def runs(run_log: str) -> tuple[dict[float, list[int]], list[dict]]:
    """val_f1 -> step counts of the runs that scored it, and the runs that never scored."""
    lines = Path(run_log).read_text(errors="replace").split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith(RUN_START)]
    # Unscored runs count from the first run scored under protocol v3 (10-16).
    v3 = next(i for i, line in enumerate(lines) if V3 in line)
    v3_start = max(s for s in starts if s < v3)
    scored, unscored = defaultdict(list), []
    for k, s in enumerate(starts):
        seg = lines[s : starts[k + 1] if k + 1 < len(starts) else len(lines)]
        steps = [line for line in seg if line.startswith("Step ")]
        if not steps:
            continue
        last = re.match(r"Step (\d+) .*Remaining: (\d+)s", steps[-1])
        f1 = [
            m.group(1)
            for m in (re.match(r"\s*val_f1:\s+([0-9.]+)", x) for x in seg)
            if m
        ]
        if f1:
            scored[round(float(f1[0]), 6)].append(int(last.group(1)))
        elif s >= v3_start:
            budget = int(re.search(r"Budget: (\d+)s", seg[0]).group(1))
            unscored.append(
                {
                    "budget": budget,
                    "steps": int(last.group(1)),
                    "remaining_s": int(last.group(2)),
                }
            )
    return scored, unscored


def cycles(pattern: str) -> list[dict]:
    """Each sprint-log cycle with its overhead; the budget comes from the shift."""
    out = []
    for path in sorted(glob.glob(pattern)):
        text = Path(path).read_text()
        budget = 3600 if "night_shift" in path else 900
        start = re.search(r"\*\*Start Time\*\*: (\d+:\d+:\d+)", text).group(1)
        prev = dt.datetime.strptime(start, "%H:%M:%S")
        for block in re.split(r"\n## ", text)[1:]:
            # A restart inside the shift: the next cycle starts here, not at
            # the last cycle before the stop.
            if resumed := re.match(r"Resumed at (\d+:\d+:\d+)", block):
                prev = dt.datetime.strptime(resumed.group(1), "%H:%M:%S")
                continue
            m = re.match(
                r"Cycle (\d+): (\S+) \((\w+)\)\n- \*\*Timestamp\*\*: (\d+:\d+:\d+)",
                block,
            )
            if not m:
                continue
            now = dt.datetime.strptime(m.group(4), "%H:%M:%S")
            seconds = (now - prev).total_seconds() % 86400
            prev = now
            f1 = re.search(r"val_f1: ([0-9.]+)", block)
            out.append(
                {
                    "shift": Path(path).name[len("sprint_log_") : -len(".md")],
                    "budget": budget,
                    "cycle": m.group(2),
                    "result": m.group(3),
                    "batch_size": int(re.search(r"batch_size: (\d+)", block).group(1)),
                    "val_f1": float(f1.group(1)) if f1 else None,
                    "overhead_s": int(seconds - budget),
                }
            )
    return out


def fit(rows: list[dict]) -> dict:
    xs = [r["boundaries"] for r in rows]
    ys = [r["overhead_s"] for r in rows]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum(
        (x - mx) ** 2 for x in xs
    )
    intercept = my - slope * mx
    residuals = [y - intercept - slope * x for x, y in zip(xs, ys, strict=True)]
    return {
        "n": len(rows),
        "intercept_s": intercept,
        "per_boundary_s": slope,
        "residual_sd_s": statistics.stdev(residuals),
    }


def analyse(run_log: str, pattern: str) -> dict:
    scored, unscored = runs(run_log)
    rows = []
    for c in cycles(pattern):
        steps = scored.get(round(c["val_f1"], 6)) if c["val_f1"] is not None else None
        # A unique match, and an interval a pause or restart did not stretch.
        if (
            c["result"] != "CRASHED"
            and steps
            and len(steps) == 1
            and 0 < c["overhead_s"] < 600
        ):
            rows.append(
                dict(
                    c,
                    steps=steps[0],
                    boundaries=steps[0] * c["batch_size"] // CATALOGUE,
                )
            )
    groups = defaultdict(list)
    for r in rows:
        groups[(r["budget"], r["boundaries"])].append(r["overhead_s"])
    model = fit(rows)
    # The 60-minute runs that never scored, paired in order with the crashed
    # 60-minute cycles of the same sprint logs.
    crashed = [
        c for c in cycles(pattern) if c["result"] == "CRASHED" and c["budget"] == 3600
    ]
    unscored_long = [u for u in unscored if u["budget"] == 3600]
    killed = []
    if len(crashed) == len(unscored_long):
        for c, u in zip(crashed, unscored_long, strict=True):
            boundaries = u["steps"] * c["batch_size"] // CATALOGUE
            killed.append(
                dict(
                    u,
                    shift=c["shift"],
                    cycle=c["cycle"],
                    batch_size=c["batch_size"],
                    boundaries=boundaries,
                    predicted_overhead_s=model["intercept_s"]
                    + model["per_boundary_s"] * boundaries,
                )
            )
    return {
        "catalogue": CATALOGUE,
        "timeout_margin_s": TIMEOUT_MARGIN,
        "fit": model,
        "groups": [
            {
                "budget": b,
                "boundaries": n,
                "n": len(v),
                "median_s": statistics.median(v),
                "min_s": min(v),
                "max_s": max(v),
            }
            for (b, n), v in sorted(groups.items())
        ],
        "killed": killed,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--sprint-logs", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = analyse(args.run_log, args.sprint_logs)
    result["sources"] = {"run_log": args.run_log, "sprint_logs": args.sprint_logs}
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("fit", "groups", "killed")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
