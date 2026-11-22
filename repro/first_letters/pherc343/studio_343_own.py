"""Finding 136: does Studio draw PHerc. 343's letters on our own fit of the place, as on the recipe's published surface?

Registration: docs/preregistration/2026-11-22_studio_343_own_windings.md.

    compare  OUT.json --published-mesh DIR --published-render ZARR --published-studio NPY --published-studio-reversed NPY
             --sidecar JSON --ink-png PNG
             --ours MESH RENDER STUDIO_NPY STUDIO_REVERSED_NPY   (once per winding: finding 110's w047 and w048)
             [--image PNG]

Studio's map of each of our windings (layers 41 down to 26 of its 66-layer render, the winner's command) is carried
onto the recipe's published surface by finding 110's transfer: each 4 x 4 cell of the published surface takes the
nearest cell of our windings within 4 voxels. The cells are those of the published image's area (the sidecar's
raw-frame area) that the published render covers in all 66 layers and that receive a value. The registered number is
finding 124's r between the carried map and Studio's map of the published surface (finding 127's), both with the
broad background taken off; the controls are the carried map of our reversed planes and the carried map slid 64
pixels. Before anything is scored, finding 127's own number (Studio on the published surface against `u`) must come
out again. Against `u`, the recipe's ensemble image, both maps are described on the same reading-frame cells.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "pherc0211_control"))

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import dense_read as f131  # noqa: E402
import end_to_end as f121  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_343 as f127  # noqa: E402
import studio_e2e as f124  # noqa: E402

CLOSE, PARTLY = 0.70, 0.40  # finding 124's lines
RATIO = 2.0  # r at least twice the absolute value of each control
MIN_CELL_SHARE = 0.5  # of the area's cells the published render covers
F127_R = 0.6238  # finding 127's registered r: Studio on the published surface against u


def area_cells(shape: tuple[int, int], sidecar: dict) -> np.ndarray:
    """Lattice cells of the published render lying wholly inside the sidecar's raw-frame area (exclusive ends)."""
    a = sidecar["area"]["raw_render_px"]
    lat = analysis.LATTICE
    rows = np.arange(shape[0])
    cols = np.arange(shape[1])
    in_r = (rows * lat >= a["row0"]) & ((rows + 1) * lat <= a["row1"])
    in_c = (cols * lat >= a["col0"]) & ((cols + 1) * lat <= a["col1"])
    return in_r[:, None] & in_c[None, :]


def verdict(
    numbers: dict | None,
    share: float | None,
    reproduces: bool,
    cosines: list[float | None] | None,
) -> str:
    """Finding 124's table, with finding 127's reproduction and the normals' direction as failure branches."""
    if (
        not reproduces
        or numbers is None
        or share is None
        or share < MIN_CELL_SHARE
        or not cosines
        or any(c is None or c <= 0 for c in cosines)
    ):
        return "DOES_NOT_RUN"
    r = numbers.get("r")
    wrong = numbers.get("control_wrong_side")
    slid = (numbers.get("control_slid") or {}).get("largest_absolute")
    if r is None or wrong is None or slid is None:
        return "DOES_NOT_RUN"
    clear = all(r >= RATIO * abs(c) for c in (wrong, slid))
    if r >= CLOSE and clear:
        return "STUDIO_343_OWN_CLOSE"
    if r >= PARTLY and clear:
        return "STUDIO_343_OWN_PARTLY"
    return "STUDIO_343_OWN_FAR"


def lattice_to_raw(values: np.ndarray, raw_shape: tuple[int, int]) -> np.ndarray:
    """A lattice map as render pixels (each cell's value on its 4 x 4 pixels; NaN where no cell)."""
    lat = analysis.LATTICE
    out = np.full(raw_shape, np.nan)
    h, w = values.shape
    out[: h * lat, : w * lat] = np.repeat(np.repeat(values, lat, axis=0), lat, axis=1)
    return out


def reading_frame(args: argparse.Namespace, raw_shape: tuple[int, int]) -> dict:
    """Finding 127's reading frame: the area's valid pixels, u, and its cells (all 66 layers above 0)."""
    import cv2
    import zarr

    level0 = zarr.open(str(args.published_render), mode="r")["0"]
    if level0.shape[0] != 66 or tuple(level0.shape[1:]) != raw_shape:
        raise SystemExit(
            f"{args.published_render} is {level0.shape}, not 66 layers of {raw_shape}"
        )
    valid_raw = np.ones(raw_shape, dtype=bool)
    for k in range(66):
        valid_raw &= np.asarray(level0[k]) > 0
    sidecar = json.loads(args.sidecar.read_text())
    valid = f127.to_reading(valid_raw, sidecar)
    ink_png = cv2.imread(str(args.ink_png), cv2.IMREAD_GRAYSCALE)
    if ink_png is None:
        raise SystemExit(f"cannot read {args.ink_png}")
    u = ink_png.astype(np.float64) / 255.0
    if u.shape != valid.shape:
        raise SystemExit(f"{args.ink_png} is {u.shape}, the area {valid.shape}")
    cells = analysis.block_mean(valid.astype(np.float64)) == 1.0
    reference = analysis.block_mean(u)
    return {
        "sidecar": sidecar,
        "valid": valid,
        "u": u,
        "cells": cells,
        "reference": reference,
    }


def compare(args: argparse.Namespace) -> dict:
    published = f131.side(args.published_mesh, args.published_render)
    canvas = published["canvas"]
    theirs_raw = f124.read_studio(args.published_studio, canvas)
    theirs_rev = f124.read_studio(args.published_studio_reversed, canvas)
    frame = reading_frame(args, canvas)
    sidecar = frame["sidecar"]

    # finding 127's own number first: Studio on the published surface against u, on its cells
    to_r = {k: np.load(p, allow_pickle=False).astype(np.float64)
            for k, p in (("forward", args.published_studio), ("reversed", args.published_studio_reversed))}  # fmt: skip
    theirs_u = analysis.highpass(frame["reference"], frame["cells"])
    drawn = (frame["reference"] >= f127.DRAWN) & frame["cells"]
    f127_numbers = f124.score(
        theirs_u,
        drawn,
        analysis.block_mean(f127.to_reading(to_r["forward"], sidecar)),
        frame["cells"],
        analysis.block_mean(f127.to_reading(to_r["reversed"], sidecar)),
    )
    reproduces = f127_numbers["r"] == F127_R

    area = area_cells(published["ok"].shape, sidecar)
    target = published["ok"] & area & np.isfinite(theirs_raw)
    sides = []
    for mesh, render, studio, studio_reversed in args.ours:
        s = f131.side(mesh, render)
        s["studio"] = f124.read_studio(studio, s["canvas"])
        s["studio_reversed"] = f124.read_studio(studio_reversed, s["canvas"])
        sides.append(s)
    which, cell, dist = analysis.transfer(
        published["points"], target, [(s["points"], s["ok"]) for s in sides]
    )
    cosines = [
        analysis.normals_agree(published["points"], s["points"], which, cell, k)
        for k, s in enumerate(sides)
    ]
    carried = f121.carry([{"s": s["studio"]} for s in sides], which, cell)["s"]
    other = f121.carry([{"s": s["studio_reversed"]} for s in sides], which, cell)["s"]
    cells = target & (which >= 0) & np.isfinite(carried) & np.isfinite(other)
    share = round(float(cells.sum()) / max(int(target.sum()), 1), 4)
    result: dict = {
        "finding": 136,
        "layers": list(f124.LAYERS),
        "ours": [
            {
                "mesh": s["mesh"],
                "cells_given": int((which == k).sum()),
                "normal_cosine_median": cosines[k],
            }
            for k, s in enumerate(sides)
        ],  # fmt: skip
        "area_cells_covered_by_the_published_render": int(target.sum()),
        "cells": int(cells.sum()),
        "cell_share": share,
        "f127_r_again": f127_numbers["r"],
        "f127_reproduced": reproduces,
    }
    if (
        not reproduces
        or share < MIN_CELL_SHARE
        or any(c is None or c <= 0 for c in cosines)
    ):
        result.update({"registered": None, "verdict": "DOES_NOT_RUN"})
        return result
    theirs = analysis.highpass(theirs_raw, cells)
    ink = (theirs_raw >= f120.INK) & cells
    numbers = f124.score(theirs, ink, carried, cells, other)
    result["registered"] = {
        k: numbers[k] for k in ("r", "control_wrong_side", "control_slid")
    }
    result["verdict"] = verdict(result["registered"], share, reproduces, cosines)

    # described: each winding, the transfer, the published surface's reversed planes, and both maps against u
    hp = analysis.highpass(f120.standardise(carried, cells), cells)
    per_winding = {}
    for k, s in enumerate(sides):
        mine = cells & (which == k)
        enough = mine.sum() >= f121.MIN_WINDING_CELLS
        per_winding[Path(s["mesh"]).name.removesuffix(".tifxyz")] = {
            "cells": int(mine.sum()),
            "r": f118._rounded(analysis.pearson(theirs[mine], hp[mine]))
            if enough
            else None,
        }
    q = np.percentile(dist[cells], [50, 95])
    carried_px = f127.to_reading(lattice_to_raw(carried, canvas), sidecar)
    other_px = f127.to_reading(lattice_to_raw(other, canvas), sidecar)
    ours_u_cells = frame["cells"] & np.isfinite(analysis.block_mean(carried_px)) & np.isfinite(
        analysis.block_mean(other_px))  # fmt: skip
    theirs_u2 = analysis.highpass(frame["reference"], ours_u_cells)
    drawn2 = (frame["reference"] >= f127.DRAWN) & ours_u_cells
    pub_forward = analysis.block_mean(f127.to_reading(to_r["forward"], sidecar))
    pub_reversed = analysis.block_mean(f127.to_reading(to_r["reversed"], sidecar))
    result["described"] = {
        "carried": numbers,
        "by_winding": per_winding,
        "transfer_distance_voxels": {
            "p50": round(float(q[0]), 2),
            "p95": round(float(q[1]), 2),
        },
        "published_surface_reversed_planes_against_its_forward": f118._rounded(
            analysis.pearson(
                theirs[cells],
                analysis.highpass(f120.standardise(theirs_rev, cells), cells)[cells],
            )
        ),
        "against_u": {
            "cells": int(ours_u_cells.sum()),
            "ours_carried": f124.score(
                theirs_u2,
                drawn2,
                analysis.block_mean(carried_px),
                ours_u_cells,
                analysis.block_mean(other_px),
            ),
            "published_surface": f124.score(
                theirs_u2, drawn2, pub_forward, ours_u_cells, pub_reversed
            ),
        },  # fmt: skip
        "f127_numbers_again": f127_numbers,
    }
    if args.image:
        valid = frame["valid"] & np.isfinite(carried_px)
        f127.write_image(args.image, [np.nan_to_num(carried_px), f127.to_reading(to_r["forward"], sidecar),
                                      frame["u"]], valid)  # fmt: skip
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    for flag in ("--published-mesh", "--published-render", "--published-studio", "--published-studio-reversed",
                 "--sidecar", "--ink-png"):  # fmt: skip
        c.add_argument(flag, required=True, type=Path)
    c.add_argument("--ours", nargs=4, action="append", required=True, type=Path,
                   metavar=("MESH", "RENDER", "STUDIO", "STUDIO_REVERSED"))  # fmt: skip
    c.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is written once", file=sys.stderr)
        return 2
    result = compare(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "described"}, indent=1))
    return 0 if result["verdict"] != "DOES_NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
