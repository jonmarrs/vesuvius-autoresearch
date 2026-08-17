#!/usr/bin/env python3
"""Task 2 of the second-1667-column-target plan: run the tifxyz transfer against the
real w011 flatboi flattening, apply the coverage and teacher-free gates, and decide
whether a second column target is even buildable.

This does NOT read ink to place columns (see transfer_columns_to_flattening.py). It
does, for the SUPPORTING check only, read the destination segment's own published
ink-detection prediction -- that figure is explicitly teacher-dependent and does not
gate the pre-registered stop condition.

Gates a column must clear to count toward the floor (all four):
  1. fully_inside     -- transfer_columns' strict-interior test.
  2. coverage >= 0.5   -- n_mapped / n_source_cells, guards against a column whose
                          correspondences are mostly outliers still slipping through
                          fully_inside on a single lucky point (Task 1 review finding).
  3. n_mapped >= 1000  -- a one-point column is not a column.
  4. periodicity gate  -- line-pitch autocorrelation on the destination segment's own
                          RAW surface texture (not ink-detection), inside the mapped
                          box, in the merged target's calibrated band [85, 160] grid px.
                          Teacher-free: no detector model is involved.

If fewer than 5 columns clear all four, the plan's pre-registered stop condition fires:
do not build a target, write up the finding, and return BLOCKED.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.spatial import cKDTree

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCROLLGT_ROOT = REPO_ROOT.parent / "scrollgt"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import transfer_columns_to_flattening as _tcf  # noqa: E402
from transfer_columns_to_flattening import _valid_mask, transfer_columns  # noqa: E402

from repro.sota_data.distill_run import _fs  # noqa: E402
from repro.sota_data.register import label_line_periodicity, read_tifxyz  # noqa: E402


class _ParallelKDTree(cKDTree):
    """cKDTree with tree.query(..., k=1) defaulting to workers=-1.

    bridge_points() (Task 1, committed) calls tree.query(query, k=1) with scipy's
    single-threaded default. Measured on the real merged-1667 grid: one column's
    query set (~580k points against a ~1.16M-point tree) took ~73s single-threaded
    in a direct timing and a similar wall time with workers=-1 on 4 cores in one
    run, but isolated micro-benchmarks showed workers=-1 roughly 2.4x faster per
    query -- across 22 columns (~27M query points total) that is the difference
    between multiple hours and roughly one. This subclasses cKDTree (the class
    itself can't be monkeypatched: it's an immutable Cython extension type) and
    rebinds the name inside the ALREADY-IMPORTED transfer_columns_to_flattening
    module, so bridge_points()'s `cKDTree(...)` calls build this subclass instead.
    It does not change transfer_columns_to_flattening.py on disk or its tested
    behavior -- only how many cores answer the same query.
    """

    def query(self, x, k=1, **kwargs):
        kwargs.setdefault("workers", -1)
        return super().query(x, k=k, **kwargs)


_tcf.cKDTree = _ParallelKDTree

BUCKET = "vesuvius-challenge-open-data"
SRC_SEG = "20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4"
SRC_MESH_REL = "mesh/20260612121456-on-20251217075048-2.399um.tifxyz"
DST_SEG = "20260108140509-w011_20260108140509268_flatboi"
DST_MESH_REL = "mesh/20260108140509-on-20251217075048-2.399um.tifxyz"
DST_INK_TIF = (
    "ink-detection/PHerc1667-20260108140509-2.399um-0.22m-78keV-volume-"
    "20251217075048-20260417190342-new_canon_autoresearch_recipe-tile256-stride128.tif"
)
DST_SURFACE_ZARR = "surface-volumes/2.399um-0.22m-78keV-volume-20251217075048.zarr"

LOCAL_DIR = REPO_ROOT / "local_data" / "1667_flattenings"
SRC_LOCAL = LOCAL_DIR / "merged_v4.tifxyz"
DST_LOCAL = LOCAL_DIR / "w011_flatboi.tifxyz"
DST_INK_LOCAL = LOCAL_DIR / "w011_flatboi_inkdet.tif"
# A prior render task already fetched and z-overrun-corrected the (~750MB) source
# mesh. Reuse it instead of re-downloading: it excludes points where the straightened
# merged mesh's z overruns the scan volume (repro/sota_data/merged_fullband_render.py),
# which is MORE correct for this transfer than the raw bucket copy, not less -- those
# points have no valid destination correspondence either way.
EXISTING_MERGED_CACHE = REPO_ROOT / "local_data" / "merged_w011_tifxyz"

COLUMNS_JSON = SCROLLGT_ROOT / "data" / "pherc1667_merged_columns" / "columns.json"
OUT_JSON = REPO_ROOT / "reports" / "detector" / "w011_column_transfer.json"
OUT_MD = REPO_ROOT / "reports" / "detector" / "w011_column_transfer.md"

MIN_COVERAGE = 0.5
MIN_N_MAPPED = 1000
# label_line_periodicity's own test (tests/test_sota_register.py) uses 0.5 as the
# synthetic-periodic-vs-scrambled cutoff, and register_run.py's one shipped
# teacher-free pass scored 0.867 on a REGISTERED HUMAN GT LABEL. Reused here as the
# best available reference point -- but see the report: this run applies the same
# function to raw surface texture (no ink label exists for column boxes), a
# materially weaker signal, so a column failing this exact cutoff is not evidence
# of misplacement to the same degree that failing it would be for a labeled mask.
MIN_PERIODICITY = 0.5
PERIODICITY_BAND = (85, 160)
PERIODICITY_LEVEL = (
    2  # per-segment surface-volumes zarr pyramid level for the texture read
)
GRID_TO_LEVEL0 = 20  # tifxyz grid scale is 0.05 -> 1 grid px = 20 level-0 px
GUTTER_WIDTH_GRID = (
    150  # grid px either side of a column, for the supporting enrichment check
)
STOP_FLOOR = 5


def _fetch_tifxyz_dir(seg, mesh_rel, local_dir):
    if all((local_dir / f"{c}.tif").exists() for c in "xyz"):
        return local_dir
    local_dir.mkdir(parents=True, exist_ok=True)
    fs = _fs()
    src = f"{BUCKET}/PHerc1667/segments/{seg}/{mesh_rel}"
    print(f"fetching {src} -> {local_dir} ...", flush=True)
    fs.get(src + "/", str(local_dir), recursive=True)
    return local_dir


def ensure_src_tifxyz():
    if all((SRC_LOCAL / f"{c}.tif").exists() for c in "xyz"):
        return SRC_LOCAL
    if all((EXISTING_MERGED_CACHE / f"{c}.tif").exists() for c in "xyz"):
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        if not SRC_LOCAL.exists():
            SRC_LOCAL.symlink_to(EXISTING_MERGED_CACHE, target_is_directory=True)
        return SRC_LOCAL
    return _fetch_tifxyz_dir(SRC_SEG, SRC_MESH_REL, SRC_LOCAL)


def ensure_dst_tifxyz():
    return _fetch_tifxyz_dir(DST_SEG, DST_MESH_REL, DST_LOCAL)


def ensure_dst_ink_tif():
    if DST_INK_LOCAL.exists():
        return DST_INK_LOCAL
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    fs = _fs()
    src = f"{BUCKET}/PHerc1667/segments/{DST_SEG}/{DST_INK_TIF}"
    print(f"fetching {src} -> {DST_INK_LOCAL} ...", flush=True)
    fs.get(src, str(DST_INK_LOCAL))
    return DST_INK_LOCAL


def n_source_cells(src_valid, col):
    """Replicates transfer_columns' box-selection exactly, so coverage is comparable."""
    y0, y1 = col["text_band"]
    x0, x1 = col["gx0"], col["gx1"]
    sub = np.zeros(src_valid.shape, bool)
    sub[max(0, y0) : y1 + 1, max(0, x0) : x1 + 1] = True
    return int((sub & src_valid).sum())


def surface_periodicity(fs, seg, box, level, band):
    """Teacher-free line-periodicity of the destination's own RAW surface texture
    (no ink-detection model involved) inside a mapped column box, in GRID-px band units.

    box = (gx0, gx1, y0, y1) in destination GRID coordinates (inclusive).
    """
    import zarr

    gx0, gx1, y0, y1 = box
    ds = 2**level
    grid_to_level = GRID_TO_LEVEL0 // ds
    if GRID_TO_LEVEL0 % ds != 0:
        raise ValueError(
            f"level {level} does not evenly divide the grid-to-level0 scale "
            f"({GRID_TO_LEVEL0}); pick a level whose 2**level divides it"
        )
    uri = f"{BUCKET}/PHerc1667/segments/{seg}/{DST_SURFACE_ZARR}"
    g = zarr.open(zarr.storage.FSStore(uri, fs=fs), mode="r")
    arr = g[str(level)]
    n_z = arr.shape[0]
    zmid = n_z // 2
    lx0, lx1 = gx0 * grid_to_level, (gx1 + 1) * grid_to_level
    ly0, ly1 = y0 * grid_to_level, (y1 + 1) * grid_to_level
    lx1, ly1 = min(lx1, arr.shape[2]), min(ly1, arr.shape[1])
    sub = np.asarray(arr[zmid, ly0:ly1, lx0:lx1], np.float32)
    h, w = sub.shape
    h2, w2 = (h // grid_to_level) * grid_to_level, (w // grid_to_level) * grid_to_level
    if h2 == 0 or w2 == 0:
        return None
    sub = sub[:h2, :w2]
    grid_img = sub.reshape(
        h2 // grid_to_level, grid_to_level, w2 // grid_to_level, grid_to_level
    ).mean(axis=(1, 3))
    return label_line_periodicity(grid_img.astype(np.uint8), band=band)


def column_gutter_enrichment(ink_full, box):
    """Supporting, TEACHER-DEPENDENT check: mean predicted-ink in the mapped column vs.
    its adjacent gutters, on the destination's own published ink-detection prediction.
    box = (gx0, gx1, y0, y1) in destination GRID coordinates (inclusive)."""
    gx0, gx1, y0, y1 = box
    h, w = ink_full.shape
    px0, px1 = gx0 * GRID_TO_LEVEL0, (gx1 + 1) * GRID_TO_LEVEL0
    py0, py1 = y0 * GRID_TO_LEVEL0, (y1 + 1) * GRID_TO_LEVEL0
    px1, py1 = min(px1, w), min(py1, h)
    col_region = ink_full[py0:py1, px0:px1]
    gw = GUTTER_WIDTH_GRID * GRID_TO_LEVEL0
    left = ink_full[py0:py1, max(0, px0 - gw) : px0]
    right = ink_full[py0:py1, px1 : min(w, px1 + gw)]
    gutter_px = (
        np.concatenate([left.ravel(), right.ravel()])
        if (left.size or right.size)
        else np.array([])
    )
    if col_region.size == 0 or gutter_px.size == 0:
        return None
    col_mean = float(col_region.mean())
    gutter_mean = float(gutter_px.mean())
    if gutter_mean <= 0:
        return None
    return col_mean / gutter_mean


def main():
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    src_dir = ensure_src_tifxyz()
    dst_dir = ensure_dst_tifxyz()

    src_xyz = read_tifxyz(str(src_dir))
    dst_xyz = read_tifxyz(str(dst_dir))
    sh, sw = src_xyz.shape[:2]
    dh, dw = dst_xyz.shape[:2]
    print(f"source grid  (merged_v4):  {sh} x {sw}", flush=True)
    print(f"dest grid    (w011_flatboi): {dh} x {dw}", flush=True)

    report = {
        "src": {
            "segment": SRC_SEG,
            "tifxyz": SRC_MESH_REL,
            "grid_shape": [int(sh), int(sw)],
        },
        "dst": {
            "segment": DST_SEG,
            "tifxyz": DST_MESH_REL,
            "grid_shape": [int(dh), int(dw)],
            "ink_detection_tif": DST_INK_TIF,
        },
        "gates": {
            "min_coverage": MIN_COVERAGE,
            "min_n_mapped": MIN_N_MAPPED,
            "periodicity_band_grid_px": list(PERIODICITY_BAND),
            "min_periodicity": MIN_PERIODICITY,
            "periodicity_note": (
                "measured on the destination segment's RAW surface texture "
                "(surface-volumes zarr level 2, block-downsampled to grid resolution), "
                "not a human-labeled ink mask -- weaker signal than this project's prior "
                "validated use of label_line_periodicity on registered GT labels; see report"
            ),
            "stop_floor": STOP_FLOOR,
        },
    }

    if dh > sh and dw > sw:
        report["stop"] = {
            "result": "STOP",
            "reason": (
                f"destination grid ({dh}x{dw}) is larger than the source "
                f"({sh}x{sw}) in BOTH axes -- these are not the flattenings this "
                "plan assumes."
            ),
        }
        OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")
        print("STOP: destination grid larger than source in both axes.", flush=True)
        print(json.dumps(report["stop"], indent=2))
        return 2

    with open(COLUMNS_JSON) as f:
        columns = json.load(f)["columns"]

    print(f"transferring {len(columns)} columns ...", flush=True)
    mapped, stats = transfer_columns(src_xyz, dst_xyz, columns, max_residual=None)
    src_valid = _valid_mask(src_xyz)

    fs = _fs()
    ensure_dst_ink_tif()
    ink_full = np.asarray(tifffile.imread(str(DST_INK_LOCAL)))

    rows = []
    n_fully_inside = n_coverage_pass = n_periodicity_pass = n_all_pass = 0
    n_edge_exclusion_only = n_no_cells = 0
    for c, m in zip(columns, mapped, strict=False):
        nsc = n_source_cells(src_valid, c)
        n_mapped = m["n_mapped"]
        coverage = (n_mapped / nsc) if nsc > 0 else 0.0
        coverage_ok = coverage >= MIN_COVERAGE and n_mapped >= MIN_N_MAPPED
        fully_inside = m["fully_inside"]

        edge_exclusion_only = False
        if not fully_inside and n_mapped > 0 and m["gx0"] is not None:
            gx0, gx1 = m["gx0"], m["gx1"]
            tb0, tb1 = m["text_band"]
            loosely_inside = gx0 >= 0 and gx1 < dw and tb0 >= 0 and tb1 < dh
            edge_exclusion_only = loosely_inside and (gx0 == 0 or gx1 == dw - 1)

        periodicity = None
        periodicity_pass = False
        if fully_inside:
            box = (m["gx0"], m["gx1"], m["text_band"][0], m["text_band"][1])
            periodicity = surface_periodicity(
                fs, DST_SEG, box, PERIODICITY_LEVEL, PERIODICITY_BAND
            )
            if periodicity is not None:
                periodicity_pass = periodicity > MIN_PERIODICITY

        enrichment = None
        if fully_inside:
            box = (m["gx0"], m["gx1"], m["text_band"][0], m["text_band"][1])
            enrichment = column_gutter_enrichment(ink_full, box)

        passes_all = bool(fully_inside and coverage_ok and periodicity_pass)

        if fully_inside:
            n_fully_inside += 1
        if fully_inside and coverage_ok:
            n_coverage_pass += 1
        if periodicity_pass:
            n_periodicity_pass += 1
        if passes_all:
            n_all_pass += 1
        if edge_exclusion_only:
            n_edge_exclusion_only += 1
        if n_mapped == 0:
            n_no_cells += 1

        rows.append(
            {
                "col": c["col"],
                "cross_strip": bool(c.get("cross_strip", False)),
                "src_gx0": c["gx0"],
                "src_gx1": c["gx1"],
                "src_text_band": c["text_band"],
                "n_source_cells": nsc,
                "n_mapped": n_mapped,
                "coverage": coverage,
                "median_residual": m["median_residual"],
                "fully_inside": fully_inside,
                "edge_exclusion_only": edge_exclusion_only,
                "coverage_ok": coverage_ok,
                "dst_gx0": m["gx0"],
                "dst_gx1": m["gx1"],
                "dst_text_band": m["text_band"],
                "periodicity_teacher_free": periodicity,
                "periodicity_pass": periodicity_pass,
                "enrichment_teacher_dependent_supporting_only": enrichment,
                "passes_all_gates": passes_all,
            }
        )
        print(
            f"col {c['col']:>2}: n_mapped={n_mapped:>8} coverage={coverage:.3f} "
            f"fully_inside={fully_inside!s:5} periodicity={periodicity} "
            f"enrichment={enrichment} all_gates={passes_all}",
            flush=True,
        )

    report["columns"] = rows
    report["stats"] = {
        "n_columns": len(columns),
        "n_fully_inside": n_fully_inside,
        "n_coverage_pass": n_coverage_pass,
        "n_periodicity_pass": n_periodicity_pass,
        "n_all_gates_pass": n_all_pass,
        "n_edge_exclusion_only": n_edge_exclusion_only,
        "n_no_source_correspondence": n_no_cells,
    }
    result = "CONTINUE" if n_all_pass >= STOP_FLOOR else "BLOCKED"
    report["stop"] = {
        "floor": STOP_FLOOR,
        "n_passing": n_all_pass,
        "result": result,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"\nwrote {OUT_JSON}", flush=True)
    print(
        f"fully_inside={n_fully_inside} coverage_pass={n_coverage_pass} "
        f"periodicity_pass={n_periodicity_pass} ALL_GATES={n_all_pass} "
        f"(floor={STOP_FLOOR}) -> {result}",
        flush=True,
    )
    return 0 if result == "CONTINUE" else 1


if __name__ == "__main__":
    sys.exit(main())
