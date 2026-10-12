import os
import unittest

import numpy as np
import torch
from PIL import Image

from vesuvius_autoresearch.core import patch_catalog, vesuvius_loader
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


def _tiny_fragment(root):
    import zarr

    volume = zarr.open(
        str(root / "surface_volume.zarr"),
        mode="w",
        shape=(8, 32, 32),
        chunks=(4, 16, 16),
        dtype="u1",
    )
    volume[:] = 64
    labels = np.zeros((32, 32), np.uint8)
    labels[8:24, 8:24] = 255
    Image.fromarray(labels).save(root / "inklabels.png")
    return str(root / "surface_volume.zarr"), str(root / "inklabels.png")


def test_default_valid_coords_cache_stays_out_of_cwd(tmp_path, monkeypatch):
    # With no cache_dir the valid_coords cache used to be saved under a bare
    # relative filename, so every run left a .npy in whatever directory it was
    # launched from -- the repo root for the loop and the test suite.
    volume_uri, labels_path = _tiny_fragment(tmp_path)
    cache = tmp_path / "cache"
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(cache), raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    VesuviusLabeledDataset(volume_uri, labels_path, patch_size=16, num_layers=4)

    assert list(cwd.iterdir()) == []
    assert len(list(cache.glob("valid_coords_*.npy"))) == 1


def test_default_valid_coords_cache_is_reused(tmp_path, monkeypatch):
    volume_uri, labels_path = _tiny_fragment(tmp_path)
    monkeypatch.setattr(
        vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "cache"), raising=False
    )
    monkeypatch.chdir(tmp_path)
    first = VesuviusLabeledDataset(volume_uri, labels_path, patch_size=16, num_layers=4)

    def no_search(**_):
        raise AssertionError("valid coordinates recomputed despite a cache")

    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    second = VesuviusLabeledDataset(
        volume_uri, labels_path, patch_size=16, num_layers=4
    )

    np.testing.assert_array_equal(second.valid_coords, first.valid_coords)


if __name__ == "__main__":
    unittest.main()
