"""Opt-in input receipts and read-only context checks for 3D proofreading.

Receipts bind configured inputs, not GUI edits, reviewed patch contents or a
resume position. Keep sources stable and serialize the GUI and verification.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from pathlib import Path

from .file_capture import capture_bytes
from .new_artifacts import publish_new_file
from .prediction_artifacts import validate_output_file

RECORD_NAME = "autoresearch_session.json"
PROGRESS_NAME = "progress.json"
DEFAULT_LIMITS = {
    "max_source_bytes": 8 * 1024**3,
    "max_file_bytes": 64 * 1024**2,
    "max_entries": 100_000,
}
JSON_BYTES = 2 * 1024**2


def limits(**values):
    result = DEFAULT_LIMITS | values
    if set(result) != set(DEFAULT_LIMITS) or any(
        type(value) is not int or value < 1 for value in result.values()
    ):
        raise ValueError(
            "session limits must be positive integers with supported names"
        )
    return result


def _state(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _inventory(root, budget):
    stack, states, files, size = [root], {}, [], 0
    while stack:
        path = stack.pop()
        info = path.lstat()
        states[path.relative_to(root).as_posix()] = _state(info)
        if len(states) > budget["max_entries"]:
            raise ValueError("proofreader source exceeds max_entries")
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                for entry in entries:
                    # Bound discovery too, before retaining a huge directory listing.
                    if len(stack) + len(states) >= budget["max_entries"]:
                        raise ValueError("proofreader source exceeds max_entries")
                    stack.append(Path(entry.path))
        else:
            validate_output_file(path, info, label="proofreader source")
            if info.st_size > budget["max_file_bytes"]:
                raise ValueError("proofreader source exceeds max_file_bytes")
            size += info.st_size
            if size > budget["max_source_bytes"]:
                raise ValueError("proofreader source exceeds max_source_bytes")
            files.append(path)
    return sorted(files), states, size


def fingerprint_source(path, budget):
    """Hash every encoded file in a bounded local tree, including Zarr metadata."""
    budget = limits(**budget)
    root = Path(path)
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("proofreader source must be a nonsymlink directory")
    root = root.resolve()
    files, before, size = _inventory(root, budget)
    digest = hashlib.sha256()
    for path in files:
        _, raw = capture_bytes(path, budget["max_file_bytes"])
        entry = [
            path.relative_to(root).as_posix(),
            len(raw),
            hashlib.sha256(raw).hexdigest(),
        ]
        digest.update(json.dumps(entry, ensure_ascii=True).encode() + b"\n")
    _, after, _ = _inventory(root, budget)
    if before != after:
        raise ValueError("proofreader source changed while fingerprinting")
    return {
        "path": str(root),
        "file_count": len(files),
        "encoded_bytes": size,
        "tree_sha256": digest.hexdigest(),
    }


def recorded_config(volume, labels, output, patch_size):
    """Explicit destinations prevent Villa's filename-based output discovery."""
    if type(patch_size) is not int or patch_size < 1:
        raise ValueError("patch_size must be a positive integer")
    output = Path(output).resolve()
    return {
        "dataset_out_path": str(output),
        "patch_size": patch_size,
        "min_z": 0,
        "min_label_percentage": 1,
        "sampling": "sequence",
        "target_label_value": "",
        "save_progress": True,
        "progress_file": str(output / PROGRESS_NAME),
        "output_label_zarr": str(output / "edited_labels.zarr"),
        "volumes": {
            "Autoresearch_Prediction": {
                "volume_path": str(Path(volume).resolve()),
                "label_path": str(Path(labels).resolve()),
            }
        },
    }


def _file_hash(path):
    validate_output_file(path, label="proofreader record/source")
    _, raw = capture_bytes(path, JSON_BYTES)
    return hashlib.sha256(raw).hexdigest()


def create_record(config, proofreader, budget):
    """Publish an immutable initial-input receipt after launcher input preflight."""
    from volume_cartographer_wrapper.volume import FastLocalVolume

    budget = limits(**budget)
    selected = config["volumes"]["Autoresearch_Prediction"]
    record = {
        "schema_version": 1,
        "kind": "autoresearch_proofreader_input_record",
        "config": config,
        "shape_zyx": list(FastLocalVolume(selected["volume_path"]).shape),
        "proofreader_sha256": _file_hash(proofreader),
        "limits": budget,
        "sources": {
            role: fingerprint_source(selected[key], budget)
            for role, key in (("ct", "volume_path"), ("labels", "label_path"))
        },
    }
    path = Path(config["dataset_out_path"]) / RECORD_NAME
    with publish_new_file(
        path, selected["volume_path"], selected["label_path"]
    ) as staging:
        staging.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    return path


def _json_file(path):
    validate_output_file(path, label="proofreader JSON")
    _, raw = capture_bytes(path, JSON_BYTES)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate proofreader JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite proofreader JSON value: {value}")

    return (
        json.loads(raw, object_pairs_hook=pairs, parse_constant=constant),
        hashlib.sha256(raw).hexdigest(),
    )


def _progress_summary(root, config, shape):
    path = root / PROGRESS_NAME
    if not path.exists() and not path.is_symlink():
        return {"present": False, "status_counts": None}
    progress, captured_sha256 = _json_file(path)
    expected = {
        "patch_size": config["patch_size"],
        "volume_selection": "Autoresearch_Prediction",
        "image_zarr": config["volumes"]["Autoresearch_Prediction"]["volume_path"],
        "label_zarr": config["volumes"]["Autoresearch_Prediction"]["label_path"],
        "volume_shape": shape,
        "coordinate_system": "highest_resolution",
        "dataset_out_path": str(root),
        "images_out_dir": str(root / "imagesTr"),
        "labels_out_dir": str(root / "labelsTr"),
    }
    if not isinstance(progress, dict) or not isinstance(progress.get("metadata"), dict):
        raise ValueError("proofreader progress needs source metadata")
    if any(progress["metadata"].get(key) != value for key, value in expected.items()):
        raise ValueError("proofreader progress context differs from the input record")
    log = progress.get("progress_log")
    if not isinstance(log, list):
        raise ValueError("proofreader progress_log must be a list")
    counts = dict.fromkeys(("approved", "skipped", "auto-skipped", "pending"), 0)
    for entry in log:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("status"), str)
            or entry["status"] not in counts
        ):
            raise ValueError("invalid proofreader progress status")
        coords, index, percent = (
            entry.get("coords"),
            entry.get("index"),
            entry.get("percentage"),
        )
        if (
            not isinstance(coords, list)
            or len(coords) != 3
            or any(
                type(c) is not int or c < 0 or c + config["patch_size"] > n
                for c, n in zip(coords, shape, strict=True)
            )
            or type(index) is not int
            or index < 0
            or index >= math.prod(n // config["patch_size"] for n in shape)
            or type(percent) not in (int, float)
            or not math.isfinite(percent)
            or not 0 <= percent <= 100
        ):
            raise ValueError(
                "invalid proofreader progress coordinates/index/percentage"
            )
        counts[entry["status"]] += 1
    return {
        "present": True,
        "captured_sha256": captured_sha256,
        "status_counts": counts,
    }


def verify_record(output, proofreader, budget):
    """Rehash sources and check logged context; do not resume, approve or ingest."""
    from volume_cartographer_wrapper.volume import FastLocalVolume

    root = Path(output).resolve()
    record, record_sha256 = _json_file(root / RECORD_NAME)
    if (
        not isinstance(record, dict)
        or type(record.get("schema_version")) is not int
        or record["schema_version"] != 1
        or record.get("kind") != "autoresearch_proofreader_input_record"
        or set(record)
        != {
            "schema_version",
            "kind",
            "config",
            "shape_zyx",
            "proofreader_sha256",
            "limits",
            "sources",
        }
    ):
        raise ValueError("unsupported proofreader input record")
    config, sources = record["config"], record["sources"]
    if (
        not isinstance(config, dict)
        or not isinstance(sources, dict)
        or set(sources) != {"ct", "labels"}
    ):
        raise ValueError("invalid proofreader input record config/sources")
    if any(
        not isinstance(sources[role], dict)
        or not isinstance(sources[role].get("path"), str)
        for role in sources
    ):
        raise ValueError("invalid proofreader source record")
    expected = recorded_config(
        sources["ct"]["path"], sources["labels"]["path"], root, config.get("patch_size")
    )
    if config != expected:
        raise ValueError(
            "proofreader config differs from the supported recorded settings"
        )
    shape = record["shape_zyx"]
    if (
        not isinstance(shape, list)
        or len(shape) != 3
        or any(type(n) is not int or n < config["patch_size"] for n in shape)
    ):
        raise ValueError("invalid proofreader recorded shape")
    if not isinstance(record["limits"], dict) or set(record["limits"]) != set(
        DEFAULT_LIMITS
    ):
        raise ValueError("invalid proofreader recorded limits")
    own, saved = limits(**budget), limits(**record["limits"])
    effective = {key: min(own[key], saved[key]) for key in own}
    if _file_hash(proofreader) != record["proofreader_sha256"]:
        raise ValueError("pinned proofreader source differs from the input record")
    for role, source in sources.items():
        if fingerprint_source(source["path"], effective) != source:
            raise ValueError(f"{role} source differs from the proofreader input record")
        if list(FastLocalVolume(source["path"]).shape) != shape:
            raise ValueError(
                f"{role} source shape differs from the proofreader input record"
            )
    return {
        "input_record_matches": True,
        "input_record_sha256": record_sha256,
        "progress": _progress_summary(root, config, shape),
        "resume_supported": False,
        "approved_patch_files_verified": False,
        "ink_training_ingestion_supported": False,
        "scope": "Configured input bytes and logged context only; not GUI-setting history, approval provenance, physical registration or patch contents.",
    }
