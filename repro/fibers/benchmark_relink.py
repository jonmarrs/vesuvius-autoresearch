"""Replay fragment linking on released ScrollGT skeleton geometry, without a GPU.

This measures execution time and exact geometry equivalence, not tracing accuracy.
See docs/FIBER_RELINKING.md for the pinned inputs and command.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from vesuvius_autoresearch.fibers.eval_trace import _resample_fiber
from vesuvius_autoresearch.fibers.trace import (
    RelinkParams,
    StopReason,
    TracedFiber,
    TraceResult,
    relink_fragments,
)

SOURCE = "src/vesuvius_autoresearch/fibers/trace.py"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fragments(path):
    """Remove every fourth 8-voxel span from ordered annotated paths.

    Breaks are deliberately imposed on reference geometry. They are not observed
    tracer failures, and a successful rejoin is not independent quality evidence.
    No pickle-containing NPZ members (fiber_names) are loaded.
    """
    fibers = []
    with np.load(path, allow_pickle=False) as data:
        coords, edges = data["coords"], data["edges"]
        offsets, edge_offsets = data["fiber_offsets"], data["edge_offsets"]
        shape = tuple(int(s) for s in data["shape"])
        for i in range(len(offsets) - 1):
            start, stop = offsets[i : i + 2]
            points = coords[start:stop]
            local_edges = edges[edge_offsets[i] : edge_offsets[i + 1]] - start
            stretch = []

            def flush(stretch):
                for first in range(0, len(stretch), 64):
                    segment = np.asarray(stretch[first : first + 48], dtype=float)
                    if len(segment) >= 2:
                        fibers.append(
                            TracedFiber(
                                segment,
                                1.0,
                                1.0,
                                StopReason.LOW_RESPONSE,
                                StopReason.LOW_RESPONSE,
                            )
                        )
                stretch.clear()

            for point, _ in _resample_fiber(points, local_edges, step=0.5):
                if point is None:
                    flush(stretch)
                elif np.all(point >= 0) and np.all(point <= np.asarray(shape) - 1):
                    stretch.append(point)
                else:
                    flush(stretch)
            flush(stretch)
    if len(fibers) < 2:
        raise ValueError(f"not enough in-bounds fragments in {path}")
    return TraceResult(fibers=fibers, shape=shape)


def geometry_sha(result):
    h = hashlib.sha256()
    for fiber in result.fibers:
        points = np.ascontiguousarray(fiber.points, dtype="<f8")
        h.update(np.asarray(points.shape, dtype="<i8").tobytes())
        h.update(points.tobytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-ref", required=True, help="baseline commit SHA")
    ap.add_argument("--skeleton", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True, help="new JSON output file")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{7,40}", args.baseline_ref) or args.repeats < 1:
        ap.error("baseline must be a commit SHA; repeats must be positive")
    if args.out.exists() or args.out.is_symlink():
        ap.error("output must be new")
    harness_hash = digest(__file__)
    baseline_bytes = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "show",
            f"{args.baseline_ref}:{SOURCE}",
        ]
    )
    before_hash = digest(ROOT / SOURCE)
    resampler_source = inspect.getsourcefile(_resample_fiber)
    resampler_hash = digest(resampler_source)
    input_hashes = {str(p.resolve()): digest(p) for p in args.skeleton}
    # Load the real baseline function, rather than a separately reimplemented oracle.
    with tempfile.TemporaryDirectory() as temporary:
        baseline_file = Path(temporary) / "baseline_trace.py"
        baseline_file.write_bytes(baseline_bytes)
        spec = importlib.util.spec_from_file_location("_relink_baseline", baseline_file)
        baseline = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = baseline
        spec.loader.exec_module(baseline)
        rows = []
        params = RelinkParams(
            max_gap=10.0, max_link_angle_deg=30.0, max_tangent_angle_deg=35.0
        )
        for path in args.skeleton:
            result = fragments(path)
            functions = {
                "baseline": baseline.relink_fragments,
                "candidate": relink_fragments,
            }
            warm = {name: fn(result, params) for name, fn in functions.items()}
            expected = geometry_sha(warm["baseline"])
            if geometry_sha(warm["candidate"]) != expected:
                raise ValueError("geometry changed")
            times = {name: [] for name in functions}
            for repeat in range(args.repeats):
                order = (
                    list(functions) if repeat % 2 == 0 else list(reversed(functions))
                )
                for name in order:
                    started = time.perf_counter()
                    actual = functions[name](result, params)
                    times[name].append(time.perf_counter() - started)
                    if geometry_sha(actual) != expected:
                        raise ValueError("geometry changed")
            medians = {
                name: statistics.median(values) for name, values in times.items()
            }
            rows.append(
                {
                    "input": str(path.resolve()),
                    "input_sha256": input_hashes[str(path.resolve())],
                    "input_fragments": len(result),
                    "output_fibers": len(warm["candidate"]),
                    "geometry_sha256": expected,
                    "exact_geometry": True,
                    "seconds": times,
                    "median_seconds": medians,
                    "median_speedup": medians["baseline"] / medians["candidate"],
                }
            )
    if (
        digest(ROOT / SOURCE) != before_hash
        or digest(resampler_source) != resampler_hash
        or digest(__file__) != harness_hash
        or any(digest(p) != sha for p, sha in input_hashes.items())
    ):
        raise ValueError("source or inputs changed during replay")
    record = {
        "measurement": "annotation-derived fragment replay; performance and geometry equivalence only",
        "accuracy_measured": False,
        "gpu_used": False,
        "baseline_ref": args.baseline_ref,
        "baseline_source_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "candidate_source_sha256": before_hash,
        "harness_sha256": harness_hash,
        "resampler_source_sha256": resampler_hash,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "command": sys.argv,
        "repeats": args.repeats,
        "rows": rows,
    }
    with args.out.open("x") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(rows, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
