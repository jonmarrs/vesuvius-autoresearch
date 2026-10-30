"""Bounded CT candidate labels, published as one new completed run directory."""

from __future__ import annotations

import csv
import io
import json
import math
import time
from pathlib import Path

import numpy as np
import tifffile

from scripts.candidate_artifacts import array_content_sha256, integer, write_json
from scripts.labeling.label_artifacts import (
    MAX_FRAGMENT_VOXELS,
    bbox_zyx,
    bounded_number,
    new_output,
    publish_new,
    volume,
)
from scripts.text_snapshot import Snapshot
from vesuvius_autoresearch.core.prediction_artifacts import prediction_stem
from vesuvius_autoresearch.fibers import detection
from vesuvius_autoresearch.fibers.provenance import file_sha256


def _shape(depth, height, width, max_voxels):
    shape = tuple(
        integer(value, name, 3)
        for value, name in zip(
            (depth, height, width), ("depth", "height", "width"), strict=True
        )
    )
    if math.prod(shape) > integer(max_voxels, "max_voxels", 1):
        raise ValueError(
            f"candidate shape {shape} exceeds max_voxels={max_voxels}; choose a bounded crop"
        )
    return shape


def load_candidates(path, top_n, depth, max_voxels):
    top_n = integer(top_n, "top_n", 1)
    if top_n > 256:
        raise ValueError("top_n must not exceed 256")
    # A regular file only: its bytes are hashed again before publication.
    source = Snapshot.read(path, 16 * 1024**2)
    reader = csv.DictReader(io.StringIO(source.text(), newline=""), delimiter="\t")
    headers = reader.fieldnames or []
    required = {"artifact_stem", "local_uri", "z", "y", "x", "width", "height"}
    if (
        any(not name for name in headers)
        or len(set(headers)) != len(headers)
        or not required.issubset(headers)
    ):
        raise ValueError(
            "candidate TSV needs unique headers including artifact_stem, local_uri, z/y/x, width/height"
        )
    candidates, windows = [], set()
    try:
        for row in reader:
            if len(candidates) == top_n:
                break
            if None in row or any(value is None for value in row.values()):
                raise ValueError("candidate TSV row does not match its headers")
            prediction_stem(row["artifact_stem"])
            uri = row["local_uri"]
            if not uri.strip() or "://" in uri or any(ord(c) < 32 for c in uri):
                raise ValueError("local_uri must name a local CT Zarr")
            metadata = dict(row)
            metadata["local_uri"] = str(Path(uri).expanduser().resolve())
            for key in ("scroll_id", "short_id", "division"):
                if key in metadata and (
                    not metadata[key].strip()
                    or len(metadata[key]) > 256
                    or any(ord(char) < 32 for char in metadata[key])
                ):
                    raise ValueError(f"{key} must be a nonempty bounded identifier")
            for key in ("z", "y", "x", "width", "height"):
                metadata[key] = integer(
                    row[key], key, 3 if key in ("height", "width") else 0
                )
            shape = _shape(depth, metadata["height"], metadata["width"], max_voxels)
            window = (
                metadata["local_uri"],
                metadata["z"],
                metadata["y"],
                metadata["x"],
                shape,
            )
            if window in windows:
                raise ValueError("duplicate physical candidate window")
            windows.add(window)
            score = row.get("review_score")
            if score not in (None, ""):
                score = float(score)
                if not math.isfinite(score):
                    raise ValueError("review_score must be finite")
                metadata["review_score"] = score
            else:
                metadata.pop("review_score", None)
            candidates.append(
                {"index": len(candidates), "metadata": metadata, "shape": shape}
            )
    except csv.Error as exc:
        raise ValueError(f"invalid candidate TSV: {exc}") from exc
    if not candidates:
        raise ValueError("candidate TSV has no selected rows")
    return candidates, source.provenance()["sha256"]


def _inspect(path, z, y, x, depth, height, width, max_voxels):
    shape = _shape(depth, height, width, max_voxels)
    root, array = volume(path)
    if array.dtype.kind not in "uif" or array.dtype.itemsize > 8:
        raise ValueError("CT must contain real numeric intensities")
    bounds, selection = bbox_zyx(
        (z, z + shape[0], y, y + shape[1], x, x + shape[2]), array.shape
    )
    snapshot = {
        "source_path": str(Path(path).resolve()),
        "source_shape_zyx": list(array.shape),
        "source_dtype": str(array.dtype),
        "source_root_attrs": dict(root.attrs),
        "source_array_attrs": dict(array.attrs),
        "evaluated_bbox_zyx": list(bounds),
        "shape_zyx": list(shape),
    }
    json.dumps(snapshot, allow_nan=False)
    return array, selection, snapshot


def _arguments(candidate) -> tuple[str, int, int, int, int, int, int]:
    m = candidate["metadata"]
    depth, height, width = candidate["shape"]
    return (m["local_uri"], m["z"], m["y"], m["x"], depth, height, width)


def load_ct_window(
    local_uri, z, y, x, depth, height, width, max_voxels=MAX_FRAGMENT_VOXELS
):
    array, selection, _ = _inspect(local_uri, z, y, x, depth, height, width, max_voxels)
    return _convert(array[selection], (depth, height, width))


def _convert(raw, shape):
    if raw.shape != tuple(shape):
        raise ValueError("CT read did not match the exact requested shape")
    data = raw.astype(np.float32)
    if not np.isfinite(data).all():
        raise ValueError("CT contains nonfinite or unrepresentable intensities")
    if raw.dtype == np.uint8:
        data /= 255.0
    return data


def _filter(ct, backend, filter_fn):
    if backend == "cupy":
        import cupy as cp

        result = cp.asnumpy(filter_fn(cp.asarray(ct)))
    elif backend == "numpy":
        result = filter_fn(ct)
    else:
        raise ValueError("unknown fiber filter backend")
    result = np.asarray(result)
    if result.dtype.kind != "f":
        raise ValueError("vesselness must be floating-point")
    result = result.astype(np.float32, copy=False)
    if (
        result.shape != ct.shape
        or not np.isfinite(result).all()
        or np.any((result < 0) | (result > 1))
    ):
        raise ValueError("vesselness must be finite in [0,1] and match the CT shape")
    return result


def run_candidates(args, *, select_backend, filter_fn):
    depth = integer(args.depth, "depth", 3)
    threshold = bounded_number(args.threshold, "threshold", 0, 1)
    budget = integer(args.max_voxels, "max_voxels", 1)
    table = Path(args.candidates).resolve()
    candidates, table_sha = load_candidates(table, args.top_n, depth, budget)
    output = new_output(
        args.evidence_root, table, *(c["metadata"]["local_uri"] for c in candidates)
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "PLANNED",
                    "output": str(output),
                    "candidates": candidates,
                    "max_voxels": budget,
                    "input_tsv_sha256": table_sha,
                    "scope": "TSV/settings/output checks only; CT and CUDA not checked",
                },
                allow_nan=False,
            )
        )
        return 0
    # Inspect every selected source header before backend resolution or staging.
    snapshots = [_inspect(*_arguments(c), budget)[2] for c in candidates]
    backend = select_backend(args.use_gpu)
    filter_sha = file_sha256(detection.__file__)
    checks, records = [], []
    with publish_new(output) as staging:
        for candidate, planned in zip(candidates, snapshots, strict=True):
            started = time.perf_counter()
            array, selection, snapshot = _inspect(*_arguments(candidate), budget)
            if snapshot != planned:
                raise ValueError("CT metadata changed after preflight")
            raw = array[selection]
            ct_sha = array_content_sha256(raw)
            ct = _convert(raw, candidate["shape"])
            response = _filter(ct, backend, filter_fn)
            label = (response >= threshold).astype(np.uint8)
            name = f"candidate_{candidate['index']:03d}"
            directory = staging / name
            directory.mkdir()
            for filename, values in (
                ("fiber_prob.tif", response),
                ("fiber_label.tif", label),
            ):
                path = directory / filename
                tifffile.imwrite(
                    path, values, photometric="minisblack", metadata={"axes": "ZYX"}
                )
                with tifffile.TiffFile(path) as tif:
                    if (
                        len(tif.series) != 1
                        or tif.series[0].axes != "ZYX"
                        or tif.series[0].dtype != values.dtype
                        or not np.array_equal(tif.asarray(), values)
                    ):
                        raise ValueError("serialized fiber TIFF failed readback")
            metadata = {
                "contract": 1,
                "label_kind": "ct_vesselness_pseudo_label",
                "axes": ["z", "y", "x"],
                **snapshot,
                "ct_content_sha256": ct_sha,
                "threshold": threshold,
                "backend": backend,
                "filter_source_sha256": filter_sha,
                "value_semantics": "vesselness heuristic, not calibrated fiber probability",
                "fiber_voxel_fraction": float(label.mean()),
                "prob_file_sha256": file_sha256(directory / "fiber_prob.tif"),
                "label_file_sha256": file_sha256(directory / "fiber_label.tif"),
            }
            write_json(directory / "candidate.json", candidate["metadata"])
            write_json(directory / "fiber_labels_meta.json", metadata)
            records.append(
                {
                    "candidate_index": candidate["index"],
                    "artifact_stem": candidate["metadata"]["artifact_stem"],
                    "status": "OK",
                    "prob_path": str(output / name / "fiber_prob.tif"),
                    "label_path": str(output / name / "fiber_label.tif"),
                    "elapsed_s": time.perf_counter() - started,
                    "fiber_voxel_fraction": metadata["fiber_voxel_fraction"],
                }
            )
            checks.append((candidate, snapshot, ct_sha))
            del raw, ct, response, label
        # Bind the captured TSV bytes to the parse and recheck all decoded CT
        # windows at the end, including candidates processed earlier in the run.
        if (
            file_sha256(table) != table_sha
            or file_sha256(detection.__file__) != filter_sha
        ):
            raise ValueError("candidate TSV or filter source changed during processing")
        for candidate, snapshot, expected in checks:
            array, _, current = _inspect(*_arguments(candidate), budget)
            m = candidate["metadata"]
            if (
                current != snapshot
                or array_content_sha256(
                    array, start=(m["z"], m["y"], m["x"]), shape=candidate["shape"]
                )
                != expected
            ):
                raise ValueError("CT source changed during processing")
        # After every recheck, so a staging directory left by a killed run
        # claims completion only once its contents have all been checked.
        write_json(
            staging / "fiber_labels_summary.json",
            {
                "contract": 1,
                "complete": True,
                "label_kind": "ct_vesselness_pseudo_label",
                "backend": backend,
                "threshold": threshold,
                "depth": depth,
                "max_voxels": budget,
                "input_tsv": str(table),
                "input_tsv_sha256": table_sha,
                "candidates": records,
            },
        )
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "output": str(output),
                "candidates": len(records),
                "backend": backend,
            }
        )
    )
    return 0
