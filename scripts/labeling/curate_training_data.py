#!/usr/bin/env python3
"""Curate local 3D segmentation labels with the pinned VC Proofreader heuristics.

Chunk density, connected components, and optional skeleton branches select
chunks; they do not establish segmentation accuracy or ground truth. A complete
chunk grid is required because the pinned upstream tool skips partial edges.
Existing outputs are never overwritten.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import zarr

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, integer
from scripts.labeling.label_artifacts import (
    bounded_number,
    new_output,
    publish_new,
    volume,
)

VC_PROOFREADER_PATH = REPO_ROOT / "villa/segmentation/vc_proofreader"


def _load_upstream():
    """Load only after argument parsing and preflight; --help needs no upstream code."""
    script = VC_PROOFREADER_PATH / "extract_good_labels.py"
    if not script.is_file():
        raise FileNotFoundError(f"missing {script}; initialize the villa submodule")
    if str(VC_PROOFREADER_PATH) not in sys.path:
        sys.path.insert(0, str(VC_PROOFREADER_PATH))
    module = importlib.import_module("extract_good_labels")
    if Path(module.__file__).resolve() != script.resolve():
        raise RuntimeError(
            "extract_good_labels resolved to a different upstream script"
        )
    if module.cc3d is None:
        raise RuntimeError(
            "curation requires the project's connected-components-3d dependency"
        )
    return module


def curate_training_data(
    input_path,
    output_path,
    chunk_size=64,
    min_percent=1.0,
    max_percent=95.0,
    min_cc=1,
    max_cc=5,
    reject_branches=True,
    workers=4,
):
    """Filter complete chunks using upstream process(), then publish and report coverage."""
    output_path = new_output(output_path, input_path)
    input_path = Path(input_path).resolve()
    chunk_size = integer(chunk_size, "chunk_size", 1)
    workers = integer(workers, "workers", 1)
    min_cc = integer(min_cc, "min_cc")
    max_cc = integer(max_cc, "max_cc")
    min_percent = bounded_number(min_percent, "min_percent", 0, 100)
    max_percent = bounded_number(max_percent, "max_percent", 0, 100)
    if min_cc > max_cc or min_percent > max_percent:
        raise ValueError("minimum curation bounds must not exceed maximum bounds")
    if not isinstance(reject_branches, bool):
        raise ValueError("reject_branches must be boolean")
    root, source = volume(input_path)
    if source.dtype.kind not in "uib":
        raise ValueError("segmentation labels must be integer or boolean IDs")
    if any(size % chunk_size != 0 for size in source.shape):
        raise ValueError(
            f"shape {source.shape} must be divisible by chunk_size={chunk_size}; upstream skips partial edges. Choose an aligned chunk size or an explicit crop"
        )
    upstream = _load_upstream()
    if reject_branches and (upstream.skeletonize is None or upstream.convolve is None):
        raise RuntimeError(
            "branch rejection requires the project's scikit-image and scipy dependencies"
        )
    settings = {
        "chunk_size": chunk_size,
        "min_percent": min_percent,
        "max_percent": max_percent,
        "min_cc": min_cc,
        "max_cc": max_cc,
        "reject_branches": reject_branches,
        "workers": workers,
        "connectivity": 26,
        "require_nonzero": True,
        "target_value": None,
    }
    provenance = {
        "contract": 1,
        "label_kind": "heuristically_curated_segmentation",
        "axes": ["z", "y", "x"],
        "source_path": str(input_path),
        "source_shape_zyx": list(source.shape),
        "source_dtype": str(source.dtype),
        "source_root_attrs": dict(root.attrs),
        "source_array_attrs": dict(source.attrs),
        "upstream_script": str(VC_PROOFREADER_PATH / "extract_good_labels.py"),
        "settings": settings,
        "zero_chunks": "rejected or originally empty; not verified negative labels",
    }
    json.dumps(provenance, allow_nan=False)
    with publish_new(output_path) as staging:
        upstream.process(
            input_path=str(input_path),
            output_path=str(staging),
            chunk_size=(chunk_size,) * 3,
            array_key="0" if isinstance(root, zarr.Group) else None,
            min_cc=min_cc,
            max_cc=max_cc,
            min_percent=min_percent,
            max_percent=max_percent,
            require_nonzero=True,
            target_value=None,
            connectivity=26,
            write_empty_chunks=False,
            reject_branches=reject_branches,
            workers=workers,
        )
        result = zarr.open(str(staging), mode="r+")
        if (
            not isinstance(result, zarr.Array)
            or result.shape != source.shape
            or result.dtype != source.dtype
            or result.chunks != (chunk_size,) * 3
        ):
            raise ValueError("upstream did not produce the expected segmentation array")
        # Verify readable payloads and upstream's all-or-zero chunk contract.
        total, retained, labeled = 0, 0, 0
        for z in range(0, source.shape[0], chunk_size):
            for y in range(0, source.shape[1], chunk_size):
                for x in range(0, source.shape[2], chunk_size):
                    selection = tuple(
                        slice(start, start + chunk_size) for start in (z, y, x)
                    )
                    before, after = source[selection], result[selection]
                    if source.dtype.kind == "i" and np.any(before < 0):
                        raise ValueError("segmentation IDs must be nonnegative")
                    nonzero = int(np.count_nonzero(after))
                    if nonzero and not np.array_equal(before, after):
                        raise ValueError(
                            "upstream altered labels inside a retained chunk"
                        )
                    total += 1
                    retained += int(nonzero > 0)
                    labeled += nonzero
        stats = {
            "chunks_evaluated": total,
            "chunks_retained_nonempty": retained,
            "chunks_zero": total - retained,
            "labeled_voxels": labeled,
        }
        provenance["result"] = stats
        result.attrs["label_curation_completion"] = provenance
    return stats


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input", required=True, help="Local 3D integer label array or group level 0"
    )
    parser.add_argument(
        "--output", required=True, help="New curated Zarr; existing paths fail"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=64,
        help="Cubic evaluation size; must divide every input dimension",
    )
    parser.add_argument("--min-percent", type=float, default=1.0)
    parser.add_argument("--max-percent", type=float, default=95.0)
    parser.add_argument("--min-cc", type=int, default=1)
    parser.add_argument("--max-cc", type=int, default=5)
    parser.add_argument(
        "--reject-branches",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reject chunks with upstream 2D skeleton junctions (default enabled)",
    )
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        result = curate_training_data(
            args.input,
            args.output,
            args.chunk_size,
            args.min_percent,
            args.max_percent,
            args.min_cc,
            args.max_cc,
            args.reject_branches,
            args.workers,
        )
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
        print(f"Label curation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Heuristic curation complete: {result['chunks_retained_nonempty']} nonempty chunks retained out of {result['chunks_evaluated']}; {result['labeled_voxels']} labeled voxels. Review before training."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
