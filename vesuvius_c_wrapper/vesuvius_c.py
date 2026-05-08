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
from pathlib import Path
from types import ModuleType
from typing import Optional

import numpy as np
import zarr


REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_MODULE = REPO_ROOT / "villa" / "vesuvius-c" / "python" / "vesuvius_c.py"
NATIVE_LIBRARY = UPSTREAM_MODULE.with_name("libvesuvius.so")


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
        return self._volume.get_chunk(z, y, x, depth=depth, height=height, width=width)


class FastLocalVolume:
    """Read local Zarr chunks through Vesuvius-C when possible.

    ``get_chunk`` keeps the legacy Autoresearch grid-index API:
    ``get_chunk(z_chunk, y_chunk, x_chunk)``. If the native backend is
    unavailable, it reads the equivalent voxel slice with ``zarr``.
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
                self._native = VesuviusVolume(self.path)
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

    def get_chunk(self, z_chunk: int, y_chunk: int, x_chunk: int):
        start = (
            int(z_chunk) * self.chunks[0],
            int(y_chunk) * self.chunks[1],
            int(x_chunk) * self.chunks[2],
        )
        stop = tuple(
            min(axis_start + chunk, shape)
            for axis_start, chunk, shape in zip(start, self.chunks, self.shape)
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
            except Exception:
                self.backend = "zarr"
                self._native = None

        return np.asarray(
            self._zarr[
                start[0] : stop[0],
                start[1] : stop[1],
                start[2] : stop[2],
            ]
        )
