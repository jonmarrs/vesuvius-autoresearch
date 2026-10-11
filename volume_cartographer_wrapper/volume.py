"""Volume Cartographer-aligned local volume access.

Villa maintainers deprecated ``vesuvius-c`` in favor of
``volume-cartographer``. Autoresearch still needs a small Python-side data
access surface for training and non-GPU handoff gates, so this module mirrors
the chunk API the project used while staying aligned with VC3D's OME-Zarr
volume conventions.

Native Volume Cartographer is C++/CLI today, not a Python package. This wrapper
therefore uses direct Zarr reads for Python training and records the backend as
``volume-cartographer-zarr``. The C++ bridge can be added here later without
reintroducing a dependency on deprecated ``vesuvius-c``.
"""

from __future__ import annotations

import json
from numbers import Integral
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import zarr


class VolumeCartographerUnavailable(RuntimeError):
    """Raised when a requested Volume Cartographer path cannot be opened."""


def _coerce_local_path(path_or_url: str | Path | None) -> Path:
    if path_or_url is None:
        raise VolumeCartographerUnavailable("a local OME-Zarr path is required")

    value = str(path_or_url)
    parsed = urlparse(value)
    if parsed.scheme == "file":
        if (
            parsed.netloc not in {"", "localhost"}
            or parsed.query
            or parsed.fragment
            or not parsed.path.startswith("/")
        ):
            raise VolumeCartographerUnavailable(
                "file URI must identify an absolute local path"
            )
        return Path(unquote(parsed.path))
    if parsed.scheme in {"http", "https", "s3"}:
        raise VolumeCartographerUnavailable(
            "remote Volume Cartographer reads are not exposed through the "
            "Python wrapper yet; use a local OME-Zarr mirror or VC3D tooling"
        )
    if "://" in value:
        raise VolumeCartographerUnavailable(
            "only local paths and local file URIs are supported"
        )
    return Path(value)


def _select_zarr_level(path: Path) -> Path:
    if (path / ".zarray").exists():
        return path
    level0 = path / "0"
    if (level0 / ".zarray").exists():
        return level0
    return path


class FastLocalVolume:
    """Read local OME-Zarr volumes with the chunk API Autoresearch expects.

    ``get_chunk`` supports both grid-indexed chunk reads
    ``get_chunk(z_chunk, y_chunk, x_chunk)`` and voxel-coordinate reads
    ``get_chunk(z, y, x, depth, height, width)``.
    Origins must be inside the volume; positive requested sizes clip only at
    the high boundary, including partial edge chunks. No implicit padding.
    """

    def __init__(self, path: str | Path, prefer_native: bool | None = None):
        del prefer_native  # Kept for compatibility with old call sites.
        self.source_path = _coerce_local_path(path).resolve()
        self.path = _select_zarr_level(self.source_path)
        self._zarr = zarr.open(str(self.path), mode="r")
        if (
            not isinstance(self._zarr, zarr.Array)
            or self._zarr.ndim != 3
            or min(self._zarr.shape) <= 0
        ):
            raise ValueError(
                "local volume must be a nonempty 3D Zarr array or group with array '0'"
            )
        if self._zarr.dtype.kind not in "uifb":
            raise ValueError("local volume must contain real numeric or boolean voxels")
        self.shape = tuple(int(value) for value in self._zarr.shape)
        self.chunks = tuple(int(value) for value in self._zarr.chunks)
        self.dtype = self._zarr.dtype
        self.sep = self._detect_separator()
        self.backend = "volume-cartographer-zarr"

    def _detect_separator(self) -> str:
        zarray = self.path / ".zarray"
        if not zarray.exists():
            return "."
        return json.loads(zarray.read_text()).get("dimension_separator", ".")

    def get_chunk(self, z: int, y: int, x: int, depth=None, height=None, width=None):
        def integer(value, name, minimum):
            if (
                isinstance(value, (bool, np.bool_))
                or not isinstance(value, Integral)
                or value < minimum
            ):
                raise ValueError(f"{name} must be an integer >= {minimum}")
            return int(value)

        origin = tuple(integer(value, "origin", 0) for value in (z, y, x))
        if depth is None and height is None and width is None:
            start = (
                origin[0] * self.chunks[0],
                origin[1] * self.chunks[1],
                origin[2] * self.chunks[2],
            )
            dims = self.chunks
        else:
            if depth is None or height is None or width is None:
                raise ValueError("depth, height, and width must be provided together")
            start = origin
            dims = tuple(integer(value, "size", 1) for value in (depth, height, width))

        if any(
            axis_start >= size
            for axis_start, size in zip(start, self.shape, strict=True)
        ):
            raise ValueError("read origin must lie inside the source volume")

        stop = tuple(
            min(axis_start + dim, shape)
            for axis_start, dim, shape in zip(start, dims, self.shape, strict=True)
        )
        return np.asarray(
            self._zarr[
                start[0] : stop[0],
                start[1] : stop[1],
                start[2] : stop[2],
            ]
        )


class VolumeCartographerVolume(FastLocalVolume):
    """Compatibility constructor for local Volume Cartographer OME-Zarr reads."""

    def __init__(self, cache_dir: str | Path | None = None, url: str | None = None):
        super().__init__(url or cache_dir)
