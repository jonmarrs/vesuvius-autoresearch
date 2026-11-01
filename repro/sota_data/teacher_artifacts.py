"""Immutable teacher caches using the raw downloader's conditional range transport."""

import hashlib
import io
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import tifffile

from . import download_artifacts as transport
from .fragment import resolve_float_encoding

DEFAULT_MAX_BYTES = 2 * 1024**3
MAX_BYTES = 8 * 1024**3
# The largest teacher the distillation runners recorded is 34880 x 97280 = 3,393,126,400
# pixels (reports/detector/sota_distill_measurement.json).
MAX_PIXELS = 4 * 1024**3


def _budget(value):
    if type(value) is not int or not 1 <= value <= MAX_BYTES:
        raise ValueError(f"max_bytes must be an integer from 1 to {MAX_BYTES}")
    return value


def _header(source):
    try:
        image = tifffile.TiffFile(source)
    except tifffile.TiffFileError as exc:  # an Exception, not a ValueError
        raise ValueError(f"teacher is not a readable TIFF: {exc}") from exc
    with image:
        if len(image.pages) != 1 or len(image.series) != 1:
            raise ValueError("teacher must be one scalar 2D TIFF, not a stack")
        page = image.pages[0]
        if len(page.shape) != 2 or min(page.shape) <= 0 or page.samplesperpixel != 1:
            raise ValueError("teacher must be a nonempty scalar 2D TIFF")
        if math.prod(page.shape) > MAX_PIXELS:
            raise ValueError(f"teacher exceeds max_pixels={MAX_PIXELS}")
        dtype = np.dtype(page.dtype)
        if not (
            dtype.kind == "u"
            and dtype.itemsize in {1, 2}
            or dtype.kind == "f"
            and dtype.itemsize in {2, 4, 8}
        ):
            raise ValueError(f"unsupported teacher dtype: {dtype}")
        return {"shape": list(page.shape), "dtype": dtype.str}


def plan_teacher(filesystem, prefix, source=None, max_bytes=DEFAULT_MAX_BYTES):
    prefix = transport.source_prefix(prefix)
    maximum = _budget(max_bytes)
    entries = transport._listing(filesystem, prefix, 4096)
    candidates = sorted(
        name for name in entries if not name.startswith(".") and name.endswith(".tif")
    )
    if not candidates:
        raise ValueError(f"no teacher .tif under {prefix}")
    if source is None:
        if len(candidates) != 1:
            raise ValueError(
                f"ambiguous teacher predictions; choose source explicitly: {candidates}"
            )
        source = candidates[0]
    if not isinstance(source, str) or source not in candidates:
        raise ValueError("source must be one exact candidate TIFF basename")
    item = transport._file(
        entries[source],
        "teacher.tif",
        "teacher_prediction",
        {"max_file_bytes": maximum},
    )
    if transport._is_s3(filesystem) and item["etag"] is None:
        raise ValueError("S3 teacher requires an ETag for conditional requests")
    plan = {
        "contract": 1,
        "status": "METADATA_PLAN_ONLY",
        "prefix": "s3://" + prefix,
        "source": "s3://" + item["key"],
        "candidates": ["s3://" + prefix + "/" + name for name in candidates],
        "payload": item,
        "max_bytes": maximum,
        "max_pixels": MAX_PIXELS,
        "ground_truth": False,
        "alignment_verified": False,
        "training_ready": False,
    }
    if len(json.dumps(plan, indent=2).encode("utf-8")) > 60 * 1024:
        raise ValueError("teacher selection metadata exceeds completion record budget")
    return plan


def _local_output(output):
    if "://" in str(output) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", str(output)):
        raise ValueError("teacher cache must be a local filesystem directory")
    return Path(output).absolute()


def _cache_record(
    output, prefix, source=None, max_bytes=DEFAULT_MAX_BYTES, *, verify=True
):
    output = _local_output(output)
    if (
        output.is_symlink()
        or not output.is_dir()
        or {path.name for path in output.iterdir()} != {"teacher.tif", "teacher.json"}
    ):
        raise ValueError(
            "incomplete or unexpected teacher cache; use a fresh cache directory"
        )
    path = output / "teacher.json"
    if (
        path.is_symlink()
        or not path.is_file()
        or not 0 < path.stat().st_size <= 64 * 1024
    ):
        raise ValueError("invalid teacher completion record")
    with path.open("rb") as stream:
        data = stream.read(64 * 1024 + 1)
    if len(data) > 64 * 1024:
        raise ValueError("teacher completion record too large")
    try:
        record = json.loads(data)
        if (
            type(record["contract"]) is not int
            or record["contract"] != 1
            or record["status"] != "DOWNLOADED"
        ):
            raise ValueError("unsupported teacher completion record")
        if any(
            record.get(flag) is not False
            for flag in ("ground_truth", "alignment_verified", "training_ready")
        ):
            raise ValueError(
                "teacher cache cannot certify ground truth, alignment or readiness"
            )
        wanted_prefix = "s3://" + transport.source_prefix(prefix)
        key = transport.canonical_key(record["source"])
        if (
            record["prefix"] != wanted_prefix
            or "s3://" + key.rsplit("/", 1)[0] != wanted_prefix
        ):
            raise ValueError("cached teacher belongs to a different source prefix")
        if source is not None and key.rsplit("/", 1)[1] != source:
            raise ValueError(
                "cached teacher is a different prediction; use a fresh cache"
            )
        candidates = record["candidates"]
        if (
            not isinstance(candidates, list)
            or not candidates
            or len(candidates) > 4096
            or any(not isinstance(candidate, str) for candidate in candidates)
            or len(set(candidates)) != len(candidates)
            or record["source"] not in candidates
        ):
            raise ValueError("invalid cached teacher candidates")
        for candidate in candidates:
            candidate_key = transport.canonical_key(candidate)
            if "s3://" + candidate_key.rsplit("/", 1)[
                0
            ] != wanted_prefix or not candidate_key.endswith(".tif"):
                raise ValueError("cached candidate outside teacher prefix")
        payload = record["payload"]
        if (
            payload["key"] != key
            or payload["relative_path"] != "teacher.tif"
            or type(payload["bytes"]) is not int
            or not 0 < payload["bytes"] <= _budget(max_bytes)
            or not isinstance(payload["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", payload["sha256"])
        ):
            raise ValueError("invalid cached teacher identity or byte budget")
        teacher = output / "teacher.tif"
        if (
            teacher.is_symlink()
            or not teacher.is_file()
            or teacher.stat().st_size != payload["bytes"]
        ):
            raise ValueError("cached teacher file is missing or changed")
        if _header(teacher) != record["header"]:
            raise ValueError("cached teacher header changed")
        if verify:
            transport._verify_local(teacher, payload)
        return record
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"invalid teacher cache: {exc}") from exc


def fetch_teacher(
    prefix,
    output,
    *,
    source=None,
    max_bytes=DEFAULT_MAX_BYTES,
    filesystem=None,
    dry_run=False,
):
    """Return teacher.tif, rechecking cached bytes; dry-run returns metadata only."""
    prefix = transport.source_prefix(prefix)
    maximum = _budget(max_bytes)
    output = _local_output(output)
    if os.path.lexists(output):
        record = _cache_record(output, prefix, source, maximum, verify=not dry_run)
        return (
            {**record, "status": "CACHED_METADATA_ONLY", "payload_hash_checked": False}
            if dry_run
            else str(output / "teacher.tif")
        )
    if filesystem is None:
        import s3fs

        filesystem = s3fs.S3FileSystem(anon=True)
    plan = plan_teacher(filesystem, prefix, source, maximum)
    if dry_run:
        return plan
    from scripts.data_catalogue import write_verified_json
    from scripts.labeling.label_artifacts import publish_new

    with publish_new(output) as staging:
        payload = transport._download(
            filesystem, plan["payload"], staging / "teacher.tif"
        )
        header = _header(staging / "teacher.tif")
        if plan_teacher(filesystem, prefix, source, maximum) != plan:
            raise ValueError(
                "teacher listing or object identity changed during download"
            )
        transport._verify_local(staging / "teacher.tif", payload)
        report = {**plan, "status": "DOWNLOADED", "payload": payload, "header": header}
        write_verified_json(staging / "teacher.json", report)
        _cache_record(staging, prefix, source, maximum)
    return str(output / "teacher.tif")


def read_teacher(path, *, float_encoding="auto"):
    """Decode and record the same captured bytes; legacy files claim no remote identity."""
    path = Path(path)
    record = None
    if path.name == "teacher.tif":
        metadata = path.parent / "teacher.json"
        # A bundle payload never becomes an unverified legacy file when metadata is lost.
        if (
            metadata.is_symlink()
            or not metadata.is_file()
            or not 0 < metadata.stat().st_size <= 64 * 1024
        ):
            raise ValueError("teacher completion record missing")
        with metadata.open("rb") as stream:
            raw = stream.read(64 * 1024 + 1)
        try:
            prefix = json.loads(raw)["prefix"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("invalid teacher completion record") from exc
        record = _cache_record(path.parent, prefix, max_bytes=MAX_BYTES, verify=False)
    if (
        path.is_symlink()
        or not path.is_file()
        or not 0 < path.stat().st_size <= MAX_BYTES
    ):
        raise ValueError("teacher must be a bounded regular nonsymlink file")
    planned_header = _header(path)
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("teacher exceeds encoded byte budget")
    identity = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if record is not None and identity != {
        key: record["payload"][key] for key in identity
    }:
        raise ValueError("teacher bytes disagree with completion record")
    header = _header(io.BytesIO(data))
    if header != planned_header:
        raise ValueError("teacher header changed during capture")
    teacher = tifffile.imread(io.BytesIO(data))
    if list(teacher.shape) != header["shape"] or teacher.dtype.str != header["dtype"]:
        raise ValueError("decoded teacher disagrees with its header")
    mode = resolve_float_encoding(teacher, float_encoding)
    provenance = {
        "shape": list(teacher.shape),
        "dtype": str(teacher.dtype),
        "min": float(teacher.min()),
        "max": float(teacher.max()),
        "source": record["source"] if record else None,
        "candidates": record["candidates"] if record else None,
        "input": identity,
        "pixels_bound_to_source": True,
        "float_encoding_requested": float_encoding,
        "float_encoding_applied": mode if teacher.dtype.kind == "f" else None,
        "ground_truth": False,
        "alignment_verified": False,
        "training_ready": False,
    }
    return teacher, provenance
