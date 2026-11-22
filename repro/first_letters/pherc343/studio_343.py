"""Finding 127: Studio at the place where the PHerc. 343 recipe's published image shows 18 letters.

Registration: docs/preregistration/2026-11-20_first_letters_343_studio.md.

    compare  OUT.json --render ZARR --sidecar JSON --ink-png PNG --studio NPY --studio-reversed NPY --maps DIR
             [--image PNG]

Studio's maps (raw render frame, float32 [H, W]) are cropped to the published image's area and mirrored as the
sidecar records, which puts them on the pixels of `u`, the recipe's 8-bit ensemble ink image
(`make_submission_image.py --write-components`). On 4-pixel cells whose pixels are all valid (all 66 layers above
0), the registered number is finding 118's r between `u` and Studio's map, both with the broad background taken
off. The controls are Studio's map of the reversed planes and the map slid 64 pixels. The lines come from how well
each of the recipe's four models agrees with the other three on the same cells (`leave_one_out`), measured before
any Studio map existed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "pherc0211_control"))

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_e2e as f124  # noqa: E402

AGREES, PARTLY = (
    0.41,
    0.20,
)  # the lowest member against the other three (Hecate, 0.4100), and about half of it
RATIO = 2.0
DRAWN = 0.35  # the overlay's threshold on u / 255: ink drawn in the published image
STUDIO_INK = 0.5
MIN_CELL_SHARE = 0.5
MODELS = {  # the published image's four reading-side maps, as make_submission_image.py names them
    "dnative": "__dnative__L66s26_reverse.tif",
    "hecate": "__hecate__L66zc33.50_reverse.png",
    "ink9-42": "__hybrid_3d2d-seed42__L66s26_reverse.tif",
    "ink9-43": "__hybrid_3d2d-seed43__L66s26_reverse.tif",
}
REGISTERED_LEAVE_ONE_OUT = {
    "dnative": 0.6195,
    "hecate": 0.41,
    "ink9-42": 0.525,
    "ink9-43": 0.5152,
}


def to_reading(raw: np.ndarray, sidecar: dict) -> np.ndarray:
    """The sidecar's area of a raw-frame image, mirrored into reading orientation."""
    a = sidecar["area"]["raw_render_px"]
    o = sidecar["orientation"]
    out = raw[a["row0"] : a["row1"], a["col0"] : a["col1"]]
    if o["flip_ud"]:
        out = out[::-1]
    if o["flip_lr"]:
        out = out[:, ::-1]
    return out


def verdict(numbers: dict | None, cell_share: float | None) -> str:
    if numbers is None or cell_share is None or cell_share < MIN_CELL_SHARE:
        return "DOES_NOT_RUN"
    r = numbers["r"]
    slid = numbers["control_slid"]["largest_absolute"]
    wrong = numbers["control_wrong_side"]
    if r is None or slid is None or wrong is None:
        return "DOES_NOT_RUN"
    clear = r >= RATIO * abs(slid) and r >= RATIO * abs(wrong)
    if clear and r >= AGREES:
        return "STUDIO_343_AGREES"
    if clear and r >= PARTLY:
        return "STUDIO_343_PARTLY"
    return "STUDIO_343_FAR"


def read_model(path: Path, raw_shape: tuple[int, int]) -> np.ndarray:
    """A recipe map in the raw frame, as make_submission_image.py reads it: villa TIFF v -> clip((v - 64) / 128, 0,
    1); Hecate PNG v / 255, bilinearly resized to the render grid."""
    import cv2
    import tifffile

    if path.suffix == ".png":
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise SystemExit(f"cannot read {path}")
        image = cv2.resize(
            image, (raw_shape[1], raw_shape[0]), interpolation=cv2.INTER_LINEAR
        )
        return image.astype(np.float64) / 255.0
    image = tifffile.imread(path).astype(np.float64)
    if image.shape != raw_shape:
        raise SystemExit(f"{path} is {image.shape}, the render {raw_shape}")
    return np.clip((image - 64.0) / 128.0, 0.0, 1.0)


def leave_one_out(models: dict[str, np.ndarray], cells: np.ndarray) -> dict:
    """Each model (block means, reading frame) against the mean of the other three's z-scores, as the registered r,
    with the largest slid control."""
    z = {k: f120.standardise(m, cells) for k, m in models.items()}
    out = {}
    for name in z:
        others = analysis.highpass(
            np.mean([z[j] for j in z if j != name], axis=0), cells
        )
        mine = analysis.highpass(z[name], cells)
        slid = analysis.slid_control(others, mine, cells, cells)
        out[name] = {
            "r": f118._rounded(analysis.pearson(others[cells], mine[cells])),
            "control_slid_largest_absolute": f118._rounded(slid["largest_absolute"]),
        }
    return out


def letter_boxes(
    letters: dict, studio: np.ndarray, u: np.ndarray, valid: np.ndarray
) -> dict:
    """Per letter box of the sidecar (`letters_area_px`: area pixels, reading orientation; x1, y1 exclusive): Studio's ink share and u's drawn share
    over its valid pixels, and whether Studio's share there exceeds its share over the whole valid area."""
    overall = float((studio[valid] >= STUDIO_INK).mean())
    boxes = []
    for entry in letters["letters_area_px"]:
        x0, y0, x1, y1 = entry["box"]
        sl = (
            slice(int(round(y0)), int(round(y1))),
            slice(int(round(x0)), int(round(x1))),
        )
        inside = valid[sl]
        if not inside.any():
            boxes.append({"id": entry["id"], "valid_pixels": 0})
            continue
        share = float((studio[sl][inside] >= STUDIO_INK).mean())
        boxes.append(
            {
                "id": entry["id"],
                "valid_pixels": int(inside.sum()),
                "studio_ink_share": round(share, 4),
                "u_drawn_share": round(float((u[sl][inside] >= DRAWN).mean()), 4),
                "studio_above_its_area_share": share > overall,
            }
        )
    scored = [b for b in boxes if b["valid_pixels"]]
    return {
        "studio_ink_share_over_the_valid_area": round(overall, 4),
        "boxes": boxes,
        "boxes_scored": len(scored),
        "boxes_where_studio_is_above_its_area_share": sum(
            b["studio_above_its_area_share"] for b in scored
        ),
    }


def write_image(path: Path, panels: list[np.ndarray], valid: np.ndarray) -> None:
    """Full-resolution panels one above another, each 0..1 to 0..255, invalid pixels black."""
    import cv2

    gap = np.zeros((12, valid.shape[1]), dtype=np.uint8)
    stack: list[np.ndarray] = []
    for panel in panels:
        stack += [
            np.where(valid, np.clip(np.round(panel * 255), 0, 255), 0).astype(np.uint8),
            gap,
        ]
    cv2.imwrite(str(path), np.vstack(stack[:-1]))


def compare(args: argparse.Namespace) -> dict:
    import cv2
    import zarr

    sidecar = json.loads(args.sidecar.read_text())
    level0 = zarr.open(str(args.render), mode="r")["0"]
    if level0.shape[0] != 66:
        raise SystemExit(f"{args.render} has {level0.shape[0]} layers, not 66")
    raw_shape = tuple(level0.shape[1:])
    valid_raw = np.ones(raw_shape, dtype=bool)
    for k in range(66):
        valid_raw &= np.asarray(level0[k]) > 0
    valid = to_reading(valid_raw, sidecar)
    ink_png = cv2.imread(str(args.ink_png), cv2.IMREAD_GRAYSCALE)
    if ink_png is None:
        raise SystemExit(f"cannot read {args.ink_png}")
    u = ink_png.astype(np.float64) / 255.0
    if u.shape != valid.shape:
        raise SystemExit(f"{args.ink_png} is {u.shape}, the area {valid.shape}")

    def studio(path: Path) -> np.ndarray:
        values = np.load(path, allow_pickle=False).astype(np.float64)
        if values.shape != raw_shape:
            raise SystemExit(f"{path} is {values.shape}, the render {raw_shape}")
        return to_reading(values, sidecar)

    forward, reversed_ = studio(args.studio), studio(args.studio_reversed)
    cells = analysis.block_mean(valid.astype(np.float64)) == 1.0
    area_cells = cells.size
    share = float(cells.sum()) / area_cells
    result: dict = {
        "finding": 127,
        "layers": list(f124.LAYERS),
        "area_shape": list(valid.shape),
        "cells": int(cells.sum()),
        "area_cells": area_cells,
        "cell_share": round(share, 4),
    }
    if share < MIN_CELL_SHARE:
        result.update(
            {
                "registered": None,
                "verdict": "DOES_NOT_RUN",
                "why": "too few valid cells",
            }
        )
        return result
    reference = analysis.block_mean(u)
    theirs = analysis.highpass(reference, cells)
    drawn = (reference >= DRAWN) & cells
    ours, other = analysis.block_mean(forward), analysis.block_mean(reversed_)
    numbers = f124.score(theirs, drawn, ours, cells, other)
    result["registered"] = {
        k: numbers[k] for k in ("r", "control_wrong_side", "control_slid")
    }
    result["verdict"] = verdict(result["registered"], share)
    reversed_numbers = f124.score(theirs, drawn, other, cells)
    models = {
        name: analysis.block_mean(to_reading(read_model(args.maps / f"{args.render_name}{suffix}", raw_shape), sidecar))
        for name, suffix in MODELS.items()
    }  # fmt: skip
    result["described"] = {
        "studio": numbers,
        "studio_reversed_planes": {k: reversed_numbers[k] for k in ("r", "overlap")},
        "leave_one_out": leave_one_out(models, cells),
        "letters": letter_boxes(sidecar["letters"], forward, u, valid),
        "studio_ink_share": {
            "forward": round(float((forward[valid] >= STUDIO_INK).mean()), 4),
            "reversed": round(float((reversed_[valid] >= STUDIO_INK).mean()), 4),
        },
        "u_drawn_share": round(float((u[valid] >= DRAWN).mean()), 4),
    }
    if args.image:
        write_image(args.image, [forward, u], valid)
        write_image(
            args.image.with_name(args.image.stem + "_reversed.png"),
            [reversed_, u],
            valid,
        )
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compare")
    c.add_argument("out", type=Path)
    for flag in (
        "--render",
        "--sidecar",
        "--ink-png",
        "--studio",
        "--studio-reversed",
        "--maps",
    ):
        c.add_argument(flag, required=True, type=Path)
    c.add_argument("--render-name", default="concat_w047-w048_R5B2_z9500-11000")
    c.add_argument("--image", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = compare(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "described"}, indent=1))
    print("VERDICT", result["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
