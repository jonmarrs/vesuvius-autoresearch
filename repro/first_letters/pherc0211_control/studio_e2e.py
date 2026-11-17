"""Finding 124: Studio reading our own geometry at the place where PHerc. 211's First Letters prize was won.

Registration: docs/preregistration/2026-11-16_first_letters_0211_studio_e2e.md.

    planes   RENDER_ZARR OUT.npy [--reverse]
             Studio's 16-plane input from one of our 66-layer renders: layers LAYERS (41 down to 26), uint8
             [16, H, W]. The order was matched to the winner's own Studio input by CT correlation on finding 118's
             render of the winner's surface (plane i against our layer 41 - i, r about 0.95 each). --reverse gives
             the same planes in the opposite order (26 up to 41): the other-side control.
    compare  OUT.json --winner-mesh --winner-maps --winner-render --studio --studio-mask
             --ours-render-map NPY (Studio on finding 118's render of the winner's surface)
             --ours-flipped MESH MAPS RENDER NPY NPY_REVERSED ... (finding 121's windings, Studio's map of each
             and its map of the reversed planes)
             [--image PNG]

The registered numbers are finding 118's, for our own windings' Studio maps carried onto the winner's surface by
finding 110's transfer (end_to_end.py's): r against the winner's map with the broad background taken off; the
controls are Studio's map of the same planes in reversed order (the other side, as findings 118 and 121), carried
the same way, and the map slid 64 pixels in four directions.
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

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import end_to_end as f121  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps as tm  # noqa: E402

LAYERS = tuple(range(41, 25, -1))  # Studio plane i <- our render layer 41 - i
CLOSE, PARTLY, RATIO = 0.70, 0.40, 2.0


def planes_cmd(render: Path, out: Path, reverse: bool = False) -> dict:
    import zarr

    level0 = zarr.open(str(render), mode="r")["0"]
    if level0.shape[0] != 66:
        raise SystemExit(f"{render} has {level0.shape[0]} layers, not 66")
    layers = LAYERS[::-1] if reverse else LAYERS
    stack = np.stack([np.asarray(level0[k]) for k in layers])
    if stack.dtype != np.uint8:
        raise SystemExit(f"{render} is {stack.dtype}, not 8-bit")
    np.save(out, stack, allow_pickle=False)
    return {"render": str(render), "layers": list(layers), "shape": list(stack.shape)}


def read_studio(path: Path, canvas: tuple[int, int]) -> np.ndarray:
    """A Studio probability map (float32 [H, W], inference.py's .npy) as block means on the 4-pixel lattice."""
    values = np.load(path, allow_pickle=False).astype(np.float64)
    if values.shape != canvas:
        raise SystemExit(f"{path} is {values.shape}, the render is {canvas}")
    return analysis.block_mean(values)


def score(
    theirs: np.ndarray,
    ink: np.ndarray,
    ours: np.ndarray,
    cells: np.ndarray,
    other: np.ndarray | None = None,
) -> dict:
    """finding 118's r, other side and slid control, and finding 120's overlap, for one map."""
    hp = analysis.highpass(f120.standardise(ours, cells), cells)
    slid = analysis.slid_control(theirs, hp, cells, cells)
    slid_ov = f120.slid_overlap(ink, hp, cells, analysis.SHIFT_CELLS)
    wrong = None
    if other is not None:
        wrong = f118._rounded(
            analysis.pearson(
                theirs[cells],
                analysis.highpass(f120.standardise(other, cells), cells)[cells],
            )
        )
    return {
        "r": f118._rounded(analysis.pearson(theirs[cells], hp[cells])),
        "control_wrong_side": wrong,
        "r_with_background": f118._rounded(
            analysis.pearson(ours[cells], theirs[cells])
        ),
        "control_slid": {k: f118._rounded(v) for k, v in slid.items()},
        "overlap": f118._rounded(f120.overlap(ink, hp, cells)),
        "control_overlap_slid": {k: f118._rounded(v) for k, v in slid_ov.items()},
    }


def verdict(numbers: dict | None, cell_share: float | None) -> str:
    if numbers is None or cell_share is None or cell_share < f118.MIN_CELL_SHARE:
        return "DOES_NOT_RUN"
    r, slid, wrong = (
        numbers["r"],
        numbers["control_slid"]["largest_absolute"],
        numbers["control_wrong_side"],
    )
    if r is None or slid is None or wrong is None:
        return "DOES_NOT_RUN"
    clear = r >= RATIO * abs(slid) and r >= RATIO * abs(wrong)
    if clear and r >= CLOSE:
        return "STUDIO_E2E_CLOSE"
    if clear and r >= PARTLY:
        return "STUDIO_E2E_PARTLY"
    return "STUDIO_E2E_FAR"


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
    ours = []
    for mesh, maps, render, studio_map, reversed_map in args.ours_flipped:
        side = tm.side(mesh, maps, render, blind_too=False, depth=f121.DEPTH)
        canvas = (
            side["ok"].shape[0] * analysis.LATTICE,
            side["ok"].shape[1] * analysis.LATTICE,
        )
        side.update(
            {
                "studio": read_studio(studio_map, canvas),
                "studio_reversed": read_studio(reversed_map, canvas),
                "studio_file": str(studio_map),
            }
        )
        ours.append(side)
    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(o["points"], o["ok"]) for o in ours]
    )
    cosines = [
        analysis.normals_agree(winner["points"], o["points"], which, cell, k)
        for k, o in enumerate(ours)
    ]
    result: dict = {
        "finding": 124,
        "layers": list(LAYERS),
        "ours": [
            {
                "mesh": o["mesh"],
                "studio_map": o["studio_file"],
                "normal_cosine_median": cosines[k],
                "cells_given": int((which == k).sum()),
            }
            for k, o in enumerate(ours)
        ],  # fmt: skip
    }
    if any(
        c is not None and -c <= 0 for c in cosines
    ):  # every winding was rendered flipped (finding 121)
        result.update(
            {
                "verdict": "DOES_NOT_RUN",
                "why": "a render samples against the winner's normals",
            }
        )
        return result

    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    carried = f121.carry([{"studio": o["studio"]} for o in ours], which, cell)["studio"]
    carried_other = f121.carry(
        [{"studio": o["studio_reversed"]} for o in ours], which, cell
    )["studio"]
    own_render = read_studio(args.ours_render_map, canvas_w)
    cells = (
        (which >= 0)
        & winner["ok"]
        & in_mask
        & np.isfinite(studio)
        & np.isfinite(own_render)
    )
    cells &= np.isfinite(carried) & np.isfinite(carried_other)
    share = float(cells.sum()) / max(int(in_mask.sum()), 1)
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": int(cells.sum()),
            "cell_share": round(share, 4),
        }
    )
    if share < f118.MIN_CELL_SHARE:
        result.update(
            {"registered": None, "verdict": "DOES_NOT_RUN", "why": "too few cells"}
        )
        return result
    theirs = analysis.highpass(studio, cells)
    ink = (studio >= f120.INK) & cells
    numbers = score(theirs, ink, carried, cells, carried_other)
    result["registered"] = {
        k: numbers[k] for k in ("r", "control_wrong_side", "control_slid")
    }
    result["verdict"] = verdict(result["registered"], share)
    own = score(theirs, ink, own_render, cells)
    carried_hp = analysis.highpass(f120.standardise(carried, cells), cells)
    own_hp = analysis.highpass(f120.standardise(own_render, cells), cells)
    per_winding = {}
    for k, o in enumerate(ours):
        mine = cells & (which == k)
        per_winding[Path(o["mesh"]).name] = {
            "cells": int(mine.sum()),
            "r": f118._rounded(analysis.pearson(theirs[mine], carried_hp[mine]))
            if mine.sum() >= f121.MIN_WINDING_CELLS
            else None,
        }
    by_part = {}
    for label, columns in f121.PARTS.items():
        inside = cells & f121.part_mask(cells.shape, columns)
        by_part[label] = {
            "cells": int(inside.sum()),
            "r": f118._rounded(analysis.pearson(theirs[inside], carried_hp[inside])),
        }
    q = np.percentile(dist[cells], [50, 95])
    result["described"] = {
        "whole_pipeline": numbers,
        "our_render_of_the_winners_surface": own,
        "r_whole_pipeline_with_our_render": f118._rounded(
            analysis.pearson(carried_hp[cells], own_hp[cells])
        ),
        "by_winding": per_winding,
        "by_part": by_part,
        "transfer_distance_voxels": {
            "p50": round(float(q[0]), 2),
            "p95": round(float(q[1]), 2),
        },
    }
    if args.image:
        f120.write_image(args.image, [carried_hp, own_hp, theirs], cells)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("planes")
    p.add_argument("render", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--reverse", action="store_true")
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
    c.add_argument(
        "--ours-flipped",
        nargs=5,
        action="append",
        required=True,
        type=Path,
        metavar=("MESH", "MAPS", "RENDER", "NPY", "NPY_REVERSED"),
    )
    c.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is written once", file=sys.stderr)
        return 2
    if args.command == "planes":
        print(json.dumps(planes_cmd(args.render, args.out, args.reverse)))
        return 0
    result = compare_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {k: result.get(k) for k in ("cell_share", "registered", "verdict")},
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
