#!/usr/bin/env python3
"""Subsample stored Tifxyz coordinates by a positive integer grid stride.

Usage: .venv/bin/python scripts/subsample_mesh.py SRC_TIFXYZ DST_TIFXYZ STRIDE
This file remains standalone for the frozen coarse-grid research driver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
import uuid
from numbers import Integral, Real
from pathlib import Path

import numpy as np
import tifffile

MAX_POINTS = 16 * 1024**2
MAX_DECODED_BYTES = 256 * 1024**2
MAX_METADATA_BYTES = 1024**2


def positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be a positive integer")
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate metadata key: {key}")
        result[key] = value
    return result


def source_fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def source_signature(stat):
    # Access time can change when this tool reads a previously untouched file.
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def subsample(
    src: Path,
    dst: Path,
    stride: int,
    *,
    max_points=MAX_POINTS,
    max_decoded_bytes=MAX_DECODED_BYTES,
) -> dict:
    """Publish a new geometry-only mesh; preserve all valid sampled XYZ values.

    Coordinates must be 2D float32 planes. Invalid points use (-1, -1, -1).
    An optional boolean/uint8 mask is honored; without one use upstream z > 0.
    Bounds apply before TIFF decoding, not to total process memory. Serialize
    writers and keep source files stable throughout preparation.
    """
    stride = positive_integer(stride, "stride")
    max_points = positive_integer(max_points, "max_points")
    max_decoded_bytes = positive_integer(max_decoded_bytes, "max_decoded_bytes")
    dst = Path(dst)
    if dst.exists() or dst.is_symlink():
        raise ValueError(f"output already exists: {dst}")
    src, dst = Path(src).resolve(), dst.resolve()
    if src == dst or src in dst.parents or dst in src.parents:
        raise ValueError("source and output must not overlap or alias")
    if not src.is_dir():
        raise ValueError(f"source must be a local Tifxyz directory: {src}")
    paths = {name: src / f"{name}.tif" for name in "xyz"}
    mask_path = src / "mask.tif"
    if mask_path.exists() or mask_path.is_symlink():
        paths["mask"] = mask_path
    metadata_path = src / "meta.json"
    for path in [metadata_path, *paths.values()]:
        if path.is_symlink() or not path.is_file():
            raise ValueError(
                f"source component must be a regular nonsymlink file: {path}"
            )
    snapshots = {path: path.stat() for path in [metadata_path, *paths.values()]}
    if snapshots[metadata_path].st_size > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds the 1 MiB limit")
    with metadata_path.open("rb") as stream:
        raw_metadata = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw_metadata) > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds the 1 MiB limit")
    meta = json.loads(raw_metadata, object_pairs_hook=strict_object)
    if not isinstance(meta, dict):
        raise ValueError("meta.json must contain an object")
    # Also reject JSON's nonstandard NaN/Infinity extensions anywhere in metadata.
    json.dumps(meta, allow_nan=False)
    if meta.get("format", "tifxyz") != "tifxyz" or meta.get("type", "seg") != "seg":
        raise ValueError("source metadata must describe a tifxyz segmentation")
    scale = meta.get("scale")
    if (
        not isinstance(scale, list)
        or len(scale) != 2
        or any(isinstance(s, bool) or not isinstance(s, Real) for s in scale)
    ):
        raise ValueError("scale must contain two finite positive numbers in x/y order")
    try:
        new_scale = [float(s) / stride for s in scale]
    except OverflowError as exc:
        raise ValueError("scale is not representable") from exc
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        native_scale = np.asarray(new_scale, dtype=np.float32)
    if not np.isfinite(native_scale).all() or np.any(native_scale <= 0):
        raise ValueError("derived scale must be finite and positive in float32")

    shape = None
    decoded_bytes = 0
    for name, path in paths.items():
        with tifffile.TiffFile(path) as tif:
            if len(tif.series) != 1:
                raise ValueError(f"{name}.tif must contain exactly one 2D plane")
            series = tif.series[0]
            if len(series.shape) != 2 or min(series.shape) < 2:
                raise ValueError(
                    f"{name}.tif must be a 2D grid with both dimensions >= 2"
                )
            if shape is None:
                shape = series.shape
            elif series.shape != shape:
                raise ValueError("coordinate and mask grid shapes must match")
            if math.prod(shape) > max_points:
                raise ValueError(f"source grid exceeds max_points={max_points}")
            dtype = series.dtype
            if name == "mask":
                if dtype not in (np.dtype("bool"), np.dtype("uint8")):
                    raise ValueError("mask.tif must contain boolean or uint8 values")
            elif dtype.kind != "f" or dtype.itemsize != 4:
                raise ValueError("coordinate TIFFs must contain float32 values")
            decoded_bytes += math.prod(shape) * dtype.itemsize
    if decoded_bytes > max_decoded_bytes:
        raise ValueError(f"source planes exceed max_decoded_bytes={max_decoded_bytes}")
    sampled_shape = tuple((n + stride - 1) // stride for n in shape)
    if min(sampled_shape) < 2:
        raise ValueError("stride must retain at least a 2x2 grid")

    planes = {}
    invalid = None
    for name in "xyz":
        values = tifffile.imread(paths[name])
        if (
            values.shape != shape
            or values.dtype.kind != "f"
            or values.dtype.itemsize != 4
        ):
            raise ValueError("coordinate layout changed after header inspection")
        if not np.isfinite(values).all() or np.any((values < 0) & (values != -1)):
            raise ValueError(
                "coordinates must be finite and nonnegative, or the -1 sentinel"
            )
        negative = values == -1
        if invalid is not None and not np.array_equal(invalid, negative):
            raise ValueError(
                "invalid coordinates must use the full (-1, -1, -1) sentinel"
            )
        invalid = negative
        planes[name] = np.ascontiguousarray(values[::stride, ::stride])
    valid = ~invalid[::stride, ::stride]
    if "mask" in paths:
        mask = tifffile.imread(paths["mask"])
        if mask.shape != shape or mask.dtype not in (
            np.dtype("bool"),
            np.dtype("uint8"),
        ):
            raise ValueError("mask layout changed after header inspection")
        if not np.isin(mask, [0, 1, 255]).all():
            raise ValueError("mask values must be binary (0, 1 or 255)")
        valid &= mask[::stride, ::stride] != 0
    else:
        valid &= planes["z"] > 0
    if not valid.any():
        raise ValueError("subsampled grid has no valid coordinates")
    for values in planes.values():
        values[~valid] = -1
    bbox = [
        [float(planes[name][valid].min()) for name in "xyz"],
        [float(planes[name][valid].max()) for name in "xyz"],
    ]
    record = {
        "type": "seg",
        "format": "tifxyz",
        "uuid": str(uuid.uuid4()),
        "scale": new_scale,
        "tiff_dimensions": [sampled_shape[1], sampled_shape[0]],
        "bbox": bbox,
        "subsampled_from": {
            "src": str(src),
            "stride": stride,
            "source_shape_yx": list(shape),
            "valid_points": int(valid.sum()),
            "files": {path.name: source_fingerprint(path) for path in snapshots},
            "source_metadata": meta,
            "scope": "geometry and validity mask only; auxiliary files are not transferred",
        },
    }
    if any(
        source_signature(path.stat()) != source_signature(stat)
        for path, stat in snapshots.items()
    ):
        raise ValueError("source components changed during preparation")
    serialized = json.dumps(record, indent=2, allow_nan=False) + "\n"
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Local publication stays standalone: the research driver copies just this
    # script into its frozen work directory, outside the repository import path.
    with tempfile.TemporaryDirectory(prefix=f".{dst.name}-", dir=dst.parent) as tmp:
        staging = Path(tmp) / "mesh"
        staging.mkdir()
        for name, values in planes.items():
            tifffile.imwrite(staging / f"{name}.tif", values, photometric="minisblack")
        tifffile.imwrite(staging / "mask.tif", valid.astype(np.uint8) * 255)
        (staging / "meta.json").write_text(serialized)
        if dst.exists() or dst.is_symlink():
            raise ValueError(f"output appeared during preparation: {dst}")
        staging.rename(dst)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("stride", type=int)
    parser.add_argument("--max-points", type=int, default=MAX_POINTS)
    parser.add_argument("--max-decoded-bytes", type=int, default=MAX_DECODED_BYTES)
    args = parser.parse_args(argv)
    try:
        record = subsample(
            args.src,
            args.dst,
            args.stride,
            max_points=args.max_points,
            max_decoded_bytes=args.max_decoded_bytes,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        OverflowError,
        RuntimeError,
        tifffile.TiffFileError,
    ) as exc:
        print(f"Mesh subsampling failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Mesh published: {args.dst.resolve()}; grid={record['tiff_dimensions']}, scale={record['scale']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
