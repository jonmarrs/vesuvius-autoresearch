"""Finding 138, checks written after the result (not registered): how much the rank of the winner's place rests on the
window that ends at each winding's end, and how far its score stands from its neighbours'.

glyph.py adds one window per winding where the last window on the 1,300-pixel grid stops short of the winding's end
(`starts`): that window begins off the grid, so it is the window whose x0 is not a multiple of STEP. The 306B team's
glyph_win.py has no such window. Reported, from the records alone:
- how many windows are those end windows, overall and among the first 10, 20 and 50;
- the median glyph score of end windows and of the others;
- the rank of the best window holding the place when only the grid's windows are ranked (theirs);
- the best place window's score against the first rank's, the next rank's and the 10th rank's.

usage: band_triage_audit.py GLYPH.json TRIAGE.json PLACE.json OUT.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

STEP = 1300  # glyph.py's stride, render pixels
FIRST = 10  # the registered short list


def windows(glyph: dict) -> list[dict]:
    """Every scored window, best first (ties by winding index, then x0), as band_triage.py ranks them."""
    out = [
        {"winding": w, "x0": x["x0"], "glyph": x["glyph"], "end": x["x0"] % STEP != 0}
        for w, xs in glyph["windings"].items()
        for x in xs
        if x["glyph"] is not None
    ]
    return sorted(out, key=lambda x: (-x["glyph"], int(x["winding"][1:]), x["x0"]))


def best_rank(order: list[dict], places: set[tuple[str, int]]) -> int | None:
    for i, x in enumerate(order, start=1):
        if (x["winding"], x["x0"]) in places:
            return i
    return None


def audit(glyph: dict, triage: dict, place: dict) -> dict:
    order = windows(glyph)
    places = {(p["winding"], p["x0"]) for p in triage["described"]["place_windows"]}
    grid = [x for x in order if not x["end"]]
    rank = best_rank(order, places)
    assert rank == triage["registered"]["best_place_rank"], (
        "the ranking does not reproduce the verdict's"
    )
    best = order[rank - 1]
    cells = {
        (w, b["x0"]): b["place_cells"]
        for w, v in place["windows"].items()
        for b in v["by_window"]
    }
    return {
        "finding": 138,
        "registered": False,
        "written": "after the result, to check it",
        "windows": len(order),
        "end_windows": {
            "all": sum(x["end"] for x in order),
            "share": round(sum(x["end"] for x in order) / len(order), 4),
            "in_first": {
                str(k): sum(x["end"] for x in order[:k]) for k in (10, 20, 50)
            },
            "glyph_median": round(
                statistics.median(x["glyph"] for x in order if x["end"]), 3
            ),
            "others_glyph_median": round(
                statistics.median(x["glyph"] for x in order if not x["end"]), 3
            ),
        },
        "grid_only": {"windows": len(grid), "best_place_rank": best_rank(grid, places)},
        "best_place_window": {
            "winding": best["winding"],
            "x0": best["x0"],
            "end_window": best["end"],
            "place_cells": cells[(best["winding"], best["x0"])],
            "glyph": best["glyph"],
            "below_first_rank": round(order[0]["glyph"] - best["glyph"], 3),
            "above_next_rank": round(best["glyph"] - order[rank]["glyph"], 3)
            if rank < len(order)
            else None,
            "above_rank_10": round(best["glyph"] - order[FIRST - 1]["glyph"], 3)
            if len(order) >= FIRST
            else None,
        },
        "first_rank": {
            "winding": order[0]["winding"],
            "x0": order[0]["x0"],
            "end_window": order[0]["end"],
        },
    }


def main(argv: list[str]) -> dict:
    glyph, triage, place = (json.loads(Path(a).read_text()) for a in argv[:3])
    record = audit(glyph, triage, place)
    Path(argv[3]).write_text(json.dumps(record, indent=1) + "\n")
    return record


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    print(json.dumps(main(sys.argv[1:]), indent=1))
