#!/usr/bin/env python3
"""Crop a ranked Vesuvius candidate window into a small local Zarr array.

The Lasagna/structure-tensor path must run on a candidate crop, not an entire
scroll division. This script extracts a bounded [z, y, x] window from an input
Zarr array and writes a compact Zarr array that downstream villa tools can read.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import zarr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import (
    array_3d,
    integer,
    separate_paths,
    spatial_blocks,
    staged_directory,
)


def _clamp_start(start: int, size: int, limit: int) -> int:
    if size <= 0:
        raise ValueError("crop sizes must be positive")
    if size > limit:
        raise ValueError(f"crop size {size} exceeds source dimension {limit}")
    return max(0, min(start, limit - size))


def crop_candidate_zarr(
    input_path: str | Path,
    output_path: str | Path,
    z: int,
    y: int,
    x: int,
    depth: int = 128,
    height: int = 64,
    width: int = 64,
    chunks: tuple[int, int, int] | None = None,
) -> tuple[int, int, int]:
    """Crop a candidate volume and return the output shape."""
    input_path, output_path = separate_paths(input_path, output_path)
    src = array_3d(input_path)
    requested = tuple(
        integer(value, name)
        for value, name in zip((z, y, x), ("z", "y", "x"), strict=True)
    )
    shape = tuple(
        integer(value, name, 1)
        for value, name in zip(
            (depth, height, width), ("depth", "height", "width"), strict=True
        )
    )
    start = tuple(
        _clamp_start(origin, size, limit)
        for origin, size, limit in zip(requested, shape, src.shape, strict=True)
    )
    if chunks is None:
        chunks = tuple(
            min(src_chunk, dim)
            for src_chunk, dim in zip(src.chunks, shape, strict=True)
        )
    if len(chunks) != 3:
        raise ValueError("crop chunks must have three dimensions")
    chunks = tuple(integer(value, "chunk size", 1) for value in chunks)
    with staged_directory(output_path) as staging:
        dst = zarr.open(
            str(staging),
            mode="w",
            shape=shape,
            chunks=chunks,
            dtype=src.dtype,
            compressor=src.compressor,
            filters=src.filters,
            order=src.order,
            fill_value=src.fill_value,
            zarr_version=2,
        )
        for selection in spatial_blocks(shape):
            source_selection = tuple(
                slice(part.start + origin, part.stop + origin)
                for part, origin in zip(selection, start, strict=True)
            )
            dst[selection] = src[source_selection]
        dst.attrs.update(
            {
                "source_path": str(input_path),
                "source_start_zyx": list(start),
                "source_requested_zyx": list(requested),
                "crop_shape_zyx": list(shape),
                "source_shape_zyx": list(src.shape),
                "source_dtype": str(src.dtype),
                "candidate_crop_contract": 1,
                "crop_generation": uuid.uuid4().hex,
            }
        )
    return shape


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop a candidate Zarr volume for Lasagna/ST processing"
    )
    parser.add_argument("--input", required=True, help="Input 3D Zarr array path")
    parser.add_argument(
        "--output", required=True, help="Output cropped 3D Zarr array path"
    )
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--depth", type=int, default=128)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--width", type=int, default=64)
    args = parser.parse_args()

    shape = crop_candidate_zarr(
        args.input,
        args.output,
        z=args.z,
        y=args.y,
        x=args.x,
        depth=args.depth,
        height=args.height,
        width=args.width,
    )
    print(f"Wrote cropped Zarr {args.output} with shape {shape}")


if __name__ == "__main__":
    main()
