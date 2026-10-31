"""Explicit object selection and bounded, staged downloads for raw SOTA segments."""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import re
from pathlib import Path

BUCKET = "vesuvius-challenge-open-data"
BLOCK_BYTES = 1024 * 1024
DEFAULT_MAX_BYTES = 4 * 1024**3
DEFAULT_MAX_FILE_BYTES = 512 * 1024**2
MAX_BYTES = 64 * 1024**3
MAX_FILE_BYTES = 2 * 1024**3
MAX_FILES = 1024
MAX_ENTRIES = 4096


def _version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _integer(value, name, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer from 1 to {maximum}")
    return value


def limits(max_bytes, max_file_bytes, max_files, max_entries, center_layers):
    return {
        "max_bytes": _integer(max_bytes, "max_bytes", MAX_BYTES),
        "max_file_bytes": _integer(max_file_bytes, "max_file_bytes", MAX_FILE_BYTES),
        "max_files": _integer(max_files, "max_files", MAX_FILES),
        "max_entries": _integer(max_entries, "max_entries", MAX_ENTRIES),
        "center_layers": None
        if center_layers is None
        else _integer(center_layers, "center_layers", MAX_FILES),
    }


def canonical_key(value):
    if not isinstance(value, str):
        raise ValueError("object keys must be strings")
    key = value.removeprefix("s3://").lstrip("/").rstrip("/")
    if (
        not key.startswith(BUCKET + "/")
        or len(key.removeprefix(BUCKET + "/").encode("utf-8")) > 1024
        or any(part in {"", ".", ".."} for part in key.split("/"))
        or "\\" in key
        or any(not character.isprintable() for character in key)
    ):
        raise ValueError("expected a safe key inside the public Vesuvius bucket")
    return key


def source_prefix(value):
    if not isinstance(value, str) or not value:
        raise ValueError("segment prefix must be a nonempty string")
    if value.startswith(("s3://", BUCKET + "/")):
        return canonical_key(value)
    if value.startswith("/") or "://" in value:
        raise ValueError("use a bucket-relative segment prefix or its public s3:// URI")
    return canonical_key(f"{BUCKET}/{value}")


def _listing(filesystem, prefix, maximum):
    # The SDK may materialize its response; this limits accepted metadata, not
    # the filesystem implementation's listing buffers. Never recurse.
    filesystem.invalidate_cache(prefix)
    entries = filesystem.ls(prefix, detail=True)
    if not isinstance(entries, list) or len(entries) > maximum:
        raise ValueError(f"listing exceeds max_entries={maximum}: {prefix}")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("object listing must contain metadata records")
        key = canonical_key(entry.get("name"))
        if key.rsplit("/", 1)[0] != prefix:
            raise ValueError(
                f"listing returned an object outside its direct prefix: {key}"
            )
        name = key.rsplit("/", 1)[1]
        if name in result:
            raise ValueError(f"duplicate object listing: {key}")
        if entry.get("type") not in {"file", "directory"}:
            raise ValueError(f"unsupported object type: {key}")
        result[name] = {**entry, "name": key}
    return result


def _identifier(value, name):
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 1024
        or not value.isprintable()
    ):
        raise ValueError(f"invalid remote {name}")
    return value


def _file(entry, relative, role, options):
    if entry["type"] != "file":
        raise ValueError(f"{entry['name']} is not a file; convert reads one file")
    size = _integer(
        entry.get("size"),
        f"object size for {entry['name']} (max_file_bytes)",
        options["max_file_bytes"],
    )
    return {
        "key": entry["name"],
        "relative_path": relative,
        "role": role,
        "bytes": size,
        "etag": _identifier(entry.get("ETag", entry.get("etag")), "ETag"),
        "version_id": _identifier(
            entry.get("VersionId", entry.get("version_id")), "version ID"
        ),
    }


def build_plan(filesystem, prefix, options):
    entries = _listing(filesystem, prefix, options["max_entries"])
    if entries.get("layers", {}).get("type") != "directory":
        raise ValueError(f"{prefix}: no layers/ to fetch")
    wanted = [
        name
        for name in entries
        if not name.startswith(".") and ("inklabels" in name or "mask" in name)
    ]
    for name in wanted:
        if entries[name]["type"] != "file":
            raise ValueError(f"{prefix}/{name} is not a file; convert reads one file")
    labels = [name for name in wanted if "inklabels" in name]
    masks = [name for name in wanted if "mask" in name]
    if len(labels) != 1 or len(masks) > 1 or set(labels) & set(masks):
        raise ValueError(
            "need exactly one unambiguous inklabels file and at most one distinct mask"
        )
    layer_entries = _listing(filesystem, prefix + "/layers", options["max_entries"])
    if len(entries) + len(layer_entries) > options["max_entries"]:
        raise ValueError("combined listing exceeds max_entries")
    layers = []
    for name, entry in layer_entries.items():
        if name.endswith(".tif"):
            if not re.fullmatch(r"[0-9]+\.tif", name) or entry["type"] != "file":
                raise ValueError(
                    "layer TIFF names must be direct files with integer depth indices"
                )
            layers.append((int(name[:-4]), name))
    layers.sort()
    indices = [index for index, _ in layers]
    if not layers or len(set(indices)) != len(indices):
        raise ValueError("need nonempty layers with unique numeric depth indices")
    selected = layers
    if options["center_layers"] is not None:
        count = options["center_layers"]
        if count > len(layers):
            raise ValueError("center_layers exceeds available layers")
        start = (len(layers) - count) // 2
        selected = layers[start : start + count]
    if any(b[0] != a[0] + 1 for a, b in zip(selected, selected[1:], strict=False)):
        raise ValueError("selected layer depth indices must be consecutive")
    files = [
        _file(layer_entries[name], f"layers/{name}", "layer", options)
        for _, name in selected
    ]
    files += [
        _file(entries[name], name, "inklabels" if name in labels else "mask", options)
        for name in sorted(wanted)
    ]
    if len(files) > options["max_files"]:
        raise ValueError(
            "download exceeds max_files; select center_layers or raise the explicit budget"
        )
    total = sum(item["bytes"] for item in files)
    if total > options["max_bytes"]:
        raise ValueError(
            f"download needs {total} bytes, exceeds max_bytes={options['max_bytes']}"
        )
    if _is_s3(filesystem) and any(item["etag"] is None for item in files):
        raise ValueError("S3 objects require ETags for conditional download requests")
    return {
        "contract": 1,
        "source": "s3://" + prefix,
        "options": options,
        "available_layers": len(layers),
        "selected_depth_indices": [index for index, _ in selected],
        "selection": "all direct numeric .tif layers"
        if options["center_layers"] is None
        else "center slice of numerically sorted layers, floor((available - count) / 2)",
        "mask_present": bool(masks),
        "ignored_root_entries": len(entries) - len(wanted) - 1,
        "ignored_layer_entries": len(layer_entries) - len(layers),
        "file_count": len(files),
        "total_bytes": total,
        "files": files,
        "image_geometry_verified": False,
        "label_quality_verified": False,
        "training_ready": False,
    }


def _protocols(filesystem):
    protocol = getattr(filesystem, "protocol", ())
    return [protocol] if isinstance(protocol, str) else list(protocol or ())


def _is_s3(filesystem):
    return any(name in {"s3", "s3a"} for name in _protocols(filesystem))


def _read_range(filesystem, item, start, end):
    """Use explicit GetObject conditions; open(size=...) can bypass s3fs's ETag guard."""
    expected = end - start
    if not _is_s3(filesystem):
        data = filesystem.cat_file(item["key"], start=start, end=end)
    else:
        from fsspec.asyn import sync

        response = filesystem.call_s3(
            "get_object",
            Bucket=BUCKET,
            Key=item["key"].removeprefix(BUCKET + "/"),
            Range=f"bytes={start}-{end - 1}",
            IfMatch=item["etag"],
        )
        body = response["Body"]
        try:
            if (
                response.get("ContentLength") != expected
                or response.get("ContentRange")
                != f"bytes {start}-{end - 1}/{item['bytes']}"
                or response.get("ETag") != item["etag"]
            ):
                raise ValueError(
                    "S3 range response does not match planned object identity and size"
                )

            async def read_body():
                parts, remaining = [], expected
                while True:
                    part = await body.read(min(BLOCK_BYTES, remaining + 1))
                    if not part:
                        break
                    if not isinstance(part, bytes) or len(part) > remaining:
                        raise ValueError("S3 body exceeds requested range")
                    parts.append(part)
                    remaining -= len(part)
                if remaining:
                    raise ValueError("short S3 body")
                return b"".join(parts)

            data = sync(filesystem.loop, read_body)
        finally:
            body.close()
    if not isinstance(data, bytes) or len(data) != expected:
        raise ValueError(f"transfer length differs from requested range: {item['key']}")
    return data


def _download(filesystem, item, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with destination.open("xb") as target:
        for start in range(0, item["bytes"], BLOCK_BYTES):
            data = _read_range(
                filesystem, item, start, min(start + BLOCK_BYTES, item["bytes"])
            )
            target.write(data)
            digest.update(data)
    return {
        **item,
        "sha256": digest.hexdigest(),
        "conditional_etag_requested": _is_s3(filesystem) and item["etag"] is not None,
    }


def _verify_local(path, item):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != item["bytes"]:
        raise ValueError(f"downloaded file changed: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for data in iter(lambda: source.read(BLOCK_BYTES), b""):
            digest.update(data)
    if digest.hexdigest() != item["sha256"]:
        raise ValueError(f"downloaded file changed: {path}")


def _verify_layout(staging, files, code):
    expected = {item["relative_path"] for item in files} | {
        f"sources/{name}" for name in code
    }
    actual = set()
    for path in staging.rglob("*"):
        relative = path.relative_to(staging).as_posix()
        if path.is_symlink():
            raise ValueError("download layout changed: symlink found")
        if path.is_dir():
            if relative not in {"layers", "sources"}:
                raise ValueError("download layout changed: unexpected directory")
        elif path.is_file():
            actual.add(relative)
            if relative not in expected:
                raise ValueError("download layout changed: unexpected file")
        else:
            raise ValueError("download layout changed: special file")
    if actual != expected:
        raise ValueError("download layout changed: missing file")


def destination_path(output):
    from scripts.labeling.label_artifacts import new_output

    if "://" in str(output) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", str(output)):
        raise ValueError("output must be a local filesystem directory")
    return new_output(
        output, Path(__file__).resolve(), Path(__file__).with_name("fetch.py").resolve()
    )


def execute_plan(filesystem, prefix, output, plan):
    from scripts.data_catalogue import write_verified_json
    from scripts.labeling.label_artifacts import publish_new
    from scripts.text_snapshot import Snapshot

    code = {
        name: Snapshot.read(Path(__file__).with_name(name), 256 * 1024)
        for name in ("fetch.py", "download_artifacts.py")
    }
    with publish_new(output) as staging:
        files = [
            _download(filesystem, item, staging / item["relative_path"])
            for item in plan["files"]
        ]
        for snapshot in code.values():
            snapshot.copy_into(staging, snapshot.path.name)
        # Fresh, direct listings bind numeric center selection and source identities.
        if build_plan(filesystem, prefix, plan["options"]) != plan:
            raise ValueError(
                "remote source listing or object identity changed during download"
            )
        _verify_layout(staging, files, code)
        for item in files:
            _verify_local(staging / item["relative_path"], item)
        for snapshot in code.values():
            snapshot.verify()
            _verify_local(
                staging / "sources" / snapshot.path.name, snapshot.provenance()
            )
        report = {
            **plan,
            "status": "DOWNLOADED",
            "files": files,
            "tool_sources": {
                name: snapshot.provenance() for name, snapshot in code.items()
            },
            "runtime": {
                "python": platform.python_version(),
                "filesystem_protocol": _protocols(filesystem),
                "packages": {name: _version(name) for name in ("fsspec", "s3fs")},
            },
            "remote_identity_scope": "observed listing metadata plus conditional ETag requests when available; not a global bucket snapshot or authenticated content checksum",
        }
        # Completion is written only after the transfer and source/local rechecks.
        write_verified_json(staging / "download.json", report)
    return report
