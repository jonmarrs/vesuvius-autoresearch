#!/usr/bin/env python3
"""Describe candidate ink/fiber array co-occurrence; this is not accuracy validation.

Read existing candidate artifacts and publish summary.json and summary.md together
in a new --out directory. Shape agreement alone does not establish registration,
independent evidence, ink correctness, held-out lineage, or prize eligibility.
Legacy output-file flags and auto-generation are retired.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from html import escape
from pathlib import Path

import numpy as np
import tifffile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, integer, write_json
from scripts.export_for_production import sha256_file
from scripts.labeling.label_artifacts import (
    MAX_FRAGMENT_VOXELS,
    bounded_number,
    level_zero,
    new_output,
    publish_new,
)
from scripts.pseudo_label_artifacts import MAX_LABEL_PIXELS, aligned_array

MAX_CANDIDATES = 256
MAX_DISCOVERED_CANDIDATES = 4096
MAX_METADATA_BYTES = 1024**2
REPORT_ERRORS = (*ARTIFACT_ERRORS, RuntimeError)


@dataclass
class CandidateRecord:
    candidate_index: int = -1
    artifact_stem: str = "?"
    scroll_id: str = "?"
    short_id: str = "?"
    division: str = "?"
    z: int | None = None
    y: int | None = None
    x: int | None = None
    review_score: float | None = None
    ink_pred_mean: float | None = None
    fiber_mean: float | None = None
    ink_mean_in_fiber_regions: float | None = None
    ink_mean_in_nonfiber_regions: float | None = None
    ink_anti_fiber_ratio: float | None = None
    ratio_status: str = "not_measured"
    fiber_region_pixel_count: int = 0
    nonfiber_region_pixel_count: int = 0
    status: str = "PENDING"
    note: str = ""
    shape_yx: list[int] = field(default_factory=list)
    fiber_shape: list[int] = field(default_factory=list)
    source_files_sha256: dict[str, str] = field(default_factory=dict)
    absent_prediction_metadata: list[str] = field(default_factory=list)
    ink_array_sha256: str | None = None
    prediction_geometry_checked: bool = False
    prediction_completeness_recorded: bool = False
    alignment_verified: bool = False
    alignment_scope: str = "array_shape_only; fiber origin is not recorded"


def _positive_integer(value, name, maximum=None):
    if isinstance(value, np.bool_):
        raise ValueError(f"{name} must be an integer")
    result = integer(value, name, 1)
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must not exceed {maximum}")
    return result


def _finite(value, name, lower=0, upper=1):
    if isinstance(value, np.bool_):
        raise ValueError(f"{name} must be numeric, not boolean")
    return bounded_number(value, name, lower, upper)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite_json(value):
    raise ValueError(f"nonfinite JSON number: {value}")


def _metadata_size(path):
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds one MiB")


def _json_object(path):
    _metadata_size(path)
    value = json.loads(
        path.read_text(), object_pairs_hook=_object, parse_constant=_nonfinite_json
    )
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def _text(value, name):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 256
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError(f"{name} must be a nonempty bounded string")
    return value


def _stem(value):
    value = _text(value, "artifact_stem")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("artifact_stem must be a basename, without path separators")
    return value


def _read_candidate_meta(candidate_dir):
    path = Path(candidate_dir) / "candidate.json"
    if not path.exists():
        return None
    meta = _json_object(path)
    meta["artifact_stem"] = _stem(meta.get("artifact_stem"))
    for name in ("scroll_id", "short_id", "division", "local_uri"):
        meta[name] = _text(meta.get(name), name)
    for name in ("z", "y", "x"):
        meta[name] = integer(meta.get(name), name)
    for name in ("width", "height"):
        meta[name] = _positive_integer(meta.get(name), name)
    if meta.get("review_score") is not None:
        meta["review_score"] = _finite(
            meta["review_score"],
            "review_score",
            -sys.float_info.max,
            sys.float_info.max,
        )
    return meta


def _probability(values, name):
    values = aligned_array(values, name)
    if values.dtype.kind not in "fiu" or not np.isfinite(values).all():
        raise ValueError(f"{name} must contain finite real probabilities")
    if (values < 0).any() or (values > 1).any():
        raise ValueError(f"{name} probabilities must lie in [0,1]")
    return values.astype(np.float64)


def _load_ink_prediction(candidate_dir, artifact_stem, *, max_pixels=MAX_LABEL_PIXELS):
    path = Path(candidate_dir) / "predictions" / f"{_stem(artifact_stem)}_ink.zarr"
    if not path.exists():
        return None
    # Older exporter directories lack .zgroup but explicitly contain array /0.
    source = path
    if not (path / ".zgroup").exists() and not (path / ".zarray").exists():
        source = path / "0"
    _, array = level_zero(source)
    if array.ndim == 3 and array.shape[0] == 1:
        shape = array.shape[1:]
    elif array.ndim == 2:
        shape = array.shape
    else:
        raise ValueError("ink surface must have shape (H,W) or (1,H,W)")
    limit = _positive_integer(max_pixels, "max_pixels")
    if math.prod(shape) > limit:
        raise ValueError("ink surface exceeds max_pixels")
    if array.dtype != np.dtype("uint8") and (
        array.dtype.kind != "f" or array.dtype.itemsize > 8
    ):
        raise ValueError("ink surface must use uint8/255 or floating probabilities")
    raw = np.asarray(array[0] if array.ndim == 3 else array[:])
    if raw.shape != tuple(shape):
        raise ValueError("ink surface read does not match its declared shape")
    values = raw.astype(np.float64) / 255 if raw.dtype == np.uint8 else raw
    return _probability(values, "ink surface")


def _load_fiber_label(candidate_dir, *, max_voxels=MAX_FRAGMENT_VOXELS):
    path = Path(candidate_dir) / "fiber_label.tif"
    if not path.exists():
        return None
    limit = _positive_integer(max_voxels, "max_voxels")
    with tifffile.TiffFile(path) as tif:
        if len(tif.series) != 1:
            raise ValueError("fiber TIFF must contain exactly one series")
        series = tif.series[0]
        if (
            series.axes not in {"YX", "ZYX", "QYX", "IYX"}
            or len(series.shape) not in (2, 3)
            or min(series.shape) <= 0
        ):
            raise ValueError("fiber TIFF must be a nonempty YX or ZYX label array")
        if math.prod(series.shape) > limit:
            raise ValueError("fiber TIFF exceeds max_voxels")
        if series.dtype.kind not in "biuf" or series.dtype.itemsize > 8:
            raise ValueError("fiber TIFF must contain real binary labels")
        values = series.asarray()
        if values.shape != series.shape:
            raise ValueError("fiber TIFF read does not match its declared shape")
    return _binary_fiber(values)


def _binary_fiber(values):
    values = np.asarray(values)
    if values.ndim not in (2, 3) or not values.size or values.dtype.kind not in "biuf":
        raise ValueError("fiber labels must be a nonempty binary YX or ZYX array")
    if not (np.isin(values, [0, 1]).all() or np.isin(values, [0, 255]).all()):
        raise ValueError("fiber labels must use binary 0/1 or 0/255 encoding")
    return values != 0


def _project_fiber_to_surface(fiber_3d):
    values = _binary_fiber(fiber_3d)
    return values.mean(axis=0) if values.ndim == 3 else values.astype(np.float64)


def _compute_metrics(ink_pred, fiber_density, fiber_threshold):
    threshold = _finite(fiber_threshold, "fiber_threshold")
    ink = _probability(ink_pred, "ink")
    density = _probability(fiber_density, "fiber density")
    if ink.shape != density.shape:
        raise ValueError("ink and projected fiber shapes must match exactly")
    mask = density > threshold
    ink_fiber = float(ink[mask].mean()) if mask.any() else None
    ink_nonfiber = float(ink[~mask].mean()) if (~mask).any() else None
    ratio = None
    if ink_fiber is None:
        ratio_status = "no_fiber_pixels"
    elif ink_nonfiber is None:
        ratio_status = "no_nonfiber_pixels"
    elif ink_fiber == 0:
        ratio_status = "zero_fiber_mean"
    else:
        ratio = ink_nonfiber / ink_fiber
        ratio_status = "defined" if math.isfinite(ratio) else "nonfinite_ratio"
        if ratio_status != "defined":
            ratio = None
    return {
        "ink_pred_mean": float(ink.mean()),
        "fiber_mean": float(density.mean()),
        "ink_mean_in_fiber_regions": ink_fiber,
        "ink_mean_in_nonfiber_regions": ink_nonfiber,
        "ink_anti_fiber_ratio": ratio,
        "ratio_status": ratio_status,
        "fiber_region_pixel_count": int(mask.sum()),
        "nonfiber_region_pixel_count": int((~mask).sum()),
    }


def _array_digest(values):
    descriptor = json.dumps(list(values.shape)).encode()
    content = np.ascontiguousarray(values, dtype="<f8").tobytes()
    return hashlib.sha256(descriptor + content).hexdigest()


def _source_uri(value):
    value = _text(value, "source_uri")
    path = Path(value)
    return str((path if path.is_absolute() else REPO_ROOT / path).resolve())


def _prediction_metadata(directory, meta, record):
    paths = [
        directory / "predictions" / f"{record.artifact_stem}_meta.json",
        directory / "predictions" / f"{record.artifact_stem}_ink.zarr" / "meta.json",
    ]
    for path in paths:
        if not path.exists():
            record.absent_prediction_metadata.append(str(path.resolve()))
            continue
        _metadata_size(path)
        digest = sha256_file(path)
        details = _json_object(path)
        exporter = path.name == "meta.json"
        width, height = ("width", "height") if exporter else ("width_px", "height_px")
        if (
            _source_uri(details.get("source_uri")) != _source_uri(meta["local_uri"])
            or _positive_integer(details.get(width), width) != meta["width"]
            or _positive_integer(details.get(height), height) != meta["height"]
        ):
            raise ValueError(
                "prediction source or dimensions contradict candidate metadata"
            )
        origin = details.get("origin_xyz" if exporter else "position_xyz")
        if not isinstance(origin, list) or len(origin) != 3:
            raise ValueError("prediction must record its x/y/z origin")
        if [integer(value, "prediction origin") for value in origin] != [
            meta["x"],
            meta["y"],
            meta["z"],
        ]:
            raise ValueError("prediction origin contradicts candidate metadata")
        if not exporter:
            if any(
                name in details and integer(details[name], name) != meta[name]
                for name in ("x", "y", "z")
            ):
                raise ValueError(
                    "prediction scalar coordinates contradict its recorded origin"
                )
            if (
                "prediction_complete" in details
                and details["prediction_complete"] is not True
            ):
                raise ValueError(
                    "partial prediction cannot be summarized as a complete surface"
                )
            if (
                "num_parts" in details
                and _positive_integer(details["num_parts"], "num_parts") != 1
            ):
                raise ValueError("sharded prediction is incomplete")
            if (
                "coverage_fraction" in details
                and _finite(details["coverage_fraction"], "coverage_fraction") != 1
            ):
                raise ValueError("prediction coverage is incomplete")
            record.prediction_completeness_recorded = (
                details.get("prediction_complete") is True
                and details.get("coverage_fraction") == 1
            )
        elif (
            "slices" in details and _positive_integer(details["slices"], "slices") != 1
        ):
            raise ValueError("prediction metadata does not describe a single surface")
        record.prediction_geometry_checked = True
        record.source_files_sha256[str(path.resolve())] = digest


def _check_unchanged(directory, record, max_pixels):
    if any(Path(path).exists() for path in record.absent_prediction_metadata):
        raise ValueError("prediction metadata appeared during reporting")
    for path, digest in record.source_files_sha256.items():
        if sha256_file(path) != digest:
            raise ValueError("candidate input changed during reporting")
    ink = _load_ink_prediction(directory, record.artifact_stem, max_pixels=max_pixels)
    if ink is None or _array_digest(ink) != record.ink_array_sha256:
        raise ValueError("ink prediction changed during reporting")


def _process_candidate(
    candidate_dir,
    fiber_threshold,
    *,
    max_pixels=MAX_LABEL_PIXELS,
    max_voxels=MAX_FRAGMENT_VOXELS,
):
    directory = Path(candidate_dir).resolve()
    record = CandidateRecord()
    stage = "METADATA"
    try:
        match = re.fullmatch(r"candidate_(\d+)", directory.name)
        if match is None:
            raise ValueError("candidate directory must be named candidate_<integer>")
        record.candidate_index = int(match[1])
        path = directory / "candidate.json"
        if not path.exists():
            record.status, record.note = "MISSING_METADATA", "candidate.json is missing"
            return record
        _metadata_size(path)
        record.source_files_sha256[str(path)] = sha256_file(path)
        meta = _read_candidate_meta(directory)
        for name in (
            "artifact_stem",
            "scroll_id",
            "short_id",
            "division",
            "z",
            "y",
            "x",
            "review_score",
        ):
            setattr(record, name, meta.get(name))
        record.shape_yx = [meta["height"], meta["width"]]
        if math.prod(record.shape_yx) > _positive_integer(max_pixels, "max_pixels"):
            raise ValueError("candidate plane exceeds max_pixels")
        stage = "INK_PREDICTION"
        ink = _load_ink_prediction(
            directory, record.artifact_stem, max_pixels=max_pixels
        )
        if ink is None:
            record.status, record.note = "MISSING_INK_PREDICTION", "ink Zarr is missing"
            return record
        if tuple(ink.shape) != tuple(record.shape_yx):
            raise ValueError("ink surface shape contradicts candidate dimensions")
        _prediction_metadata(directory, meta, record)
        record.ink_array_sha256 = _array_digest(ink)
        stage = "FIBER_LABEL"
        path = directory / "fiber_label.tif"
        if not path.exists():
            record.status, record.note = (
                "MISSING_FIBER_LABEL",
                "fiber_label.tif is missing",
            )
            return record
        if (
            path.stat().st_size
            > _positive_integer(max_voxels, "max_voxels") * 16 + MAX_METADATA_BYTES
        ):
            raise ValueError("fiber TIFF file exceeds the bounded input byte budget")
        record.source_files_sha256[str(path)] = sha256_file(path)
        fiber = _load_fiber_label(directory, max_voxels=max_voxels)
        record.fiber_shape = list(fiber.shape)
        density = _project_fiber_to_surface(fiber)
        stage = "SHAPE"
        metrics = _compute_metrics(ink, density, fiber_threshold)
        stage = "INPUT_STABILITY"
        _check_unchanged(directory, record, max_pixels)
        for name, value in metrics.items():
            setattr(record, name, value)
        record.status = "INSPECTED"
    except REPORT_ERRORS as exc:
        record.status, record.note = f"INVALID_{stage}", str(exc)
    return record


def _aggregate(records):
    grouped = {}
    for record in records:
        if record.status == "INSPECTED":
            grouped.setdefault(
                (record.scroll_id, record.short_id, record.division), []
            ).append(record)
    groups = []
    for (scroll_id, short_id, division), members in sorted(grouped.items()):
        ratios = [
            r.ink_anti_fiber_ratio for r in members if r.ratio_status == "defined"
        ]
        statuses = {
            r.ratio_status: sum(m.ratio_status == r.ratio_status for m in members)
            for r in members
        }
        groups.append(
            {
                "scroll_id": scroll_id,
                "short_id": short_id,
                "division": division,
                "n_candidates": len(members),
                "n_defined_ratios": len(ratios),
                "ratio_status_counts": statuses,
                "mean_ink_pred": statistics.mean(r.ink_pred_mean for r in members),
                "mean_fiber": statistics.mean(r.fiber_mean for r in members),
                "mean_anti_fiber_ratio": statistics.mean(ratios) if ratios else None,
                "stdev_anti_fiber_ratio": statistics.stdev(ratios)
                if len(ratios) >= 2
                else None,
                "candidate_indices": sorted(r.candidate_index for r in members),
            }
        )
    return {
        "groups": groups,
        "total_candidates_inspected": sum(r.status == "INSPECTED" for r in records),
        "ratio_aggregation": "equal-weight mean of defined per-candidate ratios; not a pooled pixel ratio",
    }


def _cell(value):
    return escape(str(value)).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _fmt(value):
    return "n/a" if value is None else f"{value:.6g}"


def _render_markdown(summary, output_path):
    lines = [
        "# Candidate ink/fiber co-occurrence",
        "",
        f"Report status: **{summary['status']}**.",
        "",
        "Descriptive array statistics only. Shape equality does not establish spatial registration; "
        "fiber origin is unrecorded. Both artifacts can depend on the same CT. A ratio above or "
        "below one does not establish ink correctness, independent validation, or prize eligibility.",
        "",
        "Fiber density is the mean of binary labels across depth. Fiber-region pixels have density "
        f"strictly greater than {summary['fiber_threshold']:g}. Ratios use non-fiber/fiber mean ink "
        "probabilities; zero denominators and absent regions remain undefined, with a recorded reason.",
        "",
        "Group ratios are equal-weight means of defined candidate ratios, not pooled pixel ratios. "
        "Selection is the first N numeric candidate indices, not a population estimate.",
        "",
        "## Groups",
        "",
        "| Scroll | Division | Inspected | Defined ratios | Mean ink | Mean fiber | Mean ratio |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for group in summary["aggregate"]["groups"]:
        lines.append(
            f"| {_cell(group['scroll_id'])}/{_cell(group['short_id'])} | {_cell(group['division'])} "
            f"| {group['n_candidates']} | {group['n_defined_ratios']} | {_fmt(group['mean_ink_pred'])} "
            f"| {_fmt(group['mean_fiber'])} | {_fmt(group['mean_anti_fiber_ratio'])} |"
        )
    lines += [
        "",
        "## Candidates",
        "",
        "| Index | Stem | Status | Ink mean | Fiber mean | Ratio | Ratio status | Note |",
        "|---:|---|---|---:|---:|---:|---|---|",
    ]
    for record in summary["candidates"]:
        lines.append(
            f"| {record['candidate_index']} | {_cell(record['artifact_stem'])} | {record['status']} "
            f"| {_fmt(record['ink_pred_mean'])} | {_fmt(record['fiber_mean'])} "
            f"| {_fmt(record['ink_anti_fiber_ratio'])} | {record['ratio_status']} | {_cell(record['note'])} |"
        )
    output_path.write_text("\n".join(lines) + "\n")


def inspect_candidates(
    evidence_root,
    output,
    *,
    fiber_threshold=0.001,
    top_n=12,
    max_pixels=MAX_LABEL_PIXELS,
    max_voxels=MAX_FRAGMENT_VOXELS,
):
    threshold = _finite(fiber_threshold, "fiber_threshold")
    count = _positive_integer(top_n, "top_n", MAX_CANDIDATES)
    pixels = _positive_integer(max_pixels, "max_pixels")
    voxels = _positive_integer(max_voxels, "max_voxels")
    root = Path(evidence_root).resolve()
    if not root.is_dir():
        raise ValueError("evidence root must be an existing directory")
    output = new_output(output, root)
    directories = []
    for directory in root.glob("candidate_*"):
        directories.append(directory)
        if len(directories) > MAX_DISCOVERED_CANDIDATES:
            raise ValueError("evidence root exceeds the candidate discovery limit")
    if not directories or any(
        d.is_symlink() or not d.is_dir() or not re.fullmatch(r"candidate_\d+", d.name)
        for d in directories
    ):
        raise ValueError(
            "evidence root must contain real candidate_<integer> directories"
        )
    indices = [int(d.name.split("_")[1]) for d in directories]
    if len(indices) != len(set(indices)):
        raise ValueError("candidate indices must be unique")
    selected = sorted(directories, key=lambda d: int(d.name.split("_")[1]))[:count]
    records = [
        _process_candidate(d, threshold, max_pixels=pixels, max_voxels=voxels)
        for d in selected
    ]
    sources = [Path(path) for record in records for path in record.source_files_sha256]
    sources += [
        d / "predictions" / f"{r.artifact_stem}_ink.zarr"
        for d, r in zip(selected, records, strict=True)
    ]
    output = new_output(output, root, *sources)
    inspected = sum(r.status == "INSPECTED" for r in records)
    summary = {
        "schema": "candidate-ink-fiber-report-v1",
        "scope": "array_cooccurrence_descriptive",
        "status": "INSPECTED" if inspected == len(records) else "PARTIAL",
        "evidence_root": str(root),
        "fiber_threshold": threshold,
        "max_pixels": pixels,
        "max_voxels": voxels,
        "requested_candidates": count,
        "discovered_candidates": len(directories),
        "selected_candidates": len(records),
        "inspected_candidates": inspected,
        "failed_candidates": len(records) - inspected,
        "selection": "first N numeric candidate indices; not a population estimate",
        "alignment_verified": False,
        "independent_validation": False,
        "accuracy_measured": False,
        "prediction_completeness_verified": False,
        "training_executed": False,
        "candidates": [asdict(r) for r in records],
        "aggregate": _aggregate(records),
    }
    with publish_new(output) as staging:
        write_json(staging / "summary.json", summary)
        _render_markdown(summary, staging / "summary.md")
        if _json_object(staging / "summary.json") != summary:
            raise ValueError("written summary differs from measured report")
        for directory, record in zip(selected, records, strict=True):
            if record.status == "INSPECTED":
                _check_unchanged(directory, record, pixels)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path, required=True, help="new source-disjoint report directory"
    )
    parser.add_argument(
        "--fiber-threshold",
        type=float,
        default=0.001,
        help="fiber region iff mean binary depth occupancy is strictly greater than this threshold",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=12,
        help="maximum numeric-index candidates inspected, at most 256",
    )
    parser.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    parser.add_argument("--max-voxels", type=int, default=MAX_FRAGMENT_VOXELS)
    args = parser.parse_args(argv)
    try:
        summary = inspect_candidates(
            args.evidence_root,
            args.out,
            fiber_threshold=args.fiber_threshold,
            top_n=args.top_n,
            max_pixels=args.max_pixels,
            max_voxels=args.max_voxels,
        )
    except REPORT_ERRORS as exc:
        print(f"candidate ink/fiber report: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "scope": summary["scope"],
                "output": str(args.out.resolve()),
                "inspected_candidates": summary["inspected_candidates"],
                "failed_candidates": summary["failed_candidates"],
            },
            allow_nan=False,
        )
    )
    return 0 if summary["status"] == "INSPECTED" else 2


if __name__ == "__main__":
    sys.exit(main())
