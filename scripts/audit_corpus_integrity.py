# Dogfooding inkdelta (github.com/jonmarrs/inkdelta) on this project: run from the repo root.
# Usage: .venv/bin/python scripts/audit_corpus_integrity.py reports/corpus_integrity_audit.json

"""inkdelta check on every scored run in spiral_out. Log per run: <arm>.render.log, then
outer-style <arm>_render.log; otherwise none (reported as LOG_NOT_FOUND, not as a pass)."""

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
from inkdelta.runs import load_run  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
arms = sorted({p.parent.parent.name for p in SO.glob("*/ink_metric/metrics.json")})
rows, codes = [], collections.Counter()
for a in arms:
    log = None
    for cand in (SO / f"{a}.render.log", SO / f"{a}_render.log"):
        if cand.is_file():
            log = cand
            break
    r = load_run(SO / a, log)
    fails = [f.code for f in r.findings if f.level == "FAIL"]
    warns = [f.code for f in r.findings if f.level == "WARN"]
    codes.update(fails + warns)
    rows.append(
        {
            "arm": a,
            "fg": r.total_fg_pixels,
            "fail": fails,
            "warn": warns,
            "log": str(log) if log else None,
        }
    )
print(f"scored runs: {len(arms)}")
print("finding counts:", dict(codes))
print("FAILS:")
for row in rows:
    if row["fail"]:
        print(f"  {row['arm']}: {row['fail']} fg={row['fg']}")
json.dump(rows, open(sys.argv[1], "w"), indent=1)
