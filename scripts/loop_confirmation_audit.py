"""Audit how the registered batchgeneratorsv2 confirmation matched its window's cycles to their runs, and give its
reading with each run pinned by the run log's own header. Post hoc: the registered reading stays the registered one.

The registered join (`loop_tweak_replication.cycles`) gives a cycle the runs with its val_f1 (six decimals) that faced
its incumbent, and leaves it unmatched when there are more or fewer of them than window cycles with that value. The
run logs also hold runs from before the window, which no window cycle claims, and runs after its end, so a window
cycle whose val_f1 recurs among them is left unmatched though its own run is in the logs. The loop heads every run
with `--- DAY|NIGHT SHIFT CYCLE N: <tweak> ---` and numbers the sprint log's cycles the same way. Here a run is a
cycle's when val_f1, incumbent, shift, number and tweak all agree. The registered join's matches are checked that
way, and a cycle it left unmatched gets the one run that agrees, when exactly one does.

    python3 scripts/loop_confirmation_audit.py --confirmation reports/loop_tweak_confirmation_2026-10-27.json \
        --logs local_data/loop_logs/readout_2026-10-27 --steps reports/loop_steps_vs_ranking_2026-10-26.json \
        --out reports/loop_confirmation_audit_2026-10-27.json \
        --corrected reports/loop_tweak_confirmation_corrected_2026-10-27.json

`--logs` is the directory the registered command ran in: the `sources` it records are read from there.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop_steps_vs_ranking as svr  # noqa: E402

ltr = svr.ltr
headed_runs, numbered_cycles = ltr.headed_runs, ltr.numbered_cycles


def audit(confirmation: dict, runs: dict, numbers: dict) -> dict:
    """Check each registered match by its run's header, and give each unmatched cycle the one run whose header and
    val_f1 are its own."""
    inc, tally = confirmation["incumbent"], confirmation["tally"]
    if tally["other_budget"]:
        raise SystemExit(
            "cycles of another budget also claim values; this audit does not count them"
        )
    runs = {k: [(rec, h) for rec, h in v if rec["incumbent"] == inc] for k, v in runs.items()}  # fmt: skip
    claims = defaultdict(list)
    for r in confirmation["rows"]:
        claims[round(r["val_f1"], 6)].append(r["start"])
    rows, agrees, disagreeing, unmatched = [], 0, [], []
    for r in confirmation["rows"]:
        key, want = round(r["val_f1"], 6), numbers[r["start"]]
        if want[2] != r["tweak"]:
            raise SystemExit(
                f"{r['start']}: the sprint log names {want[2]}, the row {r['tweak']}"
            )
        cands = runs.get(key, [])
        # the registered join matched it, to the run its claim's rank picks
        if "threshold" in r:
            rec, h = cands[claims[key].index(r["start"])]
            if any(r[f] != v for f, v in rec.items()):
                raise SystemExit(f"{r['start']}: the registered row is not its run")
            if h == want:
                agrees += 1
            else:
                disagreeing.append({"start": r["start"], "tweak": r["tweak"], "run": list(h) if h else None})  # fmt: skip
            rows.append(r)
            continue
        own = [rec for rec, h in cands if h == want]
        unmatched.append({
            "start": r["start"], "tweak": r["tweak"], "val_f1": r["val_f1"], "sprint_log": list(want),
            "candidates": [list(h) if h else None for _, h in cands], "resolved": len(own) == 1,
        })  # fmt: skip
        rows.append({**r, **own[0]} if len(own) == 1 else r)
    return {
        "registered_matches": {
            "checked": len(confirmation["rows"]) - len(unmatched),
            "header_agrees": agrees,
        },
        "disagreeing": disagreeing,
        "unmatched": unmatched,
        "still_unmatched": sum(not u["resolved"] for u in unmatched),
        "rows": rows,
    }


def corrected(confirmation: dict, result: dict) -> dict:
    """The registered output with the audited rows: its tally, effects, standing summary and verdict recomputed by the
    registered functions."""
    rows, inc = result["rows"], confirmation["incumbent"]
    tally = dict(confirmation["tally"], unmatched=result["still_unmatched"])
    out = dict(confirmation, tally=tally, rows=rows)
    out["effects"] = {m: ltr.effects(rows, m) for m in ltr.MEASURES}
    out["standing"] = ltr.summary(rows, ltr.REGISTERED["standing"], inc)
    out["verdict"] = ltr.registered_verdict(rows, tally, inc)
    out["corrected"] = (
        "Post hoc, not the registered reading: rows the registered join left unmatched are given the one run whose "
        "run-log header (shift, number, tweak) and val_f1 are the cycle's (scripts/loop_confirmation_audit.py)."
    )
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--confirmation", required=True, help="the registered command's output"
    )
    ap.add_argument(
        "--logs", required=True, help="the directory the registered command ran in"
    )
    ap.add_argument(
        "--steps", required=True, help="loop_steps_vs_ranking's pre-window record"
    )
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--corrected", required=True, help="where the corrected confirmation goes"
    )
    args = ap.parse_args(argv)
    raw = Path(args.confirmation).read_bytes()
    confirmation, logs = json.loads(raw), Path(args.logs)
    if "registered" not in confirmation:
        raise SystemExit("not the registered confirmation's output")
    src = confirmation["sources"]
    patterns = [str(logs / p) for p in src["sprint_logs"]]
    run_logs = [str(logs / p) for p in src["run_logs"]]
    result = audit(confirmation, headed_runs(run_logs), numbered_cycles(patterns))
    fixed = corrected(confirmation, result)
    steps_raw = Path(args.steps).read_bytes()
    steps = json.loads(steps_raw)
    sprint = sorted({p for pat in patterns for p in glob.glob(pat)})
    # #250's adjustment reads every row's steps
    adjusted = (
        svr.window_adjustment(fixed, steps) if not result["still_unmatched"] else None
    )
    out = {
        "sources": {
            "confirmation": {
                "path": args.confirmation,
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            "run_logs": [
                {"path": p, "sha256": _sha(logs / p)} for p in src["run_logs"]
            ],
            "sprint_logs": [
                {"path": str(Path(p).relative_to(logs)), "sha256": _sha(Path(p))}
                for p in sprint
            ],
            "steps": {
                "path": args.steps,
                "sha256": hashlib.sha256(steps_raw).hexdigest(),
            },
        },
        "registered": {
            "tally": confirmation["tally"],
            "verdict": confirmation["verdict"],
        },
        **{k: v for k, v in result.items() if k != "rows"},
        "corrected": {
            "tally": fixed["tally"],
            "verdict": fixed["verdict"],
            "standing_effects": {
                m: fixed["effects"][m][ltr.REGISTERED["standing"]] for m in ltr.MEASURES
            },
            "steps": adjusted,
        },
    }
    Path(args.corrected).write_text(json.dumps(fixed, indent=1) + "\n")
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("registered", "registered_matches", "still_unmatched")}, indent=1))  # fmt: skip
    print(json.dumps(out["corrected"]["verdict"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
