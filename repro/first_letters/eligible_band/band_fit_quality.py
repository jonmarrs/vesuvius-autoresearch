"""Are a fit's raw windings on predicted sheets? A measurement that needs no published windings.

For every raw winding a fit wrote, the signed distance field of the surface prediction (the one the fit was
given) is read at the winding's nodes, and again at the same nodes moved along the winding's own normal. A
winding that follows a sheet has more of its nodes inside the predicted sheet than its displaced copies do.

    on_sheet   share of nodes whose distance value is <= 0 (inside the predicted sheet)
    displaced  the same share for the nodes moved by +DISPLACE and by -DISPLACE voxels, averaged
    excess     on_sheet - displaced

usage: band_fit_quality.py OUT.json SDT_ZARR MESH_DIR [--group 1]
       MESH_DIR holds wNNN folders (tifxyz); wNNN_spliced twins are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402

DISPLACE = (
    6.0  # voxels along the winding's normal; about half the sheet spacing on PHerc. 343
)
MIN_NODES = 1000  # a winding with fewer nodes inside the distance field is not scored
NODATA = 0  # make_surf_sdt writes 0 where it has no value; distances are stored as value - offset


class DistanceField:
    """make_surf_sdt's array at one group: distance in working voxels, positive outside the sheet."""

    def __init__(self, store: Path, group: str):
        import zarr

        attrs = json.loads((store / ".zattrs").read_text())
        self.offset = float(attrs["offset"])
        self.unit = float(attrs["unit_working_voxels"])
        # group "1" is the surface prediction's own grid: scale_vs_working working voxels a cell
        self.scale = float(attrs["scale_vs_working"]) * 2 ** (int(group) - 1)
        self.array = zarr.open_group(str(store), mode="r")[group]

    def at(self, xyz: np.ndarray) -> np.ndarray:
        """Distance at points given as (n, 3) x, y, z in working voxels; NaN where there is no value."""
        index = np.rint(xyz[:, ::-1] / self.scale).astype(np.int64)
        shape = np.array(self.array.shape)
        inside = ((index >= 0) & (index < shape)).all(1)
        out = np.full(len(xyz), np.nan)
        if not inside.any():
            return out
        idx = index[inside]
        lo, hi = idx.min(0), idx.max(0) + 1
        block = np.asarray(self.array[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]])
        raw = block[tuple((idx - lo).T)].astype(np.float64)
        out[inside] = np.where(raw == NODATA, np.nan, (raw - self.offset) * self.unit)
        return out


def score(field, xyz: np.ndarray, valid: np.ndarray) -> dict | None:
    """One winding. `field` needs only `.at(points)`."""
    normals, has_normal = analysis.grid_normals(xyz, valid)
    use = valid & has_normal
    points, n = xyz[use], normals[use]
    here = field.at(points)
    plus = field.at(points + DISPLACE * n)
    minus = field.at(points - DISPLACE * n)
    ok = np.isfinite(here) & np.isfinite(plus) & np.isfinite(minus)
    if int(ok.sum()) < MIN_NODES:
        return None
    on_sheet = float((here[ok] <= 0).mean())
    displaced = float(((plus[ok] <= 0).mean() + (minus[ok] <= 0).mean()) / 2)
    return {
        "nodes": int(use.sum()),
        "nodes_scored": int(ok.sum()),
        "on_sheet": round(on_sheet, 4),
        "displaced": round(displaced, 4),
        "excess": round(on_sheet - displaced, 4),
        "abs_distance_median": round(float(np.median(np.abs(here[ok]))), 2),
    }


def summarise(windings: dict[str, dict | None]) -> dict:
    scored = {k: v for k, v in windings.items() if v is not None}
    if not scored:
        return {"windings": len(windings), "windings_scored": 0}
    excess = np.array([v["excess"] for v in scored.values()])
    on_sheet = np.array([v["on_sheet"] for v in scored.values()])
    return {
        "windings": len(windings),
        "windings_scored": len(scored),
        "excess_median": round(float(np.median(excess)), 4),
        "excess_p10": round(float(np.percentile(excess, 10)), 4),
        "excess_p90": round(float(np.percentile(excess, 90)), 4),
        "share_of_windings_with_positive_excess": round(float((excess > 0).mean()), 4),
        "on_sheet_median": round(float(np.median(on_sheet)), 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("sdt")
    ap.add_argument("meshes")
    ap.add_argument("--group", default="1")
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    field = DistanceField(Path(args.sdt), args.group)
    windings: dict[str, dict | None] = {}
    for folder in sorted(Path(args.meshes).glob("w*")):
        if folder.name.endswith("_spliced") or not (folder / "x.tif").exists():
            continue
        xyz, valid = analysis.load_tifxyz(folder)
        windings[folder.name] = score(field, xyz, valid)
    result = {
        "sdt": args.sdt,
        "meshes": args.meshes,
        "displace_voxels": DISPLACE,
        "summary": summarise(windings),
        "windings": windings,
    }
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
