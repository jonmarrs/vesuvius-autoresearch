"""Opt-in input receipts and read-only context checks for 3D proofreading.

Receipts bind configured inputs, not GUI edits, reviewed patch contents or a
resume position. Keep sources stable and serialize the GUI and verification.
"""

from __future__ import annotations

import hashlib
import io
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
    return _fingerprint_source(path, budget)[0]


def _fingerprint_source(path, budget):
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
    return (
        {
            "path": str(root),
            "file_count": len(files),
            "encoded_bytes": size,
            "tree_sha256": digest.hexdigest(),
        },
        after,
    )


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


def _progress_summary(
    root, config, shape, *, ct=None, budget=None, edited_label_path=None
):
    path = root / PROGRESS_NAME
    if not path.exists() and not path.is_symlink():
        if ct is not None:
            raise ValueError("approved export verification requires progress.json")
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
    result = {
        "present": True,
        "captured_sha256": captured_sha256,
        "status_counts": counts,
    }
    if ct is not None:
        result["approved_exports"] = _verify_exports(
            root, progress, ct, config, budget, edited_label_path=edited_label_path
        )
        if _file_hash(path) != captured_sha256:
            raise ValueError("proofreader progress changed during export verification")
    return result


def _approved_exports(progress, edge):
    """Reconstruct the pinned writer's export list from validated log entries."""
    approved, seen = [], set()
    for entry in progress["progress_log"]:
        if entry["status"] != "approved":
            continue
        z, y, x = entry["coords"]
        coords = (z, y, x)
        if coords in seen:
            raise ValueError(f"duplicate approval for {coords} shares one TIFF pair")
        seen.add(coords)
        stem = f"z{z}_y{y}_x{x}"
        approved.append(
            {
                "volume_index": 0,
                "coords": entry["coords"],
                "percentage": entry["percentage"],
                "index": entry["index"],
                "date_processed": entry.get("date_processed", ""),
                "image_filename": f"{stem}_0000.tif",
                "label_filename": f"{stem}.tif",
                "patch_size": edge,
            }
        )
    total = progress["metadata"].get("total_approved")
    if (
        type(total) is not int
        or total != len(approved)
        or json.dumps(progress.get("approved_patches"), sort_keys=True)
        != json.dumps(approved, sort_keys=True)
    ):
        raise ValueError("approved patch list/count differs from progress log")
    return approved


def _export_inventory(root, approved, budget):
    states, encoded_bytes = {}, 0
    for directory, key in (
        ("imagesTr", "image_filename"),
        ("labelsTr", "label_filename"),
    ):
        path = root / directory
        names = {patch[key] for patch in approved}
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            if not names:
                continue
            raise ValueError(f"missing approved TIFF directory: {path}") from exc
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"proofreader export directory must not be linked: {path}")
        states[path] = _state(info)
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.name not in names:
                    raise ValueError(f"unlisted proofreader export: {entry.path}")
                names.remove(entry.name)
                item = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                validate_output_file(item, info, label="proofreader export")
                states[item] = _state(info)
                encoded_bytes += info.st_size
                if info.st_size > budget["max_file_bytes"]:
                    raise ValueError(
                        f"proofreader export exceeds max_file_bytes: {item}"
                    )
                if encoded_bytes > budget["max_source_bytes"]:
                    raise ValueError("proofreader exports exceed max_source_bytes")
        if names:
            raise ValueError(f"missing approved TIFF in {path}: {min(names)}")
    if len(states) > budget["max_entries"]:
        raise ValueError("proofreader exports exceed max_entries")
    return states


def _capture_tiff(path, edge, limit, role):
    import tifffile

    _, raw = capture_bytes(path, limit)
    try:
        with tifffile.TiffFile(io.BytesIO(raw), _multifile=False) as tiff:
            if len(tiff.series) != 1:
                raise ValueError(f"expected one TIFF series: {path}")
            series = tiff.series[0]
            shape, dtype = (edge,) * 3, series.dtype
            if series.shape != shape or dtype.kind not in (
                "bui" if role == "label" else "buif"
            ):
                raise ValueError(f"invalid {role} TIFF shape or dtype: {path}")
            if edge**3 * dtype.itemsize > limit:
                raise ValueError(f"decoded TIFF exceeds max_file_bytes: {path}")
            pixels = 0
            for page in tiff.pages:
                counts, offsets = page.databytecounts, page.dataoffsets
                planes, depth, rows, width, samples = page.shaped
                # TIFF pads each scanline of a packed boolean page to a whole byte.
                row_bytes = (width * samples * page.bitspersample + 7) // 8
                # the pinned writer emits uncompressed TIFFs
                if (
                    page.dtype != dtype
                    or page.compression != 1
                    or page.is_tiled
                    or not counts
                    or sum(counts) != planes * depth * rows * row_bytes
                    or any(
                        o <= 0 or n <= 0 or o + n > len(raw)
                        for o, n in zip(offsets, counts, strict=True)
                    )
                ):
                    raise ValueError(
                        f"invalid or incomplete proofreader TIFF data: {path}"
                    )
                pixels += page.size
            if pixels != edge**3:
                raise ValueError(f"incomplete proofreader TIFF patch: {path}")
            values = series.asarray()
    except tifffile.TiffFileError as exc:
        # a structure tifffile cannot parse is refused as the other malformed exports are
        raise ValueError(f"unreadable proofreader TIFF: {path}: {exc}") from exc
    return values, {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _open_edited_labels(path, shape, budget):
    import numpy as np
    import zarr

    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"missing edited-label Zarr: {path}") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"edited-label Zarr must be a nonsymlink directory: {path}")
    _, states, _ = _inventory(path, budget)
    if ".zarray" not in states:
        raise ValueError(f"edited-label Zarr must be a bare Zarr v2 array: {path}")
    try:
        array = zarr.open_array(str(path), mode="r")
    except zarr.errors.MetadataError as exc:
        raise ValueError(f"invalid edited-label Zarr metadata: {path}") from exc
    if (
        array.shape != shape
        or any(type(n) is not int for n in array.shape)
        or array.dtype != np.dtype("uint8")
        or array.fill_value != 0
    ):
        raise ValueError(
            f"edited-label Zarr must match the CT shape with uint8 labels and zero fill: {path}"
        )
    chunks = array.chunks
    if len(chunks) != len(shape) or any(type(n) is not int or n < 1 for n in chunks):
        raise ValueError(f"invalid edited-label Zarr chunk geometry: {path}")
    if math.prod(chunks) > budget["max_file_bytes"]:
        raise ValueError(
            f"decoded edited-label Zarr chunk exceeds max_file_bytes: {path}"
        )
    return array, states


def _verify_exports(root, progress, ct, config, budget, *, edited_label_path=None):
    import numpy as np

    edge = config["patch_size"]
    approved = _approved_exports(progress, edge)
    if approved and 2 * len(approved) + 2 > budget["max_entries"]:
        raise ValueError("proofreader exports exceed max_entries")
    before = _export_inventory(root, approved, budget)
    limit = budget["max_file_bytes"]
    if approved and max(edge**3, math.prod(ct.chunks)) * ct.dtype.itemsize > limit:
        raise ValueError("decoded CT patch or chunk exceeds max_file_bytes")
    edited, edited_state = None, None
    if edited_label_path is not None:
        edited, edited_state = _open_edited_labels(edited_label_path, ct.shape, budget)
    pairs = []
    for patch in approved:
        image, image_id = _capture_tiff(
            root / "imagesTr" / patch["image_filename"], edge, limit, "image"
        )
        label, label_id = _capture_tiff(
            root / "labelsTr" / patch["label_filename"], edge, limit, "label"
        )
        coords = patch["coords"]
        source = ct.get_chunk(*coords, edge, edge, edge)
        if image.dtype.newbyteorder("=") != source.dtype.newbyteorder(
            "="
        ) or not np.array_equal(image, source):
            raise ValueError(
                f"approved image TIFF differs from recorded CT at {coords}"
            )
        if int(label.min()) < 0 or int(label.max()) > 255:
            raise ValueError(f"approved categorical label outside 0..255 at {coords}")
        if edited is not None:
            slices = tuple(slice(origin, origin + edge) for origin in coords)
            if not np.array_equal(edited[slices], label):
                raise ValueError(
                    f"approved label TIFF differs from edited-label Zarr at {coords}"
                )
        pairs.append(
            {
                "coords_zyx": coords,
                "image": {"path": "imagesTr/" + patch["image_filename"], **image_id},
                "label": {"path": "labelsTr/" + patch["label_filename"], **label_id},
            }
        )
    if _export_inventory(root, approved, budget) != before:
        raise ValueError("proofreader exports changed during verification")
    report = {"pairs_verified": len(pairs), "pairs": pairs}
    if edited_label_path is not None:
        if _inventory(edited_label_path, budget)[1] != edited_state:
            raise ValueError("edited-label Zarr changed during export verification")
        report["edited_labels"] = {
            "path": edited_label_path.name,
            "shape_zyx": list(edited.shape),
            "dtype": str(edited.dtype),
            "approved_crops_verified": len(pairs),
        }
    return report


def verify_record(
    output,
    proofreader,
    budget,
    *,
    verify_approved_patches=False,
    verify_edited_labels=False,
):
    """Rehash sources, check progress and optionally verify saved TIFFs and Zarr."""
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
    check_exports = verify_approved_patches or verify_edited_labels
    ct, source_states = None, {}
    for role, source in sources.items():
        fingerprint, snapshot = _fingerprint_source(source["path"], effective)
        if fingerprint != source:
            raise ValueError(f"{role} source differs from the proofreader input record")
        volume = FastLocalVolume(source["path"])
        if list(volume.shape) != shape:
            raise ValueError(
                f"{role} source shape differs from the proofreader input record"
            )
        if check_exports:
            source_states[role] = (Path(source["path"]), snapshot)
            if role == "ct":
                ct = volume
    progress = _progress_summary(
        root,
        config,
        shape,
        ct=ct,
        budget=effective,
        edited_label_path=Path(config["output_label_zarr"])
        if verify_edited_labels
        else None,
    )
    if check_exports:
        for role, (path, snapshot) in source_states.items():
            if _inventory(path, effective)[1] != snapshot:
                name = "CT" if role == "ct" else role
                raise ValueError(f"recorded {name} changed during export verification")
        if _file_hash(root / RECORD_NAME) != record_sha256:
            raise ValueError(
                "proofreader input record changed during export verification"
            )
    report = {
        "input_record_matches": True,
        "input_record_sha256": record_sha256,
        "progress": progress,
        "resume_supported": False,
        "approved_patch_files_verified": ct is not None,
        "ink_training_ingestion_supported": False,
        "scope": "Configured input bytes, logged context and saved TIFF pair consistency with CT. Label values are checked for categorical range."
        if ct is not None
        else "Configured input bytes and logged context only; not GUI-setting history, approval provenance, physical registration or patch contents.",
    }
    if verify_edited_labels:
        report["scope"] += " Edited-label Zarr values match within approved crops."
    return report
