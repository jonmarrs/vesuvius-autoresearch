"""How much of each read winding lies on its snapped sheet, and which way its normals point against the scroll axis.

Described after a band read; geometry only, no ink. For each winding of the arm:
- `inward_against_axis`: the share of the final (flattened) winding's grid normals whose x-y part points toward the
  published scroll axis at that node's z. The render offsets its layers along these normals, so where the share
  departs from 0 or 1 the winding's layers run one way over part of it and the other way over the rest;
- `inward_against_band_centre`: the same against the mean of every winding's nodes, as `studio_band.py orient`
  decided the render (for comparison);
- `final_on_snap`: of the final winding's nodes, the share whose nearest snapped node is within the lateral limit
  of `mesh_step_analysis.surface_distance` (`covered`), and the share within 2 voxels along its normal. Nodes not
  covered are surface the flatten made where the snap had none;
- the same inward share for the snapped winding, before the flatten;
- `trusted`: the share of the final winding's nodes that lie on the snapped sheet (covered, and within 2 voxels
  along its normal) and whose render layers run outward, as on PHerc. 211 where Studio drew the letters.

With --masks DIR, one 8-bit image per winding at grid resolution (one pixel per node, 20 render pixels):
255 on the snapped sheet with layers running outward; 128 on the snapped sheet with layers running inward (Studio
read the other side there); 64 off the snapped sheet (made by the flatten, or displaced); 0 no surface.

usage: band_geometry.py R ARM OUT.json [--masks DIR]
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

import band_index as bi  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402


def inward_share(xyz: np.ndarray, valid: np.ndarray, centre_of_z) -> float | None:
    """Share of grid normals whose x-y part points toward centre_of_z(z) (an (N, 2) array of x, y)."""
    normals, ok = analysis.grid_normals(xyz, valid)
    keep = valid & ok
    points, n = xyz[keep], normals[keep]
    radial = points[:, :2] - centre_of_z(points[:, 2])
    length = np.linalg.norm(radial, axis=1)
    good = length > 0
    if not good.any():
        return None
    dot = np.einsum("ij,ij->i", n[good][:, :2], radial[good] / length[good, None])
    return round(float((dot < 0).mean()), 4)


TRUSTED, OTHER_SIDE, OFF_SHEET = 255, 128, 64
ON_SHEET = 2.0  # voxels along the snapped sheet's normal


def node_classes(final: np.ndarray, final_valid: np.ndarray, snap: np.ndarray, snap_valid: np.ndarray, flip: bool,
                 centre_of_z) -> np.ndarray:  # fmt: skip
    """Per node of the final grid: TRUSTED, OTHER_SIDE, OFF_SHEET or 0 (see the module)."""
    from scipy.spatial import cKDTree

    normals, ok = analysis.grid_normals(final, final_valid)
    keep = final_valid & ok
    out = np.zeros(final_valid.shape, dtype=np.uint8)
    if not keep.any():
        return out
    points, n = final[keep], normals[keep]
    s_normals, s_ok = analysis.grid_normals(snap, snap_valid)
    s_keep = snap_valid & s_ok
    if not s_keep.any():
        out[keep] = OFF_SHEET
        return out
    s_points, s_n = snap[s_keep], s_normals[s_keep]
    _, index = cKDTree(s_points).query(points, k=1)
    offset = points - s_points[index]
    along = np.einsum("ij,ij->i", offset, s_n[index])
    lateral = np.sqrt(np.maximum((offset**2).sum(1) - along**2, 0.0))
    on_sheet = (lateral <= analysis.LATERAL_MAX) & (np.abs(along) <= ON_SHEET)
    radial = points[:, :2] - centre_of_z(points[:, 2])
    inward = np.einsum("ij,ij->i", n[:, :2], radial) < 0
    outward_layers = (
        inward if flip else ~inward
    )  # a flipped render offsets its layers along -n
    out[keep] = np.where(
        on_sheet, np.where(outward_layers, TRUSTED, OTHER_SIDE), OFF_SHEET
    )
    return out


def axis_centre(umbilicus: np.ndarray):
    def centre(z: np.ndarray) -> np.ndarray:
        return np.stack(
            [
                np.interp(z, umbilicus[0], umbilicus[1]),
                np.interp(z, umbilicus[0], umbilicus[2]),
            ],
            1,
        )

    return centre


def fixed_centre(xy: np.ndarray):
    def centre(z: np.ndarray) -> np.ndarray:
        return np.broadcast_to(xy, (len(z), 2))

    return centre


def geometry(root: Path, arm: str, masks: Path | None = None) -> dict:
    import cv2

    work = root / "work"
    names = (work / f"windings_{arm}.txt").read_text().split()
    orient = json.loads((work / f"studio_{arm}" / "orient.json").read_text())[
        "windings"
    ]
    if masks is not None:
        masks.mkdir(parents=True, exist_ok=True)
    finals = {
        n: analysis.load_tifxyz(work / f"final_{arm}" / f"{n}.tifxyz") for n in names
    }
    band = np.concatenate([xyz[v] for xyz, v in finals.values()]).mean(0)[:2]
    on_axis = axis_centre(bi.axis(root / "dataset" / "umbilicus.json"))
    out: dict = {"band_centre_xy": [round(float(c), 1) for c in band], "windings": {}}
    for n, (xyz, valid) in finals.items():
        snap, snap_valid = analysis.load_tifxyz(work / f"snap_{arm}" / n)
        d = analysis.surface_distance(xyz, valid, snap, snap_valid)
        classes = node_classes(
            xyz, valid, snap, snap_valid, orient[n]["render"] == "flip", on_axis
        )
        if masks is not None:
            cv2.imwrite(str(masks / f"{n}.png"), classes)
        surface = int((classes > 0).sum())
        out["windings"][n] = {
            "render": orient[n]["render"],
            "trusted": round(float((classes == TRUSTED).sum()) / surface, 4)
            if surface
            else None,
            "other_side": round(float((classes == OTHER_SIDE).sum()) / surface, 4)
            if surface
            else None,
            "inward_against_axis": inward_share(xyz, valid, on_axis),
            "inward_against_band_centre": inward_share(xyz, valid, fixed_centre(band)),
            "snapped_inward_against_axis": inward_share(snap, snap_valid, on_axis),
            "final_on_snap": {
                "covered": round(d["covered_fraction"], 4),
                "within_2": round(d["fraction_within"]["2"], 4),
            },
        }
    w = out["windings"].values()

    def med(values) -> float:
        return round(float(np.median([v for v in values if v is not None])), 4)

    out["summary"] = {
        "windings": len(out["windings"]),
        "inward_against_axis": {
            "median": med(x["inward_against_axis"] for x in w),
            "min": min(x["inward_against_axis"] for x in w),
            "max": max(x["inward_against_axis"] for x in w),
        },
        "inward_against_band_centre_median": med(x["inward_against_band_centre"] for x in w),
        "trusted_median": med(x["trusted"] for x in w),
        "other_side_median": med(x["other_side"] for x in w),
        "snapped_inward_against_axis_median": med(x["snapped_inward_against_axis"] for x in w),
        "final_on_snap_covered_median": med(x["final_on_snap"]["covered"] for x in w),
        "final_on_snap_within_2_median": med(x["final_on_snap"]["within_2"] for x in w),
        "rendered_against_the_axis_rule": sorted(
            n for n, x in out["windings"].items()
            if (x["inward_against_axis"] > 0.5) != (x["inward_against_band_centre"] > 0.5)
        ),
    }  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("arm")
    ap.add_argument("out", type=Path)
    ap.add_argument("--masks", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    result = geometry(args.root, args.arm, args.masks)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
