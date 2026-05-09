"""Local compatibility wrapper for ScrollPrize/villa ``vesuvius-c``.

The upstream module is useful when its native dependencies are available, but
it builds and loads ``libvesuvius.so`` at import time. Autoresearch needs a
stable import surface for planning, tests, and CPU-only handoff gates, so this
module loads the upstream implementation lazily and falls back to direct Zarr
reads for local volumes.
"""

from __future__ import annotations

import importlib.util
import os
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Optional

import numpy as np
import zarr


REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_MODULE = REPO_ROOT / "villa" / "vesuvius-c" / "python" / "vesuvius_c.py"
NATIVE_LIBRARY = UPSTREAM_MODULE.with_name("libvesuvius.so")
_WARNING_COUNTS = defaultdict(int)

def _warn_limited(key: str, message: str, limit: int = 3) -> None:
    _WARNING_COUNTS[key] += 1
    count = _WARNING_COUNTS[key]
    if count <= limit:
        print(f"Warning: {message}")
    elif count == limit + 1:
        print(f"Warning: suppressing further {key} warnings")


class VesuviusCUnavailable(RuntimeError):
    """Raised when the native Vesuvius-C backend cannot be loaded."""


def _load_upstream_module() -> ModuleType:
    if not UPSTREAM_MODULE.exists():
        raise VesuviusCUnavailable(f"missing upstream module: {UPSTREAM_MODULE}")

    spec = importlib.util.spec_from_file_location("_villa_vesuvius_c", UPSTREAM_MODULE)
    if spec is None or spec.loader is None:
        raise VesuviusCUnavailable(f"could not load upstream module: {UPSTREAM_MODULE}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SystemExit as exc:
        raise VesuviusCUnavailable("upstream Vesuvius-C exited while loading") from exc
    except Exception as exc:
        raise VesuviusCUnavailable(str(exc)) from exc
    return module


class VesuviusVolume:
    """Lazy proxy for the official ``villa/vesuvius-c`` VesuviusVolume."""

    def __init__(self, cache_dir: str | Path, url: Optional[str] = None):
        module = _load_upstream_module()
        self._volume = module.VesuviusVolume(str(cache_dir), url=url)

    @property
    def shape(self):
        return self._volume.shape

    @property
    def chunks(self):
        return self._volume.chunks

    def get_chunk(self, z, y, x, depth=None, height=None, width=None):
        """Fetch a volume chunk with automatic alignment expansion if needed."""
        # Standard defaults from upstream
        depth = depth or self.chunks[0]
        height = height or self.chunks[1]
        width = width or self.chunks[2]
        
        start = (int(z), int(y), int(x))
        stop = (start[0] + int(depth), start[1] + int(height), start[2] + int(width))
        
        # Check if the requested region is already aligned to block boundaries
        is_aligned = all(
            start[i] % self.chunks[i] == 0 and (stop[i] - start[i]) % self.chunks[i] == 0
            for i in range(3)
        )
        
        if is_aligned:
            return self._volume.get_chunk(
                start[0], start[1], start[2], 
                depth=depth, height=height, width=width
            )
            
        # Unaligned read: Expand to chunk boundaries for the native call
        # and then crop the result to the requested region.
        aligned_start = tuple((s // c) * c for s, c in zip(start, self.chunks))
        aligned_stop = tuple(((e + c - 1) // c) * c for e, c in zip(stop, self.chunks))
        aligned_dims = tuple(st - st_a for st, st_a in zip(aligned_stop, aligned_start))
        
        # Native get_chunk is still faster for full-block reads than pure Python zarr
        # even with the overhead of expansion and cropping.
        block = self._volume.get_chunk(
            aligned_start[0], aligned_start[1], aligned_start[2],
            depth=aligned_dims[0], height=aligned_dims[1], width=aligned_dims[2]
        )
        
        return block[
            start[0]-aligned_start[0] : stop[0]-aligned_start[0],
            start[1]-aligned_start[1] : stop[1]-aligned_start[1],
            start[2]-aligned_start[2] : stop[2]-aligned_start[2]
        ]


class FastLocalVolume:
    """Read local Zarr chunks through Vesuvius-C when possible.

    ``get_chunk`` supports both local call styles used in Autoresearch:
    ``get_chunk(z_chunk, y_chunk, x_chunk)`` for grid-indexed chunk reads and
    ``get_chunk(z, y, x, depth, height, width)`` for voxel-coordinate reads.
    If the native backend is unavailable, it reads the equivalent slice with
    ``zarr``.
    """

    def __init__(self, path: str | Path, prefer_native: Optional[bool] = None):
        self.path = Path(path)
        self._zarr = zarr.open(str(self.path), mode="r")
        self.shape = tuple(int(value) for value in self._zarr.shape)
        self.chunks = tuple(int(value) for value in self._zarr.chunks)
        self.sep = self._detect_separator()
        self.backend = "zarr"
        self._native = None

        if prefer_native is None:
            prefer_native = (
                NATIVE_LIBRARY.exists()
                or os.environ.get("VESUVIUS_C_BUILD") == "1"
            )
        if prefer_native:
            try:
                self._native = VesuviusVolume(self.path, url=f"file://{self.path.absolute()}")
                self.backend = "vesuvius-c"
            except (VesuviusCUnavailable, RuntimeError):
                self._native = None

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

        if self._native is not None:
            try:
                return self._native.get_chunk(
                    start[0],
                    start[1],
                    start[2],
                    depth=stop[0] - start[0],
                    height=stop[1] - start[1],
                    width=stop[2] - start[2],
                )
            except Exception as exc:
                _warn_limited(
                    "vesuvius_c_native_fallback",
                    f"native Vesuvius-C chunk read failed for {self.path}; falling back to Zarr: {type(exc).__name__}: {exc}",
                )
                self.backend = "zarr"
                self._native = None

        return np.asarray(
            self._zarr[
                start[0] : stop[0],
                start[1] : stop[1],
                start[2] : stop[2],
            ]
        )
