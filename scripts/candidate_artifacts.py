"""Local candidate artifact contracts shared by preprocessing and resume checks."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from itertools import product
from pathlib import Path

import zarr

ARTIFACT_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    zarr.errors.MetadataError,
)


def tensor_settings(sigma, gpus):
    if isinstance(sigma, bool) or not math.isfinite(sigma) or sigma < 0:
        raise ValueError("sigma must be finite and nonnegative")
    if gpus != "all" and not re.fullmatch(r"\d+(,\d+)*", gpus):
        raise ValueError(
            "gpus must be 'all' or comma-separated nonnegative GPU indices"
        )


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write("\n")
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def integer(value, name, minimum=0):
    try:
        number = float(value)
        if (
            isinstance(value, bool)
            or not math.isfinite(number)
            or not number.is_integer()
        ):
            raise ValueError
        result = int(number)
        if result < minimum:
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be an integer >= {minimum}") from exc


def separate_paths(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (
        source == destination
        or source in destination.parents
        or destination in source.parents
    ):
        raise ValueError("source and output paths must not overlap or alias")
    return source, destination


@contextmanager
def staged_directory(destination):
    """Publish only after success; keep an existing directory if building fails.

    Replacement uses two renames on the same filesystem and rolls back rename
    errors. Callers must serialize writers; this is not a concurrent writer API.
    """
    destination = Path(destination)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError(
            f"output must be a directory, not a file or symlink: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    staging, backup = workspace / "new.zarr", workspace / "previous"
    staging.mkdir()
    published = False
    try:
        yield staging
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
            published = True
        except BaseException:
            if backup.exists():
                try:
                    backup.rename(destination)
                except OSError as exc:
                    raise RuntimeError(
                        f"publication rollback failed; previous output retained at {backup}"
                    ) from exc
            raise
    finally:
        if published or not backup.exists():
            shutil.rmtree(workspace)


def spatial_blocks(shape, block_size=64, step=1):
    """Bound in-memory reads while keeping subsampling anchored at voxel zero."""
    step = integer(step, "subsample", 1)
    sampled = tuple((size + step - 1) // step for size in shape)
    for starts in product(*(range(0, size, block_size) for size in sampled)):
        yield tuple(
            slice(start * step, min(start + block_size, size) * step, step)
            for start, size in zip(starts, sampled, strict=True)
        )


def array_3d(path):
    array = zarr.open(str(path), mode="r")
    if (
        not isinstance(array, zarr.Array)
        or len(array.shape) != 3
        or min(array.shape) <= 0
    ):
        raise ValueError(f"expected a nonempty 3D Zarr array: {path}")
    return array


def tensor_arrays(path, shape=None, mode="r"):
    root = zarr.open_group(str(path), mode=mode)
    tensor = root["structure_tensor"]
    if len(tensor.shape) != 4 or tensor.shape[0] != 6 or min(tensor.shape) <= 0:
        raise ValueError("structure_tensor must have shape (6, z, y, x)")
    expected = tuple(shape or tensor.shape[1:])
    if tensor.shape[1:] != expected:
        raise ValueError("structure tensor and candidate shapes differ")
    arrays = [tensor]
    for component in ("first_component", "second_component", "normal"):
        arrays.extend(root[f"{component}/{axis}/0"] for axis in ("z", "y", "x"))
    arrays.append(root["confidence/0"])
    if any(array.shape != expected for array in arrays[1:]):
        raise ValueError(
            "structure tensor eigenanalysis arrays have inconsistent shapes"
        )
    return root, arrays


def crop_matches(path, source, requested, shape):
    try:
        array = array_3d(path)
        attrs = dict(array.attrs)
        src = array_3d(source)
        return (
            array.shape == tuple(shape)
            and array.dtype == src.dtype
            and attrs.get("candidate_crop_contract") == 1
            and attrs.get("source_path") == str(Path(source).resolve())
            and attrs.get("source_requested_zyx") == list(requested)
            and attrs.get("crop_shape_zyx") == list(shape)
            and attrs.get("source_shape_zyx") == list(src.shape)
            and attrs.get("source_dtype") == str(src.dtype)
            and attrs.get("source_start_zyx")
            == [
                max(0, min(origin, limit - size))
                for origin, limit, size in zip(requested, src.shape, shape, strict=True)
            ]
            and bool(attrs.get("crop_generation"))
        )
    except ARTIFACT_ERRORS:
        return False


def tensor_matches(path, source=None, sigma=2.0):
    try:
        src = array_3d(source) if source is not None else None
        root, _ = tensor_arrays(path, src.shape if src is not None else None)
        completion = root.attrs.get("candidate_tensor_completion", {})
        return (
            completion.get("contract") == 1
            and completion.get("sigma") == sigma
            and (
                src is None
                or completion.get("source_path") == str(Path(source).resolve())
            )
            and (src is None or completion.get("source_crop") == dict(src.attrs))
        )
    except ARTIFACT_ERRORS:
        return False
