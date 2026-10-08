"""Local array, geometry, and publication boundaries for heuristic labels."""

from __future__ import annotations

import math
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import zarr

from scripts.candidate_artifacts import integer, separate_paths, staged_directory

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


def new_output(output, *sources):
    """Require a separate, new local artifact; reject symlinks, including broken ones."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists; choose a new artifact path: {output}")
    for source in sources:
        _, output = separate_paths(source, output)
    return output.resolve()


@contextmanager
def publish_new(output):
    """Publish a complete immutable directory. Callers must serialize writers."""
    output = new_output(output)
    with staged_directory(output) as staging:
        yield staging
        # The shared publisher supports replacement; these label tools don't.
        if output.exists() or output.is_symlink():
            raise ValueError(f"output appeared during processing: {output}")


@contextmanager
def publish_new_file(output, *sources):
    """Publish one validated new file by rename; serialize writers."""
    output = new_output(output, *sources)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=output.parent, prefix=f".{output.stem}-", suffix=output.suffix, delete=False
    ) as stream:
        staging = Path(stream.name)
    try:
        yield staging
        if output.exists() or output.is_symlink():
            raise ValueError(f"output appeared during processing: {output}")
        staging.rename(output)
    finally:
        staging.unlink(missing_ok=True)
