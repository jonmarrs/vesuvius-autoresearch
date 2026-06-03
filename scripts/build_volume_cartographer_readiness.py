#!/usr/bin/env python3
"""Build a non-GPU readiness report for the Villa Volume Cartographer path."""

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
    arr = zarr.open(
        str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32"
    )
    arr[:] = data
    return data


def _smoke_local_volume(wrapper):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "volume.zarr"
        data = _make_smoke_zarr(path)
        volume = wrapper.FastLocalVolume(path)
        grid_chunk = volume.get_chunk(1, 1, 1)
        voxel_chunk = volume.get_chunk(1, 2, 3, 2, 3, 4)
        return {
            "status": (
                "pass"
                if np.array_equal(grid_chunk, data[2:4, 3:6, 4:8])
                and np.array_equal(voxel_chunk, data[1:3, 2:5, 3:7])
                else "fail"
            ),
            "backend": volume.backend,
            "shape": list(volume.shape),
            "chunks": list(volume.chunks),
        }


def _smoke_loader_slice():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "volume.zarr"
        data = _make_smoke_zarr(path)

        from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume

        volume = FastVesuviusVolume(str(path))
        patch = volume[1:3, 2:5, 3:7]
        return {
            "status": "pass"
            if np.allclose(patch.numpy(), data[1:3, 2:5, 3:7])
            else "fail",
            "shape": list(patch.shape),
            "backend": volume.vol.backend,
        }


def _probe_sample(wrapper, sample_zarr):
    sample_path = _resolve(sample_zarr)
    if not sample_path.exists():
        return {
            "status": "missing_sample",
            "path": str(sample_path),
        }

    try:
        volume = wrapper.FastLocalVolume(sample_path)
        chunk = volume.get_chunk(0, 0, 0)
    except Exception as exc:
        return {
            "status": "fail",
            "path": str(sample_path),
            "error": str(exc),
        }

    return {
        "status": "pass",
        "path": str(sample_path),
        "backend": volume.backend,
        "shape": list(volume.shape),
        "chunks": list(volume.chunks),
        "sample_chunk_shape": list(chunk.shape),
    }


def build_readiness(sample_zarr=DEFAULT_SAMPLE_ZARR):
    wrapper_path = _resolve("volume_cartographer_wrapper/volume.py")
    official_path = _resolve("villa/volume-cartographer")
    volume_header = _resolve(
        "villa/volume-cartographer/core/include/vc/core/types/Volume.hpp"
    )
    vc3d_launcher = _resolve("scripts/launch_vc3d.py")

    report = {
        "source": "ScrollPrize/villa volume-cartographer",
        "wrapper_path": str(wrapper_path),
        "official_path": str(official_path),
        "volume_header": str(volume_header),
        "sample_zarr": str(_resolve(sample_zarr)),
        "checks": {
            "wrapper_present": wrapper_path.exists(),
            "official_component_present": official_path.exists(),
            "volume_header_present": volume_header.exists(),
            "vc3d_launcher_present": vc3d_launcher.exists(),
        },
        "local_volume_smoke": {"status": "not_run"},
        "loader_slice_smoke": {"status": "not_run"},
        "sample_probe": {"status": "not_run"},
        "prize_claim_status": "blocked",
        "next_action": "Restore the Volume Cartographer wrapper and Villa checkout.",
    }

    checks = report["checks"]
    if not checks["wrapper_present"] or not checks["official_component_present"]:
        return report

    from volume_cartographer_wrapper import volume as wrapper

    report["local_volume_smoke"] = _smoke_local_volume(wrapper)
    report["loader_slice_smoke"] = _smoke_loader_slice()
    report["sample_probe"] = _probe_sample(wrapper, sample_zarr)

    if report["local_volume_smoke"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = (
            "Fix the local OME-Zarr chunk compatibility layer before running handoff gates."
        )
    elif report["loader_slice_smoke"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = (
            "Fix FastVesuviusVolume slicing before running another training sprint."
        )
    elif report["sample_probe"]["status"] == "missing_sample":
        report["prize_claim_status"] = "ready_for_local_data"
        report["next_action"] = (
            "Download or mount a local CT Zarr sample, then rerun this readiness report."
        )
    elif report["sample_probe"]["status"] != "pass":
        report["prize_claim_status"] = "blocked"
        report["next_action"] = (
            "Fix sample chunk reads before packaging VC3D-aligned evidence."
        )
    else:
        report["prize_claim_status"] = "volume_cartographer_aligned"
        report["next_action"] = (
            "Keep VC3D overlay validation in the prize handoff gate; add native C++ bridge only if Python training needs it."
        )

    return report


def render_markdown(report):
    checks = report["checks"]
    sample = report["sample_probe"]
    local_volume = report["local_volume_smoke"]
    loader_slice = report["loader_slice_smoke"]
    lines = [
        "# Volume Cartographer Readiness",
        "",
        "This report checks whether Autoresearch is aligned with Villa's maintained `volume-cartographer` path instead of deprecated `vesuvius-c`.",
        "",
        "## Summary",
        "",
        f"- Prize claim status: `{report['prize_claim_status']}`",
        f"- Wrapper present: `{checks['wrapper_present']}`",
        f"- Official component present: `{checks['official_component_present']}`",
        f"- Volume API header present: `{checks['volume_header_present']}`",
        f"- VC3D launcher present: `{checks['vc3d_launcher_present']}`",
        f"- Local volume smoke: `{local_volume.get('status')}`",
        f"- Loader slice smoke: `{loader_slice.get('status')}`",
        f"- Sample probe: `{sample.get('status')}`",
        f"- Sample backend: `{sample.get('backend', 'n/a')}`",
        "",
        "## Next Action",
        "",
        f"- {report['next_action']}",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-zarr", default=DEFAULT_SAMPLE_ZARR)
    parser.add_argument(
        "--out-json", default="reports/volume_cartographer_readiness.json"
    )
    parser.add_argument("--out-md", default="reports/volume_cartographer_readiness.md")
    args = parser.parse_args()

    report = build_readiness(sample_zarr=args.sample_zarr)

    out_json = _resolve(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n")

    out_md = _resolve(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
