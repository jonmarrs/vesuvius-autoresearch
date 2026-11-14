"""Finding 113, step 8: the registered table, applied to the reader's marks and the key.

usage: score_marks.py KEY.json MARKS.csv OUT.json
       MARKS.csv has a line `strip,mark` per strip, mark 0 (nothing), 1 (strokes) or 2 (letter shapes).

The record holds counts. It names no strip and no place on the scroll.
"""

from __future__ import annotations

import csv
import json
import sys
from math import comb
from pathlib import Path

ANCHOR_READING_MIN = 0.70
ANCHOR_OTHER_MAX = 0.30
LETTER_STRIPS_MIN = 3
P_MAX = 0.05


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(at least `a` marked among the first row) for the table [[a, b], [c, d]] with fixed margins."""
    row, column, total = a + b, a + c, a + b + c + d
    if total == 0 or comb(total, column) == 0:
        return 1.0
    top = min(row, column)
    return sum(
        comb(row, k) * comb(total - row, column - k) for k in range(a, top + 1)
    ) / comb(total, column)


def counts(key: dict[str, dict], marks: dict[str, int], source: str) -> dict:
    out = {}
    for side in ("reading", "other"):
        values = [
            marks[s]
            for s, k in key.items()
            if k["source"] == source and k["side"] == side
        ]
        out[side] = {
            "strips": len(values),
            "marked": sum(v >= 1 for v in values),
            "letters": sum(v == 2 for v in values),
        }
    return out


def verdict(target: dict, anchors: dict) -> dict:
    """`target` and `anchors` are `counts` results for the scroll's strips and the anchors' strips."""
    reading, other = anchors["reading"], anchors["other"]
    calibrated = (
        reading["strips"] > 0
        and other["strips"] > 0
        and reading["marked"] / reading["strips"] >= ANCHOR_READING_MIN
        and other["marked"] / other["strips"] <= ANCHOR_OTHER_MAX
    )
    r, o = target["reading"], target["other"]
    p = fisher_one_sided(
        r["marked"], r["strips"] - r["marked"], o["marked"], o["strips"] - o["marked"]
    )
    p_other = fisher_one_sided(
        o["marked"], o["strips"] - o["marked"], r["marked"], r["strips"] - r["marked"]
    )
    if not calibrated:
        name = "READER_NOT_CALIBRATED"
    elif r["letters"] >= LETTER_STRIPS_MIN and r["letters"] > o["letters"]:
        name = "LETTER_CANDIDATES"
    elif r["marked"] > o["marked"] and p < P_MAX:
        name = "STROKES"
    else:
        name = "NOTHING_SEEN"
    return {
        "verdict": name,
        "anchors_calibrated": calibrated,
        "p_reading_over_other": round(p, 4),
        "other_side_wins": bool(o["marked"] > r["marked"] and p_other < P_MAX),
    }


def main(argv: list[str] | None = None) -> int:
    key_file, marks_file, out = (
        Path(p) for p in (argv if argv is not None else sys.argv[1:])
    )
    if out.exists():
        print(f"{out} exists: the marks are scored once", file=sys.stderr)
        return 2
    key = json.loads(key_file.read_text())["strips"]
    with marks_file.open() as handle:
        marks = {
            row[0].strip(): int(row[1])
            for row in csv.reader(handle)
            if row and row[0].strip() != "strip"
        }
    missing = sorted(set(key) - set(marks))
    if missing or any(v not in (0, 1, 2) for v in marks.values()):
        print(
            f"marks are incomplete or not 0/1/2; missing {missing[:5]}", file=sys.stderr
        )
        return 1
    target, anchors = counts(key, marks, "target"), counts(key, marks, "anchor")
    record = {"target": target, "anchors": anchors, **verdict(target, anchors)}
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
