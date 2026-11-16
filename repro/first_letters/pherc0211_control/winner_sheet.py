"""Does the recipe's fit of PHerc. 211's band z 7650-9150 put a winding on the surface that won the prize?

Finding 119 (registration: docs/preregistration/2026-11-16_first_letters_0211_winner_band.md). The reference is
the winner's three-row surface; only its nodes inside the band are measured. Distances are finding 110's
(`surface_distance`: from each of the winner's nodes to the nearest node of ours, along our normal there, uncovered
beyond 30 voxels sideways, shares over all the winner's nodes in the band).

    choose   every raw winding against the winner's nodes; the chosen winding is finding 110's choice (smallest
             median among those that cover at least half of them); writes the snap list (it and both index
             neighbours) and, described, how much of the winner's surface lies near any winding and the
             per-tile score of the chosen winding against it (finding 117's tiles)
    verdict  the snapped chosen winding against the winner's nodes, and the registered verdict

usage: winner_sheet.py choose OUT.json WINNER_TIFXYZ FIT_MESH_DIR SNAP_LIST.txt [--sdt SDT_ZARR]
       winner_sheet.py verdict OUT.json WINNER_TIFXYZ CHOSEN.json SNAP_DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "pherc343" / "tile_gate"))
sys.path.insert(0, str(HERE.parent / "eligible_band"))

import mesh_step_analysis as analysis  # noqa: E402

Z_BEGIN, Z_END = 7650, 9150
WITHIN = str(int(analysis.WITHIN))  # "2"
ON_SHARE, ON_MEDIAN = (
    analysis.P1_FRACTION,
    analysis.P1_MEDIAN,
)  # 0.50, 3.0 voxels: finding 110's P1
PARTLY_SHARE = 0.25


def in_band(xyz: np.ndarray, valid: np.ndarray) -> np.ndarray:
    return valid & (xyz[..., 2] >= Z_BEGIN) & (xyz[..., 2] <= Z_END)


def winding_index(name: str) -> int:
    index = analysis.winding_index(name)
    if index is None:
        raise ValueError(f"{name} is not a winding name")
    return index


def neighbours(chosen: str, names: list[str]) -> list[str]:
    """The chosen winding and its index neighbours that exist, in index order."""
    i = winding_index(chosen)
    width = len(chosen) - 1
    wanted = [f"w{j:0{width}d}" for j in (i - 1, i, i + 1)]
    return [n for n in wanted if n in names]


def near_any(
    winner: np.ndarray,
    mask: np.ndarray,
    windings: dict[str, tuple[np.ndarray, np.ndarray]],
) -> dict:
    """Described: per winner node, the nearest of all windings along that winding's normal."""
    import tile_gate

    best = np.full(mask.shape, np.inf)
    for xyz, valid in windings.values():
        d = tile_gate.distance_to(winner, mask, xyz, valid)
        best = np.fmin(best, np.where(np.isfinite(d), d, np.inf))
    total = int(mask.sum())
    d = best[mask]
    return {
        "nodes": total,
        "within_2_of_any_winding": round(float((d <= 2.0).sum()) / total, 4),
        "within_4_of_any_winding": round(float((d <= 4.0).sum()) / total, 4),
    }


def tiles_against_winner(
    sdt: Path,
    chosen: tuple[np.ndarray, np.ndarray],
    winner: np.ndarray,
    mask: np.ndarray,
) -> dict:
    """Described: finding 117's tiles of the chosen raw winding, labelled against the winner's surface."""
    import band_fit_quality as bq
    import tile_gate

    xyz, valid = chosen
    field = bq.DistanceField(sdt, "1")
    readings = tile_gate.node_readings(field, xyz, valid)
    distance = tile_gate.distance_to(xyz, valid, winner, mask)
    found = tile_gate.tiles(readings, distance, valid)
    for t in found:
        t["winding"] = "chosen"
    summary = tile_gate.summarise(found) if found else None
    return {"summary": summary, "tiles": found}


def verdict(score: dict | None) -> str:
    if score is None or score["median"] is None:
        return "DOES_NOT_RUN"
    share = score["fraction_within"][WITHIN]
    if share >= ON_SHARE and score["median"] <= ON_MEDIAN:
        return "ON_THE_WINNERS_SHEET"
    if share >= PARTLY_SHARE:
        return "PARTLY_ON_IT"
    return "OFF_IT"


def choose_cmd(args: argparse.Namespace) -> dict:
    winner, valid = analysis.load_tifxyz(args.winner)
    mask = in_band(winner, valid)
    names = sorted(
        p.name
        for p in Path(args.fit).iterdir()
        if p.is_dir() and analysis.winding_index(p.name) is not None
    )
    windings = {n: analysis.load_tifxyz(Path(args.fit) / n) for n in names}
    scores = {n: analysis.surface_distance(winner, mask, *windings[n]) for n in names}
    chosen = analysis.choose(scores)
    ranked = sorted(
        (s["median"], n) for n, s in scores.items() if s["median"] is not None
    )
    out: dict = {
        "finding": 119,
        "band": [Z_BEGIN, Z_END],
        "winner_nodes_in_band": int(mask.sum()),
        "winner_nodes": int(valid.sum()),
        "windings": len(names),
        "chosen": chosen,
        "chosen_raw": scores[chosen] if chosen else None,
        "three_closest": [{"winding": n, **scores[n]} for _, n in ranked[:3]],
        "described": {"near_any": near_any(winner, mask, windings)},
    }
    if chosen:
        snap = neighbours(chosen, names)
        out["snap_list"] = snap
        Path(args.snap_list).write_text("".join(f"{n}\n" for n in snap))
        if args.sdt:
            out["described"]["tiles"] = tiles_against_winner(
                Path(args.sdt), windings[chosen], winner, mask
            )
    return out


def verdict_cmd(args: argparse.Namespace) -> dict:
    chosen = json.loads(Path(args.chosen).read_text())
    name = chosen["chosen"]
    out: dict = {"finding": 119, "chosen": name}
    if name is None:
        out.update(
            {
                "snapped": None,
                "verdict": "DOES_NOT_RUN",
                "why": "no raw winding covers half the winner's surface",
            }
        )
        return out
    winner, valid = analysis.load_tifxyz(args.winner)
    mask = in_band(winner, valid)
    snapped = {}
    for n in chosen["snap_list"]:
        path = Path(args.snap) / n
        if (path / "x.tif").exists():
            snapped[n] = analysis.surface_distance(
                winner, mask, *analysis.load_tifxyz(path)
            )
    score = snapped.get(name)
    out.update(
        {
            "snapped": score,
            "snapped_neighbours": {n: s for n, s in snapped.items() if n != name},
        }
    )
    out["verdict"] = verdict(score)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("choose")
    c.add_argument("out")
    c.add_argument("winner")
    c.add_argument("fit")
    c.add_argument("snap_list")
    c.add_argument("--sdt")
    v = sub.add_parser("verdict")
    v.add_argument("out")
    v.add_argument("winner")
    v.add_argument("chosen")
    v.add_argument("snap")
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = choose_cmd(args) if args.command == "choose" else verdict_cmd(args)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    summary = {
        k: result.get(k)
        for k in ("chosen", "chosen_raw", "snapped", "verdict")
        if k in result
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
