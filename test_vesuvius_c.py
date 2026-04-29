import sys
import os

# Add the directory containing vesuvius_c.py to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vesuvius_c_wrapper'))

try:
    from vesuvius_c import FastLocalVolume
    print("Successfully imported vesuvius_c")
    
    # Path to local test data
    zarr_path = os.path.abspath('local_data/PHercParis2Fr47/surface_volume.zarr/0')
    
    print(f"Initializing FastLocalVolume at {zarr_path}")
    vol = FastLocalVolume(zarr_path)
    
    print(f"Volume shape: {vol.shape}, chunk sizes: {vol.chunks}")
    
    print("Requesting chunk 0, 0, 0...")
    chunk_data = vol.get_chunk(0, 0, 0)
    
    print("Back in Python!")
    print(f"Success! Chunk shape: {chunk_data.shape}, mean: {chunk_data.mean():.4f}")
    print(chunk_data[0, :2, :2])
    
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
