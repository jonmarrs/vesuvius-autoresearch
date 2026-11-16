"""Does our reader see, on the winning PHerc. 211 surface, the ink that the winning reader saw?

Finding 118 (registration: docs/preregistration/2026-11-16_first_letters_0211_reader_control.md). Both maps are
on one raster: our render of the winner's surface and the winner's probability map are both 1740 x 6020 pixels,
20 pixels to a node of the same mesh. This script checks that by the CT before it compares any ink:

    alignment  the layer of our render that best matches the winner's CT image, and the shift between them
    cells      4 x 4 pixel blocks inside the winner's mask, on our mesh lattice, with CT in all 66 layers
    ours       the PHerc. 343 recipe's four-model ensemble at depth +1 on the reading side (`_reverse`), as
               finding 110 builds it; its broad background taken off
    theirs     the winner's probability map, block means, its background taken off the same way
    r          Pearson over the cells; controls: our other side against theirs, and ours slid by 64 pixels

usage: compare.py OUT.json --mesh DIR --maps DIR --render ZARR --studio TIF --studio-mask PNG --winner-ct TIF
                  [--image PNG]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps as tm  # noqa: E402

DEPTH = 1  # the registered depth: PHerc. 343's published image
DEPTHS = tuple(range(-3, 3))  # described
ALIGN_LAYERS = tuple(
    range(25, 42)
)  # render layers searched for the winner's CT image (33 is the mesh)
ALIGN_SEARCH = 16  # pixels each way
ALIGN_TOLERANCE = 1  # pixels: within this the rasters are the same
MIN_CELL_SHARE = 0.5  # of the winner's mask cells
R_AGREES, R_PARTLY, RATIO = 0.30, 0.15, 2.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def standardised(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = image[mask].astype(np.float64)
    sd = float(values.std())
    if sd == 0:
        raise ValueError("constant image")
    return np.where(mask, (image - values.mean()) / sd, 0.0)


def best_shift(
    reference: np.ndarray, moving: np.ndarray, mask: np.ndarray, search: int
) -> tuple[int, int, float]:
    """The shift (rows, columns) to apply to `moving` that best matches `reference` over `mask`, within
    +-search pixels, by cross-correlation of the standardised images; and the Pearson r at that shift."""
    from scipy.signal import fftconvolve

    a = standardised(reference, mask)
    b = standardised(moving, mask)
    xc = fftconvolve(a, b[::-1, ::-1], mode="full")
    centre = (b.shape[0] - 1, b.shape[1] - 1)
    window = xc[
        centre[0] - search : centre[0] + search + 1,
        centre[1] - search : centre[1] + search + 1,
    ]
    i, j = np.unravel_index(int(np.argmax(window)), window.shape)
    dr, dc = int(i) - search, int(j) - search
    return dr, dc, shifted_r(reference, moving, mask, dr, dc)


def shifted_r(
    reference: np.ndarray, moving: np.ndarray, mask: np.ndarray, dr: int, dc: int
) -> float:
    moved = np.roll(moving, (dr, dc), axis=(0, 1))
    moved_mask = np.roll(mask, (dr, dc), axis=(0, 1))
    both = mask & moved_mask
    r = analysis.pearson(
        reference[both].astype(np.float64), moved[both].astype(np.float64)
    )
    return float("nan") if r is None else r


def alignment(render_layers: dict[int, np.ndarray], winner_ct: np.ndarray) -> dict:
    """The layer whose zero-shift r with the winner's CT is highest, and its best shift."""
    mask = winner_ct > 0
    for layer in render_layers.values():
        mask &= layer > 0
    if int(mask.sum()) < 2:
        raise ValueError("no pixel with CT in both images")
    at_zero = {
        k: shifted_r(winner_ct, img, mask, 0, 0) for k, img in render_layers.items()
    }
    layer = max(at_zero, key=lambda k: at_zero[k])
    dr, dc, r = best_shift(winner_ct, render_layers[layer], mask, ALIGN_SEARCH)
    return {
        "layer": layer,
        "r_at_zero_by_layer": {str(k): round(v, 4) for k, v in at_zero.items()},
        "shift_pixels": [dr, dc],
        "r_at_shift": round(r, 4),
        "aligned": abs(dr) <= ALIGN_TOLERANCE and abs(dc) <= ALIGN_TOLERANCE,
    }


def roll_cells(image: np.ndarray, shift_pixels: list[int]) -> np.ndarray:
    """Our lattice moved by the alignment shift, in whole cells; cells moved in from outside are NaN."""
    dr, dc = (int(round(s / analysis.LATTICE)) for s in shift_pixels)
    out = np.roll(image.astype(np.float64), (dr, dc), axis=(0, 1))
    if dr > 0:
        out[:dr] = np.nan
    elif dr < 0:
        out[dr:] = np.nan
    if dc > 0:
        out[:, :dc] = np.nan
    elif dc < 0:
        out[:, dc:] = np.nan
    return out


def measure(
    ours_maps: dict[str, np.ndarray],
    blind_maps: dict[str, np.ndarray],
    studio: np.ndarray,
    cells: np.ndarray,
) -> dict:
    """The registered numbers: r of our reading-side ensemble against the winner's map, and the two controls."""
    ours = analysis.highpass(analysis.zscore_ensemble(ours_maps, cells), cells)
    blind = analysis.highpass(analysis.zscore_ensemble(blind_maps, cells), cells)
    theirs = analysis.highpass(studio, cells)
    r = analysis.pearson(theirs[cells], ours[cells])
    wrong_side = analysis.pearson(theirs[cells], blind[cells])
    slid = analysis.slid_control(theirs, ours, cells, cells)
    return {
        "r": _rounded(r),
        "control_wrong_side": _rounded(wrong_side),
        "control_slid": {k: _rounded(v) for k, v in slid.items()},
    }


def verdict(numbers: dict | None, cell_share: float | None) -> str:
    if numbers is None or cell_share is None or cell_share < MIN_CELL_SHARE:
        return "DOES_NOT_RUN"
    r = numbers["r"]
    controls = [
        numbers["control_wrong_side"],
        numbers["control_slid"]["largest_absolute"],
    ]
    if r is None or None in controls:
        return "DOES_NOT_RUN"
    clear = all(r >= RATIO * abs(c) for c in controls)
    if clear and r >= R_AGREES:
        return "READER_AGREES"
    if clear and r >= R_PARTLY:
        return "READER_PARTLY"
    return "READER_DISAGREES"


def described(
    maps_dir: Path,
    render: Path,
    mesh: Path,
    shift: list[int],
    studio: np.ndarray,
    cells: np.ndarray,
    ours_maps: dict[str, np.ndarray],
) -> dict:
    """Not registered: each model alone, every depth and side, the maps with their background, how far our own
    four models agree with each other, the slide of 256 pixels, and the rows."""
    theirs = analysis.highpass(studio, cells)
    hp = {m: analysis.highpass(ours_maps[m], cells) for m in analysis.MODELS}
    per_model = {
        m: _rounded(analysis.pearson(theirs[cells], hp[m][cells]))
        for m in analysis.MODELS
    }
    pairs = {
        f"{a}|{b}": _rounded(analysis.pearson(hp[a][cells], hp[b][cells]))
        for a, b in itertools.combinations(analysis.MODELS, 2)
    }
    by_depth = {}
    for d in DEPTHS:
        side = tm.side(mesh, maps_dir, render, blind_too=True, depth=d)
        for label, key in (("reading", "maps"), ("other", "blind_maps")):
            maps = {m: roll_cells(v, shift) for m, v in side[key].items()}
            ens = analysis.highpass(analysis.zscore_ensemble(maps, cells), cells)
            by_depth[f"{d:+d}_{label}"] = _rounded(
                analysis.pearson(theirs[cells], ens[cells])
            )
    raw_ours = analysis.zscore_ensemble(ours_maps, cells)
    rows = [i for i in range(cells.shape[0]) if cells[i].sum() >= 20]
    profile_theirs = np.array([studio[i][cells[i]].mean() for i in rows])
    profile_ours = np.array([raw_ours[i][cells[i]].mean() for i in rows])
    ours_hp = analysis.highpass(raw_ours, cells)
    return {
        "per_model_r": per_model,
        "our_models_pairwise_r": pairs,
        "by_depth_and_side": by_depth,
        "r_with_background": _rounded(analysis.pearson(studio[cells], raw_ours[cells])),
        "control_slid_256px": {
            k: _rounded(v)
            for k, v in analysis.slid_control(
                theirs, ours_hp, cells, cells, cells=4 * analysis.SHIFT_CELLS
            ).items()
        },
        "row_profile_r": _rounded(analysis.pearson(profile_theirs, profile_ours)),
        "rows_in_profile": len(rows),
    }


def write_image(
    path: Path, ours: np.ndarray, theirs: np.ndarray, cells: np.ndarray
) -> None:
    """Our reading-side ensemble above the winner's map, each on its own 1st-99th percentile grey scale."""
    import cv2

    def grey(image: np.ndarray) -> np.ndarray:
        lo, hi = np.percentile(image[cells], [1, 99])
        scaled = np.clip((image - lo) / max(hi - lo, 1e-9), 0, 1)
        return np.where(cells, scaled * 255, 0).astype(np.uint8)

    gap = np.zeros((8, ours.shape[1]), dtype=np.uint8)
    cv2.imwrite(str(path), np.vstack([grey(ours), gap, grey(theirs)]))


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def main(argv: list[str] | None = None) -> int:
    import cv2
    import tifffile
    import zarr

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--maps", required=True, type=Path)
    ap.add_argument("--render", required=True, type=Path)
    ap.add_argument("--studio", required=True, type=Path)
    ap.add_argument("--studio-mask", required=True, type=Path)
    ap.add_argument("--winner-ct", required=True, type=Path)
    ap.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2

    winner_ct = tifffile.imread(args.winner_ct)
    level0 = zarr.open(str(args.render), mode="r")["0"]
    if tuple(level0.shape[1:]) != tuple(winner_ct.shape):
        raise SystemExit(
            f"render {level0.shape} and winner's CT {winner_ct.shape} differ in size"
        )
    align = alignment({k: np.asarray(level0[k]) for k in ALIGN_LAYERS}, winner_ct)
    result: dict = {
        "finding": 118,
        "inputs_sha256": {
            "studio": sha256(args.studio),
            "studio_mask": sha256(args.studio_mask),
            "winner_ct": sha256(args.winner_ct),
        },
        "depth": DEPTH,
        "alignment": align,
    }
    if max(abs(s) for s in align["shift_pixels"]) >= ALIGN_SEARCH:
        result.update(
            {"verdict": "DOES_NOT_RUN", "why": "no alignment within the search"}
        )
        Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
        print(json.dumps(result, indent=1))
        return 0
    shift = [0, 0] if align["aligned"] else align["shift_pixels"]
    result["shift_applied_pixels"] = shift

    side = tm.side(args.mesh, args.maps, args.render, blind_too=True, depth=DEPTH)
    ok = roll_cells(side["ok"].astype(np.float64), shift) == 1.0
    ours_maps = {m: roll_cells(v, shift) for m, v in side["maps"].items()}
    blind_maps = {m: roll_cells(v, shift) for m, v in side["blind_maps"].items()}
    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    if studio.shape != ok.shape or in_mask.shape != ok.shape:
        raise SystemExit(
            f"lattices differ: ours {ok.shape}, map {studio.shape}, mask {in_mask.shape}"
        )
    cells = ok & in_mask & np.isfinite(studio)
    for maps in (ours_maps, blind_maps):
        for v in maps.values():
            cells &= np.isfinite(v)
    share = float(cells.sum()) / max(int(in_mask.sum()), 1)
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": int(cells.sum()),
            "cell_share": round(share, 4),
            "maps": side["files"],
        }
    )
    numbers = (
        measure(ours_maps, blind_maps, studio, cells)
        if share >= MIN_CELL_SHARE
        else None
    )
    result["registered"] = numbers
    result["verdict"] = verdict(numbers, share)
    if numbers is not None:
        result["described"] = described(
            args.maps, args.render, args.mesh, shift, studio, cells, ours_maps
        )
        if args.image:
            write_image(
                args.image,
                analysis.highpass(analysis.zscore_ensemble(ours_maps, cells), cells),
                analysis.highpass(studio, cells),
                cells,
            )
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("alignment", "cell_share", "registered", "verdict")
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
