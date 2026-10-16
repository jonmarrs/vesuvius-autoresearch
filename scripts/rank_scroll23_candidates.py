#!/usr/bin/env python3
"""
Rank Scroll 2/3 candidate windows for First Letters / First Title review.

Inputs are the deterministic queue plus optional prediction artifacts. This is a
cheap metadata/statistics pass: it does not download data or run inference.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from zipfile import BadZipFile

import numpy as np

from vesuvius_autoresearch.core.inference_constants import INK_PROBABILITY

ARTIFACT_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    EOFError,
    BadZipFile,
)


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON value {value}")


def _integer(value, label, minimum=0):
    number = float(value)
    if (
        isinstance(value, bool)
        or not math.isfinite(number)
        or not number.is_integer()
        or number < minimum
    ):
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return int(number)


def _geometry(row):
    patch = _integer(row.get("patch_size", 64), "candidate patch_size", 1)
    return {
        "position_xyz": [_integer(row.get(axis, 0), axis) for axis in ("x", "y", "z")],
        "width_px": _integer(row.get("width", patch), "candidate width", 1),
        "height_px": _integer(row.get("height", patch), "candidate height", 1),
        "patch_size": patch,
    }


def _read_zarr_array_info(local_uri):
    if not local_uri:
        return None
    zarray_path = Path(local_uri) / ".zarray"
    if not zarray_path.exists():
        return None
    with open(zarray_path) as f:
        meta = json.load(f, parse_constant=_reject_constant)
    chunks = meta.get("chunks")
    separator = meta.get("dimension_separator", ".")
    if (
        not isinstance(chunks, list)
        or len(chunks) != 3
        or any(type(value) is not int or value <= 0 for value in chunks)
        or separator not in (".", "/")
    ):
        raise ValueError(
            "CT chunks must be three positive integers with a valid separator"
        )
    return {
        "chunks": tuple(chunks),
        "dimension_separator": separator,
    }


def _chunk_exists(local_uri, coord, dimension_separator):
    root = Path(local_uri)
    zc, yc, xc = coord
    if dimension_separator == "/":
        return (root / str(zc) / str(yc) / str(xc)).is_file()
    return (root / f"{zc}.{yc}.{xc}").is_file()


def _ct_occupancy_stats(row):
    unknown = {
        "ct_occupied_status": "unknown",
        "ct_occupied": None,
        "ct_occupied_error": "",
    }
    try:
        info = _read_zarr_array_info(row.get("local_uri"))
        if not info:
            return unknown
        geometry = _geometry(row)
        x, y, z = geometry["position_xyz"]
        center = (z, y + geometry["height_px"] // 2, x + geometry["width_px"] // 2)
        coord = tuple(
            value // size for value, size in zip(center, info["chunks"], strict=True)
        )
        occupied = _chunk_exists(
            row.get("local_uri"), coord, info["dimension_separator"]
        )
    except ARTIFACT_ERRORS as exc:
        unknown["ct_occupied_error"] = f"{type(exc).__name__}: {exc}"
        return unknown
    return {
        "ct_occupied_status": "true" if occupied else "false",
        "ct_occupied": occupied,
        "ct_chunk_coord": ".".join(str(part) for part in coord),
    }


def _float(row, key, default=0.0):
    try:
        number = float(row.get(key, default))
        if not math.isfinite(number):
            raise ValueError
        return number
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"candidate {key} must be finite") from exc


def _artifact_stem(row):
    geometry = _geometry(row)
    x, y, z = geometry["position_xyz"]
    return f"pred_{z}_{y}_{x}_{geometry['width_px']}x{geometry['height_px']}"


def _source_identity(uri):
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("candidate and prediction must record source_uri")
    return uri.rstrip("/") if "://" in uri else str(Path(uri).resolve())


def _validate_prediction_metadata(meta, row):
    """A coordinate-only basename cannot identify a scroll or a completed run."""
    source = row.get("local_uri") or row.get("source_uri")
    if _source_identity(meta.get("source_uri")) != _source_identity(source):
        raise ValueError("prediction source_uri does not match candidate")
    for field, expected in _geometry(row).items():
        actual = meta.get(field)
        if field == "position_xyz":
            valid = isinstance(actual, list) and all(type(v) is int for v in actual)
        else:
            valid = type(actual) is int
        if not valid or actual != expected:
            raise ValueError(f"prediction {field} does not match candidate")
    voxel = meta.get("voxel_size_um")
    if (
        isinstance(voxel, bool)
        or not isinstance(voxel, (int, float))
        or not math.isfinite(voxel)
        or voxel <= 0
    ):
        raise ValueError("prediction voxel_size_um must be positive and finite")
    if row.get("voxel_um") and not math.isclose(
        voxel, float(row["voxel_um"]), abs_tol=1e-6, rel_tol=0
    ):
        raise ValueError("prediction voxel_size_um does not match candidate")
    if meta.get("prediction_complete") is not True:
        raise ValueError("prediction must record a complete region")
    for field, expected in (("num_parts", 1), ("part_id", 0)):
        if type(meta.get(field)) is not int or meta[field] != expected:
            raise ValueError("prediction must be an unsharded complete region")
    coverage = meta.get("coverage_fraction")
    total, processed = meta.get("tiles_total"), meta.get("tiles_processed")
    if (
        isinstance(coverage, bool)
        or coverage != 1.0
        or type(total) is not int
        or total <= 0
        or type(processed) is not int
        or processed != total
    ):
        raise ValueError("prediction must record full coverage and all tiles")


def _probability_array(path, shape):
    array = np.load(path, allow_pickle=False, mmap_mode="r")
    if not isinstance(array, np.ndarray):
        array.close()
        raise ValueError(f"prediction must be a NumPy array: {path}")
    if (
        array.shape != shape
        or array.dtype.kind != "f"
        or not np.isfinite(array).all()
        or (array < 0).any()
        or (array > 1).any()
    ):
        raise ValueError(
            "prediction must be finite floating-point probabilities in [0,1] "
            f"with shape {shape}: {path}"
        )
    return array


def _load_prediction_stats(prediction_dir, row):
    pred_dir = Path(prediction_dir)
    stem = _artifact_stem(row)
    ink_path = pred_dir / f"{stem}_ink.npy"
    fiber_path = pred_dir / f"{stem}_fiber.npy"
    meta_path = pred_dir / f"{stem}_meta.json"

    stats = {
        "prediction_found": False,
        "prediction_error": "",
        "prediction_recipe": "",
        "ink_mean": 0.0,
        "ink_std": 0.0,
        "ink_max": 0.0,
        "ink_hot_fraction": 0.0,
        "fiber_mean": 0.0,
        "metadata_found": meta_path.exists(),
        "metadata_error": "",
    }

    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f, parse_constant=_reject_constant)
            recipe = meta.get("inference_recipe") or {}
            stats["prediction_recipe"] = str(recipe.get("ink_probability", ""))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            stats["metadata_error"] = f"{type(exc).__name__}: {exc}"
            meta = {}
    # Only maps served as sigmoid(ink) share a scale. QC-gated maps from before
    # 2026-10-13 sit near zero, and a map without a recorded recipe cannot be
    # placed, so neither earns a prediction bonus.
    if stats["prediction_recipe"] != INK_PROBABILITY:
        stats["prediction_found"] = False
        return stats

    try:
        _validate_prediction_metadata(meta, row)
    except ARTIFACT_ERRORS as exc:
        stats["metadata_error"] = f"{type(exc).__name__}: {exc}"
        return stats
    geometry = _geometry(row)
    shape = (geometry["height_px"], geometry["width_px"])
    try:
        arr = _probability_array(ink_path, shape)
        stats.update(
            prediction_found=True,
            ink_mean=float(arr.mean(dtype=np.float64)),
            ink_std=float(arr.std(dtype=np.float64)),
            ink_max=float(arr.max()),
            ink_hot_fraction=float((arr >= 0.5).mean()),
        )
    except ARTIFACT_ERRORS as exc:
        stats["prediction_error"] = f"{type(exc).__name__}: {exc}"
        return stats

    # The fiber map counts only when this prediction's metadata records one: a
    # model without a fiber head writes none, so a file of that name is an
    # earlier model's.
    if isinstance(meta.get("fiber_stats"), dict) and meta["fiber_stats"]:
        try:
            fiber = _probability_array(fiber_path, shape)
            stats["fiber_mean"] = float(fiber.mean(dtype=np.float64))
        except ARTIFACT_ERRORS as exc:
            stats["prediction_error"] = f"{type(exc).__name__}: {exc}"

    return stats


def score_row(row, prediction_dir="predictions"):
    stats = _load_prediction_stats(prediction_dir, row)
    ct_stats = _ct_occupancy_stats(row)
    base_priority = _float(row, "priority", 1.0)
    div = row.get("division", "")
    core_bonus = 0.35 if div in {"div_90", "div_100"} else 0.0
    local_bonus = 0.15 if row.get("local_uri") else 0.0
    submittable_bonus = 0.25 if row.get("submittable_window") == "true" else -1.0
    ct_occupancy_bonus = -2.0 if ct_stats["ct_occupied"] is False else 0.0
    prediction_bonus = 0.0
    if stats["prediction_found"]:
        # Favor sparse, high-confidence signal over broad foggy activations.
        prediction_bonus = (
            2.0 * stats["ink_max"]
            + 1.5 * stats["ink_std"]
            + 1.0 * stats["ink_hot_fraction"]
            - 0.5 * stats["ink_mean"]
        )

    review_score = (
        base_priority
        + core_bonus
        + local_bonus
        + submittable_bonus
        + ct_occupancy_bonus
        + prediction_bonus
    )
    out = dict(row)
    out.update(
        {
            "review_score": f"{review_score:.6f}",
            "prediction_found": str(stats["prediction_found"]).lower(),
            "prediction_recipe": stats["prediction_recipe"],
            "metadata_found": str(stats["metadata_found"]).lower(),
            "metadata_error": stats["metadata_error"],
            "prediction_error": stats["prediction_error"],
            "ink_mean": f"{stats['ink_mean']:.6f}",
            "ink_std": f"{stats['ink_std']:.6f}",
            "ink_max": f"{stats['ink_max']:.6f}",
            "ink_hot_fraction": f"{stats['ink_hot_fraction']:.6f}",
            "fiber_mean": f"{stats['fiber_mean']:.6f}",
            "artifact_stem": _artifact_stem(row),
            "ct_occupied_status": ct_stats["ct_occupied_status"],
            "ct_chunk_coord": ct_stats.get("ct_chunk_coord", ""),
            "ct_occupied_error": ct_stats.get("ct_occupied_error", ""),
        }
    )
    return out


def rank_candidates(queue_path, out_path, prediction_dir="predictions", limit=None):
    with open(queue_path, newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    ranked = [score_row(row, prediction_dir=prediction_dir) for row in rows]
    ranked.sort(key=lambda row: float(row["review_score"]), reverse=True)
    if limit is not None:
        ranked = ranked[:limit]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if ranked:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(ranked[0].keys()),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(ranked)
    else:
        out_path.write_text("")
    return ranked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="reports/scroll23_search_queue.tsv")
    parser.add_argument("--out", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    ranked = rank_candidates(args.queue, args.out, args.prediction_dir, args.limit)
    print(f"Wrote {len(ranked)} ranked candidates to {args.out}")
    if ranked:
        print(
            f"Top candidate: {ranked[0]['scroll_id']} {ranked[0]['division']} score={ranked[0]['review_score']}"
        )


if __name__ == "__main__":
    main()
