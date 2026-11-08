"""Path planning and captured instance-label inputs for the benchmark CLI."""

import hashlib
import io
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vesuvius_autoresearch.core.file_capture import capture_bytes
from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_stem,
    validate_plan_paths,
)

MAX_INSTANCE_BYTES = 2 * 1024**3


def cube_sources(data_dir, cube):
    prediction_stem(cube)
    return [
        (data_dir / f"{cube}{suffix}", f"{cube} {kind}")
        for suffix, kind in (
            ("_image.tif", "CT"),
            (".nml", "ground truth"),
            ("_semantic.tif", "semantic labels"),
        )
    ]


def model_sources(model_dir):
    return [
        (model_dir / name, f"semantic model {name}")
        for name in ("plans.json", "dataset.json", "fold_0/checkpoint_final.pth")
    ]


def cache_outputs(data_dir, cube):
    return [
        (data_dir / f"{cube}_fiberprob{suffix}", f"{cube} probability cache")
        for suffix in (".npy", ".json")
    ]


def validate_paths(writes, reads):
    validate_plan_paths(writes, reads)
    for path, owner in writes:
        if os.path.lexists(path) and not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(
                f"{owner} output must be a nonsymlink regular file: {path}"
            )


def validate_cache(data_dir, cube, model_dir):
    validate_paths(
        cache_outputs(Path(data_dir), cube),
        cube_sources(Path(data_dir), cube) + model_sources(Path(model_dir)),
    )


@dataclass(frozen=True)
class BenchmarkArtifactPlan:
    writes: tuple
    reads: tuple

    @classmethod
    def create(cls, args, mode, cubes):
        root = Path(args.data_dir).resolve()
        reads = [item for cube in cubes for item in cube_sources(root, cube)]
        reads.extend(model_sources(Path(args.model).resolve()))
        writes = []
        if getattr(args, "json_out", None):
            writes.append((Path(args.json_out), "benchmark report"))
        if mode == "trace" and getattr(args, "save_instances", None):
            writes.append((Path(args.save_instances), "traced instances"))
        if mode == "score":
            reads.append((Path(args.instances), "scored instances"))
        if mode != "score" or getattr(args, "with_floors", False):
            writes.extend(item for cube in cubes for item in cache_outputs(root, cube))
        else:
            reads.extend(item for cube in cubes for item in cache_outputs(root, cube))
        plan = cls(tuple(writes), tuple(reads))
        plan.validate()
        return plan

    def validate(self):
        validate_paths(self.writes, self.reads)


def read_instances(path, shape, limit=MAX_INSTANCE_BYTES):
    """Parse/hash one bounded NPY capture, retaining its integer IDs and layout.

    The immutable array views the captured bytes; no second full array is needed.
    The header is checked before exposing any array or trusting its allocation.
    """
    path, data = capture_bytes(path, limit)
    # NumPy's public readers cap headers at 10,000 bytes. Only copy the header
    # prefix into a seekable stream; the potentially large payload stays shared.
    stream = io.BytesIO(data[:10_012])
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        header = np.lib.format.read_array_header_1_0(stream)
    elif version in {(2, 0), (3, 0)}:
        # v2/v3 share the length field. Plain integer descriptors and required
        # keys are ASCII; Unicode structured field names are not instance IDs.
        header = np.lib.format.read_array_header_2_0(stream)
    else:
        raise ValueError(f"unsupported NPY version: {version}")
    stored_shape, fortran, dtype = header
    if (
        tuple(stored_shape) != tuple(shape)
        or len(stored_shape) != 3
        or any(type(size) is not int or size < 1 for size in stored_shape)
    ):
        raise ValueError(f"instances {stored_shape} must match cube shape {shape}")
    if dtype.kind not in "ui" or dtype.itemsize > 8:
        raise ValueError(
            "instances must contain integer labels without objects or structured fields"
        )
    count = math.prod(stored_shape)
    if len(data) - stream.tell() != count * dtype.itemsize:
        raise ValueError(
            "NPY payload size must match its declared shape and dtype exactly"
        )
    array = np.frombuffer(data, dtype=dtype, count=count, offset=stream.tell()).reshape(
        stored_shape, order="F" if fortran else "C"
    )
    if dtype.kind == "i" and np.any(array < 0):
        raise ValueError("instance IDs must be nonnegative")
    return array, {
        "instances_path": str(path),
        "instances_sha256": hashlib.sha256(data).hexdigest(),
        "instances_size_bytes": len(data),
        "instances_dtype": dtype.str,
    }
