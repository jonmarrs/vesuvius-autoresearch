"""Validated binary proofreader stores, published after complete staged writes."""

import json
import math
import os
import re
import stat
from itertools import product
from pathlib import Path

import numpy as np
import zarr

from scripts.candidate_artifacts import staged_directory
from vesuvius_autoresearch.core.prediction_artifacts import (
    validate_output_tree,
    validate_plan_paths,
)

MAX_MASK_VOXELS = 128 * 1024**2
MAX_OUTPUT_ENTRIES = 100_000


def mask_shape(shape, max_voxels=MAX_MASK_VOXELS):
    if type(max_voxels) is not int or max_voxels < 1:
        raise ValueError("max_voxels must be a positive integer")
    shape = tuple(shape)
    if len(shape) == 4:
        if shape[0] != 1:
            raise ValueError("proofreader mask must have exactly one channel")
        shape = shape[1:]
    elif len(shape) == 2:
        shape = (1, *shape)
    if len(shape) != 3 or any(type(n) is not int or n < 1 for n in shape):
        raise ValueError(
            "proofreader mask must be nonempty H/W, Z/Y/X or singleton-channel C/Z/Y/X"
        )
    if math.prod(shape) > max_voxels:
        raise ValueError(
            f"proofreader mask exceeds max_voxels={max_voxels}; use a bounded region"
        )
    return shape


def _sources(values):
    if isinstance(values, (str, bytes, os.PathLike)):
        raise ValueError("sources must be a sequence of local filesystem paths")
    return tuple(values)


def validate_destination(path, *, overwrite=False, sources=()):
    if type(overwrite) is not bool:
        raise ValueError("overwrite must be a boolean")
    raw = os.fspath(path)
    if (
        not isinstance(raw, str)
        or not raw.strip()
        or "://" in raw
        or (re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", raw) and not Path(raw).drive)
    ):
        raise ValueError("uncertainty output must be a nonempty local filesystem path")
    path = Path(path)
    validate_plan_paths(
        [(path, "uncertainty mask")],
        [(source, "mask source") for source in _sources(sources)],
    )
    if os.path.lexists(path):
        if not overwrite:
            raise ValueError(
                f"output already exists; use a new path or overwrite=True: {path}"
            )
        validate_output_tree(
            path, max_entries=MAX_OUTPUT_ENTRIES, label="uncertainty mask"
        )
        try:
            array = zarr.open(str(path), mode="r")
        except (OSError, ValueError) as exc:
            # Zarr's own error for a directory that holds no store names no path.
            raise ValueError(
                f"existing uncertainty output must be a bare 3D Zarr array: {path}"
            ) from exc
        if not isinstance(array, zarr.Array) or array.ndim != 3:
            raise ValueError(
                f"existing uncertainty output must be a bare 3D Zarr array: {path}"
            )
    return path.absolute()


def publish_mask(
    mask,
    path,
    *,
    overwrite=False,
    sources=(),
    metadata=None,
    max_voxels=MAX_MASK_VOXELS,
):
    """Publish a normalized float32 0/1 mask; keep a prior store on build failure.

    Existing stores require explicit replacement. Publication uses two renames
    with rollback, not a concurrent-reader or power-loss transaction.
    """
    if not isinstance(mask, np.ndarray) or np.ma.isMaskedArray(mask):
        raise ValueError("proofreader mask must be a NumPy array or torch tensor")
    shape = mask_shape(mask.shape, max_voxels)
    if mask.dtype.kind not in "buif":
        raise ValueError("proofreader mask must contain real binary values")
    values = np.array(mask, copy=True).reshape(shape)
    if not (np.isin(values, [0, 1]).all() or np.isin(values, [0, 255]).all()):
        raise ValueError(
            "proofreader mask must contain finite binary 0/1 or 0/255 values"
        )
    values = values != 0
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("mask metadata must be a finite JSON object")
    try:
        provenance = json.loads(json.dumps(metadata or {}, allow_nan=False))
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"mask metadata must be finite JSON: {exc}") from exc
    sources = _sources(sources)
    path = validate_destination(path, overwrite=overwrite, sources=sources)
    permissions = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    count = int(np.count_nonzero(values))
    attributes = {
        "uncertainty_mask_contract": 1,
        "axes": ["z", "y", "x"],
        "shape_zyx": list(shape),
        "mask_encoding": {"background": 0, "uncertain": 1},
        "uncertain_voxels": count,
        "source": provenance,
    }
    with staged_directory(path) as staging:
        array = zarr.open(
            str(staging),
            mode="w",
            shape=shape,
            chunks=(1, 64, 64),
            dtype="f4",
            fill_value=0,
        )
        if count:
            for z, y, x in product(
                range(shape[0]), range(0, shape[1], 64), range(0, shape[2], 64)
            ):
                slices = (
                    slice(z, z + 1),
                    slice(y, min(y + 64, shape[1])),
                    slice(x, min(x + 64, shape[2])),
                )
                if values[slices].any():
                    array[slices] = values[slices]
        array.attrs.update(attributes)
        validate_destination(path, overwrite=overwrite, sources=sources)
        if permissions is not None:
            staging.chmod(permissions)
    return {
        "status": "EXPORTED" if count else "EMPTY",
        "path": str(path.resolve()),
        "shape_zyx": list(shape),
        "uncertain_voxels": count,
        "mask_voxels": int(values.size),
    }
