"""Finding 110, P3: carry the ink maps of our windings into the frame of the published segment and compare.

Usage:
    transfer_maps.py OUT.json --published-mesh DIR --published-maps DIR --published-render ZARR \
        --letter-boxes JSON --ours MESH_DIR MAPS_DIR RENDER_ZARR [--ours ...] \
        [--ours-flipped MESH_DIR MAPS_DIR RENDER_ZARR ...]

Every 4 x 4 block of render pixels of the published segment gets a scroll position from its mesh. The
nearest block centre of our windings within 4 voxels gives it our ink; a block with nothing that close
gets none. Both sides use the same four models at depth +1 on the reading side (the `_reverse` maps), the
same value scaling as the recipe's ensemble_maps.py, and one ensemble: the mean of the four per-model
z-scores over the blocks that are compared, with its broad background taken off. Blocks where either
render has an empty CT layer are left out. The published segment's blind-side maps (the same files
without `_reverse`) are read for the wrong-side control.

The depth and the reading side only mean the same thing on both renders if both sample along normals
that point the same way. This script measures that from the meshes and stops if they do not; it never
picks a side by looking at the ink. A winding whose normals point against the published ones is rendered
with the renderer's --flip-normals and passed as --ours-flipped: it must then measure as opposite, and a
winding passed that way whose normals agree is refused just the same.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mesh_step_analysis as analysis  # noqa: E402

DEPTH = 1  # the depth the published image shows


def map_file(
    maps: Path,
    render_name: str,
    model: str,
    reading_side: bool = True,
    depth: int = DEPTH,
) -> Path:
    """The recipe's map name for `model` at `depth` (run_ink.sh: villa layers s..s+16 with s = depth + 25,
    Hecate centred on layer 32.5 + depth)."""
    side_tag = "_reverse" if reading_side else ""
    if model == "hecate":
        return maps / f"{render_name}__hecate__L66zc{32.5 + depth:.2f}{side_tag}.png"
    return maps / f"{render_name}__{model}__L66s{depth + 25}{side_tag}.tif"


def read_map(path: Path, model: str, canvas_hw: tuple[int, int]) -> np.ndarray:
    """One model's map on the render grid, scaled as in the recipe's ensemble_maps.py."""
    import cv2

    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None or raw.ndim != 2 or raw.dtype != np.uint8:
        raise SystemExit(f"cannot read {path} as an 8-bit grey map")
    if model == "hecate":
        values = raw.astype(np.float32) / 255.0
        if values.shape != canvas_hw:
            values = cv2.resize(
                values, (canvas_hw[1], canvas_hw[0]), interpolation=cv2.INTER_LINEAR
            )
    else:
        if raw.shape != canvas_hw:
            raise SystemExit(f"{path} is {raw.shape}, the render is {canvas_hw}")
        values = np.clip((raw.astype(np.float32) - 64.0) / 128.0, 0.0, 1.0)
    return analysis.block_mean(values)


def render_valid(render: Path, lattice_hw: tuple[int, int]) -> np.ndarray:
    """Blocks whose CT is above zero in all 66 layers, from the render's own 4x level (a block mean)."""
    import zarr

    level = zarr.open(str(render), mode="r")["2"]
    if level.shape[1:] != lattice_hw:
        raise SystemExit(
            f"{render} level 2 is {level.shape[1:]}, the lattice is {lattice_hw}"
        )
    return np.asarray(level[:]).min(axis=0) > 0


def side(
    mesh: Path, maps: Path, render: Path, blind_too: bool = False, depth: int = DEPTH
) -> dict:
    xyz, valid = analysis.load_tifxyz(mesh)
    points, ok = analysis.lattice_points(xyz, valid)
    canvas = (
        xyz.shape[0] * analysis.PX_PER_NODE,
        xyz.shape[1] * analysis.PX_PER_NODE,
    )
    name = render.name.removesuffix(".zarr")
    files = {
        model: map_file(maps, name, model, depth=depth) for model in analysis.MODELS
    }
    out = {
        "points": points,
        "ok": ok & render_valid(render, ok.shape),
        "maps": {model: read_map(files[model], model, canvas) for model in files},
        "files": {model: str(path) for model, path in files.items()},
        "mesh": str(mesh),
    }
    if blind_too:
        out["blind_maps"] = {
            model: read_map(map_file(maps, name, model, False), model, canvas)
            for model in analysis.MODELS
        }
    return out


def letter_mask(boxes: list[dict], shape: tuple[int, int]) -> tuple[np.ndarray, list]:
    mask = np.zeros(shape, dtype=bool)
    slices = []
    for letter in boxes:
        x0, y0, x1, y1 = (v / analysis.LATTICE for v in letter["box"])
        window = (
            slice(max(int(np.floor(y0)), 0), min(int(np.ceil(y1)), shape[0])),
            slice(max(int(np.floor(x0)), 0), min(int(np.ceil(x1)), shape[1])),
        )
        mask[window] = True
        slices.append((letter["id"], window))
    return mask, slices


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out")
    parser.add_argument("--published-mesh", required=True, type=Path)
    parser.add_argument("--published-maps", required=True, type=Path)
    parser.add_argument("--published-render", required=True, type=Path)
    parser.add_argument("--letter-boxes", required=True, type=Path)
    parser.add_argument(
        "--ours",
        nargs=3,
        action="append",
        default=[],
        type=Path,
        metavar=("MESH", "MAPS", "RENDER"),
    )
    parser.add_argument(
        "--ours-flipped",
        nargs=3,
        action="append",
        default=[],
        type=Path,
        metavar=("MESH", "MAPS", "RENDER"),
        help="a winding whose render was made with --flip-normals",
    )
    parser.add_argument(
        "--ours-depth",
        type=int,
        default=DEPTH,
        help="depth of OUR maps; anything but +1 is a reference measurement, never the registered one",
    )
    args = parser.parse_args(argv)

    published = side(
        args.published_mesh, args.published_maps, args.published_render, blind_too=True
    )
    given = [(*item, False) for item in args.ours] + [
        (*item, True) for item in args.ours_flipped
    ]
    if not given:
        parser.error("give at least one --ours or --ours-flipped")
    ours = [
        {**side(mesh, maps, render, depth=args.ours_depth), "flipped": flipped}
        for mesh, maps, render, flipped in given
    ]
    which, cell, dist = analysis.transfer(
        published["points"], published["ok"], [(o["points"], o["ok"]) for o in ours]
    )
    accepted = which >= 0
    cosines = [
        analysis.normals_agree(published["points"], o["points"], which, cell, k)
        for k, o in enumerate(ours)
    ]
    opposite = [
        ours[k]["mesh"]
        for k, c in enumerate(cosines)
        if c is not None and (-c if ours[k]["flipped"] else c) <= 0
    ]
    if opposite:
        raise SystemExit(
            "the render does not sample along the published normals on "
            + ", ".join(opposite)
            + ": depth +1 and the reading side are not the same thing there. Render with the normals "
            "the other way, as the registration says; do not choose a side from the ink."
        )

    transferred = {}
    for model in analysis.MODELS:
        moved = np.zeros(accepted.shape, dtype=np.float64)
        for k, o in enumerate(ours):
            mask = which == k
            moved[mask] = o["maps"][model].reshape(-1)[cell[mask]]
        transferred[model] = moved

    boxes = json.loads(args.letter_boxes.read_text())["letters"]
    letters, windows = letter_mask(boxes, accepted.shape)
    result = analysis.agreement(
        published["maps"], published["blind_maps"], transferred, accepted, letters
    )
    result["published"] = {"mesh": published["mesh"], "maps": published["files"]}
    result["ours"] = [
        {
            "mesh": o["mesh"],
            "maps": o["files"],
            "cells_given": int((which == k).sum()),
            "normal_cosine_median": cosines[k],
            "render_flipped": o["flipped"],
        }
        for k, o in enumerate(ours)
    ]
    result["ours_depth"] = args.ours_depth
    result["registered_comparison"] = args.ours_depth == DEPTH
    result["published_cells"] = int(published["ok"].sum())
    result["accepted_fraction_of_published"] = round(
        float(accepted.sum()) / max(int(published["ok"].sum()), 1), 4
    )
    if accepted.any():
        q = np.percentile(dist[accepted], [50, 95])
        result["transfer_distance_voxels"] = {
            "p50": round(float(q[0]), 2),
            "p95": round(float(q[1]), 2),
        }
    if result["evaluable"]:
        theirs = analysis.highpass(
            analysis.zscore_ensemble(published["maps"], accepted), accepted
        )
        mine = analysis.highpass(
            analysis.zscore_ensemble(transferred, accepted), accepted
        )
        per_box = []
        for letter_id, window in windows:
            inside = np.zeros(accepted.shape, dtype=bool)
            inside[window] = True
            inside &= accepted
            r = analysis.pearson(theirs[inside], mine[inside])
            per_box.append(
                {
                    "id": letter_id,
                    "cells": int(inside.sum()),
                    "r": None if r is None else round(r, 4),
                }
            )
        result["letter_boxes"] = per_box
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("r", "control_wrong_side", "control_slid", "p3", "evaluable")
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
