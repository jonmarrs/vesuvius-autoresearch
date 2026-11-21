"""Finding 134: does a three-pass snap read better than one pass, where PHerc. 211's First Letters prize was won?

Registration: docs/preregistration/2026-11-20_first_letters_0211_snap_passes.md.

    compare OUT.json --winner-mesh --winner-maps --winner-render --studio --studio-mask --ours-render-map NPY
            --windings w033 w034 w035 w036
            --arm NAME FINALS RENDERS MAPS   (repeated: f124, rerun, dense2, dense2s3)
            [--sdt SDT_ZARR]

Finding 131's arms (f124, its rerun and its dense2) and this finding's dense2s3, the same densified windings snapped
three times, are scored as finding 131 scores its arms (dense_read.py: finding 110's transfer onto the winner's
surface and finding 124's statistic), on the cells all four arms reach. The change that counts is finding 131's
margin, max(0.02, twice the rerun's distance from finding 124).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dense_read as f131  # noqa: E402

ARMS = ["dense2", "dense2s3", "f124", "rerun"]


def verdict(
    r_f124: float | None,
    r_rerun: float | None,
    r_one: float | None,
    r_three: float | None,
    share: float | None,
    reproduces: bool,
) -> str:
    if (
        not reproduces
        or share is None
        or share < f131.f118.MIN_CELL_SHARE
        or None in (r_f124, r_rerun, r_one, r_three)
    ):
        return "DOES_NOT_RUN"
    m = f131.margin(r_rerun - r_f124)  # type: ignore[operator]
    change = round(r_three - r_one, 4)  # type: ignore[operator]
    if change >= m:
        return "SNAP3_READS_BETTER"
    if change <= -m:
        return "SNAP3_READS_WORSE"
    return "SNAP3_READS_SAME"


def geometry_gain(shares: dict) -> float | None:
    """The median over the windings of dense2s3's share of final nodes within 2 voxels of the predicted sheet, less
    dense2's; None without the distance field or a winding's share."""
    one, three = shares.get("dense2"), shares.get("dense2s3")
    if (
        not one
        or not three
        or set(one) != set(three)
        or None in one.values()
        or None in three.values()
    ):
        return None
    return round(float(np.median([three[w] - one[w] for w in one])), 4)


def consequence(verdict_: str, gain: float | None) -> str:
    """What finding 133 does: three passes if they read better, or read the same and sit more on the sheet."""
    if verdict_ == "SNAP3_READS_BETTER" or (
        verdict_ == "SNAP3_READS_SAME" and gain is not None and gain > 0
    ):
        return "three_passes"
    return "one_pass"


def compare_cmd(args: argparse.Namespace) -> dict:
    import cv2
    import tifffile

    winner = f131.tm.side(args.winner_mesh, args.winner_maps, args.winner_render, blind_too=False,
                          depth=f131.f121.DEPTH)  # fmt: skip
    canvas_w = (
        winner["ok"].shape[0] * f131.analysis.LATTICE,
        winner["ok"].shape[1] * f131.analysis.LATTICE,
    )
    studio = f131.analysis.block_mean(tifffile.imread(args.studio).astype(np.float64))
    mask_px = cv2.imread(str(args.studio_mask), cv2.IMREAD_GRAYSCALE)
    if mask_px is None:
        raise SystemExit(f"cannot read {args.studio_mask}")
    in_mask = f131.analysis.block_mean((mask_px > 0).astype(np.float64)) == 1.0
    own_render = f131.f124.read_studio(args.ours_render_map, canvas_w)
    base = winner["ok"] & in_mask & np.isfinite(studio) & np.isfinite(own_render)

    arms = {
        name: f131.carry_arm(
            winner, args.windings, Path(finals), Path(renders), Path(maps)
        )
        for name, finals, renders, maps in args.arm
    }
    result: dict = {
        "finding": 134,
        "windings": args.windings,
        "arms": {
            name: {"meshes": a["meshes"], "normal_cosine_median": a["cosines"]}
            for name, a in arms.items()
        },
    }
    if any(
        c is not None and c >= 0 for a in arms.values() for c in a["cosines"]
    ):  # as findings 124 and 131
        result.update({"verdict": "DOES_NOT_RUN", "why": "a render samples against the winner's normals",
                       "consequence": "one_pass"})  # fmt: skip
        return result
    common = base.copy()
    for a in arms.values():
        common &= f131.arm_cells(a)
    share = float(common.sum()) / max(int(in_mask.sum()), 1)
    own = {
        name: f131.scored(studio, a, base & f131.arm_cells(a))
        for name, a in arms.items()
    }
    reproduces = own.get("f124", {}).get("r") == f131.F124_R
    result.update({"mask_cells": int(in_mask.sum()), "cells": int(common.sum()), "cell_share": round(share, 4),
                   "f124_reproduced_on_its_own_cells": reproduces})  # fmt: skip
    registered = {name: f131.scored(studio, a, common) for name, a in arms.items()}
    r = {name: registered[name]["r"] for name in registered}
    result["registered"] = {
        "r": r,
        "noise_rerun_minus_f124": round(r["rerun"] - r["f124"], 4),
        "margin": f131.margin(r["rerun"] - r["f124"]),
        "change_dense2s3_minus_dense2": round(r["dense2s3"] - r["dense2"], 4),
    }
    result["verdict"] = verdict(
        r["f124"], r["rerun"], r["dense2"], r["dense2s3"], share, reproduces
    )
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
            name: f131.sheet_share(args.sdt, Path(finals), args.windings)
            for name, finals, _, _ in args.arm
        },
    }
    gain = geometry_gain(
        result["described"]["final_nodes_within_2_of_the_predicted_sheet"]
    )
    result["geometry_gain_dense2s3_minus_dense2"] = gain
    result["consequence"] = consequence(result["verdict"], gain)
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
    names = sorted(a[0] for a in args.arm)
    if names != ARMS:
        raise SystemExit(f"the arms are {', '.join(ARMS)}, not {names}")
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    result = compare_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "described"}, indent=1))
    return 0 if result["verdict"] != "DOES_NOT_RUN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
