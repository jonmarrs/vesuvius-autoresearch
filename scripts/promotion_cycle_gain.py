"""Each loop cycle's val_f1 against the incumbent it faced, grouped by incumbent.

Reads the loop's console log (autoresearch.out). A cycle's incumbent is the "best was"
of its verdict line; a promotion's is the incumbent the loop held before it (the last
start-up value or promotion). Cycles count from the first start-up whose incumbent is
``--first-incumbent``.

    python3 scripts/promotion_cycle_gain.py --log autoresearch.out \
        --first-incumbent 0.249348 --out reports/X.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

START = re.compile(r"Starting with incumbent val_f1 from best_model\.pt: ([0-9.]+)")
APPLY = re.compile(r"Cycle \d+: Applying (\S+) \(Family Weight")
RUNNING = re.compile(r"Running (\d+)-minute training for ")
KEPT = re.compile(r"No improvement\. \(val_f1: ([0-9.]+), best was: ([0-9.]+)\)")
PROMOTED = re.compile(r"IMPROVEMENT FOUND! \(val_f1: ([0-9.]+)\)")
CRASHED = "CYCLE CRASHED"


def cycles(text: str, first_incumbent: float) -> list[dict]:
    rows, incumbent, name, minutes, started = [], None, None, None, False
    for line in text.splitlines():
        if m := START.search(line):
            incumbent = float(m.group(1))
            started = started or incumbent == first_incumbent
        elif m := APPLY.search(line):
            name, minutes = m.group(1), None
        elif m := RUNNING.search(line):
            minutes = int(m.group(1))
        elif not started:
            continue
        elif m := KEPT.search(line):
            incumbent = float(m.group(2))
            rows.append(
                _row(name, minutes, float(m.group(1)), incumbent, "kept_incumbent")
            )
        elif m := PROMOTED.search(line):
            rows.append(_row(name, minutes, float(m.group(1)), incumbent, "promoted"))
            incumbent = float(m.group(1))
        elif CRASHED in line:
            rows.append(_row(name, minutes, None, incumbent, "crashed"))
    if not started:
        raise ValueError(f"no start-up with incumbent {first_incumbent}")
    return rows


def _row(name, minutes, val_f1, incumbent, outcome) -> dict:
    return {
        "cycle": name,
        "minutes": minutes,
        "val_f1": val_f1,
        "incumbent": incumbent,
        "gain": None if val_f1 is None else val_f1 - incumbent,
        "outcome": outcome,
    }


def segments(rows: list[dict], tolerances=(0.01, 0.03)) -> list[dict]:
    """One entry per incumbent, in the order the loop held them."""
    out: list[dict] = []
    for r in rows:
        if not out or out[-1]["incumbent"] != r["incumbent"]:
            out.append({"incumbent": r["incumbent"], "rows": []})
        out[-1]["rows"].append(r)
    for seg in out:
        gains = [r["gain"] for r in seg["rows"] if r["gain"] is not None]
        seg.update(
            scored=len(gains),
            crashed=sum(r["outcome"] == "crashed" for r in seg["rows"]),
            promoted=sum(r["outcome"] == "promoted" for r in seg["rows"]),
            mean_gain=statistics.mean(gains) if gains else None,
            sd_gain=statistics.stdev(gains) if len(gains) > 1 else None,
            min_gain=min(gains) if gains else None,
            max_gain=max(gains) if gains else None,
            clear={f"{t:g}": sum(g > t for g in gains) for t in tolerances},
        )
        del seg["rows"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--first-incumbent", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = cycles(Path(args.log).read_text(errors="replace"), args.first_incumbent)
    result = {
        "source": args.log,
        "first_incumbent": args.first_incumbent,
        "segments": segments(rows),
        "rows": rows,
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["segments"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
