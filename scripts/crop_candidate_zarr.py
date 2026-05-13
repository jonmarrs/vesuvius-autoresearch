#!/usr/bin/env python3
"""Crop a ranked Vesuvius candidate window into a small local Zarr array.

The Lasagna/structure-tensor path must run on a candidate crop, not an entire
scroll division. This script extracts a bounded [z, y, x] window from an input
Zarr array and writes a compact Zarr array that downstream villa tools can read.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import zarr


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
    src = zarr.open(str(input_path), mode="r")
    if len(src.shape) != 3:
        raise ValueError(f"expected 3D zarr array, got shape {src.shape}")

    z0 = _clamp_start(int(z), int(depth), int(src.shape[0]))
    y0 = _clamp_start(int(y), int(height), int(src.shape[1]))
    x0 = _clamp_start(int(x), int(width), int(src.shape[2]))
    shape = (int(depth), int(height), int(width))
    chunks = chunks or tuple(min(src_chunk, dim) for src_chunk, dim in zip(src.chunks, shape))

    output_path = Path(output_path)
    if output_path.exists():
        import shutil
        shutil.rmtree(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dst = zarr.open(
        str(output_path),
        mode="w",
        shape=shape,
        chunks=chunks,
        dtype=src.dtype,
        compressor=src.compressor,
        fill_value=getattr(src, "fill_value", 0),
        zarr_format=2,
    )
    dst[:] = src[z0:z0 + shape[0], y0:y0 + shape[1], x0:x0 + shape[2]]
    dst.attrs.update({
        "source_path": str(input_path),
        "source_start_zyx": [z0, y0, x0],
        "source_requested_zyx": [int(z), int(y), int(x)],
        "crop_shape_zyx": list(shape),
    })
    return shape


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop a candidate Zarr volume for Lasagna/ST processing")
    parser.add_argument("--input", required=True, help="Input 3D Zarr array path")
    parser.add_argument("--output", required=True, help="Output cropped 3D Zarr array path")
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
