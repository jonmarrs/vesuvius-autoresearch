"""Finding 135: at what depth does Studio read our geometry best, where PHerc. 211's First Letters prize was won?

Registration: docs/preregistration/2026-11-22_studio_depth_sweep.md.

    planes      RENDER_ZARR OUT.npy --shift D
                Studio's 16-plane input with every plane moved D layers along the render's frame: layers 41+D down
                to 26+D of the 66-layer frame. At D = 0 these are studio_e2e.py's planes, byte for byte. A render's
                layers run outward from the scroll's axis (the render rule), so D > 0 reads further out.
    compare     OUT.json --winner-mesh --winner-maps --winner-render --studio --studio-mask --ours-render-map NPY
                --windings w033 w034 w035 w036
                --arm NAME FINALS RENDERS ZERO_MAPS SWEEP_DIR   (e2e and dense2s3)
                [--sdt SDT_ZARR]
    compare343  OUT.json --render --sidecar --ink-png --zero NPY --zero-reversed NPY --sweep DIR

An arm is four of our windings at the winner's place with their 66-layer renders. ZERO_MAPS holds Studio's maps of
layers 41 to 26 and of the reversed planes (finding 124's for e2e, finding 134's for dense2s3); SWEEP_DIR/d<D>/
holds the maps of the other shifts. Each arm is carried onto the winner's surface once (finding 110's transfer) and
every shift's map is scored there with finding 124's statistic (studio_e2e.score), on the cells that every shift of
that arm reaches. At PHerc. 343 each shift's map of the recipe's surface is scored with finding 127's statistic.
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
sys.path.insert(0, str(HERE.parent / "pherc343"))
sys.path.insert(0, str(HERE.parent / "eligible_band"))

import compare as f118  # noqa: E402
import compare_readers as f120  # noqa: E402
import dense_read as f131  # noqa: E402
import end_to_end as f121  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_e2e as f124  # noqa: E402
import transfer_maps as tm  # noqa: E402
from render_frame import FRAME, frame_index  # noqa: E402

SHIFTS = (-8, -6, -4, -2, -1, 0, 1, 2, 4, 6, 8)
ARMS = ("e2e", "dense2s3")
LINE = 0.02  # the smallest gain in r called a gain (findings 131 and 134)
F124_R = 0.8247  # finding 124's registered r: the e2e arm at D = 0 on its own cells must give it again
F127_R = 0.6238  # finding 127's registered r: PHerc. 343's D = 0 map must give it again


def shifted_layers(shift: int) -> tuple[int, ...]:
    layers = tuple(k + shift for k in f124.LAYERS)
    if min(layers) < 0 or max(layers) >= FRAME:
        raise ValueError(
            f"shift {shift} leaves the {FRAME}-layer frame ({min(layers)} to {max(layers)})"
        )
    return layers


def planes_cmd(render: Path, out: Path, shift: int) -> dict:
    import zarr

    level0 = zarr.open(str(render), mode="r")["0"]
    try:
        index = [frame_index(level0.shape[0], k) for k in shifted_layers(shift)]
    except ValueError as e:
        raise SystemExit(f"{render}: {e}") from None
    stack = np.stack([np.asarray(level0[i]) for i in index])
    if stack.dtype != np.uint8:
        raise SystemExit(f"{render} is {stack.dtype}, not 8-bit")
    np.save(out, stack, allow_pickle=False)
    return {
        "render": str(render),
        "shift": shift,
        "layers": list(shifted_layers(shift)),
        "shape": list(stack.shape),
    }


def shift_dir(shift: int) -> str:
    return f"d{shift:+d}"


def best_shift(r: dict[str, dict[int, float | None]]) -> int | None:
    """The shift with the largest summed r over the arms (4 decimals); ties go to the smaller |D|, then to D > 0."""
    totals = {}
    for d in SHIFTS:
        values = [r[arm].get(d) for arm in ARMS]
        if any(v is None for v in values):
            return None
        totals[d] = round(sum(values), 4)  # type: ignore[arg-type]
    return max(SHIFTS, key=lambda d: (totals[d], -abs(d), d))


def verdict(
    r: dict[str, dict[int, float | None]] | None,
    shares: dict[str, float] | None,
    reproduces: bool,
) -> tuple[str, int | None, dict[str, float] | None]:
    """The registered verdict, the chosen shift and each arm's gain over D = 0."""
    if (
        not reproduces
        or r is None
        or shares is None
        or sorted(r) != sorted(ARMS)
        or any(sorted(r[arm]) != sorted(SHIFTS) for arm in ARMS)
        or any(
            shares.get(arm) is None or shares[arm] < f118.MIN_CELL_SHARE for arm in ARMS
        )
    ):
        return "DOES_NOT_RUN", None, None
    d = best_shift(r)
    if d is None:
        return "DOES_NOT_RUN", None, None
    gains = {arm: round(r[arm][d] - r[arm][0], 4) for arm in ARMS}  # type: ignore[operator]
    if d == 0:
        return "DEPTH_ZERO_BEST", d, gains
    if all(g >= LINE for g in gains.values()):
        return "DEPTH_SHIFT_READS_BETTER", d, gains
    return "DEPTH_SHIFT_WITHIN_MARGIN", d, gains


def half_widths(curve: dict[int, float | None]) -> dict[str, int | None]:
    """Described: on each side, the smallest |D| in the sweep where r is at most half of r at D = 0."""
    zero = curve.get(0)
    out: dict[str, int | None] = {}
    for side, sign in (("inward", -1), ("outward", 1)):
        hits = [abs(d) for d in SHIFTS if d * sign > 0 and zero is not None and curve.get(d) is not None
                and curve[d] <= zero / 2]  # type: ignore[operator]  # fmt: skip
        out[side] = min(hits) if hits else None
    return out


def sweep_map(zero_maps: Path, sweep: Path, shift: int, winding: str) -> Path:
    return (
        zero_maps / f"{winding}.npy"
        if shift == 0
        else sweep / shift_dir(shift) / f"{winding}.npy"
    )


def carry_arm(
    winner: dict,
    windings: list[str],
    finals: Path,
    renders: Path,
    zero_maps: Path,
    sweep: Path,
) -> dict:
    """One transfer for the arm's geometry; every shift's maps (and the D = 0 reversed planes) carried by it."""
    sides = [
        f131.side(finals / f"{w}.tifxyz", renders / f"{w}_66.zarr") for w in windings
    ]
    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(s["points"], s["ok"]) for s in sides]
    )
    carried = {}
    for d in SHIFTS:
        maps = [
            {"s": f124.read_studio(sweep_map(zero_maps, sweep, d, w), s["canvas"])}
            for w, s in zip(windings, sides, strict=True)
        ]
        carried[d] = f121.carry(maps, which, cell)["s"]
    other = f121.carry([{"s": f124.read_studio(zero_maps / f"{w}_reversed.npy", s["canvas"])}
                        for w, s in zip(windings, sides, strict=True)], which, cell)["s"]  # fmt: skip
    return {
        "which": which,
        "dist": dist,
        "cosines": [
            analysis.normals_agree(winner["points"], s["points"], which, cell, k)
            for k, s in enumerate(sides)
        ],
        "carried": carried,
        "other": other,
        "meshes": [s["mesh"] for s in sides],
    }


def arm_cells(arm: dict) -> np.ndarray:
    cells = (arm["which"] >= 0) & np.isfinite(arm["other"])
    for values in arm["carried"].values():
        cells &= np.isfinite(values)
    return cells


def score_one(
    studio: np.ndarray, carried: np.ndarray, other: np.ndarray, cells: np.ndarray
) -> dict:
    theirs = analysis.highpass(studio, cells)
    ink = (studio >= f120.INK) & cells
    return {"cells": int(cells.sum()), **f124.score(theirs, ink, carried, cells, other)}


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
    arms = {name: carry_arm(winner, args.windings, Path(finals), Path(renders), Path(zero), Path(sweep))
            for name, finals, renders, zero, sweep in args.arm}  # fmt: skip
    result: dict = {
        "finding": 135,
        "windings": args.windings,
        "shifts": list(SHIFTS),
        "arms": {
            name: {"meshes": a["meshes"], "normal_cosine_median": a["cosines"]}
            for name, a in arms.items()
        },
    }
    if any(
        c is None or c >= 0 for a in arms.values() for c in a["cosines"]
    ):  # every render flipped (finding 124)
        result.update(
            {
                "verdict": "DOES_NOT_RUN",
                "why": "a render samples against the winner's normals",
            }
        )
        return result
    cells = {name: base & arm_cells(a) for name, a in arms.items()}
    shares = {
        name: round(float(c.sum()) / max(int(in_mask.sum()), 1), 4)
        for name, c in cells.items()
    }
    numbers = {name: {d: score_one(studio, a["carried"][d], a["other"], cells[name]) for d in SHIFTS}
               for name, a in arms.items()}  # fmt: skip
    r = {name: {d: numbers[name][d]["r"] for d in SHIFTS} for name in arms}
    # finding 124's own cells: the e2e arm at D = 0 with its reversed map, as dense_read.py checks it
    e2e = arms.get("e2e")
    own = None
    if e2e is not None:
        own_cells = (
            base
            & (e2e["which"] >= 0)
            & np.isfinite(e2e["carried"][0])
            & np.isfinite(e2e["other"])
        )
        own = score_one(studio, e2e["carried"][0], e2e["other"], own_cells)["r"]
    reproduces = own == F124_R
    v, d, gains = verdict(r, shares, reproduces)
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "cells": {name: int(c.sum()) for name, c in cells.items()},
            "cell_share": shares,
            "f124_r_on_its_own_cells": own,
            "f124_reproduced": reproduces,
            "registered": {
                "r": {
                    name: {shift_dir(k): v_ for k, v_ in curve.items()}
                    for name, curve in r.items()
                },
                "best_shift": d,
                "gain_over_zero": gains,
            },
            "verdict": v,
        }
    )
    per_winding: dict = {}
    for name, a in arms.items():
        theirs = analysis.highpass(studio, cells[name])
        hp = {
            s: analysis.highpass(
                f120.standardise(a["carried"][s], cells[name]), cells[name]
            )
            for s in SHIFTS
        }
        per_winding[name] = {}
        for k, w in enumerate(args.windings):
            mine = cells[name] & (a["which"] == k)
            enough = mine.sum() >= f121.MIN_WINDING_CELLS
            per_winding[name][w] = {
                "cells": int(mine.sum()),
                "r": {shift_dir(s): f118._rounded(analysis.pearson(theirs[mine], hp[s][mine])) if enough else None
                      for s in SHIFTS},
            }  # fmt: skip
    result["described"] = {
        "each_shift": {
            name: {shift_dir(s): numbers[name][s] for s in SHIFTS} for name in arms
        },
        "half_widths": {name: half_widths(r[name]) for name in arms},
        "by_winding": per_winding,
        "transfer_distance_voxels": {
            name: dict(
                zip(
                    ("p50", "p95"),
                    (
                        round(float(q), 2)
                        for q in np.percentile(a["dist"][cells[name]], [50, 95])
                    ),
                    strict=True,
                )
            )
            for name, a in arms.items()
        },  # fmt: skip
        "final_nodes_within_2_of_the_predicted_sheet": {
            name: f131.sheet_share(args.sdt, Path(finals), args.windings)
            for name, finals, _, _, _ in args.arm
        },
    }
    return result


def compare343_cmd(args: argparse.Namespace) -> dict:
    """Finding 127's statistic for every shift's map of the recipe's PHerc. 343 surface (described)."""
    import cv2
    import studio_343 as f127
    import zarr

    sidecar = json.loads(args.sidecar.read_text())
    level0 = zarr.open(str(args.render), mode="r")["0"]
    if level0.shape[0] != FRAME:
        raise SystemExit(f"{args.render} has {level0.shape[0]} layers, not {FRAME}")
    raw_shape = tuple(level0.shape[1:])
    valid_raw = np.ones(raw_shape, dtype=bool)
    for k in range(FRAME):
        valid_raw &= np.asarray(level0[k]) > 0
    valid = f127.to_reading(valid_raw, sidecar)
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
        return analysis.block_mean(f127.to_reading(values, sidecar))

    cells = analysis.block_mean(valid.astype(np.float64)) == 1.0
    reference = analysis.block_mean(u)
    theirs = analysis.highpass(reference, cells)
    drawn = (reference >= f127.DRAWN) & cells
    other = studio(args.zero_reversed)
    numbers = {}
    for d in SHIFTS:
        path = args.zero if d == 0 else args.sweep / shift_dir(d) / "forward.npy"
        numbers[d] = f124.score(theirs, drawn, studio(path), cells, other)
    r = {d: numbers[d]["r"] for d in SHIFTS}
    best = max(SHIFTS, key=lambda d: (-1.0 if r[d] is None else r[d], -abs(d), d))
    return {
        "finding": 135,
        "scroll": "PHerc. 343",
        "described_only": True,
        "cells": int(cells.sum()),
        "f127_reproduced": r[0] == F127_R,
        "r": {shift_dir(d): r[d] for d in SHIFTS},
        "best_shift": best,
        "half_widths": half_widths(r),
        "each_shift": {shift_dir(d): numbers[d] for d in SHIFTS},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("planes")
    p.add_argument("render", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--shift", type=int, required=True)
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
    c.add_argument("--arm", nargs=5, action="append", required=True,
                   metavar=("NAME", "FINALS", "RENDERS", "ZERO_MAPS", "SWEEP_DIR"))  # fmt: skip
    c.add_argument("--sdt", type=Path)
    h = sub.add_parser("compare343")
    h.add_argument("out", type=Path)
    for flag in (
        "--render",
        "--sidecar",
        "--ink-png",
        "--zero",
        "--zero-reversed",
        "--sweep",
    ):
        h.add_argument(flag, required=True, type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is written once", file=sys.stderr)
        return 2
    if args.command == "planes":
        print(json.dumps(planes_cmd(args.render, args.out, args.shift)))
        return 0
    if args.command == "compare":
        names = [a[0] for a in args.arm]
        if sorted(names) != sorted(ARMS):
            raise SystemExit(f"the arms are {', '.join(ARMS)}, not {names}")
        result = compare_cmd(args)
    else:
        result = compare343_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("described", "each_shift")},
            indent=1,
        )
    )
    return 0 if result.get("verdict") != "DOES_NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
