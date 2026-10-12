#!/usr/bin/env python3
"""Compare two local Python Zarr access paths on the same validated voxel region."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from numbers import Integral
from pathlib import Path

import numpy as np
import zarr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.labeling.label_artifacts import new_output, publish_new_file
from volume_cartographer_wrapper.volume import (
    FastLocalVolume,
    VolumeCartographerUnavailable,
)

MAX_READ_BYTES = 64 * 1024**2
MAX_REPEATS = 1000


def integer(value, name, minimum, maximum=None):
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, Integral)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(
            f"{name} must be an integer >= {minimum}"
            + (f" and <= {maximum}" if maximum is not None else "")
        )
    return int(value)


def triple(values, name, minimum):
    if not isinstance(values, (list, tuple, np.ndarray)) or len(values) != 3:
        raise ValueError(f"{name} must contain three integers in z/y/x order")
    return tuple(integer(value, name, minimum) for value in values)


def timed(call):
    start = time.perf_counter_ns()
    result = call()
    elapsed = time.perf_counter_ns() - start
    if elapsed <= 0:
        raise ValueError("benchmark timer must produce a positive duration")
    return result, elapsed


def benchmark(
    path,
    *,
    origin_zyx,
    shape_zyx,
    iterations=10,
    warmup=2,
    max_read_bytes=MAX_READ_BYTES,
):
    """Return verified repeated-read timings; no native C++ or cold-cache claim."""
    origin = triple(origin_zyx, "origin", 0)
    shape = triple(shape_zyx, "shape", 1)
    iterations = integer(iterations, "iterations", 2, MAX_REPEATS)
    if iterations % 2:
        raise ValueError("iterations must be even to balance the first-read order")
    warmup = integer(warmup, "warmup", 0, MAX_REPEATS)
    max_read_bytes = integer(max_read_bytes, "max_read_bytes", 1)
    wrapper, wrapper_open_ns = timed(lambda: FastLocalVolume(path))
    if any(
        start + size > limit
        for start, size, limit in zip(origin, shape, wrapper.shape, strict=True)
    ):
        raise ValueError("benchmark region must fit entirely inside the source volume")
    payload_bytes = math.prod(shape) * wrapper.dtype.itemsize
    if payload_bytes > max_read_bytes:
        raise ValueError(f"benchmark region exceeds max_read_bytes={max_read_bytes}")
    direct, direct_open_ns = timed(lambda: zarr.open(str(wrapper.path), mode="r"))
    selection = tuple(
        slice(start, start + size) for start, size in zip(origin, shape, strict=True)
    )
    reads = {
        "direct_zarr": lambda: direct[selection],
        "wrapper_zarr": lambda: wrapper.get_chunk(*origin, *shape),
    }
    durations = {name: [] for name in reads}
    payload_hash = None

    def validate(value):
        nonlocal payload_hash
        if (
            not isinstance(value, np.ndarray)
            or value.shape != shape
            or value.dtype != wrapper.dtype
        ):
            raise ValueError("benchmark read returned an incompatible shape or dtype")
        digest = hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
        if payload_hash is None:
            payload_hash = digest
        elif digest != payload_hash:
            raise ValueError("benchmark reads differ or source payload changed")
        return digest

    for round_index in range(warmup + iterations):
        names = tuple(reads)
        if round_index % 2:
            names = names[::-1]
        for name in names:
            if round_index < warmup:
                value = reads[name]()
            else:
                value, elapsed = timed(reads[name])
                durations[name].append(elapsed)
            # Hash, layout and content checks are outside the timed read.
            validate(value)
    summaries = {
        name: {
            "samples_ns": samples,
            "median_ns": statistics.median(samples),
            "min_ns": min(samples),
            "max_ns": max(samples),
        }
        for name, samples in durations.items()
    }
    ratio = (
        summaries["direct_zarr"]["median_ns"] / summaries["wrapper_zarr"]["median_ns"]
    )
    if not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("benchmark ratio must be finite and positive")
    return {
        "contract": 1,
        "purpose": "verified paired local Python Zarr repeated-read comparison",
        "source": str(wrapper.path),
        "source_input": str(wrapper.source_path),
        "source_shape_zyx": list(wrapper.shape),
        "chunks_zyx": list(wrapper.chunks),
        "dtype": wrapper.dtype.str,
        "dimension_separator": wrapper.sep,
        "origin_zyx": list(origin),
        "shape_zyx": list(shape),
        "bytes_per_read": payload_bytes,
        "payload_sha256": payload_hash,
        "iterations_per_path": iterations,
        "warmup_per_path": warmup,
        "order": "alternating first reader; measured first-reader counts balanced",
        "timer": "perf_counter_ns; initialization and verification excluded from read samples",
        "initialization_ns": {
            "direct_zarr": direct_open_ns,
            "wrapper_zarr": wrapper_open_ns,
        },
        "backend": wrapper.backend,
        "native_volume_cartographer_measured": False,
        "cache_policy": "configured repeated reads; no OS/storage/codec cache flush or isolation",
        "timings": summaries,
        "direct_over_wrapper_median_ratio": ratio,
        "ratio_meaning": "direct read median / wrapper read median; >1 means wrapper was faster in this run",
        "limits": "local workload only; no cold-cache, full-scroll, native C++, GPU or general speedup inference",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, help="local 3D Zarr array or group with array '0'"
    )
    parser.add_argument("--origin-zyx", type=int, nargs=3, default=(0, 0, 0))
    parser.add_argument("--shape-zyx", type=int, nargs=3, required=True)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--max-read-bytes", type=int, default=MAX_READ_BYTES)
    parser.add_argument(
        "--output", type=Path, help="optional new JSON report outside the source"
    )
    args = parser.parse_args(argv)
    try:
        source = FastLocalVolume(args.input).source_path if args.output else None
        output = new_output(args.output, source) if args.output else None
        if output is not None and output.suffix.lower() != ".json":
            raise ValueError("benchmark report must end in .json")
        record = benchmark(
            args.input,
            origin_zyx=args.origin_zyx,
            shape_zyx=args.shape_zyx,
            iterations=args.iterations,
            warmup=args.warmup,
            max_read_bytes=args.max_read_bytes,
        )
        serialized = json.dumps(record, indent=2, allow_nan=False) + "\n"
        if output is not None:
            with publish_new_file(output, source) as staging:
                staging.write_text(serialized)
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        KeyError,
        OverflowError,
    ) as exc:
        print(f"Volume-read benchmark failed: {exc}", file=sys.stderr)
        return 1
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
