"""Bounded scalar volumes and recorded input contents for binary evaluation."""

from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import tifffile

from scripts.candidate_artifacts import array_content_sha256, integer
from scripts.labeling.label_artifacts import bbox_zyx, volume

MAX_METADATA_BYTES = 1024**2


def _shape_dtype(shape, dtype):
    if len(shape) != 3 or min(shape) < 1:
        raise ValueError("evaluation requires nonempty scalar 3D ZYX volumes")
    if dtype.kind not in "biuf" or dtype.itemsize > 8:
        raise ValueError("evaluation inputs must contain real numeric values")
    return {"shape_zyx": list(shape), "dtype": str(dtype)}


def _tiff_header(tif, limit):
    if len(tif.series) != 1 or tif.series[0].axes not in {"ZYX", "QYX", "IYX"}:
        raise ValueError("TIFF must contain one scalar ZYX stack, not channels or RGB")
    series = tif.series[0]
    result = _shape_dtype(series.shape, series.dtype)
    if math.prod(series.shape) > limit:
        raise ValueError(
            "full TIFF exceeds max_voxels; use a bounded TIFF or Zarr crop"
        )
    return {**result, "tiff_axes": series.axes}


def _tiff_bytes(path, limit):
    byte_limit = 16 * limit + MAX_METADATA_BYTES
    if not path.is_file():
        raise ValueError("TIFF input must be a regular file")
    if path.stat().st_size > byte_limit:
        raise ValueError("TIFF exceeds the input byte budget")
    with path.open("rb") as stream:
        captured = stream.read(byte_limit + 1)
    if len(captured) > byte_limit:
        raise ValueError("TIFF exceeds the input byte budget")
    return captured


@dataclass
class VolumeSource:
    path: Path
    kind: str
    header: dict
    limit: int
    bbox: tuple = ()
    content_sha256: str | None = None
    file_sha256: str | None = None

    @classmethod
    def inspect(cls, path, max_voxels):
        path = Path(path).expanduser().resolve()
        limit = integer(max_voxels, "max_voxels", 1)
        if path.is_dir():
            root, array = volume(path)
            header = {
                **_shape_dtype(array.shape, array.dtype),
                "root_attrs": dict(root.attrs),
                "array_attrs": dict(array.attrs),
            }
            if len(json.dumps(header, allow_nan=False).encode()) > MAX_METADATA_BYTES:
                raise ValueError("Zarr metadata exceeds one MiB")
            return cls(path, "zarr", header, limit)
        if path.suffix.lower() not in {".tif", ".tiff"}:
            raise ValueError(
                "input must be a local Zarr directory or scalar TIFF stack"
            )
        if not path.is_file() or path.stat().st_size > 16 * limit + MAX_METADATA_BYTES:
            raise ValueError("TIFF must be a regular file within the input byte budget")
        with tifffile.TiffFile(path) as tif:
            header = _tiff_header(tif, limit)
        return cls(path, "tiff", header, limit)

    def select(self, bbox):
        shape = self.header["shape_zyx"]
        values = (
            tuple(bbox) if bbox is not None else tuple(v for n in shape for v in (0, n))
        )
        self.bbox, _ = bbox_zyx(values, shape)
        if math.prod(self.shape) > self.limit:
            raise ValueError(
                "selected volume exceeds max_voxels; choose an explicit --bbox"
            )

    @property
    def shape(self):
        return tuple(
            stop - start
            for start, stop in zip(self.bbox[::2], self.bbox[1::2], strict=True)
        )

    def read(self):
        selection = tuple(
            slice(a, b) for a, b in zip(self.bbox[::2], self.bbox[1::2], strict=True)
        )
        if self.kind == "tiff":
            captured = _tiff_bytes(self.path, self.limit)
            with tifffile.TiffFile(io.BytesIO(captured)) as tif:
                if _tiff_header(tif, self.limit) != self.header:
                    raise ValueError("TIFF metadata changed after preflight")
                raw = tif.series[0].asarray()
                if list(raw.shape) != self.header["shape_zyx"]:
                    raise ValueError("TIFF read does not match the declared shape")
                result = np.array(raw[selection], copy=True)
            self.file_sha256 = hashlib.sha256(captured).hexdigest()
        else:
            current = VolumeSource.inspect(self.path, self.limit)
            if current.header != self.header:
                raise ValueError("Zarr metadata changed after preflight")
            _, array = volume(self.path)
            result = np.asarray(array[selection])
        if result.shape != self.shape:
            raise ValueError("volume read does not match the exact selected shape")
        self.content_sha256 = array_content_sha256(result)
        return result

    def verify(self):
        if self.kind == "tiff":
            if (
                hashlib.sha256(_tiff_bytes(self.path, self.limit)).hexdigest()
                != self.file_sha256
            ):
                raise ValueError("TIFF input changed during evaluation")
        else:
            if VolumeSource.inspect(self.path, self.limit).header != self.header:
                raise ValueError("Zarr metadata changed during evaluation")
            _, array = volume(self.path)
            if (
                array_content_sha256(array, start=self.bbox[::2], shape=self.shape)
                != self.content_sha256
            ):
                raise ValueError("Zarr input changed during evaluation")

    def provenance(self):
        return {
            "path": str(self.path),
            "kind": self.kind,
            **self.header,
            "bbox_zyx": list(self.bbox),
            "decoded_region_sha256": self.content_sha256,
            "file_sha256": self.file_sha256,
        }


def binary_reference(raw):
    if not (np.isin(raw, [0, 1]).all() or np.isin(raw, [0, 255]).all()):
        raise ValueError(
            "reference must use binary 0/1 or 0/255 labels; multiclass/ignore IDs are unsupported"
        )
    return (raw != 0).astype(np.uint8)


def probabilities(raw, encoding):
    if encoding == "binary":
        return binary_reference(raw).astype(np.float64)
    if encoding == "uint8":
        if raw.dtype != np.uint8:
            raise ValueError("uint8 prediction encoding requires uint8 data")
        return raw.astype(np.float64) / 255
    result = raw.astype(np.float64)
    if not np.isfinite(result).all() or np.any((result < 0) | (result > 1)):
        raise ValueError(
            "probability predictions must be finite in [0,1]; select uint8 or binary encoding explicitly"
        )
    return result
