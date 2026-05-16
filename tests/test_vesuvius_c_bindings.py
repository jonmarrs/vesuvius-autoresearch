import unittest
import numpy as np
from vesuvius_c_wrapper.vesuvius_c import FastLocalVolume
import os

class TestVesuviusCBindings(unittest.TestCase):
    def setUp(self):
        # Use Fragment 47 Surface Volume 0 as the test subject
        self.path = "local_data/PHercParis2Fr47/surface_volume.zarr/0"
        if not os.path.exists(self.path):
            self.skipTest(f"Test data not found: {self.path}")

    def test_native_read_uint8(self):
        # Frag 47 SV 0 is uint8
        vol = FastLocalVolume(self.path, prefer_native=True)
        self.assertEqual(vol.backend, "vesuvius-c")
        
        # Read a known chunk
        chunk = vol.get_chunk(10, 1000, 1000, 64, 64, 64)
        
        self.assertEqual(chunk.shape, (23, 64, 64))
        self.assertEqual(chunk.dtype, np.uint8)
        
        # Compare against standard zarr read to ensure parity
        vol_zarr = FastLocalVolume(self.path, prefer_native=False)
        self.assertEqual(vol_zarr.backend, "zarr")
        chunk_zarr = vol_zarr.get_chunk(10, 1000, 1000, 64, 64, 64)
        
        np.testing.assert_array_equal(chunk, chunk_zarr)

    def test_unaligned_read(self):
        vol = FastLocalVolume(self.path, prefer_native=True)
        # 47 SV 0 chunks are likely (1, 512, 512) or similar. 
        # Read across a boundary if possible, but the wrapper handles it.
        # Just test a small slice that isn't a full chunk.
        chunk = vol.get_chunk(10, 50, 50, 5, 10, 10)
        self.assertEqual(chunk.shape, (5, 10, 10))
        
        vol_zarr = FastLocalVolume(self.path, prefer_native=False)
        chunk_zarr = vol_zarr.get_chunk(10, 50, 50, 5, 10, 10)
        np.testing.assert_array_equal(chunk, chunk_zarr)

if __name__ == '__main__':
    unittest.main()
