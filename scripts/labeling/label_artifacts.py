"""Local array, geometry, and publication boundaries for heuristic labels."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import zarr

from scripts.candidate_artifacts import integer
from vesuvius_autoresearch.core.new_artifacts import (
    new_output,
    publish_new,
    publish_new_file,
)

MAX_FRAGMENT_VOXELS = 128**3


def bounded_number(value, name, lower, upper):
    try:
        number = float(value)
        if (
            isinstance(value, bool)
            or not math.isfinite(number)
            or not lower <= number <= upper
        ):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"{name} must be finite and between {lower} and {upper}"
        ) from exc
    return number


def level_zero(path):
    """Accept only a bare array or an explicit level 0; never guess a group child."""
    root = zarr.open(str(path), mode="r")
    array = root if isinstance(root, zarr.Array) else root.get("0")
    if not isinstance(array, zarr.Array) or not array.shape or min(array.shape) <= 0:
        raise ValueError(
            f"expected a nonempty Zarr array or group with array '0': {path}"
        )
    return root, array


def volume(path):
    root, array = level_zero(path)
    if array.ndim != 3:
        raise ValueError(f"expected a 3D (z, y, x) volume, got {array.shape}: {path}")
    return root, array


def bounded_volume(path, max_voxels=MAX_FRAGMENT_VOXELS):
    root, array = volume(path)
    limit = integer(max_voxels, "max_voxels", 1)
    if int(np.prod(array.shape, dtype=object)) > limit:
        raise ValueError(
            f"fragment shape {array.shape} exceeds max_voxels={limit}; make an explicit bounded crop"
        )
    return root, array


def bbox_zyx(values, shape):
    if len(values) != 6:
        raise ValueError("bbox must contain z0, z1, y0, y1, x0, x1")
    bounds = tuple(integer(value, "bbox coordinate") for value in values)
    for start, stop, limit in zip(bounds[::2], bounds[1::2], shape, strict=True):
        if not 0 <= start < stop <= limit:
            raise ValueError(f"bbox {bounds} must fit entirely inside shape {shape}")
    return bounds, tuple(
        slice(start, stop)
        for start, stop in zip(bounds[::2], bounds[1::2], strict=True)
    )
