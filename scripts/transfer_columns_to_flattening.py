#!/usr/bin/env python3
"""Move column boxes from one flattening of a scroll to another, via the shared 3D scan.

Motivation (2026-08-16): ScrollGT's column family has one target. A genuinely independent
second reading does not exist in published artifacts -- PHerc 0172's reading image is
unannotated disconnected patches, and Scroll 1's would require deriving boxes from ink,
which would make a column-vs-gutter metric measure agreement with an ink-detection output.
What IS available is the same 1667 reading on a different flattening of the same winding,
which tests whether a column-level score survives a change of geometry.

Method: both flattenings store a 3D point per grid cell (tifxyz). For each source cell
inside a column, look up its 3D point, find the nearest point in the destination
flattening, and take that cell's coordinates. A column's destination extent is the envelope
of its mapped cells.

What this deliberately does NOT do:
  * it does not read ink, so column identities stay anchored to the papyrological reading;
  * it does not clip a column silently -- a column whose envelope leaves the destination
    grid is reported `fully_inside: False` and excluded upstream;
  * it does not bridge invalid cells. tifxyz marks them (-1, -1, -1); treating those as
    real points would invent correspondence where the surface has none.

Usage:
    uv run python scripts/transfer_columns_to_flattening.py --help
"""

import argparse
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _valid_mask(xyz):
    """Cells with a real 3D point. tifxyz marks invalid as (-1,-1,-1); zeros are also unset."""
    a = np.asarray(xyz, np.float32)
    finite = np.isfinite(a).all(axis=-1)
    not_neg1 = ~(np.abs(a + 1.0) < 1e-6).all(axis=-1)
    not_zero = ~(np.abs(a) < 1e-9).all(axis=-1)
    return finite & not_neg1 & not_zero


def bridge_points(src_xyz, dst_xyz, pts_yx):
    """Map source grid cells to destination grid cells through 3D.

    Returns (dst_yx int array, residual float array). Points whose source cell is invalid
    must be filtered by the caller; this function assumes the given cells are valid.
    """
    src = np.asarray(src_xyz, np.float32)
    dst = np.asarray(dst_xyz, np.float32)
    pts_yx = np.asarray(pts_yx, int)

    dst_valid = _valid_mask(dst)
    dst_idx = np.argwhere(dst_valid)
    if len(dst_idx) == 0:
        raise ValueError("destination flattening has no valid cells")
    tree = cKDTree(dst[dst_valid])

    query = src[pts_yx[:, 0], pts_yx[:, 1]]
    resid, nn = tree.query(query, k=1)
    return dst_idx[nn], np.asarray(resid, float)


def transfer_columns(src_xyz, dst_xyz, columns, max_residual=None):
    """Map each column's box into the destination flattening.

    `max_residual` (in scan units) drops individual point correspondences that are outliers;
    None keeps all. Returns (mapped columns, stats).
    """
    src = np.asarray(src_xyz, np.float32)
    dst = np.asarray(dst_xyz, np.float32)
    src_valid = _valid_mask(src)
    dh, dw = dst.shape[:2]

    mapped = []
    for c in columns:
        y0, y1 = c["text_band"]
        x0, x1 = c["gx0"], c["gx1"]
        sub = np.zeros(src_valid.shape, bool)
        sub[max(0, y0) : y1 + 1, max(0, x0) : x1 + 1] = True
        cells = np.argwhere(sub & src_valid)

        entry = {
            "col": c["col"],
            "cross_strip": bool(c.get("cross_strip", False)),
            "n_mapped": 0,
            "median_residual": None,
            "fully_inside": False,
            "gx0": None,
            "gx1": None,
            "text_band": None,
        }
        if len(cells) == 0:
            mapped.append(entry)
            continue

        dst_yx, resid = bridge_points(src, dst, cells)
        if max_residual is not None:
            keep = resid <= max_residual
            dst_yx, resid = dst_yx[keep], resid[keep]
        if len(dst_yx) == 0:
            mapped.append(entry)
            continue

        entry["n_mapped"] = int(len(dst_yx))
        entry["median_residual"] = float(np.median(resid))
        entry["gx0"] = int(dst_yx[:, 1].min())
        entry["gx1"] = int(dst_yx[:, 1].max())
        entry["text_band"] = [int(dst_yx[:, 0].min()), int(dst_yx[:, 0].max())]
        entry["fully_inside"] = bool(
            entry["gx0"] >= 0
            and entry["gx1"] < dw
            and entry["text_band"][0] >= 0
            and entry["text_band"][1] < dh
            # A column pinned to the destination edge is a clipped column, not a mapped one.
            and entry["gx0"] > 0
            and entry["gx1"] < dw - 1
        )
        mapped.append(entry)

    stats = {
        "n_columns": len(columns),
        "n_fully_inside": int(sum(1 for m in mapped if m["fully_inside"])),
        "dst_grid_shape": [int(dh), int(dw)],
    }
    return mapped, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src-tifxyz", required=True, help="source flattening tifxyz dir")
    ap.add_argument(
        "--dst-tifxyz", required=True, help="destination flattening tifxyz dir"
    )
    ap.add_argument("--columns-json", required=True, help="source columns.json")
    ap.add_argument("--out-json", required=True, help="where to write mapped columns")
    ap.add_argument("--max-residual", type=float, default=None)
    args = ap.parse_args()

    sys.path.insert(0, str(REPO_ROOT))
    from repro.sota_data.register import read_tifxyz

    src = read_tifxyz(args.src_tifxyz)
    dst = read_tifxyz(args.dst_tifxyz)
    with open(args.columns_json) as f:
        columns = json.load(f)["columns"]

    mapped, stats = transfer_columns(src, dst, columns, max_residual=args.max_residual)
    out = {"columns": mapped, "stats": stats}
    pathlib.Path(args.out_json).write_text(json.dumps(out, indent=2) + "\n")

    print(f"{'col':>4} {'n_mapped':>9} {'resid':>8} {'gx0':>7} {'gx1':>7} inside")
    for m in mapped:
        r = "-" if m["median_residual"] is None else f"{m['median_residual']:.2f}"
        print(
            f"{m['col']:>4} {m['n_mapped']:>9} {r:>8} {str(m['gx0']):>7} "
            f"{str(m['gx1']):>7} {m['fully_inside']}"
        )
    print(f"\nfully inside: {stats['n_fully_inside']} / {stats['n_columns']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
