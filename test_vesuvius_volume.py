
import os
import sys
import numpy as np
from vesuvius_c_wrapper.vesuvius_c import VesuviusVolume

def test_vesuvius_volume():
    cache_dir = 'local_data/PHercParis2Fr47/surface_volume.zarr/0'
    if not os.path.exists(cache_dir):
        print(f"Skipping test: {cache_dir} not found.")
        return

    print(f"Testing VesuviusVolume with local cache {cache_dir}")
    # Use file:// URL to satisfy vs_vol_new's requirement for a URL to find .zarray
    abs_path = os.path.abspath(cache_dir)
    url = f"file://{abs_path}"
    vol = VesuviusVolume(cache_dir, url=url)
    print(f"Shape: {vol.shape}, Chunks: {vol.chunks}")
    
    # Fetch a chunk by voxel coordinates
    # Grid (0, 16, 12) corresponds to (0, 16*256, 12*256)
    try:
        chunk = vol.get_chunk(0, 4096, 3072)
        print(f"Successfully loaded chunk at (0, 4096, 3072). Shape: {chunk.shape}")
        print(f"Chunk mean: {chunk.mean():.4f}, Max: {chunk.max():.4f}")
    except Exception as e:
        print(f"Failed to load chunk: {e}")

if __name__ == "__main__":
    test_vesuvius_volume()
