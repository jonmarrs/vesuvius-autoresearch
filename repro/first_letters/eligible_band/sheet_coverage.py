"""Geometry only (no ink): at one slice of a band, how many predicted-sheet crossings have a winding on them?

usage: sheet_coverage.py SDT_ZARR UMBILICUS_JSON Z_WORKING OUT.json NAME=LIST_FILE [NAME=LIST_FILE...]

Each LIST_FILE names tifxyz folders (in working voxels), one per line. Each winding is cut by the plane z = Z: every
edge of its node grid whose two ends straddle Z gives one point, linearly interpolated, so the cut is a curve and not
the few nodes near Z (the recipe's nodes are 20 voxels apart). Along 360 rays from the published axis, one per degree,
the surface prediction's sheet (SDT level 1, two working voxels a grid voxel; values 1 to 127 are inside a sheet) is
cut into runs. A run is covered by a set when a cut point of one of its windings, within half a degree of the ray, lies
in the run widened by one grid voxel each way. Only runs whose middle lies between the innermost and outermost cut
point of the FIRST set on that ray, widened by the same grid voxel, are counted: the band's radial range. Reported per set: the runs counted, the share
covered, the share covered by two or more windings, and the share covered in each third of the range.

A run is not a sheet. The prediction can break one sheet into pieces along a ray or mark both its faces, so a share
under 1 does not by itself mean a sheet was missed: compare sets and bands measured the same way. Numbers only.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import tifffile
import zarr


def axis_at(umb: dict, z: float) -> tuple[float, float]:
    pts = sorted(umb["control_points"], key=lambda p: p["z"])
    zs = np.array([p["z"] for p in pts], float)
    return float(np.interp(z, zs, [p["x"] for p in pts])), float(
        np.interp(z, zs, [p["y"] for p in pts])
    )


def cut(wdir: str, z0: float) -> np.ndarray:
    """(N, 2) x, y where the winding's grid edges cross z0, in working voxels."""
    x, y, z = (tifffile.imread(f"{wdir}/{c}.tif").astype(np.float64) for c in "xyz")
    ok = np.isfinite(x) & (x > 0) & np.isfinite(z) & (z > 0)
    pts = []
    for a, b in (
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
    ):
        za, zb = z[a], z[b]
        both = ok[a] & ok[b] & ((za - z0) * (zb - z0) <= 0) & (za != zb)
        t = (z0 - za[both]) / (zb[both] - za[both])
        xa, xb, ya, yb = x[a][both], x[b][both], y[a][both], y[b][both]
        pts.append(np.stack([xa + t * (xb - xa), ya + t * (yb - ya)], 1))
    return np.concatenate(pts)


def sheet_runs(sl: np.ndarray, cx: float, cy: float) -> list[np.ndarray]:
    """Per degree, the (start, end) grid radii of each predicted-sheet run along the ray, end inclusive."""
    sheet = (sl >= 1) & (sl < 128)
    radii = np.arange(0, int(min(sl.shape) * 0.75))
    out = []
    for deg in range(360):
        a = np.deg2rad(deg)
        xs = np.round(cx + radii * np.cos(a)).astype(int)
        ys = np.round(cy + radii * np.sin(a)).astype(int)
        ok = (xs >= 0) & (xs < sl.shape[1]) & (ys >= 0) & (ys < sl.shape[0])
        s = np.zeros(len(radii), np.int8)
        s[ok] = sheet[ys[ok], xs[ok]]
        d = np.diff(np.concatenate([[0], s, [0]]))
        out.append(np.stack([np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1], 1))
    return out


def coverage(
    sl: np.ndarray, ax: float, ay: float, z0: float, sets: list[tuple[str, list[str]]]
) -> dict:
    runs = sheet_runs(sl, ax / 2, ay / 2)
    cuts = {}
    for name, dirs in sets:
        th, r, lab = [], [], []
        for k, wdir in enumerate(dirs):
            p = cut(wdir, z0)
            th.append(np.mod(np.rad2deg(np.arctan2(p[:, 1] - ay, p[:, 0] - ax)), 360))
            r.append(np.hypot(p[:, 0] - ax, p[:, 1] - ay) / 2)  # grid voxels
            lab.append(np.full(len(p), k))
        cuts[name] = (
            np.concatenate(th),
            np.concatenate(r),
            np.concatenate(lab),
            len(dirs),
        )

    def near(th: np.ndarray, deg: int) -> np.ndarray:
        return np.abs(((th - deg + 180) % 360) - 180) <= 0.5

    th0, r0, _, _ = cuts[sets[0][0]]
    span = {}
    for deg in range(360):
        sel = near(th0, deg)
        if sel.sum() >= 2:
            span[deg] = (float(r0[sel].min()), float(r0[sel].max()))
    out = {"range_from": sets[0][0], "degrees_with_range": len(span), "sets": {}}
    for name, (th, r, lab, n) in cuts.items():
        counted = covered = multi = 0
        thirds = [[0, 0], [0, 0], [0, 0]]
        for deg, (lo, hi) in span.items():
            sel = near(th, deg)
            rr, ll = r[sel], lab[sel]
            for s0, s1 in runs[deg]:
                mid = (s0 + s1) / 2
                if mid < lo - 1 or mid > hi + 1:
                    continue
                on = len(np.unique(ll[(rr >= s0 - 1) & (rr <= s1 + 1)]))
                t = min(2, int(3 * (mid - lo) / max(hi - lo, 1e-9)))
                counted += 1
                thirds[t][0] += 1
                covered += on >= 1
                thirds[t][1] += on >= 1
                multi += on >= 2
        out["sets"][name] = {
            "windings": n,
            "runs_counted": counted,
            "covered_share": round(covered / max(counted, 1), 4),
            "covered_by_two_or_more_share": round(multi / max(counted, 1), 4),
            "covered_share_by_third_of_range": [
                round(c / max(m, 1), 4) for m, c in thirds
            ],
        }
    return out


def main(argv: list[str]) -> dict:
    sdt_path, umb_path, z0, out_path = argv[0], argv[1], float(argv[2]), argv[3]
    sets = []
    for spec in argv[4:]:
        name, listfile = spec.split("=", 1)
        with open(listfile) as f:
            sets.append((name, [line.strip() for line in f if line.strip()]))
    with open(umb_path) as f:
        ax, ay = axis_at(json.load(f), z0)
    sl = np.asarray(zarr.open(sdt_path, mode="r")["1"][int(round(z0 / 2))])
    result = {"z_working": z0, "axis_xy_working": [round(ax, 1), round(ay, 1)]}
    result |= coverage(sl, ax, ay, z0, sets)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 6:
        raise SystemExit(__doc__)
    print(json.dumps(main(sys.argv[1:]), indent=1))
