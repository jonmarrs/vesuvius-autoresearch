"""Pinned local TIFF/PNG imports for the checkout's CT ink-training layout.

No download, resampling, intensity conversion, checkpoint update or training.
Each input is captured/decoded separately; callers keep sources/writers stable.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import zarr

from scripts.labeling.label_artifacts import new_output, publish_new, publish_new_file
from vesuvius_autoresearch.core.file_capture import capture_bytes
from vesuvius_autoresearch.core.fragment_conversion import (
    MAX_PIXELS,
    decode_fragment_image,
)

DEFAULT_FILE_BYTES = 512 * 1024**2
DEFAULT_VOLUME_BYTES = 1024**3
MANIFEST_BYTES = 2 * 1024**2
LIMIT_KEYS = {"max_file_bytes", "max_pixels", "max_volume_bytes"}


def _integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _limits(max_file_bytes, max_pixels, max_volume_bytes):
    result = {
        "max_file_bytes": max_file_bytes,
        "max_pixels": max_pixels,
        "max_volume_bytes": max_volume_bytes,
    }
    for key, value in result.items():
        _integer(value, key)
    if max_pixels > MAX_PIXELS:
        raise ValueError(f"max_pixels must be <= {MAX_PIXELS}")
    return result


def _state(path):
    info = Path(path).stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _capture(path, limit):
    before = _state(path)
    resolved, data = capture_bytes(path, limit)
    after = _state(path)
    if before != after:
        raise ValueError(f"source changed while capturing: {path}")
    record = {
        "path": str(resolved),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return record, data, after


def _image(data, path, role, max_pixels):
    layer = role == "layer"
    values = decode_fragment_image(
        data,
        path,
        max_pixels,
        2 if layer else 1,
        formats={"TIFF"} if layer else {"PNG"},
        modes=None if layer else {"L"},
        require_identity_orientation=True,
    )
    if not layer and not np.isin(values, [0, 255]).all():
        raise ValueError(f"{role} must be binary uint8 PNG encoded as 0/255: {path}")
    return values


def _storage(shape):
    depth, height, width = shape
    chunks = (1, min(128, height), min(128, width))
    count = (
        depth
        * ((height + chunks[1] - 1) // chunks[1])
        * ((width + chunks[2] - 1) // chunks[2])
    )
    return chunks, count * math.prod(chunks) * 2


def _entries(plan):
    return (
        [("labels", plan["sources"]["labels"])]
        + (
            [("mask", plan["sources"]["mask"])]
            if plan["sources"]["mask"] is not None
            else []
        )
        + [("layer", record) for record in plan["sources"]["layers"]]
    )


def plan_import(
    source_dir,
    labels,
    z_start,
    z_stop,
    *,
    mask=None,
    aligned_labels=False,
    max_file_bytes=DEFAULT_FILE_BYTES,
    max_pixels=MAX_PIXELS,
    max_volume_bytes=DEFAULT_VOLUME_BYTES,
):
    """Decode/verify captures and return an allocation-bounded import manifest."""
    if aligned_labels is not True:
        raise ValueError("declare aligned_labels only after verifying the same XY grid")
    _integer(z_start, "z_start", 0)
    _integer(z_stop, "z_stop")
    if not 1 <= z_stop - z_start <= 512:
        raise ValueError("require 1..512 consecutive layers in [z_start, z_stop)")
    limits = _limits(max_file_bytes, max_pixels, max_volume_bytes)
    records = {"layers": [], "labels": None, "mask": None}
    shape: tuple[int, ...] | None = None
    paths: list[tuple[str, Path, int | None]] = [("labels", Path(labels), None)]
    if mask is not None:
        paths.append(("mask", Path(mask), None))
    paths += [
        ("layer", Path(source_dir) / f"{z:02d}.tif", z) for z in range(z_start, z_stop)
    ]
    states = []
    for role, path, index in paths:
        record, data, state = _capture(path, max_file_bytes)
        values = _image(data, path, role, max_pixels)
        if shape is None:
            shape = values.shape
            _, size = _storage((z_stop - z_start, *shape))
            if size > max_volume_bytes:
                raise ValueError(
                    f"CT chunk storage requires {size} bytes, exceeds max_volume_bytes={max_volume_bytes}"
                )
        if values.shape != shape:
            raise ValueError(
                f"all layers, labels and mask must have the same XY shape: {path}"
            )
        if role == "layer":
            records["layers"].append({"index": index, **record})
        else:
            records[role] = record
        states.append((record["path"], state))
        del values, data
    for path, state in states:
        if _state(path) != state:
            raise ValueError(f"source changed during planning: {path}")
    assert shape is not None  # The required label image establishes the XY shape.
    return {
        "contract": 1,
        "kind": "autoresearch_surface_volume_import",
        "shape_zyx": [z_stop - z_start, *shape],
        "source_z_range": [z_start, z_stop],
        "ct_dtype": "uint16",
        "ct_transform": "none",
        "alignment_basis": "caller_declared_same_xy_grid",
        "limits": limits,
        "sources": records,
    }


def write_plan(plan, output):
    _validate_plan(plan)
    encoded = (json.dumps(plan, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MANIFEST_BYTES:
        raise ValueError(f"import manifest exceeds {MANIFEST_BYTES} bytes")
    target = new_output(output, *(record["path"] for _, record in _entries(plan)))
    with publish_new_file(target) as staged:
        staged.write_bytes(encoded)
    return target


def _validate_plan(plan):
    keys = {
        "contract",
        "kind",
        "shape_zyx",
        "source_z_range",
        "ct_dtype",
        "ct_transform",
        "alignment_basis",
        "limits",
        "sources",
    }
    if (
        not isinstance(plan, dict)
        or set(plan) != keys
        or type(plan["contract"]) is not int
        or plan["contract"] != 1
    ):
        raise ValueError("unsupported import manifest contract or fields")
    if (
        plan["kind"],
        plan["ct_dtype"],
        plan["ct_transform"],
        plan["alignment_basis"],
    ) != (
        "autoresearch_surface_volume_import",
        "uint16",
        "none",
        "caller_declared_same_xy_grid",
    ):
        raise ValueError("unsupported import type, transform or alignment declaration")
    shape, span = plan["shape_zyx"], plan["source_z_range"]
    if (
        not isinstance(shape, list)
        or len(shape) != 3
        or not isinstance(span, list)
        or len(span) != 2
    ):
        raise ValueError("manifest must declare Z/Y/X shape and source Z range")
    for v in shape:
        _integer(v, "shape")
    for v in span:
        _integer(v, "source Z index", 0)
    if not 1 <= shape[0] == span[1] - span[0] <= 512:
        raise ValueError("manifest depth must match 1..512 consecutive source indices")
    if not isinstance(plan["limits"], dict) or set(plan["limits"]) != LIMIT_KEYS:
        raise ValueError("manifest limits are required")
    _limits(**plan["limits"])
    sources = plan["sources"]
    if (
        not isinstance(sources, dict)
        or set(sources) != {"labels", "mask", "layers"}
        or not isinstance(sources["layers"], list)
        or len(sources["layers"]) != shape[0]
    ):
        raise ValueError("manifest source records are incomplete")
    for index, record in enumerate(sources["layers"], span[0]):
        if (
            not isinstance(record, dict)
            or type(record.get("index")) is not int
            or record["index"] != index
        ):
            raise ValueError("source layer indices must remain consecutive and ordered")
        if (
            not isinstance(record.get("path"), str)
            or Path(record["path"]).name != f"{index:02d}.tif"
        ):
            raise ValueError("source layer filename must match its declared index")
    for role, record in _entries(plan):
        keys = {"path", "bytes", "sha256"} | ({"index"} if role == "layer" else set())
        if not isinstance(record, dict) or set(record) != keys:
            raise ValueError("invalid source record")
        if (
            not isinstance(record["path"], str)
            or not Path(record["path"]).is_absolute()
        ):
            raise ValueError("manifest source paths must be absolute")
        _integer(record["bytes"], "source byte count")
        if not isinstance(record["sha256"], str) or not re.fullmatch(
            "[0-9a-f]{64}", record["sha256"]
        ):
            raise ValueError("manifest sources must have SHA256 digests")


def build_import(
    manifest,
    output,
    *,
    max_file_bytes=DEFAULT_FILE_BYTES,
    max_pixels=MAX_PIXELS,
    max_volume_bytes=DEFAULT_VOLUME_BYTES,
):
    """Publish a new complete uint16 Zarr/PNG fragment from pinned input bytes."""
    manifest_record, raw, manifest_state = _capture(manifest, MANIFEST_BYTES)
    manifest_path = Path(manifest_record["path"])

    def invalid(token):
        raise ValueError(f"nonfinite JSON token in import manifest: {token}")

    plan = json.loads(raw, parse_constant=invalid)
    _validate_plan(plan)
    configured = _limits(max_file_bytes, max_pixels, max_volume_bytes)
    limits = {key: min(configured[key], plan["limits"][key]) for key in LIMIT_KEYS}
    shape = tuple(plan["shape_zyx"])
    chunks, stored_bytes = _storage(shape)
    if (
        shape[1] * shape[2] > limits["max_pixels"]
        or stored_bytes > limits["max_volume_bytes"]
    ):
        raise ValueError(
            "manifest geometry exceeds max_pixels/max_volume_bytes; set an explicit sufficient budget for both plan and build"
        )
    entries = _entries(plan)
    target = new_output(output, manifest_path, *(r["path"] for _, r in entries))
    states = [(str(manifest_path), manifest_state)]
    digest = hashlib.sha256()
    with publish_new(target) as staged:
        array = zarr.open(
            str(staged / "surface_volume.zarr"),
            mode="w",
            shape=shape,
            chunks=chunks,
            dtype="<u2",
            compressor=None,
        )
        array.attrs.update(
            {
                "axes": ["z", "y", "x"],
                "source_origin_zyx": [plan["source_z_range"][0], 0, 0],
                "normalization": "uint16_div_65535",
                "alignment_basis": plan["alignment_basis"],
            }
        )
        for role, expected in entries:
            record, data, state = _capture(expected["path"], limits["max_file_bytes"])
            if any(record[key] != expected[key] for key in ("path", "bytes", "sha256")):
                raise ValueError(
                    f"source no longer matches pinned manifest: {expected['path']}"
                )
            values = _image(data, record["path"], role, limits["max_pixels"])
            if values.shape != shape[1:]:
                raise ValueError("decoded input shape does not match the manifest")
            if role == "layer":
                z = expected["index"] - plan["source_z_range"][0]
                values = values.astype("<u2", copy=False)
                array[z] = values
                if not np.array_equal(array[z], values):
                    raise ValueError(f"CT readback differs at output slice {z}")
                digest.update(values.tobytes(order="C"))
            else:
                (
                    staged / ("inklabels.png" if role == "labels" else "mask.png")
                ).write_bytes(data)
            states.append((record["path"], state))
            del data, values
        record = {
            "contract": 1,
            "input_manifest_path": str(manifest_path),
            "input_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "plan": plan,
            "effective_limits": limits,
            "ct_decoded_sha256": digest.hexdigest(),
            "decoded_hash_encoding": "ZYX, C order, little-endian uint16",
            "ct_chunk_bytes": stored_bytes,
            "scope": "Verified captured values and readback; physical alignment and label quality remain caller-declared. No GPU/training or official-source verification.",
        }
        (staged / "import.json").write_text(
            json.dumps(record, indent=2, allow_nan=False) + "\n"
        )
        for path, state in states:
            if _state(path) != state:
                raise ValueError(f"source changed during import: {path}")
    return target
