"""Finding 121: the whole pipeline at the place where PHerc. 211's First Letters prize was won.

Registration: docs/preregistration/2026-11-16_first_letters_0211_end_to_end.md. Our own fit's windings (finding
119), snapped, flattened, rendered and read as a band read would read them, carried onto the winner's surface
and compared with the winning reader's map by finding 118's numbers.

    orient   OUT.json WINNER_TIFXYZ FINAL_TIFXYZ...
             the median normal cosine of each final winding against the winner's surface (finding 110's
             surface_distance, over the winner's nodes in the band); prints "NAME flip" or "NAME keep" per
             winding and exits 1 if any cosine is missing or zero. Decided from the geometry, before any ink.
    compare  OUT.json --winner-mesh DIR --winner-maps DIR --winner-render ZARR --studio TIF --studio-mask PNG
             (--ours MESH MAPS RENDER | --ours-flipped MESH MAPS RENDER)... [--v3-maps DIR] [--image PNG]

The transfer is finding 110's: every 4 x 4 pixel cell of the winner's render takes the ink of the nearest cell
of our windings within 4 voxels (in the scroll), and nothing where none is that close. A winding whose render
samples against the winner's normals stops the comparison. The winner's render, maps and lattice are finding
118's (its alignment: the same raster, shift (0, 0)). Measured once: OUT must not exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps as tm  # noqa: E402
import winner_sheet  # noqa: E402

DEPTH = 1  # registered: the reading side at depth +1, as findings 110, 118 and 120
MIN_CELL_SHARE = (
    f118.MIN_CELL_SHARE
)  # 0.5 of the winner's mask cells must receive our ink
R_AGREES, R_PARTLY, RATIO = f118.R_AGREES, f118.R_PARTLY, f118.RATIO  # 0.30, 0.15, 2
# described: finding 119's parts of the winner's surface (node columns), in 4-pixel cells (5 per node column)
PARTS = {"columns_0_181": (0, 182), "columns_193_300": (193, 301)}
CELLS_PER_NODE = analysis.PX_PER_NODE // analysis.LATTICE
MIN_WINDING_CELLS = (
    1000  # described: r for one winding's cells only where it gave at least this many
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def orientation(winner: Path, finals: list[Path]) -> dict:
    """Per final winding: the median cosine between its normals and the winner's, over the winner's nodes in
    the band that it covers, and whether its render must be flipped to sample along the winner's normals."""
    xyz, valid = analysis.load_tifxyz(winner)
    mask = winner_sheet.in_band(xyz, valid)
    out = {}
    for final in finals:
        score = analysis.surface_distance(xyz, mask, *analysis.load_tifxyz(final))
        cosine = score["normal_cosine_median"]
        decision = None if not cosine else ("flip" if cosine < 0 else "keep")
        out[Path(final).name] = {
            "normal_cosine_median": cosine,
            "covered_fraction": score["covered_fraction"],
            "render": decision,
        }
    return out


def verdict(numbers: dict | None, cell_share: float | None) -> str:
    """Finding 118's table, under this finding's names."""
    names = {
        "READER_AGREES": "E2E_AGREES",
        "READER_PARTLY": "E2E_PARTLY",
        "READER_DISAGREES": "E2E_DISAGREES",
        "DOES_NOT_RUN": "DOES_NOT_RUN",
    }
    if numbers is None:
        return "DOES_NOT_RUN"
    return names[f118.verdict(numbers, cell_share)]


def carry(
    maps: list[dict[str, np.ndarray]], which: np.ndarray, cell: np.ndarray
) -> dict[str, np.ndarray]:
    """Each winding's maps carried onto the winner's lattice by the transfer; NaN where no winding gave ink."""
    out = {}
    for model in maps[0]:
        moved = np.full(which.shape, np.nan)
        for k, per_winding in enumerate(maps):
            take = which == k
            moved[take] = per_winding[model].reshape(-1)[cell[take]]
        out[model] = moved
    return out


def part_mask(shape: tuple[int, int], columns: tuple[int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    mask[:, columns[0] * CELLS_PER_NODE : columns[1] * CELLS_PER_NODE] = True
    return mask


def compare_cmd(args: argparse.Namespace) -> dict:
    import cv2
    import tifffile

    winner = tm.side(
        args.winner_mesh,
        args.winner_maps,
        args.winner_render,
        blind_too=True,
        depth=DEPTH,
    )
    given = [(*item, False) for item in args.ours] + [
        (*item, True) for item in args.ours_flipped
    ]
    ours = []
    for mesh, maps, render, flipped in given:
        side = tm.side(mesh, maps, render, blind_too=True, depth=DEPTH)
        side.update({"flipped": flipped, "render": str(render)})
        if args.v3_maps:
            canvas = (
                side["maps"][analysis.MODELS[0]].shape[0] * analysis.LATTICE,
                side["maps"][analysis.MODELS[0]].shape[1] * analysis.LATTICE,
            )
            reading, other, files = f120.read_v3(
                args.v3_maps, Path(render), canvas, DEPTH
            )
            side.update({"v3": {"reading": reading, "other": other}, "v3_files": files})
        ours.append(side)

    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(o["points"], o["ok"]) for o in ours]
    )
    cosines = [
        analysis.normals_agree(winner["points"], o["points"], which, cell, k)
        for k, o in enumerate(ours)
    ]
    against = [
        ours[k]["mesh"]
        for k, c in enumerate(cosines)
        if c is not None and (-c if ours[k]["flipped"] else c) <= 0
    ]
    result: dict = {
        "finding": 121,
        "depth": DEPTH,
        "winner": {"mesh": str(args.winner_mesh), "maps": winner["files"]},
        "inputs_sha256": {
            "studio": _sha256(args.studio),
            "studio_mask": _sha256(args.studio_mask),
        },
        "ours": [
            {
                "mesh": o["mesh"],
                "render": o["render"],
                "maps": o["files"],
                "render_flipped": o["flipped"],
                "normal_cosine_median": cosines[k],
                "cells_given": int((which == k).sum()),
            }
            for k, o in enumerate(ours)
        ],
    }
    if against:
        result.update(
            {
                "verdict": "DOES_NOT_RUN",
                "why": "a render samples against the winner's normals: "
                + ", ".join(against),
            }
        )
        return result

    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    if studio.shape != winner["ok"].shape or in_mask.shape != winner["ok"].shape:
        raise SystemExit(
            f"lattices differ: winner's render {winner['ok'].shape}, map {studio.shape}, mask {in_mask.shape}"
        )
    reading = carry([o["maps"] for o in ours], which, cell)
    other = carry([o["blind_maps"] for o in ours], which, cell)
    cells = (which >= 0) & winner["ok"] & in_mask & np.isfinite(studio)
    for maps in (reading, other, winner["maps"], winner["blind_maps"]):
        for v in maps.values():
            cells &= np.isfinite(v)
    share = float(cells.sum()) / max(int(in_mask.sum()), 1)
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": int(cells.sum()),
            "cell_share": round(share, 4),
        }
    )
    for k, entry in enumerate(result["ours"]):
        entry["cells_compared"] = int(((which == k) & cells).sum())
    if share < MIN_CELL_SHARE:
        result.update(
            {"registered": None, "verdict": "DOES_NOT_RUN", "why": "too few cells"}
        )
        return result

    theirs = analysis.highpass(studio, cells)
    ink = (studio >= f120.INK) & cells

    def ensemble(maps: dict[str, np.ndarray], where: np.ndarray) -> np.ndarray:
        return analysis.zscore_ensemble(maps, where)

    numbers = f120.score(
        theirs, ink, ensemble(reading, cells), ensemble(other, cells), cells
    )
    result["registered"] = {
        k: numbers[k] for k in ("r", "control_wrong_side", "control_slid")
    }
    result["verdict"] = verdict(result["registered"], share)

    described: dict = {
        "ensemble_overlap": {k: numbers[k] for k in ("overlap", "control_overlap_slid")}
    }
    same_cells = f120.score(
        theirs,
        ink,
        ensemble(winner["maps"], cells),
        ensemble(winner["blind_maps"], cells),
        cells,
    )
    described["finding_118_on_these_cells"] = same_cells
    ours_hp = analysis.highpass(ensemble(reading, cells), cells)
    theirs_geometry = analysis.highpass(ensemble(winner["maps"], cells), cells)
    described["r_with_finding_118_maps"] = f118._rounded(
        analysis.pearson(theirs_geometry[cells], ours_hp[cells])
    )
    q = np.percentile(dist[cells], [50, 95])
    described["transfer_distance_voxels"] = {
        "p50": round(float(q[0]), 2),
        "p95": round(float(q[1]), 2),
    }
    per_winding = {}
    for k, o in enumerate(ours):
        mine = cells & (which == k)
        name = Path(o["mesh"]).name
        per_winding[name] = {
            "cells": int(mine.sum()),
            "r": f118._rounded(analysis.pearson(theirs[mine], ours_hp[mine]))
            if mine.sum() >= MIN_WINDING_CELLS
            else None,
        }
    described["by_winding"] = per_winding
    described["by_part"] = {}
    for label, columns in PARTS.items():
        inside = cells & part_mask(cells.shape, columns)
        described["by_part"][label] = {
            "cells": int(inside.sum()),
            "r": f118._rounded(analysis.pearson(theirs[inside], ours_hp[inside])),
            "r_finding_118_maps": f118._rounded(
                analysis.pearson(theirs[inside], theirs_geometry[inside])
            ),
        }
    panels = [ours_hp]
    if args.v3_maps:
        v3_reading = carry([{"v3": o["v3"]["reading"]} for o in ours], which, cell)[
            "v3"
        ]
        v3_other = carry([{"v3": o["v3"]["other"]} for o in ours], which, cell)["v3"]
        v3_cells = cells & np.isfinite(v3_reading) & np.isfinite(v3_other)
        v3 = f120.score(
            analysis.highpass(studio, v3_cells),
            ink,
            f120.standardise(v3_reading, v3_cells),
            f120.standardise(v3_other, v3_cells),
            v3_cells,
        )
        described["reader_v3"] = {**v3, "cells": int(v3_cells.sum())}
        described["reader_v3_files"] = [o["v3_files"] for o in ours]
        panels.append(
            analysis.highpass(f120.standardise(v3_reading, v3_cells), v3_cells)
        )
    result["described"] = described
    if args.image:
        f120.write_image(args.image, [*panels, theirs], cells)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    o = sub.add_parser("orient")
    o.add_argument("out", type=Path)
    o.add_argument("winner", type=Path)
    o.add_argument("finals", nargs="+", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    c.add_argument("--winner-mesh", required=True, type=Path)
    c.add_argument("--winner-maps", required=True, type=Path)
    c.add_argument("--winner-render", required=True, type=Path)
    c.add_argument("--studio", required=True, type=Path)
    c.add_argument("--studio-mask", required=True, type=Path)
    for flag in ("--ours", "--ours-flipped"):
        c.add_argument(
            flag,
            nargs=3,
            action="append",
            default=[],
            type=Path,
            metavar=("MESH", "MAPS", "RENDER"),
        )
    c.add_argument("--v3-maps", type=Path)
    c.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    if args.command == "orient":
        result = orientation(args.winner, args.finals)
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        for name, entry in result.items():
            print(f"{name} {entry['render']}")
        return 0 if all(e["render"] for e in result.values()) else 1
    if not (args.ours or args.ours_flipped):
        ap.error("give at least one --ours or --ours-flipped")
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
