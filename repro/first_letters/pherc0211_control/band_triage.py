"""Finding 138: does the PHerc. 306B team's window triage put PHerc. 211's known text first in a Studio band read?

Registration: docs/preregistration/2026-11-22_first_letters_0211_band_triage.md.

    place    OUT.json --winner-mesh --winner-maps --winner-render --studio-mask --finals --renders --list [--slices 18]
             The winner's place on our windings. Each read winding whose nodes come within ACCEPT voxels of the
             winner's surface's bounding box is carried onto it by finding 110's transfer, as finding 124 carried
             its four windings: every winner lattice point inside the winner's Studio mask takes its nearest read
             winding and cell within ACCEPT voxels. A window (glyph.py's) of a read winding holds the place when at
             least MIN_PLACE_CELLS of those cells fall in its columns (finding 121's minimum for scoring a
             winding).
    verdict  OUT.json GLYPH.json PLACE.json
             Every scored window of the band, ranked by its glyph score; the rank of the best window that holds
             the place; the registered table.

Studio's maps, the glyph weights and PHerc. 211's images stay on this machine (CC BY-NC 4.0).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "eligible_band"))
sys.path.insert(0, str(HERE.parent / "triage"))

import glyph  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402

MIN_PLACE_CELLS = 1000  # finding 121's MIN_WINDING_CELLS: lattice cells of the winner's mask in one window
FIRST = 10  # TRIAGE_FINDS_THE_TEXT: the place among the first ten windows
HIGH_SHARE = 0.05  # TRIAGE_RANKS_THE_TEXT_HIGH: within the first 5% of windows (and at least the first ten)
THEIR_P99 = 9.06  # glyph_win.py's admission line, the p99 of their negative lane windows (model gA), described


def near_box(
    xyz: np.ndarray, valid: np.ndarray, lo: np.ndarray, hi: np.ndarray
) -> bool:
    """Whether any node lies inside the box [lo, hi] (the winner's points' box widened by ACCEPT)."""
    p = xyz[valid]
    return bool(p.size and ((p >= lo) & (p <= hi)).all(axis=1).any())


def place_cells(
    which: np.ndarray, cell: np.ndarray, inside: np.ndarray, number: int, cells_c: int
) -> np.ndarray:
    """The render column (pixel) of every winner cell inside the mask that winding `number` gives ink to."""
    hit = (which == number) & inside
    columns = cell[hit] % cells_c
    return columns * analysis.LATTICE + analysis.LATTICE // 2


def window_counts(columns: np.ndarray, width: int) -> list[dict]:
    """glyph.py's windows of a winding WIDTH pixels wide, each with the place cells in its columns."""
    return [
        {
            "x0": x0,
            "place_cells": int(((columns >= x0) & (columns < x0 + glyph.WIN)).sum()),
        }
        for x0 in glyph.starts(width)
    ]


def place_cmd(args: argparse.Namespace) -> dict:
    import cv2
    import dense_read as f131
    import end_to_end as f121
    import transfer_maps as tm

    winner = tm.side(Path(args.winner_mesh), Path(args.winner_maps), Path(args.winner_render), blind_too=False,
                     depth=f121.DEPTH)  # fmt: skip
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    if in_mask.shape != winner["ok"].shape:
        raise SystemExit(
            f"the mask's lattice is {in_mask.shape}, the winner's {winner['ok'].shape}"
        )
    pts = winner["points"][winner["ok"]]
    lo, hi = pts.min(0) - analysis.ACCEPT, pts.max(0) + analysis.ACCEPT
    windings = [w for w in Path(args.list).read_text().split() if w]
    near, sides = [], []
    for w in windings:
        final = Path(args.finals) / f"{w}.tifxyz"
        if not final.exists():
            continue
        xyz, valid = analysis.load_tifxyz(final)
        if near_box(xyz, valid, lo, hi):
            near.append(w)
            sides.append(
                f131.side(final, Path(args.renders) / f"{w}_{args.slices}.zarr")
            )
    result: dict = {"windings_read": len(windings), "windings_near_the_winner": near,
                    "mask_cells": int((in_mask & winner["ok"]).sum()), "min_place_cells": MIN_PLACE_CELLS,
                    "windows": {}}  # fmt: skip
    if not sides:
        result["place_cells"] = 0
        return result
    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(s["points"], s["ok"]) for s in sides]
    )
    inside = (which >= 0) & winner["ok"] & in_mask
    result["place_cells"] = int(inside.sum())
    result["place_share_of_mask"] = round(
        result["place_cells"] / max(result["mask_cells"], 1), 4
    )
    for k, (w, s) in enumerate(zip(near, sides, strict=True)):
        columns = place_cells(which, cell, inside, k, s["ok"].shape[1])
        result["windows"][w] = {
            "place_cells": int(columns.size),
            "by_window": window_counts(columns, s["canvas"][1]),
        }
    return result


def ranked(record: dict) -> list[dict]:
    """Every scored window of the band, as glyph.rank sorts them."""
    flat = [{"winding": w, **x} for w, xs in record["windings"].items() for x in xs]
    return glyph.rank(flat, "glyph")


def holds_place(place: dict) -> set[tuple[str, int]]:
    return {(w, x["x0"]) for w, v in place["windows"].items() for x in v["by_window"]
            if x["place_cells"] >= MIN_PLACE_CELLS}  # fmt: skip


def best_rank(order: list[dict], places: set[tuple[str, int]]) -> int | None:
    for i, x in enumerate(order, start=1):
        if (x["winding"], x["x0"]) in places:
            return i
    return None


def verdict(rank: int | None, windows: int, places: int) -> str:
    if places == 0:
        return "BAND_READ_MISSES_THE_PLACE"
    if rank is None or windows == 0:
        return "DOES_NOT_RUN"
    if rank <= FIRST:
        return "TRIAGE_FINDS_THE_TEXT"
    if rank <= max(FIRST, math.ceil(HIGH_SHARE * windows)):
        return "TRIAGE_RANKS_THE_TEXT_HIGH"
    return "TRIAGE_MISSES_THE_TEXT"


def verdict_cmd(args: argparse.Namespace) -> dict:
    record = json.loads(Path(args.glyph).read_text())
    place = json.loads(Path(args.place).read_text())
    order = ranked(record)
    places = holds_place(place)
    scored_places = {
        p for p in places if any((x["winding"], x["x0"]) == p for x in order)
    }
    rank = best_rank(order, places)
    rows_order = glyph.rank(
        [{"winding": w, **x} for w, xs in record["windings"].items() for x in xs],
        "rows",
    )
    by_winding = sorted(
        ((w, max(x["glyph"] for x in xs if x["glyph"] is not None)) for w, xs in record["windings"].items()
         if any(x["glyph"] is not None for x in xs)),
        key=lambda t: (-t[1], int(t[0][1:])),
    )  # fmt: skip
    place_windings = sorted({w for w, _ in places}, key=lambda n: int(n[1:]))
    out = {
        "registered": {
            "windows": len(order),
            "place_windows": len(places),
            "place_windows_scored": len(scored_places),
            "best_place_rank": rank,
            "lines": {"first": FIRST, "high": max(FIRST, math.ceil(HIGH_SHARE * len(order)))},
        },
        "verdict": verdict(rank, len(order), len(places)),
        "described": {
            "best_place_rank_by_rows": best_rank(rows_order, places),
            "windows_with_a_row_score": len(rows_order),
            "place_windows": sorted(
                ({"winding": x["winding"], "x0": x["x0"], "glyph": x["glyph"], "rows": x["rows"], "rank": i}
                 for i, x in enumerate(order, start=1) if (x["winding"], x["x0"]) in places),
                key=lambda d: d["rank"],
            ),
            "top": [{"rank": i, **x} for i, x in enumerate(order[:20], start=1)],
            "windings_by_best_window": [w for w, _ in by_winding],
            "place_windings_rank_by_best_window": {w: 1 + [n for n, _ in by_winding].index(w)
                                                   for w in place_windings if w in dict(by_winding)},
            "share_of_windows_above_their_p99": round(
                sum(x["glyph"] > THEIR_P99 for x in order) / max(len(order), 1), 4),
            "glyph_quantiles": dict(zip(("p50", "p90", "p99", "max"), [
                round(float(q), 3) for q in np.quantile([x["glyph"] for x in order], [0.5, 0.9, 0.99, 1.0])
            ], strict=False)) if order else None,
            "missing_maps": record.get("missing", []),
        },
    }  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("place")
    p.add_argument("out", type=Path)
    for name in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio-mask",
        "--finals",
        "--renders",
        "--list",
    ):
        p.add_argument(name, required=True)
    p.add_argument("--slices", type=int, default=18)
    v = sub.add_parser("verdict")
    v.add_argument("out", type=Path)
    v.add_argument("glyph")
    v.add_argument("place")
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    result = place_cmd(args) if args.cmd == "place" else verdict_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    if args.cmd == "verdict":
        print(result["verdict"], json.dumps(result["registered"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
