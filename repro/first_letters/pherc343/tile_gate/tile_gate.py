"""Does the sheet-following score, taken per tile, pick out the tiles of a fitted winding on the right sheet?

Finding 117 (registration: docs/preregistration/2026-11-15_first_letters_343_tile_gate.md). For each fitted
winding with a published winding of the same index:

    per node   the excess's two readings (inside a predicted sheet here; mean of the same at +-6 voxels along
               the normal), and the distance along the published winding's normal to the published winding
    per tile   blocks of TILE x TILE nodes; tile_excess = inside share - displaced share over scored nodes;
               right = at least half of the covered nodes within WITHIN voxels of the published winding

The AUC of tile_excess for right against wrong tiles, against a floor of slid labels.

usage: tile_gate.py OUT.json SDT_ZARR FIT_DIR PUBLISHED_DIR [--snapped SNAPPED_DIR]
       FIT_DIR holds w047/ and w048/; PUBLISHED_DIR holds w047_*.tifxyz and w048_*.tifxyz;
       SNAPPED_DIR holds w047.tifxyz and w048.tifxyz (a description, not the test)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "mesh_step"))
sys.path.insert(0, str(HERE.parents[1] / "eligible_band"))

import band_fit_quality as bq  # noqa: E402
import mesh_step_analysis as analysis  # noqa: E402

WINDINGS = ("w047", "w048")
TILE = 19  # nodes a side; the grid step is 20 voxels, so about 380 voxels (finding 113's tile: 385)
MIN_SCORED = 200  # nodes of a tile with all three distance readings
MIN_COVERED = 0.5  # share of a tile's valid nodes with a published partner
WITHIN = 2.0  # voxels: a node on the published sheet
WITHIN_DESCRIBED = 4.0
RIGHT_SHARE = (
    0.5  # share of a tile's covered nodes within WITHIN for the tile to be right
)
NEAREST = 12
LATERAL_MAX = analysis.LATERAL_MAX
EXCESS_LINE = 0.07
MIN_PER_LABEL = 15
AUC_WEAK, AUC_WORKS, SHARE_GAIN = 0.60, 0.75, 0.15


def node_readings(field, xyz: np.ndarray, valid: np.ndarray) -> dict[str, np.ndarray]:
    """Per node of a grid: inside (here), displaced (mean of +-DISPLACE), and whether all three were read."""
    normals, has_normal = analysis.grid_normals(xyz, valid)
    use = valid & has_normal
    shape = valid.shape
    inside = np.full(shape, np.nan)
    displaced = np.full(shape, np.nan)
    p, n = xyz[use], normals[use]
    here = field.at(p)
    plus = field.at(p + bq.DISPLACE * n)
    minus = field.at(p - bq.DISPLACE * n)
    ok = np.isfinite(here) & np.isfinite(plus) & np.isfinite(minus)
    a = np.where(ok, (here <= 0).astype(float), np.nan)
    b = np.where(
        ok, ((plus <= 0).astype(float) + (minus <= 0).astype(float)) / 2, np.nan
    )
    inside[use], displaced[use] = a, b
    return {"inside": inside, "displaced": displaced, "scored": np.isfinite(inside)}


def distance_to(
    xyz: np.ndarray, valid: np.ndarray, other: np.ndarray, other_valid: np.ndarray
) -> np.ndarray:
    """Per node of the first grid: |distance| along the other grid's normal to its nearest suitable node; NaN if none."""
    from scipy.spatial import cKDTree

    normals, has_normal = analysis.grid_normals(other, other_valid)
    keep = other_valid & has_normal
    q, qn = other[keep], normals[keep]
    out = np.full(valid.shape, np.nan)
    if len(q) == 0 or not valid.any():
        return out
    tree = cKDTree(q)
    p = xyz[valid]
    _, j = tree.query(p, k=min(NEAREST, len(q)))
    if j.ndim == 1:
        j = j[:, None]
    diff = p[:, None, :] - q[j]
    along = np.einsum("nkc,nkc->nk", diff, qn[j])
    lateral = np.linalg.norm(diff - along[..., None] * qn[j], axis=-1)
    along = np.where(lateral <= LATERAL_MAX, np.abs(along), np.inf)
    best = along.min(1)
    out[valid] = np.where(np.isfinite(best), best, np.nan)
    return out


def tiles(
    readings: dict[str, np.ndarray], distance: np.ndarray, valid: np.ndarray
) -> list[dict]:
    rows, cols = valid.shape
    out = []
    for r0 in range(0, rows - TILE + 1, TILE):
        for c0 in range(0, cols - TILE + 1, TILE):
            s = np.s_[r0 : r0 + TILE, c0 : c0 + TILE]
            v = valid[s]
            scored = readings["scored"][s]
            covered = v & np.isfinite(distance[s])
            if (
                int(scored.sum()) < MIN_SCORED
                or not v.any()
                or covered.sum() < MIN_COVERED * v.sum()
            ):
                continue
            d = distance[s][covered]
            out.append(
                {
                    "row": r0 // TILE,
                    "col": c0 // TILE,
                    "tile_excess": float(
                        np.nanmean(readings["inside"][s][scored])
                        - np.nanmean(readings["displaced"][s][scored])
                    ),
                    "within": float((d <= WITHIN).mean()),
                    "within_described": float((d <= WITHIN_DESCRIBED).mean()),
                    "nodes_scored": int(scored.sum()),
                }
            )
    return out


def auc(scores: np.ndarray, labels: np.ndarray) -> float | None:
    """Mann-Whitney AUC of scores for label True against False, ties counted half."""
    pos, neg = scores[labels], scores[~labels]
    if len(pos) == 0 or len(neg) == 0:
        return None
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))


def slid_floor(tile_list: list[dict], key: str = "within") -> dict:
    """AUCs with each winding's labels slid cyclically along its rows of tiles by every non-zero whole shift."""
    by_winding: dict[str, list[dict]] = {}
    for t in tile_list:
        by_winding.setdefault(t["winding"], []).append(t)
    widest = max(
        (max(t["col"] for t in ts) + 1 for ts in by_winding.values()), default=0
    )
    values = []
    for shift in range(1, widest):
        scores, labels = [], []
        for ts in by_winding.values():
            width = max(t["col"] for t in ts) + 1
            if shift % width == 0:
                continue
            label_at = {(t["row"], t["col"]): t[key] >= RIGHT_SHARE for t in ts}
            for t in ts:
                partner = (t["row"], (t["col"] + shift) % width)
                if partner in label_at:
                    scores.append(t["tile_excess"])
                    labels.append(label_at[partner])
        a = auc(np.array(scores), np.array(labels, bool)) if scores else None
        if a is not None:
            values.append(a)
    if not values:
        return {"shifts": 0, "p95": None, "max": None}
    return {
        "shifts": len(values),
        "p95": round(float(np.percentile(values, 95)), 4),
        "max": round(max(values), 4),
    }


def summarise(tile_list: list[dict], key: str = "within") -> dict:
    scores = np.array([t["tile_excess"] for t in tile_list])
    labels = np.array([t[key] >= RIGHT_SHARE for t in tile_list], bool)
    high = scores >= EXCESS_LINE
    return {
        "tiles": len(tile_list),
        "right": int(labels.sum()),
        "wrong": int((~labels).sum()),
        "auc": None if auc(scores, labels) is None else round(auc(scores, labels), 4),
        "share_right_overall": round(float(labels.mean()), 4) if len(labels) else None,
        "tiles_at_line": int(high.sum()),
        "share_right_at_line": round(float(labels[high].mean()), 4)
        if high.any()
        else None,
        "floor": slid_floor(tile_list, key),
    }


def verdict(summary: dict | None) -> str:
    if (
        summary is None
        or summary["right"] < MIN_PER_LABEL
        or summary["wrong"] < MIN_PER_LABEL
    ):
        return "DOES_NOT_RUN"
    a, floor = summary["auc"], summary["floor"]["p95"]
    if a is None or floor is None or a <= floor or a < AUC_WEAK:
        return "LOCAL_GATE_FAILS"
    if a < AUC_WORKS:
        return "LOCAL_GATE_WEAK"
    at_line = summary["share_right_at_line"]
    if at_line is not None and at_line >= summary["share_right_overall"] + SHARE_GAIN:
        return "LOCAL_GATE_WORKS"
    return "LOCAL_GATE_WEAK"


def measure(
    field, fit_dirs: dict[str, Path], published_dirs: dict[str, Path]
) -> list[dict]:
    out = []
    for name in WINDINGS:
        xyz, valid = analysis.load_tifxyz(fit_dirs[name])
        pub, pub_valid = analysis.load_tifxyz(published_dirs[name])
        readings = node_readings(field, xyz, valid)
        distance = distance_to(xyz, valid, pub, pub_valid)
        for t in tiles(readings, distance, valid):
            out.append({"winding": name, **t})
    return out


def _published(directory: Path) -> dict[str, Path]:
    found = {}
    for name in WINDINGS:
        matches = sorted(directory.glob(f"{name}_*.tifxyz"))
        if len(matches) != 1:
            raise SystemExit(
                f"expected one {name}_*.tifxyz in {directory}, found {len(matches)}"
            )
        found[name] = matches[0]
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("sdt")
    ap.add_argument("fit")
    ap.add_argument("published")
    ap.add_argument("--snapped")
    ap.add_argument("--group", default="1")
    args = ap.parse_args(argv)
    if Path(args.out).exists():
        print(f"{args.out} exists: this is measured once", file=sys.stderr)
        return 2
    field = bq.DistanceField(Path(args.sdt), args.group)
    published = _published(Path(args.published))
    raw_tiles = measure(field, {n: Path(args.fit) / n for n in WINDINGS}, published)
    raw = summarise(raw_tiles)
    result = {
        "finding": 117,
        "tile_nodes": TILE,
        "within_voxels": WITHIN,
        "raw": raw,
        "verdict": verdict(raw),
        "described": {"raw_within_4": summarise(raw_tiles, "within_described")},
        "raw_tiles": raw_tiles,
    }
    if args.snapped:
        snapped_tiles = measure(
            field, {n: Path(args.snapped) / f"{n}.tifxyz" for n in WINDINGS}, published
        )
        result["described"]["snapped"] = summarise(snapped_tiles)
        result["snapped_tiles"] = snapped_tiles
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("raw", "verdict", "described")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
