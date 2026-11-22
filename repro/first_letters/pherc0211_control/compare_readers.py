"""Does Reader V3 put ink where the winning PHerc. 211 reader put it, more closely than the recipe's ensemble?

Finding 120 (registration: docs/preregistration/2026-11-16_first_letters_0211_reader_v3.md). The surface, render,
cells, alignment and reference are finding 118's (compare.py); two readers are measured the same way:

    ensemble   the PHerc. 343 recipe's four models at depth +1, reading side: finding 118's maps, unchanged
    reader_v3  Reader V3 at depth +1, reading side (`_reverse`), on the same 17 layers as the ink_9um seeds

For each reader, on the cells:
    r        Pearson r against the winner's map, both with their background taken off (finding 118's number)
             controls: the reader's other side at depth +1; the reader slid 64 pixels, largest absolute of four
    overlap  the winner's ink cells (probability at least 0.5) against as many of the reader's strongest cells
             (background off): 2|A and B| / (|A| + |B|). Control: the reader slid 64 pixels, the largest of four.

usage: compare_readers.py OUT.json --mesh DIR --maps DIR --v3-maps DIR --render ZARR --studio TIF
                          --studio-mask PNG --winner-ct TIF [--image PNG]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import compare as f118  # noqa: E402  (finding 118's comparison: alignment, cells, controls)

analysis = f118.analysis
tm = f118.tm

V3 = "reader_v3"
DEPTH = f118.DEPTH  # +1
DEPTHS = f118.DEPTHS  # -3..+2, described
INK = 0.5  # the winner's probability at which a cell counts as ink
R_MARGIN, OVERLAP_MARGIN = 0.10, 0.05
RATIO = f118.RATIO  # 2: a reader's r must be at least twice each of its controls
BLOCK_CELLS = 64  # 256 render pixels: the blocks of the described bootstrap
BOOTSTRAP = 1000


def v3_file(maps: Path, render_name: str, depth: int, reading_side: bool) -> Path:
    """run_reader_v3.sh's name for a map: the ink_9um seeds' window s..s+16 with s = depth + 25."""
    tag = "_reverse" if reading_side else ""
    return maps / f"{render_name}__{V3}__L66s{depth + 25}{tag}.tif"


def standardise(image: np.ndarray, cells: np.ndarray) -> np.ndarray:
    values = image[cells]
    sd = float(values.std())
    if sd == 0:
        raise ValueError("the map is constant over the compared cells")
    return (image - float(values.mean())) / sd


def strongest(image: np.ndarray, compared: np.ndarray, k: int) -> np.ndarray:
    """The k cells of `compared` where `image` is highest (ties by position, so the choice is reproducible)."""
    values = image[compared]
    order = np.argsort(-values, kind="stable")
    chosen = np.zeros(values.size, dtype=bool)
    chosen[order[:k]] = True
    out = np.zeros(compared.shape, dtype=bool)
    out[compared] = chosen
    return out


def overlap(ink: np.ndarray, ours: np.ndarray, compared: np.ndarray) -> float | None:
    """The winner's ink cells among `compared` against as many of our strongest cells: the Dice coefficient."""
    a = ink & compared
    k = int(a.sum())
    if k == 0 or k >= int(compared.sum()):
        return None
    b = strongest(ours, compared, k)
    return 2.0 * float((a & b).sum()) / float(a.sum() + b.sum())


def slid_overlap(
    ink: np.ndarray, ours: np.ndarray, cells: np.ndarray, shift: int
) -> dict:
    """overlap() with our map slid by `shift` cells each way, over the cells whose slid partner is a cell; the
    wrapped-round edge is left out, as finding 110's slid control does."""
    out: dict = {}
    for label, (dr, dc) in {
        "down": (shift, 0),
        "up": (-shift, 0),
        "right": (0, shift),
        "left": (0, -shift),
    }.items():
        slid = np.roll(ours, (dr, dc), axis=(0, 1))
        slid_mask = np.roll(cells, (dr, dc), axis=(0, 1))
        if dr > 0:
            slid_mask[:dr] = False
        elif dr < 0:
            slid_mask[dr:] = False
        if dc > 0:
            slid_mask[:, :dc] = False
        elif dc < 0:
            slid_mask[:, dc:] = False
        out[label] = overlap(ink, slid, cells & slid_mask)
    values = [v for v in out.values() if v is not None]
    out["largest"] = max(values) if values else None
    return out


def score(
    theirs: np.ndarray,
    ink: np.ndarray,
    reading: np.ndarray,
    other: np.ndarray,
    cells: np.ndarray,
) -> dict:
    """One reader's registered numbers. `reading` and `other` are standardised maps (an ensemble or one model)."""
    ours = analysis.highpass(reading, cells)
    blind = analysis.highpass(other, cells)
    slid = analysis.slid_control(theirs, ours, cells, cells)
    slid_ov = slid_overlap(ink, ours, cells, analysis.SHIFT_CELLS)
    return {
        "r": f118._rounded(analysis.pearson(theirs[cells], ours[cells])),
        "control_wrong_side": f118._rounded(
            analysis.pearson(theirs[cells], blind[cells])
        ),
        "control_slid": {k: f118._rounded(v) for k, v in slid.items()},
        "overlap": f118._rounded(overlap(ink, ours, cells)),
        "control_overlap_slid": {k: f118._rounded(v) for k, v in slid_ov.items()},
    }


def clears(numbers: dict) -> bool:
    r = numbers["r"]
    controls = [
        numbers["control_wrong_side"],
        numbers["control_slid"]["largest_absolute"],
    ]
    if r is None or None in controls:
        return False
    return all(r >= RATIO * abs(c) for c in controls)


def verdict(ensemble: dict | None, v3: dict | None, cell_share: float | None) -> str:
    if ensemble is None or v3 is None or cell_share is None:
        return "DOES_NOT_RUN"
    if cell_share < f118.MIN_CELL_SHARE:
        return "DOES_NOT_RUN"
    if None in (ensemble["r"], ensemble["overlap"], v3["r"], v3["overlap"]):
        return "DOES_NOT_RUN"
    if not clears(v3):
        return "V3_FAILS_CONTROLS"
    dr = round(v3["r"] - ensemble["r"], 4)
    do = round(v3["overlap"] - ensemble["overlap"], 4)
    if dr >= R_MARGIN and do >= OVERLAP_MARGIN:
        return "V3_CLOSER"
    if dr <= -R_MARGIN or do <= -OVERLAP_MARGIN:
        return "V3_FARTHER"
    return "V3_NO_CLOSER"


def block_bootstrap(
    theirs: np.ndarray, a: np.ndarray, b: np.ndarray, cells: np.ndarray, seed: int = 0
) -> dict:
    """Described: the spread of r(theirs, b) - r(theirs, a) when 64-cell blocks are resampled with replacement."""
    rows, cols = cells.shape
    blocks = []
    for i in range(0, rows, BLOCK_CELLS):
        for j in range(0, cols, BLOCK_CELLS):
            inside = cells[i : i + BLOCK_CELLS, j : j + BLOCK_CELLS]
            if int(inside.sum()) < 2:
                continue
            window = (slice(i, i + BLOCK_CELLS), slice(j, j + BLOCK_CELLS))
            blocks.append(
                (theirs[window][inside], a[window][inside], b[window][inside])
            )
    rng = np.random.default_rng(seed)
    differences = []
    for _ in range(BOOTSTRAP):
        pick = rng.integers(0, len(blocks), len(blocks))
        t = np.concatenate([blocks[k][0] for k in pick])
        x = np.concatenate([blocks[k][1] for k in pick])
        y = np.concatenate([blocks[k][2] for k in pick])
        ra, rb = analysis.pearson(t, x), analysis.pearson(t, y)
        if ra is not None and rb is not None:
            differences.append(rb - ra)
    low, high = np.percentile(differences, [2.5, 97.5])
    return {
        "blocks": len(blocks),
        "low": round(float(low), 4),
        "high": round(float(high), 4),
    }


def write_image(path: Path, panels: list[np.ndarray], cells: np.ndarray) -> None:
    """The panels one above another (ensemble, Reader V3, the winner's map), each on its own grey scale."""
    import cv2

    def grey(image: np.ndarray) -> np.ndarray:
        lo, hi = np.percentile(image[cells], [1, 99])
        scaled = np.clip((image - lo) / max(hi - lo, 1e-9), 0, 1)
        return np.where(cells, scaled * 255, 0).astype(np.uint8)

    gap = np.zeros((8, cells.shape[1]), dtype=np.uint8)
    stack: list[np.ndarray] = []
    for panel in panels:
        stack += [grey(panel), gap]
    cv2.imwrite(str(path), np.vstack(stack[:-1]))


def read_v3(maps: Path, render: Path, canvas: tuple[int, int], depth: int) -> tuple:
    name = render.name.removesuffix(".zarr")
    reading = v3_file(maps, name, depth, True)
    other = v3_file(maps, name, depth, False)
    return (
        tm.read_map(reading, V3, canvas),
        tm.read_map(other, V3, canvas),
        {"reading": str(reading), "other": str(other)},
    )


def main(argv: list[str] | None = None) -> int:
    import cv2
    import tifffile
    import zarr

    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    for flag in ("--mesh", "--maps", "--v3-maps", "--render", "--studio"):
        ap.add_argument(flag, required=True, type=Path)
    ap.add_argument("--studio-mask", required=True, type=Path)
    ap.add_argument("--winner-ct", required=True, type=Path)
    ap.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2

    winner_ct = tifffile.imread(args.winner_ct)
    level0 = zarr.open(str(args.render), mode="r")["0"]
    align = f118.alignment(
        {k: np.asarray(level0[k]) for k in f118.ALIGN_LAYERS}, winner_ct
    )
    result: dict = {"finding": 120, "depth": DEPTH, "alignment": align}
    if max(abs(s) for s in align["shift_pixels"]) >= f118.ALIGN_SEARCH:
        result["verdict"] = "DOES_NOT_RUN"
        Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
        return 0
    shift = [0, 0] if align["aligned"] else align["shift_pixels"]
    result["shift_applied_pixels"] = shift

    side = tm.side(args.mesh, args.maps, args.render, blind_too=True, depth=DEPTH)
    canvas = (level0.shape[1], level0.shape[2])
    ok = f118.roll_cells(side["ok"].astype(np.float64), shift) == 1.0
    ens_reading = {m: f118.roll_cells(v, shift) for m, v in side["maps"].items()}
    ens_other = {m: f118.roll_cells(v, shift) for m, v in side["blind_maps"].items()}
    v3_reading, v3_other, v3_files = read_v3(args.v3_maps, args.render, canvas, DEPTH)
    v3_reading, v3_other = (f118.roll_cells(v, shift) for v in (v3_reading, v3_other))

    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    cells = ok & in_mask & np.isfinite(studio)
    for v in [*ens_reading.values(), *ens_other.values(), v3_reading, v3_other]:
        cells &= np.isfinite(v)
    share = float(cells.sum()) / max(int(in_mask.sum()), 1)
    theirs = analysis.highpass(studio, cells)
    ink = (studio >= INK) & cells
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": int(cells.sum()),
            "cell_share": round(share, 4),
            "winner_ink_cells": int(ink.sum()),
            "v3_maps": v3_files,
        }
    )
    ensemble = v3 = None
    if share >= f118.MIN_CELL_SHARE:
        ens_img = analysis.zscore_ensemble(ens_reading, cells)
        ensemble = score(
            theirs, ink, ens_img, analysis.zscore_ensemble(ens_other, cells), cells
        )
        v3_img = standardise(v3_reading, cells)
        v3 = score(theirs, ink, v3_img, standardise(v3_other, cells), cells)
        by_depth = {}
        for d in DEPTHS:
            reading, other, _ = read_v3(args.v3_maps, args.render, canvas, d)
            reading, other = (f118.roll_cells(v, shift) for v in (reading, other))
            numbers = score(
                theirs,
                ink,
                standardise(reading, cells),
                standardise(other, cells),
                cells,
            )
            by_depth[f"{d:+d}"] = {
                k: numbers[k] for k in ("r", "control_wrong_side", "overlap")
            }
        result["described"] = {
            "v3_by_depth": by_depth,
            "r_difference_bootstrap": block_bootstrap(
                theirs,
                analysis.highpass(ens_img, cells),
                analysis.highpass(v3_img, cells),
                cells,
            ),
            "v3_r_with_ensemble": f118._rounded(
                analysis.pearson(
                    analysis.highpass(ens_img, cells)[cells],
                    analysis.highpass(v3_img, cells)[cells],
                )
            ),
        }
        if args.image:
            write_image(
                args.image,
                [
                    analysis.highpass(ens_img, cells),
                    analysis.highpass(v3_img, cells),
                    theirs,
                ],
                cells,
            )
    result["ensemble"] = ensemble
    result[V3] = v3
    result["verdict"] = verdict(ensemble, v3, share)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {k: result.get(k) for k in ("cell_share", "ensemble", V3, "verdict")},
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
