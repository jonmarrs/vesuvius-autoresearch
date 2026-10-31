"""Convert one declared uint16 fragment generation before publishing any of it.

CPU only. Keep readers and writers serialized: replacing an existing directory
uses two renames, with rollback on caught errors, not a concurrent-reader API.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .file_modes import replacement_mode

MANIFEST = "conversion.json"
MAX_PIXELS = 64 * 1024 * 1024
MAX_LAYERS = 512


def fragment_path(root, fragment_id):
    if (
        not isinstance(fragment_id, str)
        or not fragment_id
        or fragment_id in {".", ".."}
        or any(c in fragment_id for c in ("/", "\\", "\x00"))
    ):
        raise ValueError("fragment ID must be a single directory name")
    return Path(root).resolve() / fragment_id


def _settings(z_start, z_end, max_pixels):
    if (
        any(type(v) is not int for v in (z_start, z_end, max_pixels))
        or not 0 <= z_start < z_end
        or z_end - z_start > MAX_LAYERS
        or not 1 <= max_pixels <= MAX_PIXELS
    ):
        raise ValueError(
            f"require 0 <= z_start < z_end, at most {MAX_LAYERS} layers, "
            f"and 1 <= max_pixels <= {MAX_PIXELS}"
        )


def _capture(path, limit):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"expected a regular, nonsymlink file: {path}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"file exceeds {limit} bytes: {path}")
    return data


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _image(data, path, max_pixels, dtype):
    with Image.open(io.BytesIO(data)) as image:
        if (
            image.n_frames != 1
            or len(image.getbands()) != 1
            or image.width * image.height > max_pixels
            or min(image.size) <= 0
        ):
            raise ValueError(f"expected one scalar image within pixel budget: {path}")
        array = np.array(image)
    if array.ndim != 2 or array.dtype.kind != "u" or array.dtype.itemsize != dtype:
        raise ValueError(f"expected uint{dtype * 8} grayscale image: {path}")
    return array


def convert_layer_u16_to_u8(array):
    """Global high-byte scale; refuse already converted and noninteger data."""
    if array.ndim != 2 or array.dtype.kind != "u" or array.dtype.itemsize != 2:
        raise ValueError("source layers must be 2D uint16 grayscale images")
    return (array // 256).astype(np.uint8)


def _write(path, data):
    with path.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise ValueError(f"output readback failed: {path}")


def _verify_sources(records, limit):
    for record in records:
        data = _capture(Path(record["path"]), limit)
        if len(data) != record["bytes"] or _digest(data) != record["sha256"]:
            raise ValueError(f"source changed during conversion: {record['path']}")


def _replaceable(destination, frag_id):
    """Never remove unrelated annotations or files while repairing a fragment."""
    if not destination.exists():
        return
    allowed = {"layers", MANIFEST, f"{frag_id}_inklabels.png", f"{frag_id}_mask.png"}
    entries = list(destination.iterdir())
    if any(path.name not in allowed or path.is_symlink() for path in entries):
        raise ValueError(
            "destination contains unmanaged files; choose a new destination root"
        )
    layers = destination / "layers"
    if layers.exists() and (
        not layers.is_dir()
        or any(
            not path.is_file()
            or path.is_symlink()
            or not re.fullmatch(r"\d+\.tif", path.name)
            for path in layers.iterdir()
        )
    ):
        raise ValueError(
            "destination layers contain unmanaged files; choose a new destination root"
        )
    if any(path.name != "layers" and not path.is_file() for path in entries):
        raise ValueError(
            "destination contains unmanaged directories; choose a new destination root"
        )


def convert_fragment(
    frag_id, src_root, dst_root, z_start=17, z_end=43, *, max_pixels=MAX_PIXELS
):
    """Replace a fragment only after the complete conversion and readback succeed.

    Source: surface_volume/NN.tif (single-plane uint16), inklabels.png and
    mask.png (uint8 grayscale, same shape). Returns the legacy per-layer stats.
    The completion manifest binds captured source bytes and published outputs.
    """
    _settings(z_start, z_end, max_pixels)
    source, destination = (
        fragment_path(src_root, frag_id),
        fragment_path(dst_root, frag_id),
    )
    src, dst = source.resolve(), destination.resolve()
    if src == dst or src in dst.parents or dst in src.parents:
        raise ValueError("source and destination fragments must not overlap or alias")
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError(f"destination must be a nonsymlink directory: {destination}")
    _replaceable(destination, frag_id)
    if source.is_symlink() or (source / "surface_volume").is_symlink():
        raise ValueError("source fragment and surface_volume must not be symlinks")
    destination.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f".{frag_id}-", dir=destination.parent))
    staging, backup = workspace / "new", workspace / "previous"
    (staging / "layers").mkdir(parents=True)
    limit = 4 * max_pixels + 1024 * 1024
    sources, outputs, stats = [], {}, {}
    shape = None
    try:
        entries = [
            (source / "surface_volume" / f"{i:02d}.tif", f"layers/{i:02d}.tif", i)
            for i in range(z_start, z_end)
        ] + [
            (source / "inklabels.png", f"{frag_id}_inklabels.png", None),
            (source / "mask.png", f"{frag_id}_mask.png", None),
        ]
        for path, relative, index in entries:
            data = _capture(path, limit)
            array = _image(data, path, max_pixels, 2 if index is not None else 1)
            if shape is not None and array.shape != shape:
                raise ValueError(
                    f"image shape mismatch: {path}: {array.shape} != {shape}"
                )
            shape = array.shape
            sources.append(
                {"path": str(path), "bytes": len(data), "sha256": _digest(data)}
            )
            if index is not None:
                converted = convert_layer_u16_to_u8(array)
                ok, encoded = cv2.imencode(".tif", converted)
                if not ok:
                    raise ValueError(f"could not encode layer {index} of {frag_id}")
                data = encoded.tobytes()
                if not np.array_equal(_image(data, relative, max_pixels, 1), converted):
                    raise ValueError(
                        f"encoded layer differs from conversion: {relative}"
                    )
                stats[str(index)] = {
                    "u16_max": int(array.max()),
                    "u8_max": int(converted.max()),
                    "u8_mean": round(float(converted.mean()), 2),
                }
            _write(staging / relative, data)
            outputs[relative] = {"bytes": len(data), "sha256": _digest(data)}
        manifest = {
            "contract": 1,
            "fragment_id": frag_id,
            "z_range": [z_start, z_end],
            "shape_yx": list(shape),
            "scale": "uint16 // 256 -> uint8; no local normalization",
            "sources": sources,
            "outputs": outputs,
        }
        manifest_bytes = (
            json.dumps(manifest, indent=2, allow_nan=False) + "\n"
        ).encode()
        _write(staging / MANIFEST, manifest_bytes)
        _verify_sources(sources, limit)
        for relative, record in outputs.items():
            data = _capture(staging / relative, limit)
            if record != {"bytes": len(data), "sha256": _digest(data)}:
                raise ValueError(f"staged output changed: {relative}")
        if _capture(staging / MANIFEST, 1024 * 1024) != manifest_bytes:
            raise ValueError("staged completion manifest changed")
        # No old fragment files are touched before the complete generation exists.
        _replaceable(destination, frag_id)
        if destination.exists():
            for relative in [*outputs, MANIFEST]:
                os.chmod(staging / relative, replacement_mode(destination / relative))
            if (destination / "layers").exists():
                os.chmod(
                    staging / "layers",
                    stat.S_IMODE((destination / "layers").stat().st_mode),
                )
            os.chmod(staging, stat.S_IMODE(destination.stat().st_mode))
            destination.rename(backup)
        try:
            staging.rename(destination)
        except BaseException:
            if backup.exists():
                try:
                    backup.rename(destination)
                except OSError as exc:
                    raise RuntimeError(
                        f"rollback failed; recover previous fragment at {backup}"
                    ) from exc
            raise
    finally:
        # Never delete the last old generation if rollback was interrupted/failed.
        if not backup.exists() or destination.exists():
            shutil.rmtree(workspace)
    return stats


def conversion_status(data_root, frag_id, z_start, z_end, *, max_pixels=MAX_PIXELS):
    """Validate actual reusable files; legacy fragments lack source-hash evidence.

    Returns (ready, explanation). Does not require or read the original source.
    A manifest, when present, is mandatory evidence rather than an optional hint.
    """
    try:
        _settings(z_start, z_end, max_pixels)
        root = fragment_path(data_root, frag_id)
        if root.is_symlink() or (root / "layers").is_symlink():
            raise ValueError("converted fragment and layers must not be symlinks")
        labels = list(root.glob("*inklabels.*"))
        if len(labels) != 1:
            raise ValueError(
                f"expected exactly one inklabels file, found {len(labels)}"
            )
        paths = [root / "layers" / f"{i:02d}.tif" for i in range(z_start, z_end)]
        paths += [labels[0], root / f"{frag_id}_mask.png"]
        manifest_path = root / MANIFEST
        manifest = None
        if manifest_path.exists() or manifest_path.is_symlink():
            manifest = json.loads(_capture(manifest_path, 1024 * 1024))
            if (
                not isinstance(manifest, dict)
                or manifest.get("contract") != 1
                or manifest.get("fragment_id") != frag_id
                or not isinstance(manifest.get("outputs"), dict)
            ):
                raise ValueError("unsupported or invalid conversion manifest")
            band = manifest.get("z_range")
            if (
                not isinstance(band, list)
                or len(band) != 2
                or any(type(v) is not int for v in band)
                or not 0 <= band[0] <= z_start < z_end <= band[1]
            ):
                raise ValueError(
                    "conversion manifest does not cover requested layer range"
                )
        shape = None
        for path in paths:
            data = _capture(path, 4 * max_pixels + 1024 * 1024)
            array = _image(data, path, max_pixels, 1)
            if shape is not None and array.shape != shape:
                raise ValueError(f"converted image shape mismatch: {path}")
            shape = array.shape
            if manifest is not None:
                record = manifest["outputs"].get(path.relative_to(root).as_posix())
                if record != {"bytes": len(data), "sha256": _digest(data)}:
                    raise ValueError(
                        f"converted output does not match manifest: {path}"
                    )
        if manifest is not None and manifest.get("shape_yx") != list(shape):
            raise ValueError("converted shape does not match manifest")
        return (
            True,
            "verified output hashes"
            if manifest is not None
            else "legacy image checks; no source provenance",
        )
    except (OSError, ValueError, TypeError, KeyError, EOFError, RecursionError) as exc:
        return False, str(exc)
