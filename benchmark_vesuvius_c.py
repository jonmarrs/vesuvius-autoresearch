
import os
import time
import zarr
import numpy as np
from vesuvius_c_wrapper.vesuvius_c import FastLocalVolume

def benchmark():
    path = 'local_data/PHercParis2Fr47/surface_volume.zarr/0'
    if not os.path.exists(path):
        print(f"Skipping benchmark: {path} not found.")
        return

    print(f"--- Benchmarking Vesuvius-C vs Standard Zarr ---")
    
    # Standard Zarr
    start = time.time()
    z_vol = zarr.open(path, mode='r')
    # Read 10 random chunks
    for _ in range(10):
        # We need to map grid index to voxel index for zarr slice
        # Standard zarr uses voxel indexing: z_vol[z0:z1, y0:y1, x0:x1]
        _ = z_vol[0:64, 2560:2560+256, 2560:2560+256]
    zarr_time = time.time() - start
    print(f"Standard Zarr (10 chunks): {zarr_time:.4f}s")

    # Vesuvius-C
    start = time.time()
    c_vol = FastLocalVolume(path, prefer_native=True)
    print(f"Vesuvius-C backend: {c_vol.backend}")
    for _ in range(10):
        _ = c_vol.get_chunk(0, 10, 10)
    vc_time = time.time() - start
    print(f"Vesuvius-C (10 chunks):    {vc_time:.4f}s")
    
    speedup = zarr_time / vc_time
    print(f"Speedup: {speedup:.2f}x")

if __name__ == "__main__":
    benchmark()
