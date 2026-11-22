"""Finding 137: does a fit declared to turn the wrong way still read the text at PHerc. 211's winner place?

Registration: docs/preregistration/2026-11-22_first_letters_0211_wrong_hand_read.md.

    choose   FIT_MESH_DIR WINNER_TIFXYZ OUT.json LIST.txt
             Every raw winding of a fit against the winner's surface in the band: the winner's lattice points
             (4-pixel blocks, finding 110's) within ACCEPT voxels of the winding's own lattice points. The N
             windings with the most such points are read (N = 4, as finding 121; ties by name; villa's
             wNNN_spliced copies are not windings of the fit). On finding 119's
             fit this rule gives w035, w033, w036, w034: finding 121's four windings.
    compare  OUT.json --winner-mesh --winner-maps --winner-render --studio --studio-mask --ours-render-map NPY
             --arm NAME FINALS RENDERS MAPS ORIENT LIST   (twice: right, wrong)
             Each arm's windings (LIST) after snap, flatten and render: FINALS/wNNN.tifxyz, RENDERS/wNNN_66.zarr,
             Studio's maps MAPS/wNNN.npy and MAPS/wNNN_reversed.npy, and ORIENT, end_to_end.py orient's record
             of which renders were flipped ("-": all flipped, finding 121's). Each arm is carried onto the
             winner's surface by finding 110's transfer and scored with finding 124's statistic on its own cells,
             as finding 124 scored its windings; the right arm must give finding 124's r again.

The registered numbers are the wrong arm's r, its two controls and its share of the winner's mask cells, against
the right arm's (finding 124's own windings and maps: r 0.8247).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pherc343" / "mesh_step"))
sys.path.insert(0, str(HERE.parent / "eligible_band"))

import compare_readers as f120  # noqa: E402
import dense_read as f131  # noqa: E402
import end_to_end as f121  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402
import studio_e2e as f124  # noqa: E402
import transfer_maps as tm  # noqa: E402

Z_BEGIN, Z_END = 7650, 9150  # the band of findings 119 and 121
N_READ = 4
NEAR = 2.0  # voxels, described union coverage
MARGIN = 0.05  # r below the right arm's that still counts as alike
SHARE_ALIKE = 0.8  # of the right arm's cell share
SHARE_PARTLY = 0.25  # of the winner's mask cells
PARTLY, RATIO = f124.PARTLY, f124.RATIO  # 0.40, 2.0
F124_R = f131.F124_R  # 0.8247


def winner_points(winner_mesh: Path) -> np.ndarray:
    """The winner's lattice points inside the band."""
    xyz, valid = analysis.load_tifxyz(winner_mesh)
    points, ok = analysis.lattice_points(xyz, valid)
    inside = ok & (points[..., 2] >= Z_BEGIN) & (points[..., 2] < Z_END)
    return points[inside]


def choose(fit_meshes: Path, winner_mesh: Path, n: int = N_READ) -> dict:
    from scipy.spatial import cKDTree

    query = winner_points(winner_mesh)
    counts: dict[str, int] = {}
    nearest = np.full(len(query), np.inf)
    for mesh in sorted(
        p
        for p in fit_meshes.iterdir()
        if re.fullmatch(r"w[0-9]+", p.name) and (p / "x.tif").exists()
    ):
        xyz, valid = analysis.load_tifxyz(mesh)
        points, ok = analysis.lattice_points(xyz, valid)
        if not ok.any():
            counts[mesh.name] = 0
            continue
        d, _ = cKDTree(points[ok]).query(query, distance_upper_bound=analysis.ACCEPT)
        counts[mesh.name] = int(np.isfinite(d).sum())
        nearest = np.minimum(nearest, d)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    chosen = [name for name, c in ranked[:n] if c > 0]
    return {
        "winner_points_in_band": int(len(query)),
        "windings": len(counts),
        "chosen": chosen,
        "points_within_accept": dict(ranked[: max(n * 2, 8)]),
        "described": {
            "winner_points_within_2_of_any_winding": round(
                float((nearest <= NEAR).mean()), 4
            ),
            "winner_points_within_accept_of_any_winding": round(
                float(np.isfinite(nearest).mean()), 4
            ),
        },
        "rule": f"the {n} raw windings with the most winner lattice points within {analysis.ACCEPT} voxels",
    }


def flips(orient: str, windings: list[str]) -> dict[str, bool]:
    """Which renders were flipped: end_to_end.py orient's record, or '-' for finding 121's (all flipped)."""
    if orient == "-":
        return {w: True for w in windings}
    record = json.loads(Path(orient).read_text())
    out = {}
    for w in windings:
        decision = record[f"{w}.tifxyz"]["render"]
        if decision not in ("flip", "keep"):
            raise SystemExit(f"{orient}: no render decision for {w}")
        out[w] = decision == "flip"
    return out


def carry_arm(
    winner: dict, windings: list[str], finals: Path, renders: Path, maps: Path
) -> dict:
    sides = []
    for w in windings:
        s = f131.side(finals / f"{w}.tifxyz", renders / f"{w}_66.zarr")
        s["studio"] = f124.read_studio(maps / f"{w}.npy", s["canvas"])
        s["studio_reversed"] = f124.read_studio(maps / f"{w}_reversed.npy", s["canvas"])
        sides.append(s)
    which, cell, dist = analysis.transfer(
        winner["points"], winner["ok"], [(s["points"], s["ok"]) for s in sides]
    )
    return {
        "which": which,
        "dist": dist,
        "cosines": [analysis.normals_agree(winner["points"], s["points"], which, cell, k) for k, s in enumerate(sides)],
        "carried": f121.carry([{"s": s["studio"]} for s in sides], which, cell)["s"],
        "other": f121.carry([{"s": s["studio_reversed"]} for s in sides], which, cell)["s"],
    }  # fmt: skip


def sampled_along_the_winner(cosines: list[float | None], flipped: list[bool]) -> bool:
    """Every render's layers run the winner's way: a flipped render where the normals disagree, kept where they agree."""
    return all(
        c is not None and (c < 0) == f for c, f in zip(cosines, flipped, strict=True)
    )


def verdict(right: dict | None, wrong: dict | None, reproduces: bool) -> str:
    """The registered table. right/wrong: {"r", "control_wrong_side", "control_slid", "cell_share"}."""
    if not reproduces or right is None or wrong is None:
        return "DOES_NOT_RUN"
    r, share = wrong.get("r"), wrong.get("cell_share")
    controls = [
        wrong.get("control_wrong_side"),
        (wrong.get("control_slid") or {}).get("largest_absolute"),
    ]
    if share is None:
        return "DOES_NOT_RUN"
    if share < SHARE_PARTLY or r is None or None in controls:
        return "WRONG_HAND_DOES_NOT_READ"
    clear = all(r >= RATIO * abs(c) for c in controls)
    if (
        clear
        and r >= right["r"] - MARGIN
        and share >= SHARE_ALIKE * right["cell_share"]
    ):
        return "WRONG_HAND_READS_ALIKE"
    if clear and r >= PARTLY:
        return "WRONG_HAND_READS_PARTLY"
    return "WRONG_HAND_DOES_NOT_READ"


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

    result: dict = {"finding": 137, "arms": {}}
    arms = {}
    for name, finals, renders, maps, orient, listing in args.arm:
        windings = Path(listing).read_text().split()
        flipped = flips(orient, windings)
        arm = carry_arm(winner, windings, Path(finals), Path(renders), Path(maps))
        arms[name] = arm
        result["arms"][name] = {
            "windings": windings,
            "flipped": [flipped[w] for w in windings],
            "normal_cosine_median": arm["cosines"],
            "sampled_along_the_winner": sampled_along_the_winner(arm["cosines"], [flipped[w] for w in windings]),
        }  # fmt: skip
    if not all(a["sampled_along_the_winner"] for a in result["arms"].values()):
        result.update(
            {
                "verdict": "DOES_NOT_RUN",
                "why": "a render samples against the winner's normals",
            }
        )
        return result
    mask_cells = max(int(in_mask.sum()), 1)
    own = {}
    for name, arm in arms.items():
        cells = base & f131.arm_cells(arm)
        own[name] = {
            **f131.scored(studio, arm, cells),
            "cell_share": round(float(cells.sum()) / mask_cells, 4),
        }
    reproduces = own["right"]["r"] == F124_R
    keys = ("r", "control_wrong_side", "control_slid", "cell_share")
    result.update(
        {
            "mask_cells": int(in_mask.sum()),
            "f124_reproduced": reproduces,
            "registered": {name: {k: own[name][k] for k in keys} for name in own},
        }
    )
    result["verdict"] = verdict(
        result["registered"]["right"], result["registered"]["wrong"], reproduces
    )
    common = base & f131.arm_cells(arms["right"]) & f131.arm_cells(arms["wrong"])
    by_winding = {}
    for name, arm in arms.items():
        hp = analysis.highpass(
            f120.standardise(arm["carried"], base & f131.arm_cells(arm)),
            base & f131.arm_cells(arm),
        )
        theirs = analysis.highpass(studio, base & f131.arm_cells(arm))
        mine = {}
        for k, w in enumerate(result["arms"][name]["windings"]):
            sel = base & f131.arm_cells(arm) & (arm["which"] == k)
            mine[w] = {
                "cells": int(sel.sum()),
                "r": f124.f118._rounded(analysis.pearson(theirs[sel], hp[sel]))
                if sel.sum() >= f121.MIN_WINDING_CELLS
                else None,
            }
        by_winding[name] = mine
    result["described"] = {
        "each_arm_on_its_own_cells": own,
        "both_arms_on_their_common_cells": {
            "cells": int(common.sum()),
            "cell_share": round(float(common.sum()) / mask_cells, 4),
            **{name: f131.scored(studio, arm, common) for name, arm in arms.items()},
        },
        "only_the_wrong_arm_reaches": round(
            float(
                (
                    base
                    & f131.arm_cells(arms["wrong"])
                    & ~f131.arm_cells(arms["right"])
                ).sum()
            )
            / mask_cells,
            4,
        ),
        "by_winding": by_winding,
        "transfer_distance_voxels": {
            name: dict(
                zip(
                    ("p50", "p95"),
                    (
                        round(float(q), 2)
                        for q in np.percentile(
                            arm["dist"][base & f131.arm_cells(arm)], [50, 95]
                        )
                    ),
                    strict=True,
                )
            )
            for name, arm in arms.items()
        },  # fmt: skip
    }
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    ch = sub.add_parser("choose")
    ch.add_argument("fit_meshes", type=Path)
    ch.add_argument("winner_mesh", type=Path)
    ch.add_argument("out", type=Path)
    ch.add_argument("listing", type=Path)
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
    c.add_argument("--arm", nargs=6, action="append", required=True,
                   metavar=("NAME", "FINALS", "RENDERS", "MAPS", "ORIENT", "LIST"))  # fmt: skip
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    if args.command == "choose":
        if args.listing.exists():
            print(f"{args.listing} exists", file=sys.stderr)
            return 2
        result = choose(args.fit_meshes, args.winner_mesh)
        if not result["chosen"]:
            print("no winding reaches the winner's surface", file=sys.stderr)
            args.out.write_text(json.dumps(result, indent=1) + "\n")
            return 1
        args.listing.write_text("\n".join(result["chosen"]) + "\n")
    else:
        if sorted(a[0] for a in args.arm) != ["right", "wrong"]:
            raise SystemExit("the arms are right and wrong")
        result = compare_cmd(args)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("described", "points_within_accept")
            },
            indent=1,
        )
    )
    return 0 if result.get("verdict") != "DOES_NOT_RUN" else 1


if __name__ == "__main__":
    sys.exit(main())
