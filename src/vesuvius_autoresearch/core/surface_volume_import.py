"""Pinned local TIFF/PNG imports for the checkout's CT ink-training layout.

No download, resampling, intensity conversion, checkpoint update or training.
Each input is captured/decoded separately; callers keep sources/writers stable.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
import zarr

from vesuvius_autoresearch.core.file_capture import capture_bytes
from vesuvius_autoresearch.core.fragment_conversion import (
    MAX_PIXELS,
    decode_fragment_image,
)
from vesuvius_autoresearch.core.new_artifacts import (
    new_output,
    publish_new,
    publish_new_file,
)
from vesuvius_autoresearch.core.prediction_artifacts import validate_output_file

DEFAULT_FILE_BYTES = 512 * 1024**2
DEFAULT_VOLUME_BYTES = 1024**3
MANIFEST_BYTES = 2 * 1024**2
RECEIPT_BYTES = 4 * MANIFEST_BYTES
CT_HASH_ENCODING = "ZYX, C order, little-endian uint16"
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


def _ct_attrs(plan):
    return {
        "axes": ["z", "y", "x"],
        "source_origin_zyx": [plan["source_z_range"][0], 0, 0],
        "normalization": "uint16_div_65535",
        "alignment_basis": plan["alignment_basis"],
    }


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


def _recorded_source_path(value, portable):
    if isinstance(value, str):
        local = Path(value)
        if local.is_absolute():
            return local
        if portable:
            for path in (PurePosixPath(value), PureWindowsPath(value)):
                if path.is_absolute():
                    return path
    raise ValueError("manifest source paths must be absolute")


def _validate_plan(plan, *, portable_paths=False):
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
            _recorded_source_path(record.get("path"), portable_paths).name
            != f"{index:02d}.tif"
        ):
            raise ValueError("source layer filename must match its declared index")
    for role, record in _entries(plan):
        keys = {"path", "bytes", "sha256"} | ({"index"} if role == "layer" else set())
        if not isinstance(record, dict) or set(record) != keys:
            raise ValueError("invalid source record")
        if role != "layer":
            _recorded_source_path(record["path"], portable_paths)
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
            write_empty_chunks=True,
            dimension_separator=".",
        )
        array.attrs.update(_ct_attrs(plan))
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
            "decoded_hash_encoding": CT_HASH_ENCODING,
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


def _verified_json(raw, path):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def invalid(token):
        raise ValueError(f"nonfinite JSON token {token!r}")

    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def verify_import(
    fragment,
    *,
    max_file_bytes=DEFAULT_FILE_BYTES,
    max_pixels=MAX_PIXELS,
    max_volume_bytes=DEFAULT_VOLUME_BYTES,
):
    """Check the local dense CT and copied PNGs against an existing import receipt."""
    root = Path(fragment).resolve(strict=True)
    store = root / "surface_volume.zarr"
    if store.is_symlink() or not store.is_dir():
        raise ValueError(f"expected the original local CT directory: {store}")
    states = {root: _state(root), store: _state(store)}

    def read(path, limit):
        validate_output_file(path, label="prepared fragment")
        record, raw, state = _capture(path, limit)
        states[path] = state
        return record, raw

    receipt_path = root / "import.json"
    receipt_id, raw = read(receipt_path, RECEIPT_BYTES)
    receipt = _verified_json(raw, receipt_path)
    if (
        type(receipt.get("contract")) is not int
        or receipt["contract"] != 1
        or receipt.get("decoded_hash_encoding") != CT_HASH_ENCODING
        or not isinstance(receipt.get("ct_decoded_sha256"), str)
        or not re.fullmatch("[0-9a-f]{64}", receipt["ct_decoded_sha256"])
    ):
        raise ValueError("unsupported fragment import receipt or CT hash encoding")
    plan = receipt.get("plan")
    # Source paths in a completed import are provenance. A copy may have come
    # from a machine with a different filesystem path syntax.
    _validate_plan(plan, portable_paths=True)
    saved = receipt.get("effective_limits")
    if not isinstance(saved, dict) or set(saved) != LIMIT_KEYS:
        raise ValueError("invalid receipt resource limits")
    saved = _limits(**saved)
    requested = _limits(max_file_bytes, max_pixels, max_volume_bytes)
    limits = {
        key: min(saved[key], plan["limits"][key], requested[key]) for key in LIMIT_KEYS
    }
    shape = plan["shape_zyx"]
    depth, height, width = shape
    chunks, stored_bytes = _storage(shape)
    if (
        height * width > limits["max_pixels"]
        or stored_bytes > limits["max_volume_bytes"]
    ):
        raise ValueError("prepared fragment exceeds max_pixels/max_volume_bytes")
    if (
        type(receipt.get("ct_chunk_bytes")) is not int
        or receipt["ct_chunk_bytes"] != stored_bytes
    ):
        raise ValueError("receipt chunk byte count disagrees with geometry")

    header_path = store / ".zarray"
    header = _verified_json(read(header_path, RECEIPT_BYTES)[1], header_path)
    separator = header.pop("dimension_separator", ".")
    expected_header = {
        "zarr_format": 2,
        "shape": shape,
        "chunks": list(chunks),
        "dtype": "<u2",
        "compressor": None,
        "filters": None,
        "fill_value": 0,
        "order": "C",
    }
    if separator != "." or json.dumps(header, sort_keys=True) != json.dumps(
        expected_header, sort_keys=True
    ):
        raise ValueError(
            f"CT Zarr metadata differs from the import contract: {header_path}"
        )
    attrs_path = store / ".zattrs"
    attrs = _verified_json(read(attrs_path, RECEIPT_BYTES)[1], attrs_path)
    for key, value in _ct_attrs(plan).items():
        if json.dumps(attrs.get(key)) != json.dumps(value):
            raise ValueError(f"CT Zarr attribute {key} differs from the import receipt")

    images = {}
    for role, filename in (("labels", "inklabels.png"), ("mask", "mask.png")):
        path = root / filename
        expected = plan["sources"][role]
        if expected is None:
            if path.exists() or path.is_symlink():
                raise ValueError(f"unexpected {filename} in prepared fragment")
            continue
        record, raw = read(path, limits["max_file_bytes"])
        if any(record[key] != expected[key] for key in ("bytes", "sha256")):
            raise ValueError(f"{filename} differs from the import receipt")
        if _image(raw, path, role, limits["max_pixels"]).shape != (height, width):
            raise ValueError(f"{filename} shape differs from the import receipt")
        images[filename] = record["sha256"]
    del raw

    digest = hashlib.sha256()
    _, tile_y, tile_x = chunks
    chunk_bytes = math.prod(chunks) * 2
    plane = np.empty((height, width), dtype="<u2")
    for z in range(depth):
        for cy, y in enumerate(range(0, height, tile_y)):
            for cx, x in enumerate(range(0, width, tile_x)):
                chunk = store / f"{z}.{cy}.{cx}"
                try:
                    _, raw = read(chunk, chunk_bytes)
                except FileNotFoundError as exc:
                    raise ValueError(f"missing CT chunk: {chunk}") from exc
                if len(raw) != chunk_bytes:
                    raise ValueError(f"incomplete CT chunk: {chunk}")
                tile = np.frombuffer(raw, dtype="<u2").reshape(tile_y, tile_x)
                target = plane[y : y + tile_y, x : x + tile_x]
                target[:] = tile[: target.shape[0], : target.shape[1]]
        digest.update(memoryview(plane).cast("B"))
    actual = digest.hexdigest()
    if actual != receipt["ct_decoded_sha256"]:
        raise ValueError("decoded CT digest differs from the import receipt")
    for path, state in states.items():
        if path.is_symlink() or _state(path) != state:
            raise ValueError(f"prepared fragment changed during verification: {path}")
    return {
        "status": "verified",
        "path": str(root),
        "import_receipt_sha256": receipt_id["sha256"],
        "shape_zyx": shape,
        "ct_chunk_count": stored_bytes // chunk_bytes,
        "ct_decoded_sha256": actual,
        "image_sha256": images,
    }
