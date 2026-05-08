#!/usr/bin/env python3
"""Build a non-GPU readiness report for the Villa Vesuvius-C hook."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import zarr


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_ZARR = "local_data/PHercParis2Fr47/surface_volume.zarr/0"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _resolve(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _make_smoke_zarr(path):
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data
    return data


def _smoke_fallback(wrapper):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "volume.zarr"
        data = _make_smoke_zarr(path)
        volume = wrapper.FastLocalVolume(path, prefer_native=False)
        chunk = volume.get_chunk(1, 1, 1)
        return {
            "status": "pass" if np.array_equal(chunk, data[2:4, 3:6, 4:8]) else "fail",
            "backend": volume.backend,
            "shape": list(volume.shape),
            "chunks": list(volume.chunks),
        }


def _smoke_loader_slice():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "volume.zarr"
        data = _make_smoke_zarr(path)

        from vesuvius_loader import FastVesuviusVolume

        volume = FastVesuviusVolume(str(path))
        patch = volume[1:3, 2:5, 3:7]
        expected = data[1:3, 2:5, 3:7] / 255.0
        return {
            "status": "pass" if np.allclose(patch.numpy(), expected) else "fail",
            "shape": list(patch.shape),
        }


def _probe_sample(wrapper, sample_zarr, probe_native):
    sample_path = _resolve(sample_zarr)
    if not sample_path.exists():
        return {
            "status": "missing_sample",
            "path": str(sample_path),
            "native_backend": "not_probed",
        }

    prefer_native = bool(probe_native)
    try:
        volume = wrapper.FastLocalVolume(sample_path, prefer_native=prefer_native)
        chunk = volume.get_chunk(0, 0, 0)
    except Exception as exc:
        return {
            "status": "fail",
            "path": str(sample_path),
            "native_backend": "failed" if prefer_native else "not_requested",
            "error": str(exc),
        }

    return {
        "status": "pass",
        "path": str(sample_path),
        "backend": volume.backend,
        "native_backend": "used" if volume.backend == "vesuvius-c" else "not_used",
        "shape": list(volume.shape),
        "chunks": list(volume.chunks),
        "sample_chunk_shape": list(chunk.shape),
    }


def build_readiness(sample_zarr=DEFAULT_SAMPLE_ZARR, probe_native=False):
    wrapper_path = _resolve("vesuvius_c_wrapper/vesuvius_c.py")
    upstream_path = _resolve("villa/vesuvius-c/python/vesuvius_c.py")
    native_library = _resolve("villa/vesuvius-c/python/libvesuvius.so")

    report = {
        "source": "ScrollPrize/villa vesuvius-c",
        "wrapper_path": str(wrapper_path),
        "upstream_path": str(upstream_path),
        "native_library_path": str(native_library),
        "sample_zarr": str(_resolve(sample_zarr)),
        "checks": {
            "wrapper_present": wrapper_path.exists(),
            "upstream_present": upstream_path.exists(),
            "native_library_present": native_library.exists(),
            "native_probe_requested": bool(probe_native),
        },
        "fallback_smoke": {"status": "not_run"},
        "loader_slice_smoke": {"status": "not_run"},
        "sample_probe": {"status": "not_run"},
        "benchmark_command": (
            "VESUVIUS_C_BUILD=1 "
            f"{REPO_ROOT / '.venv/bin/python'} benchmark_vesuvius_c.py"
        ),
        "prize_claim_status": "blocked",
        "next_action": "Restore wrapper and upstream Villa checkout.",
    }

    if not report["checks"]["wrapper_present"] or not report["checks"]["upstream_present"]:
        return report

    from vesuvius_c_wrapper import vesuvius_c as wrapper

    report["fallback_smoke"] = _smoke_fallback(wrapper)
    report["loader_slice_smoke"] = _smoke_loader_slice()
    report["sample_probe"] = _probe_sample(wrapper, sample_zarr, probe_native)

    if report["fallback_smoke"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = "Fix the local Zarr fallback before using Vesuvius-C in handoff gates."
    elif report["loader_slice_smoke"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = "Fix FastVesuviusVolume slicing before running another training sprint."
    elif report["sample_probe"]["status"] == "missing_sample":
        report["prize_claim_status"] = "ready_for_local_data"
        report["next_action"] = "Download or mount a local CT Zarr sample, then run the benchmark command."
    elif report["sample_probe"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = "Fix sample chunk reads before benchmarking Vesuvius-C speedups."
    elif report["sample_probe"].get("backend") != "vesuvius-c":
        report["prize_claim_status"] = "fallback_only"
        report["next_action"] = "Run the benchmark with VESUVIUS_C_BUILD=1 and record native speedup before a Progress Prize claim."
    else:
        report["prize_claim_status"] = "native_probe_passed"
        report["next_action"] = "Run repeated native-vs-Zarr benchmarks and attach timings to the Progress Prize package."

    return report


def render_markdown(report):
    checks = report["checks"]
    sample = report["sample_probe"]
    fallback = report["fallback_smoke"]
    loader_slice = report["loader_slice_smoke"]
    lines = [
        "# Vesuvius-C Readiness",
        "",
        "This report checks whether the official `ScrollPrize/villa` Vesuvius-C path is ready for prize-facing Autoresearch use.",
        "",
        "## Summary",
        "",
        f"- Prize claim status: `{report['prize_claim_status']}`",
        f"- Wrapper present: `{checks['wrapper_present']}`",
        f"- Upstream present: `{checks['upstream_present']}`",
        f"- Native library present: `{checks['native_library_present']}`",
        f"- Native probe requested: `{checks['native_probe_requested']}`",
        f"- Fallback smoke: `{fallback.get('status')}`",
        f"- Loader slice smoke: `{loader_slice.get('status')}`",
        f"- Sample probe: `{sample.get('status')}`",
        f"- Sample backend: `{sample.get('backend', 'n/a')}`",
        "",
        "## Benchmark",
        "",
        f"- Command: `{report['benchmark_command']}`",
        f"- Next action: {report['next_action']}",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-zarr", default=DEFAULT_SAMPLE_ZARR)
    parser.add_argument("--probe-native", action="store_true")
    parser.add_argument("--out-json", default="reports/vesuvius_c_readiness.json")
    parser.add_argument("--out-md", default="reports/vesuvius_c_readiness.md")
    args = parser.parse_args()

    report = build_readiness(sample_zarr=args.sample_zarr, probe_native=args.probe_native)

    out_json = _resolve(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n")

    out_md = _resolve(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
