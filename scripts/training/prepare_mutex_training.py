#!/usr/bin/env python3
"""Prepare one explicit, aligned raw/segmentation fragment for Mutex affinities.

Preserves instance IDs and uses the pinned graph tool's numerical helpers.
New artifacts record raw origin, label semantics, channels, and masked coverage.
Artifact validation does not establish trainer compatibility or label accuracy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
import zarr

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, integer, write_json
from scripts.labeling.label_artifacts import (
    bbox_zyx,
    new_output,
    publish_new,
    publish_new_file,
    volume,
)
from scripts.training.mutex_data import (
    MAX_VOXELS,
    bounded_volume,
    fragment_name,
    graph_tools,
    label_values,
    validate_prepared_data,
)


def export_zarr_to_tiff(zarr_path, tiff_path, max_voxels=MAX_VOXELS):
    """Losslessly export an explicit 3D array; retain the legacy helper API."""
    target = new_output(tiff_path, zarr_path)
    _, source = bounded_volume(zarr_path, max_voxels)
    values = source[:]
    if values.dtype.kind not in "uifb" or not np.isfinite(values).all():
        raise ValueError("TIFF export requires finite real 3D values")
    with publish_new_file(target, zarr_path) as staging:
        tifffile.imwrite(
            staging, values, photometric="minisblack", metadata={"axes": "ZYX"}
        )


def prepare_mutex_data(
    curated_zarr,
    raw_zarr,
    output_dir,
    *,
    raw_start=None,
    aligned_labels=False,
    name=None,
    label_mode="instances",
    long_range_stride=2,
    max_voxels=MAX_VOXELS,
):
    if aligned_labels is not True:
        raise ValueError(
            "declare --aligned-labels only after verifying labels match the selected CT voxels"
        )
    if label_mode not in {"instances", "foreground-components"}:
        raise ValueError("label_mode must be instances or foreground-components")
    stride = integer(long_range_stride, "long_range_stride", 1)
    output_dir = new_output(output_dir, curated_zarr, raw_zarr)
    label_root, label_array = bounded_volume(curated_zarr, max_voxels)
    raw_root, raw_array = volume(raw_zarr)
    if raw_array.dtype.kind not in "uif":
        raise ValueError("raw CT must contain real intensities")
    if raw_start is None:
        if raw_array.shape != label_array.shape:
            raise ValueError(
                "different raw/label shapes require an explicit --raw-start z y x"
            )
        raw_start = (0, 0, 0)
    if len(raw_start) != 3:
        raise ValueError("raw_start must contain z, y, x")
    origin = tuple(integer(value, "raw_start") for value in raw_start)
    bounds = tuple(
        value
        for start, size in zip(origin, label_array.shape, strict=True)
        for value in (start, start + size)
    )
    _, selection = bbox_zyx(bounds, raw_array.shape)
    name = fragment_name(name if name is not None else Path(curated_zarr).stem)
    labels, raw = label_array[:], raw_array[selection]
    label_values(labels)
    if not np.isfinite(raw).all():
        raise ValueError("raw CT fragment contains nonfinite values")
    tools = graph_tools()
    supervised = labels
    if label_mode == "foreground-components":
        foreground_ids = np.unique(labels[labels != 0])
        if len(foreground_ids) > 1:
            raise ValueError(
                "foreground-components requires a binary mask, not multiple instance IDs"
            )
        supervised, _ = tools.ndimage.label(
            labels != 0, structure=tools.ndimage.generate_binary_structure(3, 1)
        )
    attractive, repulsive, long_range = tools.build_offset_sets()
    completion = {
        "contract": 1,
        "axes": ["z", "y", "x"],
        "fragment": name,
        "raw_path": str(Path(raw_zarr).resolve()),
        "label_path": str(Path(curated_zarr).resolve()),
        "raw_start_zyx": list(origin),
        "raw_source_shape_zyx": list(raw_array.shape),
        "shape_zyx": list(labels.shape),
        "raw_dtype": str(raw.dtype),
        "label_dtype": str(labels.dtype),
        "raw_root_attrs": dict(raw_root.attrs),
        "raw_array_attrs": dict(raw_array.attrs),
        "label_root_attrs": dict(label_root.attrs),
        "label_array_attrs": dict(label_array.attrs),
        "alignment_basis": "caller-declared CT voxel alignment",
        "label_mode": label_mode,
        "ignore_background_edges": True,
        "long_range_stride": stride,
        "channels": {},
        "valid_edges": {},
        "upstream_script": str(Path(tools.__file__).resolve()),
        "accuracy": "unverified; source zeros are excluded from supervision",
    }
    chunks = tuple(min(64, size) for size in labels.shape)
    with publish_new(output_dir) as staging:
        image = zarr.array(
            raw, store=str(staging / "images" / f"{name}.zarr"), chunks=chunks
        )
        image.attrs["raw_start_zyx"] = list(origin)
        graph = zarr.open_group(
            str(staging / "affinity_graph" / f"{name}.zarr"), mode="w"
        )
        graph.create_dataset("labels", data=supervised, chunks=chunks)
        if label_mode == "foreground-components":
            graph.create_dataset("source_labels", data=labels, chunks=chunks)
        graph.attrs.update(
            {
                "label_mode": label_mode,
                "ignore_background_edges": True,
                "long_range_stride": stride,
            }
        )
        for kind, offsets in (("attractive", attractive), ("repulsive", repulsive)):
            values, valid = tools.compute_affinities(
                supervised,
                offsets,
                mode=kind,
                ignore_background=True,
                stride=stride if kind == "repulsive" else 1,
                stride_applicable_offsets=long_range if kind == "repulsive" else None,
            )
            graph.create_dataset(
                f"affinities/{kind}", data=values.astype(np.uint8), chunks=(1, *chunks)
            )
            graph.create_dataset(
                f"mask/{kind}", data=valid.astype(np.uint8), chunks=(1, *chunks)
            )
            graph.attrs[f"{kind}_offsets"] = tools.offsets_to_json(offsets)
            completion["channels"][kind] = len(offsets)
            completion["valid_edges"][kind] = int(np.count_nonzero(valid))
            del values, valid
        write_json(staging / "mutex_data_completion.json", completion)
        validate_prepared_data(staging)
    return completion


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--curated-zarr",
        "--curated_zarr",
        dest="curated_zarr",
        required=True,
        help="Reviewed 3D segmentation IDs or an explicitly declared binary mask",
    )
    parser.add_argument(
        "--raw-zarr",
        required=True,
        help="Explicit raw CT source; filenames are never used to guess pairing",
    )
    parser.add_argument(
        "--output-dir",
        "--output_dir",
        dest="output_dir",
        required=True,
        help="New prepared-fragment directory",
    )
    parser.add_argument("--raw-start", type=int, nargs=3, metavar=("Z", "Y", "X"))
    parser.add_argument(
        "--aligned-labels",
        action="store_true",
        help="Declare that label voxels match the selected CT region",
    )
    parser.add_argument(
        "--name", help="Safe matching stem for image and affinity stores"
    )
    parser.add_argument(
        "--label-mode",
        choices=("instances", "foreground-components"),
        default="instances",
    )
    parser.add_argument("--long-range-stride", type=int, default=2)
    parser.add_argument(
        "--max-voxels",
        type=int,
        default=MAX_VOXELS,
        help="Explicit in-memory fragment bound; default 128 cubed",
    )
    args = parser.parse_args(argv)
    try:
        result = prepare_mutex_data(
            args.curated_zarr,
            args.raw_zarr,
            args.output_dir,
            raw_start=args.raw_start,
            aligned_labels=args.aligned_labels,
            name=args.name,
            label_mode=args.label_mode,
            long_range_stride=args.long_range_stride,
            max_voxels=args.max_voxels,
        )
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
        print(f"Mutex data preparation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Mutex fragment artifact published: {args.output_dir}; channels={result['channels']}; valid edges={result['valid_edges']}. Check runtime compatibility before training."
    )
    print(
        f"Inspect: {sys.executable} {REPO_ROOT / 'scripts/training/launch_mutex.py'} --data-path {Path(args.output_dir).resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
