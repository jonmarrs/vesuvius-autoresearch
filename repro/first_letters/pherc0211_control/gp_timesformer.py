"""Finding 122: the 2023 Grand Prize TimeSformer on the surface that won PHerc. 211's First Letters prize.

Registration: docs/preregistration/2026-11-16_first_letters_0211_gp_timesformer.md.

    segments  RENDER_ZARR OUT_DIR
              finding 118's 66-layer render as the Grand Prize script's segment layout, in both layer orders:
              OUT_DIR/v9fwd/layers/NN.tif (render layer NN) and OUT_DIR/v9rev/layers/NN.tif (render layer 65 - NN),
              only the 26 layers each order's window reads (WINDOWS). No mask file, so the script reads every tile.
    compare   OUT.json --mesh --maps --render --studio --studio-mask --winner-ct --gp-maps DIR --v3-maps DIR
              [--image PNG]
              finding 120's comparison with this model in Reader V3's place: the reversed order is the reading
              side and the forward order its other side. Reader V3 (finding 120's maps) is described beside it.

The model was trained on 65-layer volumes with the surface at layer 32, reading layers 17 to 42 (start_idx 17,
26 layers). Our render has 66 layers with the surface at layer 33 (finding 118's alignment), so the window is
render layers 18 to 43 in the forward order and 17 to 42 of the reversed order (render layers 48 down to 23).
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
import mesh_step_analysis as analysis  # noqa: E402
import transfer_maps as tm  # noqa: E402

LAYERS = 66
SURFACE = 33  # finding 118's alignment: the mesh layer of the 66-layer render
IN_CHANS = 26
TRAINED_SURFACE, TRAINED_START = 32, 17  # the model's 65-layer volumes and start_idx
WINDOWS = {
    "v9fwd": SURFACE - (TRAINED_SURFACE - TRAINED_START),  # 18: render layers 18..43
    "v9rev": (LAYERS - 1 - SURFACE)
    - (TRAINED_SURFACE - TRAINED_START),  # 17: reversed layers 17..42
}
READING, OTHER = "v9rev", "v9fwd"
NAME = "gp_timesformer"


def segment_layers(order: str) -> dict[int, int]:
    """For one order, the segment layer number the script reads -> the render layer it holds."""
    start = WINDOWS[order]
    numbers = range(start, start + IN_CHANS)
    if order == "v9fwd":
        return {n: n for n in numbers}
    return {n: LAYERS - 1 - n for n in numbers}


def gp_file(maps: Path, order: str) -> Path:
    """The script's output name: <segment>_prediction_rotated_0_layer_<start_idx>.png."""
    return maps / f"{order}_prediction_rotated_0_layer_{WINDOWS[order]}.png"


def segments_cmd(render: Path, out: Path) -> dict:
    import cv2
    import zarr

    level0 = zarr.open(str(render), mode="r")["0"]
    if level0.shape[0] != LAYERS:
        raise SystemExit(f"{render} has {level0.shape[0]} layers, not {LAYERS}")
    written = {}
    for order in WINDOWS:
        layers = out / order / "layers"
        layers.mkdir(parents=True)
        for number, source in segment_layers(order).items():
            image = np.asarray(level0[source])
            if image.dtype != np.uint8:
                raise SystemExit(f"{render} is {image.dtype}, not 8-bit")
            cv2.imwrite(str(layers / f"{number:02d}.tif"), image)
        written[order] = {
            "start_idx": WINDOWS[order],
            "render_layers": list(segment_layers(order).values()),
        }
    return written


def read_gp(path: Path, canvas: tuple[int, int]) -> np.ndarray:
    """One prediction PNG (the script pads to multiples of 256) cropped to the render, as block means of 0..1."""
    import cv2

    raw = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if raw is None:
        raise SystemExit(f"cannot read {path}")
    if raw.shape[0] < canvas[0] or raw.shape[1] < canvas[1]:
        raise SystemExit(f"{path} is {raw.shape}, smaller than the render {canvas}")
    return analysis.block_mean(raw[: canvas[0], : canvas[1]].astype(np.float64) / 255.0)


def verdict(ensemble: dict | None, gp: dict | None, cell_share: float | None) -> str:
    """Finding 120's table, under this model's name."""
    return f120.verdict(ensemble, gp, cell_share).replace("V3_", "GP_")


def compare_cmd(args: argparse.Namespace) -> dict:
    import cv2
    import tifffile
    import zarr

    winner_ct = tifffile.imread(args.winner_ct)
    level0 = zarr.open(str(args.render), mode="r")["0"]
    align = f118.alignment(
        {k: np.asarray(level0[k]) for k in f118.ALIGN_LAYERS}, winner_ct
    )
    result: dict = {
        "finding": 122,
        "alignment": align,
        "windows": WINDOWS,
        "reading_side": READING,
    }
    if max(abs(s) for s in align["shift_pixels"]) >= f118.ALIGN_SEARCH:
        result["verdict"] = "DOES_NOT_RUN"
        return result
    shift = [0, 0] if align["aligned"] else align["shift_pixels"]
    result["shift_applied_pixels"] = shift
    canvas = (level0.shape[1], level0.shape[2])

    side = tm.side(args.mesh, args.maps, args.render, blind_too=True, depth=f120.DEPTH)
    ok = f118.roll_cells(side["ok"].astype(np.float64), shift) == 1.0
    ens_reading = {m: f118.roll_cells(v, shift) for m, v in side["maps"].items()}
    ens_other = {m: f118.roll_cells(v, shift) for m, v in side["blind_maps"].items()}
    gp_reading, gp_other = (
        f118.roll_cells(read_gp(gp_file(args.gp_maps, order), canvas), shift)
        for order in (READING, OTHER)
    )
    v3_reading, v3_other, _ = f120.read_v3(
        args.v3_maps, args.render, canvas, f120.DEPTH
    )
    v3_reading, v3_other = (f118.roll_cells(v, shift) for v in (v3_reading, v3_other))

    studio = analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    cells = ok & in_mask & np.isfinite(studio)
    for v in [
        *ens_reading.values(),
        *ens_other.values(),
        gp_reading,
        gp_other,
        v3_reading,
        v3_other,
    ]:
        cells &= np.isfinite(v)
    share = float(cells.sum()) / max(int(in_mask.sum()), 1)
    theirs = analysis.highpass(studio, cells)
    ink = (studio >= f120.INK) & cells
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": int(cells.sum()),
            "cell_share": round(share, 4),
            "winner_ink_cells": int(ink.sum()),
            "gp_maps": {order: str(gp_file(args.gp_maps, order)) for order in WINDOWS},
        }
    )
    ensemble = gp = None
    if share >= f118.MIN_CELL_SHARE:
        ens_img = analysis.zscore_ensemble(ens_reading, cells)
        ensemble = f120.score(
            theirs, ink, ens_img, analysis.zscore_ensemble(ens_other, cells), cells
        )
        try:
            gp_img = f120.standardise(gp_reading, cells)
            gp = f120.score(
                theirs, ink, gp_img, f120.standardise(gp_other, cells), cells
            )
        except ValueError:  # a constant map: the model drew nothing to compare
            gp_img = None
        v3_img = f120.standardise(v3_reading, cells)
        v3 = f120.score(theirs, ink, v3_img, f120.standardise(v3_other, cells), cells)
        described: dict = {"reader_v3": v3}
        if gp_img is not None:
            gp_hp = analysis.highpass(gp_img, cells)
            described.update(
                {
                    "forward_order_as_reading_side": f120.score(
                        theirs, ink, f120.standardise(gp_other, cells), gp_img, cells
                    ),
                    "r_difference_bootstrap": f120.block_bootstrap(
                        theirs, analysis.highpass(ens_img, cells), gp_hp, cells
                    ),
                    "gp_r_with_ensemble": f118._rounded(
                        analysis.pearson(
                            analysis.highpass(ens_img, cells)[cells], gp_hp[cells]
                        )
                    ),
                    "gp_r_with_reader_v3": f118._rounded(
                        analysis.pearson(
                            analysis.highpass(v3_img, cells)[cells], gp_hp[cells]
                        )
                    ),
                }
            )
            if args.image:
                f120.write_image(
                    args.image,
                    [
                        analysis.highpass(ens_img, cells),
                        analysis.highpass(v3_img, cells),
                        gp_hp,
                        theirs,
                    ],
                    cells,
                )
        result["described"] = described
    result["ensemble"] = ensemble
    result[NAME] = gp
    result["verdict"] = verdict(ensemble, gp, share)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("segments")
    s.add_argument("render", type=Path)
    s.add_argument("out", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    for flag in (
        "--mesh",
        "--maps",
        "--render",
        "--studio",
        "--studio-mask",
        "--winner-ct",
        "--gp-maps",
        "--v3-maps",
    ):
        c.add_argument(flag, required=True, type=Path)
    c.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if args.command == "segments":
        if args.out.exists():
            print(f"{args.out} exists: the segments are written once", file=sys.stderr)
            return 2
        print(json.dumps(segments_cmd(args.render, args.out)))
        return 0
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = compare_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {k: result.get(k) for k in ("cell_share", "ensemble", NAME, "verdict")},
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
