
import os
import sys
import numpy as np
from vesuvius_c_wrapper.vesuvius_c import FastLocalVolume

def test_loading():
    path = 'local_data/PHercParis2Fr47/surface_volume.zarr/0'
    if not os.path.exists(path):
        print(f"Skipping test: {path} not found.")
        return

    print(f"Testing FastLocalVolume with {path}")
    vol = FastLocalVolume(path)
    print(f"Shape: {vol.shape}, Chunks: {vol.chunks}, Separator: '{vol.sep}'")
    
    # Try to load a middle chunk
    try:
        chunk = vol.get_chunk(0, 16, 12)
        print(f"Successfully loaded chunk (0,16,12). Shape: {chunk.shape}")
        print(f"Chunk mean: {chunk.mean():.4f}, Max: {chunk.max():.4f}")
    except Exception as e:
        print(f"Failed to load chunk: {e}")

if __name__ == "__main__":
    test_loading()
