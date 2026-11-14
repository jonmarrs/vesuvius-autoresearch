"""Finding 112's registered table, applied to the gate files and the two score files of one run directory.

usage: band_fit_verdict.py RUN_DIR OUT.json

The record carries summary numbers only: no geometry and no score of a single winding.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MIN_WINDINGS = 60
FLOOR_MAX = 0.03  # smoke fit's median excess above this: the score reads something else
P1 = {"median": 0.07, "positive": 0.80}
P2 = {"median": 0.03, "positive": 0.65}
STEPS = (("setup", "distance_field"), ("smoke", "fit"), ("full", "fit"))


def holds(summary: dict, line: dict) -> bool:
    return (
        summary["excess_median"] >= line["median"]
        and summary["share_of_windings_with_positive_excess"] >= line["positive"]
    )


def verdict(steps: dict, smoke: dict | None, full: dict | None) -> str:
    """`steps` maps a step name to its gate record, or None where the gate file is missing."""
    if any(step is None or step["exit"] != 0 for step in steps.values()):
        return "DOES_NOT_RUN"
    if smoke is None or full is None:
        return "DOES_NOT_RUN"
    if min(smoke["windings_scored"], full["windings_scored"]) < MIN_WINDINGS:
        return "DOES_NOT_RUN"
    if smoke["excess_median"] > FLOOR_MAX:
        return "INSTRUMENT_FAILS"
    if holds(full, P1):
        return "ON_SHEETS"
    if holds(full, P2):
        return "PARTLY_ON_SHEETS"
    return "NOT_ON_SHEETS"


def _read(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def by_index(quality: dict, parts: int = 3) -> list[dict]:
    """The scored windings in index order, cut into equal parts: where in the spiral the score is good."""
    scored = sorted(
        (int(name[1:]), w) for name, w in quality["windings"].items() if w is not None
    )
    size = -(-len(scored) // parts)
    out = []
    for start in range(0, len(scored), size):
        part = scored[start : start + size]
        excess = sorted(w["excess"] for _, w in part)
        on_sheet = sorted(w["on_sheet"] for _, w in part)
        nodes = sorted(w["nodes_scored"] for _, w in part)
        out.append(
            {
                "first": part[0][0],
                "last": part[-1][0],
                "windings": len(part),
                "excess_median": round(_median(excess), 4),
                "positive": round(sum(e > 0 for e in excess) / len(part), 4),
                "at_least_p1_median": sum(e >= P1["median"] for e in excess),
                "on_sheet_median": round(_median(on_sheet), 4),
                "nodes_scored_median": int(_median(nodes)),
            }
        )
    return out


def _median(ordered: list) -> float:
    n = len(ordered)
    return float(
        ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    )


def main(argv: list[str] | None = None) -> int:
    run, out = (Path(p) for p in (argv if argv is not None else sys.argv[1:]))
    steps = {
        f"{arm}/{name}": _read(run / "work" / f"gate_{arm}" / f"{name}.json")
        for arm, name in STEPS
    }
    smoke, full = (
        _read(run / "work" / f"quality_{arm}.json") for arm in ("smoke", "full")
    )
    smoke_summary = smoke and smoke["summary"]
    full_summary = full and full["summary"]
    record = {
        "steps": steps,
        "smoke": smoke_summary,
        "full": full_summary,
        "p1": bool(full_summary and holds(full_summary, P1)),
        "p2": bool(full_summary and holds(full_summary, P2)),
        "verdict": verdict(steps, smoke_summary, full_summary),
        "full_by_index": full and by_index(full),
    }
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
