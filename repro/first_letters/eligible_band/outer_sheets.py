"""Geometry only (no ink): at a band slice, how many predicted-sheet crossings lie beyond a fitted winding?

usage: outer_sheets.py SDT_ZARR UMBILICUS_JSON Z_WORKING WINDING_DIR [WINDING_DIR...]
For each winding (a tifxyz folder in working voxels), at the slice z (within 3 voxels), its radius from the axis
by angle. Along 360 rays from the axis, the predicted sheet (SDT 1..127, positive outside, 0 = no data) is cut
into runs; reported: per winding, the median over angles of the number of sheet runs beyond its radius + 4 grid
voxels, and the median outermost sheet radius vs the winding's radius. Numbers only.
"""

import json
import sys

import numpy as np
import tifffile
import zarr


def axis_at(umb, z):
    pts = sorted(umb["control_points"], key=lambda p: p["z"])
    zs = np.array([p["z"] for p in pts], float)
    return float(np.interp(z, zs, [p["x"] for p in pts])), float(
        np.interp(z, zs, [p["y"] for p in pts])
    )


def main():
    sdt_path, umb_path, z = sys.argv[1], sys.argv[2], float(sys.argv[3])
    windings = sys.argv[4:]
    umb = json.load(open(umb_path))
    ax, ay = axis_at(umb, z)
    arr = zarr.open(sdt_path, mode="r")["1"]
    zg = int(round(z / 2))
    sl = np.asarray(arr[zg])  # (y, x) at 2x working voxels
    sheet = (sl >= 1) & (sl < 128)
    data = sl > 0
    cx, cy = ax / 2, ay / 2
    rmax = int(min(sl.shape) * 0.75)
    radii = np.arange(0, rmax)
    out = {
        "z_working": z,
        "axis_xy_working": [round(ax, 1), round(ay, 1)],
        "sheet_share_of_data": round(float(sheet.sum() / max(data.sum(), 1)), 4),
    }
    angles = np.deg2rad(np.arange(360))
    rays_sheet, rays_data = [], []
    for a in angles:
        xs = np.round(cx + radii * np.cos(a)).astype(int)
        ys = np.round(cy + radii * np.sin(a)).astype(int)
        ok = (xs >= 0) & (xs < sl.shape[1]) & (ys >= 0) & (ys < sl.shape[0])
        s = np.zeros(len(radii), bool)
        d = np.zeros(len(radii), bool)
        s[ok] = sheet[ys[ok], xs[ok]]
        d[ok] = data[ys[ok], xs[ok]]
        rays_sheet.append(s)
        rays_data.append(d)
    outermost = []
    for s in rays_sheet:
        idx = np.flatnonzero(s)
        outermost.append(int(idx[-1]) if len(idx) else -1)
    out["outermost_sheet_radius_working_median"] = 2 * float(
        np.median([o for o in outermost if o >= 0])
    )
    out["outermost_data_radius_working_median"] = 2 * float(
        np.median([int(np.flatnonzero(d)[-1]) if d.any() else -1 for d in rays_data])
    )
    per = {}
    for wdir in windings:
        x = tifffile.imread(f"{wdir}/x.tif").astype(float)
        y = tifffile.imread(f"{wdir}/y.tif").astype(float)
        zz = tifffile.imread(f"{wdir}/z.tif").astype(float)
        m = np.isfinite(x) & (x > 0) & (np.abs(zz - z) <= 3)
        if not m.any():
            per[wdir.rstrip("/").split("/")[-1]] = None
            continue
        th = np.mod(np.rad2deg(np.arctan2(y[m] - ay, x[m] - ax)), 360).astype(int)
        r = np.hypot(x[m] - ax, y[m] - ay) / 2  # grid voxels
        beyond, gap = [], []
        for deg in range(360):
            sel = th == deg
            if not sel.any():
                continue
            rw = float(np.median(r[sel]))
            s = rays_sheet[deg][int(rw) + 4 :]
            runs = int(
                np.sum(np.diff(s.astype(int)) == 1) + (1 if len(s) and s[0] else 0)
            )
            beyond.append(runs)
            if outermost[deg] >= 0:
                gap.append(2 * (outermost[deg] - rw))
        per[wdir.rstrip("/").split("/")[-1]] = {
            "angles": len(beyond),
            "radius_working_median": round(2 * float(np.median(r)), 1),
            "sheet_runs_beyond_median": float(np.median(beyond)) if beyond else None,
            "sheet_runs_beyond_p10_p90": [
                float(np.percentile(beyond, 10)),
                float(np.percentile(beyond, 90)),
            ]
            if beyond
            else None,
            "outermost_sheet_minus_winding_radius_working_median": round(
                float(np.median(gap)), 1
            )
            if gap
            else None,
        }
    out["windings"] = per
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
