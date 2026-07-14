import os
import unittest

import torch

from vesuvius_autoresearch.core.vesuvius_loader import (
    FastVesuviusVolume,
    VesuviusLabeledDataset,
)


class TestVesuviusLoader(unittest.TestCase):
    def setUp(self):
        # We assume local_data/PHercParis2Fr47/surface_volume.zarr/0 exists based on previous turns
        self.volume_uri = "local_data/PHercParis2Fr47/surface_volume.zarr/0"
        self.labels_path = "local_data/PHercParis2Fr47/inklabels.png"

        if not os.path.exists(self.volume_uri):
            self.skipTest(f"Volume {self.volume_uri} not found")

    def test_fast_volume_load(self):
        vol = FastVesuviusVolume(self.volume_uri, use_ridges=False)
        self.assertGreater(vol.shape[0], 0)
        self.assertGreater(vol.shape[1], 0)
        self.assertGreater(vol.shape[2], 0)

        # Test slicing
        patch = vol[10:11, 1000:1064, 1000:1064]
        self.assertEqual(patch.shape, (1, 64, 64))
        self.assertEqual(patch.dtype, torch.float32)

    def test_labeled_dataset(self):
        # Use a small patch size for testing
        ds = VesuviusLabeledDataset(
            self.volume_uri,
            self.labels_path,
            patch_size=32,
            num_layers=8,
            require_ink=False,
        )

        self.assertGreater(len(ds), 0)
        # __getitem__ returns (patch_vol, patch_label, patch_fiber): the fiber
        # target was added for the multi-task head; the test was never updated.
        patch_vol, patch_label, patch_fiber = ds[0]

        # [C, Z, H, W]
        self.assertEqual(patch_vol.shape, (1, 8, 32, 32))
        self.assertEqual(patch_label.shape, (32, 32))
        # fiber target is z-collapsed to [1, 1, H, W]
        self.assertEqual(patch_fiber.shape, (1, 1, 32, 32))

    def test_ridge_detection_fallback(self):
        # Test if use_ridges=True doesn't crash even without GPU (will warn and return zeros)
        vol = FastVesuviusVolume(self.volume_uri, use_ridges=True)
        patch = vol[10:13, 1000:1064, 1000:1064]
        # Should return [CT, Ridges]
        self.assertEqual(patch.shape, (2, 3, 64, 64))


if __name__ == "__main__":
    unittest.main()
