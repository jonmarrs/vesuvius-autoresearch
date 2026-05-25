#!/usr/bin/env python3
"""Benchmark the Volume Cartographer-aligned Python volume wrapper."""

import os
import time

import zarr

from volume_cartographer_wrapper.volume import FastLocalVolume


def benchmark():
    path = "local_data/PHercParis2Fr47/surface_volume.zarr/0"
    if not os.path.exists(path):
        print(f"Skipping benchmark: {path} not found.")
        return

    print("--- Benchmarking Volume Cartographer-compatible Zarr reads ---")

    start = time.time()
    z_vol = zarr.open(path, mode="r")
    for _ in range(10):
        _ = z_vol[0:64, 2560 : 2560 + 256, 2560 : 2560 + 256]
    zarr_time = time.time() - start
    print(f"Direct Zarr (10 chunks): {zarr_time:.4f}s")

    start = time.time()
    vc_vol = FastLocalVolume(path)
    print(f"Volume Cartographer wrapper backend: {vc_vol.backend}")
    for _ in range(10):
        _ = vc_vol.get_chunk(0, 10, 10)
    wrapper_time = time.time() - start
    print(f"VC-compatible wrapper (10 chunks): {wrapper_time:.4f}s")

    ratio = zarr_time / wrapper_time if wrapper_time else float("inf")
    print(f"Ratio: {ratio:.2f}x")


if __name__ == "__main__":
    benchmark()
