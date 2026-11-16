"""Pinned public fragment downloads and explicit binary-palette preparation.

Fetches a bounded source example; does not change CT values, import a training
fragment, establish physical registration or modify a training configuration.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from .file_capture import capture_bytes
from .fragment_conversion import MAX_PIXELS, decode_fragment_image
from .new_artifacts import new_output, publish_new

OFFICIAL_ROOT = "https://dl.ash2txt.org/fragments/"
DEFAULT_DOWNLOAD_BYTES = 512 * 1024**2
DEFAULT_FILE_BYTES = 128 * 1024**2


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate source manifest key: {key}")
            result[key] = value
        return result

    def constant(token):
        raise ValueError(f"nonfinite source manifest token: {token}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def _manifest(raw, max_download_bytes, max_file_bytes):
    value = _json(raw)
    keys = {
        "schema_version",
        "kind",
        "fragment_id",
        "base_url",
        "source_z_range",
        "shape_zyx",
        "voxel_size_um",
        "label_semantics",
        "mask_semantics",
        "pin_observed_utc",
        "pin_basis",
        "files",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["kind"] != "official_surface_fragment_example"
    ):
        raise ValueError("unsupported official fragment manifest")
    if not isinstance(value["fragment_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9_]+", value["fragment_id"]
    ):
        raise ValueError("invalid fragment ID")
    base = value["base_url"]
    # Exact directory components only: no query, credentials, encoded paths or redirects.
    if (
        not isinstance(base, str)
        or not re.fullmatch(
            r"https://dl\.ash2txt\.org/fragments/Frag[0-9]+/[A-Za-z0-9_]+\.volpkg/working/[A-Za-z0-9_/-]+/",
            base,
        )
        or any(
            part in {".", "..", ""}
            for part in base[len(OFFICIAL_ROOT) :].rstrip("/").split("/")
        )
        or f"/{value['fragment_id']}.volpkg/" not in base
    ):
        raise ValueError(
            "source must be an explicit official fragment export directory"
        )
    span, shape = value["source_z_range"], value["shape_zyx"]
    if (
        not isinstance(span, list)
        or len(span) != 2
        or any(type(z) is not int for z in span)
        or not 0 <= span[0] < span[1] <= span[0] + 512
    ):
        raise ValueError("invalid source layer range")
    if (
        not isinstance(shape, list)
        or len(shape) != 3
        or any(type(n) is not int or n < 1 for n in shape)
        or shape[0] != span[1] - span[0]
        or shape[1] * shape[2] > MAX_PIXELS
    ):
        raise ValueError("invalid or oversized source shape")
    scale = value["voxel_size_um"]
    if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("voxel_size_um must be finite and positive")
    if (
        value["label_semantics"] != "black_background_white_ink"
        or value["mask_semantics"] != "black_excluded_white_included"
    ):
        raise ValueError("unsupported binary label/mask semantics")
    if any(
        not isinstance(value[key], str) or not value[key].strip()
        for key in ("pin_observed_utc", "pin_basis")
    ):
        raise ValueError("source pin provenance is required")
    expected = {"inklabels.png", "mask.png", "surface_volume/meta.json"} | {
        f"surface_volume/{z:02d}.tif" for z in range(*span)
    }
    files = value["files"]
    if not isinstance(files, list) or len(files) != len(expected):
        raise ValueError(
            "manifest must pin every requested layer, labels, mask and metadata"
        )
    seen, total = set(), 0
    for record in files:
        if not isinstance(record, dict) or set(record) != {
            "relative_path",
            "bytes",
            "sha256",
        }:
            raise ValueError("invalid pinned file record")
        name = record["relative_path"]
        if not isinstance(name, str) or name not in expected or name in seen:
            raise ValueError("duplicate or unsupported source filename")
        seen.add(name)
        count = _positive(record["bytes"], "pinned byte count")
        if count > max_file_bytes:
            raise ValueError("pinned source exceeds max_file_bytes")
        if name == "surface_volume/meta.json" and count > 2 * 1024**2:
            raise ValueError("source metadata JSON exceeds 2 MiB")
        if not isinstance(record["sha256"], str) or not re.fullmatch(
            "[0-9a-f]{64}", record["sha256"]
        ):
            raise ValueError("pinned source needs a lowercase SHA256")
        total += count
    if total > max_download_bytes:
        raise ValueError("pinned sources exceed max_download_bytes")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download(url, path, expected):
    digest, count = hashlib.sha256(), 0
    request = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("expected an unredirected HTTP 200 source response")
        length = response.headers.get("Content-Length")
        if length is not None and length != str(expected["bytes"]):
            raise ValueError("source Content-Length differs from pinned bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            while True:
                block = response.read(min(1024**2, expected["bytes"] - count + 1))
                if not block:
                    break
                count += len(block)
                if count > expected["bytes"]:
                    raise ValueError("source response exceeds pinned bytes")
                stream.write(block)
                digest.update(block)
        headers = {key: response.headers.get(key) for key in ("ETag", "Last-Modified")}
    if count != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        raise ValueError("download does not match pinned size/SHA256")
    return {**expected, "url": url, "response_headers": headers}


def canonical_binary_png(raw, path, max_pixels=MAX_PIXELS):
    """Map displayed exact black/white palette colors to 0/255, never raw IDs."""
    indices = decode_fragment_image(
        raw,
        path,
        max_pixels,
        1,
        formats={"PNG"},
        modes={"P", "L"},
        require_identity_orientation=True,
    )
    with Image.open(io.BytesIO(raw)) as image:
        if "transparency" in image.info:
            raise ValueError("binary label/mask must not have transparency")
        if image.mode == "P":
            if image.palette is None or image.palette.mode != "RGB":
                raise ValueError("binary PNG needs an RGB palette")
            palette = image.getpalette()
            lookup = np.zeros(256, dtype=np.uint8)
            for index in np.unique(indices):
                color = palette[3 * int(index) : 3 * int(index) + 3]
                if color not in ([0, 0, 0], [255, 255, 255]):
                    raise ValueError(
                        "used palette colors must be exactly black or white"
                    )
                lookup[index] = color[0]
            values = lookup[indices]
        else:
            values = indices
        if not np.isin(values, [0, 255]).all():
            raise ValueError("labels/mask must use only black and white")
    encoded = io.BytesIO()
    Image.fromarray(values).save(encoded, format="PNG")
    return encoded.getvalue(), values.shape


def _captured_source(staged, expected, limit):
    path = staged / "raw" / expected["relative_path"]
    _, raw = capture_bytes(path, limit)
    if (
        len(raw) != expected["bytes"]
        or hashlib.sha256(raw).hexdigest() != expected["sha256"]
    ):
        raise ValueError("captured download no longer matches pinned bytes")
    return raw


def fetch_example(
    manifest,
    output,
    *,
    max_download_bytes=DEFAULT_DOWNLOAD_BYTES,
    max_file_bytes=DEFAULT_FILE_BYTES,
):
    """Publish new pinned raw files and canonical labels after complete checks."""
    _positive(max_download_bytes, "max_download_bytes")
    _positive(max_file_bytes, "max_file_bytes")
    manifest_path, raw = capture_bytes(manifest, 2 * 1024**2)
    plan = _manifest(raw, max_download_bytes, max_file_bytes)
    target = new_output(output, manifest_path)
    records, canonical = [], {}
    with publish_new(target) as staged:
        for expected in plan["files"]:
            name = expected["relative_path"]
            records.append(
                _download(plan["base_url"] + name, staged / "raw" / name, expected)
            )
        pinned = {record["relative_path"]: record for record in plan["files"]}
        metadata_raw = _captured_source(
            staged, pinned["surface_volume/meta.json"], max_file_bytes
        )
        metadata = _json(metadata_raw)
        if (
            not isinstance(metadata, dict)
            or [metadata.get("height"), metadata.get("width")] != plan["shape_zyx"][1:]
            or type(metadata.get("slices")) is not int
            or metadata["slices"] < plan["source_z_range"][1]
            or metadata.get("voxelsize") != plan["voxel_size_um"]
        ):
            raise ValueError(
                "official surface metadata differs from pinned geometry/scale"
            )
        for name in ("inklabels.png", "mask.png"):
            data = _captured_source(staged, pinned[name], max_file_bytes)
            encoded, shape = canonical_binary_png(data, name)
            if list(shape) != plan["shape_zyx"][1:]:
                raise ValueError("source PNG shape differs from pinned grid")
            path = staged / "labels" / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(encoded)
            canonical[name] = {
                "bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "transform": "exact displayed black/white to grayscale 0/255",
            }
        for z in range(*plan["source_z_range"]):
            path = staged / "raw/surface_volume" / f"{z:02d}.tif"
            data = _captured_source(
                staged, pinned[f"surface_volume/{z:02d}.tif"], max_file_bytes
            )
            values = decode_fragment_image(
                data,
                path,
                MAX_PIXELS,
                2,
                formats={"TIFF"},
                require_identity_orientation=True,
            )
            if list(values.shape) != plan["shape_zyx"][1:]:
                raise ValueError("source TIFF shape differs from pinned grid")
            del data, values
        receipt = {
            "schema_version": 1,
            "manifest": plan,
            "captured_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "downloads": records,
            "canonical_labels": canonical,
            "scope": "Pinned public source bytes and shared export grid; no independent physical alignment, training/holdout independence or accuracy validation.",
        }
        (staged / "source.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n"
        )
    return target
