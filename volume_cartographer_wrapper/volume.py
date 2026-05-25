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

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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
        return Path(parsed.path)
    if parsed.scheme in {"http", "https", "s3"}:
        raise VolumeCartographerUnavailable(
            "remote Volume Cartographer reads are not exposed through the "
            "Python wrapper yet; use a local OME-Zarr mirror or VC3D tooling"
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
    """

    def __init__(self, path: str | Path, prefer_native: Optional[bool] = None):
        del prefer_native  # Kept for compatibility with old call sites.
        self.path = _select_zarr_level(_coerce_local_path(path))
        self._zarr = zarr.open(str(self.path), mode="r")
        self.shape = tuple(int(value) for value in self._zarr.shape)
        self.chunks = tuple(int(value) for value in self._zarr.chunks)
        self.sep = self._detect_separator()
        self.backend = "volume-cartographer-zarr"

    def _detect_separator(self) -> str:
        zarray = self.path / ".zarray"
        if not zarray.exists():
            return "."
        text = zarray.read_text(errors="ignore")
        if '"dimension_separator": "/"' in text:
            return "/"
        return "."

    def get_chunk(self, z: int, y: int, x: int, depth=None, height=None, width=None):
        if depth is None and height is None and width is None:
            start = (
                int(z) * self.chunks[0],
                int(y) * self.chunks[1],
                int(x) * self.chunks[2],
            )
            dims = self.chunks
        else:
            if depth is None or height is None or width is None:
                raise ValueError("depth, height, and width must be provided together")
            start = (int(z), int(y), int(x))
            dims = (int(depth), int(height), int(width))

        stop = tuple(
            min(axis_start + dim, shape)
            for axis_start, dim, shape in zip(start, dims, self.shape)
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

    def __init__(self, cache_dir: str | Path | None = None, url: Optional[str] = None):
        super().__init__(url or cache_dir)
