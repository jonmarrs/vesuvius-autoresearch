#!/usr/bin/env python3
"""Lazy pinned Tifxyz access with explicit resolution and bounded UV tiles."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import integer

TIFXYZ_DIR = REPO_ROOT / "villa/vesuvius/src/vesuvius/tifxyz"


def tifxyz_api():
    # Load the actual pinned package without bootstrapping unrelated ML modules.
    name = "_autoresearch_pinned_tifxyz"
    source = TIFXYZ_DIR / "__init__.py"
    if not source.is_file():
        raise ImportError(f"pinned Tifxyz package missing: {source}")
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, source, submodule_search_locations=[str(TIFXYZ_DIR)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            for key in list(sys.modules):
                if key == name or key.startswith(name + "."):
                    del sys.modules[key]
            raise
    module = sys.modules[name]
    if Path(module.__file__).resolve() != source.resolve():
        raise RuntimeError("Tifxyz resolved to a different source")
    return module


def load_tifxyz_surface(path: str, *, resolution="stored"):
    if resolution not in {"stored", "full"}:
        raise ValueError("resolution must be stored or full")
    surface = tifxyz_api().read_tifxyz(path)
    if not np.isfinite(surface._scale).all() or np.any(np.asarray(surface._scale) <= 0):
        raise ValueError("Tifxyz UV scales must be finite and positive")
    surface.resolution = resolution
    return surface


def extract_patch_coords(surface, y: int, x: int, h: int, w: int):
    """Return (x,y,z,valid) in the surface's stored/full mode; honor validity."""
    if surface is None:
        raise ValueError("a loaded Tifxyz surface is required")
    y, x, h, w = (
        integer(value, name, minimum)
        for value, name, minimum in ((y, "y", 0), (x, "x", 0), (h, "h", 1), (w, "w", 1))
    )
    if len(surface.shape) != 2 or y + h > surface.shape[0] or x + w > surface.shape[1]:
        raise ValueError(
            "UV patch must fit entirely inside the surface at its current resolution"
        )
    result = surface[y : y + h, x : x + w]
    if (
        not isinstance(result, tuple)
        or len(result) != 4
        or any(np.shape(value) != (h, w) for value in result)
    ):
        raise ValueError("Tifxyz returned an invalid coordinate tile")
    cx, cy, cz, valid = result
    if np.asarray(valid).dtype != np.bool_:
        raise ValueError("Tifxyz validity must be boolean")
    valid = valid.copy()
    for coordinate in (cx, cy, cz):
        valid &= np.isfinite(coordinate) & (coordinate >= 0)
    return cx, cy, cz, valid


if __name__ == "__main__":
    try:
        tifxyz_api()
    except (ImportError, OSError, RuntimeError) as exc:
        print(f"Tifxyz runtime unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        "Pinned Tifxyz API is available; choose stored/full resolution explicitly when loading."
    )
