"""Validate explicit patch catalogs and load the pinned Villa sampler on demand."""

import hashlib
import importlib.util
import json
import sys
from functools import lru_cache
from numbers import Integral
from pathlib import Path

from .file_capture import capture_bytes

MAX_PATCH_CATALOG_BYTES = 16 * 1024**2


def capture_patch_catalog(path):
    return capture_bytes(path, MAX_PATCH_CATALOG_BYTES)[1]


def _unique_keys(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def read_patch_catalog(path, shape, patch_size):
    """Return ordered YX origins and the hash of the exact parsed bytes."""
    if (
        not isinstance(patch_size, Integral)
        or isinstance(patch_size, bool)
        or patch_size < 1
    ):
        raise ValueError("patch catalog patch_size must be a positive integer")
    patch_size = int(patch_size)
    raw = capture_patch_catalog(path)
    try:
        catalog = json.loads(raw, object_pairs_hook=_unique_keys)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f"invalid patch catalog {path}: {exc}") from exc
    patches = catalog.get("patches") if isinstance(catalog, dict) else None
    if not isinstance(patches, list) or not patches:
        raise ValueError(f"patch catalog {path} needs a nonempty patches list")
    for key, expected in (("patch_size", patch_size), ("num_patches", len(patches))):
        if key in catalog and (
            type(catalog[key]) is not int or catalog[key] != expected
        ):
            raise ValueError(
                f"patch catalog {path} has {key} inconsistent with {expected}"
            )

    max_y, max_x = (int(n) - patch_size for n in shape[-2:])
    coords = []
    for i, patch in enumerate(patches):
        y, x = (
            (patch.get("y"), patch.get("x"))
            if isinstance(patch, dict)
            else (None, None)
        )
        if type(y) is not int or type(x) is not int:
            raise ValueError(
                f"patch catalog {path}, entry {i}: y and x must be integers"
            )
        if not (0 <= y <= max_y and 0 <= x <= max_x):
            raise ValueError(
                f"patch catalog {path}, entry {i}: origin {(y, x)} cannot fit a "
                f"{patch_size}px patch within YX shape {tuple(shape[-2:])}"
            )
        coords.append((y, x))
    return coords, hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def sampler_module():
    path = (
        Path(__file__).resolve().parents[3]
        / "villa/vesuvius/src/vesuvius/models/datasets/find_valid_patches.py"
    )
    name = "_autoresearch_pinned_patch_catalog"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pinned patch sampler: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def find_valid_patches(*args, **kwargs):
    return sampler_module().find_valid_patches(*args, **kwargs)
