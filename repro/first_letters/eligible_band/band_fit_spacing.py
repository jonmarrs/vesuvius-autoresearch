"""How far apart are a fit's raw windings, and how far apart are the predicted sheets they sit on?

Two descriptions of one fit, neither part of a verdict:

    profile   share of nodes inside a predicted sheet, with the nodes moved along the winding's normal by each
              of OFFSETS voxels; every STRIDE-th node of every raw winding, pooled. A fit on sheets peaks at 0
              and rises again at the neighbouring sheets.
    spacing   for each pair of consecutive windings, the median distance from one to the other along the normal.

`sheet_spacing` is the offset, at least NEIGHBOUR_MIN voxels out, with the highest share, averaged over the two
directions. `ratio` is the median winding spacing over it: well under 1 means more windings than sheets.

usage: band_fit_spacing.py OUT.json SDT_ZARR MESH_DIR [--group 1]
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
import mesh_step_analysis as analysis  # noqa: E402

OFFSETS = tuple(range(-24, 25, 2))
STRIDE = 4
NEIGHBOUR_MIN = 8  # voxels: nearer than this is still the winding's own sheet


def sheet_spacing(offsets: list[int], share: list[float]) -> float | None:
    """Mean over the two directions of the offset, at least NEIGHBOUR_MIN out, where the share is highest.
    None unless each direction's highest share is above the lowest share between it and zero."""
    found = []
    for sign in (-1, 1):
        side = [
            (o, s)
            for o, s in zip(offsets, share, strict=True)
            if sign * o >= NEIGHBOUR_MIN
        ]
        near = [
            s
            for o, s in zip(offsets, share, strict=True)
            if 0 < sign * o < NEIGHBOUR_MIN
        ]
        if not side or not near:
            return None
        offset, best = max(side, key=lambda pair: (pair[1], -abs(pair[0])))
        if best <= min(near):
            return None
        found.append(abs(offset))
    return float(np.mean(found))


def summarise(offsets: list[int], share: list[float], spacings: list[float]) -> dict:
    sheets = sheet_spacing(offsets, share)
    median = float(np.median(spacings)) if spacings else None
    return {
        "offsets_voxels": offsets,
        "share_inside": [round(s, 4) for s in share],
        "peak_offset": offsets[int(np.argmax(share))],
        "sheet_spacing": sheets,
        "pairs": len(spacings),
        "winding_spacing_median": None if median is None else round(median, 2),
        "winding_spacing_p10": round(float(np.percentile(spacings, 10)), 2)
        if spacings
        else None,
        "winding_spacing_p90": round(float(np.percentile(spacings, 90)), 2)
        if spacings
        else None,
        "ratio": None if not sheets or median is None else round(median / sheets, 3),
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
    field = quality.DistanceField(Path(args.sdt), args.group)
    inside = np.zeros(len(OFFSETS))
    total = 0
    spacings: list[float] = []
    previous = None
    for folder in sorted(Path(args.meshes).glob("w*")):
        if folder.name.endswith("_spliced") or not (folder / "x.tif").exists():
            continue
        xyz, valid = analysis.load_tifxyz(folder)
        normals, has_normal = analysis.grid_normals(xyz, valid)
        use = valid & has_normal
        points, n = xyz[use][::STRIDE], normals[use][::STRIDE]
        values = [field.at(points + offset * n) for offset in OFFSETS]
        ok = np.all([np.isfinite(v) for v in values], axis=0)
        inside += [float((v[ok] <= 0).sum()) for v in values]
        total += int(ok.sum())
        if previous is not None:
            distance = analysis.surface_distance(*previous, xyz, valid)
            if distance["median"] is not None:
                spacings.append(distance["median"])
        previous = (xyz, valid)
    if total == 0:
        print("no node inside the distance field", file=sys.stderr)
        return 1
    result = summarise(list(OFFSETS), (inside / total).tolist(), spacings)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
