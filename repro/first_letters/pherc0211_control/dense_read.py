"""Finding 131: does the twice-denser snap read better at the place where PHerc. 211's First Letters prize was won?

Registration: docs/preregistration/2026-11-20_first_letters_0211_dense_read.md.

    compare OUT.json --winner-mesh --winner-maps --winner-render --studio --studio-mask --ours-render-map NPY
            --windings w033 w034 w035 w036
            --arm NAME FINALS RENDERS MAPS   (repeated: f124, rerun, dense2)
            [--sdt SDT_ZARR]

An arm is finding 119's four windings after one route through snap, flatten and render: FINALS/wNNN.tifxyz,
RENDERS/wNNN_66.zarr, and Studio's maps MAPS/wNNN.npy and MAPS/wNNN_reversed.npy. Each arm is carried onto the
winner's surface by finding 110's transfer and scored with finding 124's statistic (studio_e2e.score), as finding
124 scored its windings, on the cells that every arm reaches. Finding 124's own windings and maps are the arm f124;
on its own cells the code must give finding 124's r again.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "eligible_band"))

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import end_to_end as f121  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_e2e as f124  # noqa: E402
import transfer_maps as tm  # noqa: E402

LINE = 0.02  # the smallest change in r called a change, whatever the re-run's noise
F124_R = 0.8247  # finding 124's registered r, which the f124 arm must give again on its own cells
NEAR = 2.0  # voxels from the predicted sheet (band_geometry.py)


def margin(noise: float) -> float:
    """The change in r that counts: at least LINE, and at least twice the re-run's distance from finding 124.
    Computed on the 4-decimal values the record reports, so a change exactly at the margin counts."""
    return round(max(LINE, 2 * abs(round(noise, 4))), 4)


def verdict(
    r_f124: float | None,
    r_rerun: float | None,
    r_dense: float | None,
    share: float | None,
    reproduces: bool,
) -> str:
    if (
        not reproduces
        or share is None
        or share < f118.MIN_CELL_SHARE
        or None in (r_f124, r_rerun, r_dense)
    ):
        return "DOES_NOT_RUN"
    m = margin(r_rerun - r_f124)  # type: ignore[operator]
    change = round(r_dense - r_rerun, 4)  # type: ignore[operator]
    if change >= m:
        return "DENSE_READS_BETTER"
    if change <= -m:
        return "DENSE_READS_WORSE"
    return "DENSE_READS_SAME"


def side(mesh: Path, render: Path) -> dict:
    """A winding's lattice points and the blocks its render covers (finding 110's transfer_maps.side, no ink maps)."""
    xyz, valid = analysis.load_tifxyz(mesh)
    points, ok = analysis.lattice_points(xyz, valid)
    return {
        "points": points,
        "ok": ok & tm.render_valid(render, ok.shape),
        "mesh": str(mesh),
        "canvas": (
            xyz.shape[0] * analysis.PX_PER_NODE,
            xyz.shape[1] * analysis.PX_PER_NODE,
        ),
    }


def carry_arm(
    winner: dict, windings: list[str], finals: Path, renders: Path, maps: Path
) -> dict:
    sides = []
    for w in windings:
        s = side(finals / f"{w}.tifxyz", renders / f"{w}_66.zarr")
        s["studio"] = f124.read_studio(maps / f"{w}.npy", s["canvas"])
        s["studio_reversed"] = f124.read_studio(maps / f"{w}_reversed.npy", s["canvas"])
        sides.append(s)
    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(s["points"], s["ok"]) for s in sides]
    )
    return {
        "which": which,
        "dist": dist,
        "cosines": [
            analysis.normals_agree(winner["points"], one["points"], which, cell, k)
            for k, one in enumerate(sides)
        ],
        "carried": f121.carry([{"s": s["studio"]} for s in sides], which, cell)["s"],
        "other": f121.carry([{"s": s["studio_reversed"]} for s in sides], which, cell)[
            "s"
        ],
        "meshes": [s["mesh"] for s in sides],
    }


def arm_cells(arm: dict) -> np.ndarray:
    return (arm["which"] >= 0) & np.isfinite(arm["carried"]) & np.isfinite(arm["other"])


def scored(studio: np.ndarray, arm: dict, cells: np.ndarray) -> dict:
    theirs = analysis.highpass(studio, cells)
    ink = (studio >= f120.INK) & cells
    numbers = f124.score(theirs, ink, arm["carried"], cells, arm["other"])
    return {"cells": int(cells.sum()), **numbers}


def sheet_share(sdt: Path | None, finals: Path, windings: list[str]) -> dict | None:
    """Described: the share of each final winding's nodes within 2 voxels of the predicted sheet (band_geometry.py)."""
    if sdt is None:
        return None
    import band_fit_quality as quality

    field = quality.DistanceField(sdt, "1")
    out = {}
    for w in windings:
        xyz, valid = analysis.load_tifxyz(finals / f"{w}.tifxyz")
        d = field.at(xyz[valid].astype(np.float64))
        ok = np.isfinite(d)
        out[w] = round(float((d[ok] <= NEAR).mean()), 4) if ok.any() else None
    return out


def compare_cmd(args: argparse.Namespace) -> dict:
    import cv2
    import tifffile

    winner = tm.side(
        args.winner_mesh,
        args.winner_maps,
        args.winner_render,
        blind_too=False,
        depth=f121.DEPTH,
    )
    canvas_w = (
        winner["ok"].shape[0] * analysis.LATTICE,
        winner["ok"].shape[1] * analysis.LATTICE,
    )
    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    own_render = f124.read_studio(args.ours_render_map, canvas_w)
    base = winner["ok"] & in_mask & np.isfinite(studio) & np.isfinite(own_render)

    arms = {
        name: carry_arm(winner, args.windings, Path(finals), Path(renders), Path(maps))
        for name, finals, renders, maps in args.arm
    }
    result: dict = {
        "finding": 131,
        "windings": args.windings,
        "arms": {
            name: {"meshes": a["meshes"], "normal_cosine_median": a["cosines"]}
            for name, a in arms.items()
        },
    }
    if any(
        c is not None and c >= 0 for a in arms.values() for c in a["cosines"]
    ):  # as finding 124
        result.update(
            {
                "verdict": "DOES_NOT_RUN",
                "why": "a render samples against the winner's normals",
            }
        )
        return result
    common = base.copy()
    for a in arms.values():
        common &= arm_cells(a)
    share = float(common.sum()) / max(int(in_mask.sum()), 1)
    own = {name: scored(studio, a, base & arm_cells(a)) for name, a in arms.items()}
    reproduces = own.get("f124", {}).get("r") == F124_R
    result.update({"mask_cells": int(in_mask.sum()), "cells": int(common.sum()), "cell_share": round(share, 4),
                   "f124_reproduced_on_its_own_cells": reproduces})  # fmt: skip
    registered = {name: scored(studio, a, common) for name, a in arms.items()}
    r = {name: registered[name]["r"] for name in registered}
    result["registered"] = {
        "r": r,
        "noise_rerun_minus_f124": round(r["rerun"] - r["f124"], 4),
        "margin": margin(r["rerun"] - r["f124"]),
        "change_dense2_minus_rerun": round(r["dense2"] - r["rerun"], 4),
    }
    result["verdict"] = verdict(r["f124"], r["rerun"], r["dense2"], share, reproduces)
    result["described"] = {
        "each_arm_on_the_common_cells": registered,
        "each_arm_on_its_own_cells": own,
        "transfer_distance_voxels": {
            name: dict(
                zip(
                    ("p50", "p95"),
                    (
                        round(float(q), 2)
                        for q in np.percentile(a["dist"][common], [50, 95])
                    ),
                    strict=True,
                )
            )
            for name, a in arms.items()
        },  # fmt: skip
        "final_nodes_within_2_of_the_predicted_sheet": {
            name: sheet_share(args.sdt, Path(finals), args.windings)
            for name, finals, _, _ in args.arm
        },
    }
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        c.add_argument(flag, required=True, type=Path)
    c.add_argument("--windings", nargs="+", required=True)
    c.add_argument(
        "--arm",
        nargs=4,
        action="append",
        required=True,
        metavar=("NAME", "FINALS", "RENDERS", "MAPS"),
    )
    c.add_argument("--sdt", type=Path)
    args = ap.parse_args(argv)
    names = [a[0] for a in args.arm]
    if sorted(names) != ["dense2", "f124", "rerun"]:
        raise SystemExit(f"the arms are f124, rerun and dense2, not {names}")
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = compare_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "described"}, indent=1))
    return 0 if result["verdict"] != "DOES_NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
