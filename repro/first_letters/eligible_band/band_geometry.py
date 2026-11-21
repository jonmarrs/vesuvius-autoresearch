"""Where each read winding lies on the predicted sheet, and which way its normals point against the scroll axis.

Described after a band read; geometry only, no ink. For each winding of the arm:
- `inward_against_axis`: the share of the final (flattened) winding's grid normals whose x-y part points toward the
  published scroll axis at that node's z. The render offsets its layers along these normals (`--flip-normals`
  negates them), so where the share departs from 0 or 1 the layers run one way over part of the winding and the other
  way over the rest. `inward_against_band_centre` is the same against the mean of every winding's nodes, as
  `studio_band.py orient` decided the render; `snapped_inward_against_axis` the same for the snapped winding.
- `predicted_sheet`: the surface prediction's signed distance field (the one the fit and the snap used; at or below 0
  inside the predicted sheet) read at the snapped winding's nodes and at the final winding's nodes: the share inside
  (`on_sheet`) and within 2 voxels (`within_2`), and for the final winding the share within 2 voxels in the inner,
  middle and outer third of its radii from the axis. The final grid samples the snapped surface's triangles evenly;
  the snapped grid is even in angle, so its cells are largest at large radius, where a flat triangle can leave a
  curved sheet between nodes that are on it.
- `on_snapped_triangles`: the share of the final winding's nodes within 2 voxels of the snapped winding's triangles
  (the flatten's export samples them barycentrically; a node off them is an export fault).
- `trusted`: the share of the final winding's nodes within 2 voxels of the predicted sheet whose render layers run
  outward, as on PHerc. 211 where Studio drew the letters; `other_side` the share within 2 voxels with layers inward.

Nearest-node distances between the final and snapped grids are not used: at large radius the snapped nodes are tens
of voxels apart, and such distances there measure the grid's spacing, not the surface.

With --masks DIR, one 8-bit image per winding at grid resolution (one pixel per node, 20 render pixels):
255 within 2 voxels of the predicted sheet with layers running outward; 128 within 2 voxels with layers running inward
(Studio read the other side there); 64 further from the predicted sheet, or outside its field; 0 no surface.

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

import band_fit_quality as quality  # noqa: E402
import band_index as bi  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402

TRUSTED, OTHER_SIDE, OFF_SHEET = 255, 128, 64
NEAR = 2.0  # voxels: within this of the predicted sheet, or of the snapped triangles


def inward(
    xyz: np.ndarray, valid: np.ndarray, centre_of_z
) -> tuple[np.ndarray, np.ndarray]:
    """Per node with a normal: whether its normal's x-y part points toward centre_of_z(z); and that node mask."""
    normals, ok = analysis.grid_normals(xyz, valid)
    keep = valid & ok
    points, n = xyz[keep], normals[keep]
    radial = points[:, :2] - centre_of_z(points[:, 2])
    return np.einsum("ij,ij->i", n[:, :2], radial) < 0, keep


def inward_share(xyz: np.ndarray, valid: np.ndarray, centre_of_z) -> float | None:
    towards, keep = inward(xyz, valid, centre_of_z)
    return round(float(towards.mean()), 4) if keep.any() else None


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


def _closest_on_triangles(
    p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray
) -> np.ndarray:
    """Distance from each point to its triangle (Ericson, Real-Time Collision Detection, 5.1.5), row by row."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = va + vb + vc
        v, w = vb / denom, vc / denom
        closest = a + ab * v[:, None] + ac * w[:, None]
        regions = [
            ((d1 <= 0) & (d2 <= 0), a),
            ((d3 >= 0) & (d4 <= d3), b),
            ((d6 >= 0) & (d5 <= d6), c),
            ((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + ab * (d1 / (d1 - d3))[:, None]),
            ((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + ac * (d2 / (d2 - d6))[:, None]),
            ((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None]),
        ]  # fmt: skip
    for mask, point in regions:
        closest[mask] = point[mask]
    return np.linalg.norm(p - closest, axis=-1)


def distance_to_triangles(
    points: np.ndarray, grid: np.ndarray, valid: np.ndarray, k: int = 12
) -> np.ndarray:
    """Distance from each point to the nearest triangle of a tifxyz grid (cells split as VC splits them)."""
    from scipy.spatial import cKDTree

    p00, p10, p01, p11 = grid[:-1, :-1], grid[1:, :-1], grid[:-1, 1:], grid[1:, 1:]
    ok = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
    a = np.concatenate([p00[ok], p10[ok]]).astype(np.float64)
    b = np.concatenate([p10[ok], p11[ok]]).astype(np.float64)
    c = np.concatenate([p01[ok], p01[ok]]).astype(np.float64)
    if len(a) == 0:
        return np.full(len(points), np.inf)
    k = min(k, len(a))
    _, index = cKDTree((a + b + c) / 3).query(points, k=k)
    index = np.asarray(index).reshape(len(points), k)
    best = np.full(len(points), np.inf)
    for j in range(k):
        i = index[:, j]
        best = np.minimum(best, _closest_on_triangles(points, a[i], b[i], c[i]))
    return best


def node_classes(
    final: np.ndarray, final_valid: np.ndarray, field, flip: bool, centre_of_z
) -> np.ndarray:
    """Per node of the final grid: TRUSTED, OTHER_SIDE, OFF_SHEET or 0 (see the module). `field` needs `.at()`."""
    towards, keep = inward(final, final_valid, centre_of_z)
    out = np.zeros(final_valid.shape, dtype=np.uint8)
    if not keep.any():
        return out
    d = field.at(final[keep].astype(np.float64))
    near = np.isfinite(d) & (d <= NEAR)
    outward_layers = (
        towards if flip else ~towards
    )  # a flipped render offsets its layers along -n
    out[keep] = np.where(near, np.where(outward_layers, TRUSTED, OTHER_SIDE), OFF_SHEET)
    return out


def _sheet(field, xyz: np.ndarray, valid: np.ndarray) -> dict:
    d = field.at(xyz[valid].astype(np.float64))
    ok = np.isfinite(d)
    return {
        "on_sheet": round(float((d[ok] <= 0).mean()), 4) if ok.any() else None,
        "within_2": round(float((d[ok] <= NEAR).mean()), 4) if ok.any() else None,
        "outside_field": round(float(1 - ok.mean()), 4),
    }


def geometry(root: Path, arm: str, masks: Path | None = None, field=None) -> dict:
    import cv2

    work = root / "work"
    names = (work / f"windings_{arm}.txt").read_text().split()
    orient = json.loads((work / f"studio_{arm}" / "orient.json").read_text())[
        "windings"
    ]
    if field is None:
        field = quality.DistanceField(
            sorted((work / "surf_sdt").glob("*_surf_sdt.ome.zarr"))[0], "1"
        )
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
        classes = node_classes(
            xyz, valid, field, orient[n]["render"] == "flip", on_axis
        )
        if masks is not None:
            cv2.imwrite(str(masks / f"{n}.png"), classes)
        surface = int((classes > 0).sum())
        points = xyz[valid].astype(np.float64)
        d = field.at(points)
        radius = np.linalg.norm(points[:, :2] - on_axis(points[:, 2]), axis=1)
        terciles = np.digitize(radius, np.percentile(radius, [100 / 3, 200 / 3]))
        final_sheet = _sheet(field, xyz, valid)
        final_sheet["within_2_by_radius_tercile"] = [
            round(float((d[(terciles == k) & np.isfinite(d)] <= NEAR).mean()), 4)
            if ((terciles == k) & np.isfinite(d)).any() else None
            for k in range(3)
        ]  # fmt: skip
        on_triangles = distance_to_triangles(points, snap, snap_valid)
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
            "predicted_sheet": {
                "snapped": _sheet(field, snap, snap_valid),
                "final": final_sheet,
            },
            "on_snapped_triangles": round(float((on_triangles <= NEAR).mean()), 4),
        }
    w = list(out["windings"].values())

    def med(values) -> float | None:
        v = [x for x in values if x is not None]
        return round(float(np.median(v)), 4) if v else None

    out["summary"] = {
        "windings": len(w),
        "inward_against_axis": {
            "median": med(x["inward_against_axis"] for x in w),
            "min": min(x["inward_against_axis"] for x in w),
            "max": max(x["inward_against_axis"] for x in w),
        },
        "inward_against_band_centre_median": med(x["inward_against_band_centre"] for x in w),
        "snapped_inward_against_axis_median": med(x["snapped_inward_against_axis"] for x in w),
        "trusted_median": med(x["trusted"] for x in w),
        "other_side_median": med(x["other_side"] for x in w),
        "predicted_sheet_within_2_median": {
            "snapped": med(x["predicted_sheet"]["snapped"]["within_2"] for x in w),
            "final": med(x["predicted_sheet"]["final"]["within_2"] for x in w),
        },
        "predicted_sheet_on_sheet_median": {
            "snapped": med(x["predicted_sheet"]["snapped"]["on_sheet"] for x in w),
            "final": med(x["predicted_sheet"]["final"]["on_sheet"] for x in w),
        },
        "final_within_2_by_radius_tercile_median": [
            med(x["predicted_sheet"]["final"]["within_2_by_radius_tercile"][k] for x in w) for k in range(3)
        ],
        "on_snapped_triangles_median": med(x["on_snapped_triangles"] for x in w),
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
