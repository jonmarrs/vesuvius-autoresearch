import numpy as np
import torch
import zarr

import vesuvius_loader


class DummyVolume:
    shape = (12, 24, 24)

    def __getitem__(self, key):
        z_slice, y_slice, x_slice = key
        depth = z_slice.stop - z_slice.start
        height = y_slice.stop - y_slice.start
        width = x_slice.stop - x_slice.start
        return torch.ones((depth, height, width), dtype=torch.float32)


def test_s3_dataset_samples_deterministic_z_without_fallback(monkeypatch):
    monkeypatch.setattr(
        vesuvius_loader, "FastVesuviusVolume", lambda *args, **kwargs: DummyVolume()
    )

    dataset = vesuvius_loader.VesuviusS3Dataset(
        uri="s3://example/scroll.zarr/0",
        patch_size=8,
        num_layers=4,
        seed=123,
    )

    patch, label = dataset[0]

    assert patch.shape == (1, 4, 8, 8)
    assert label.shape == (8, 8)
    assert np.isclose(float(patch.sum()), 256.0)


def test_fast_vesuvius_volume_reads_local_zarr_without_c_wrapper(tmp_path):
    zarr_path = tmp_path / "volume.zarr"
    arr = zarr.open(
        str(zarr_path),
        mode="w",
        shape=(4, 6, 8),
        chunks=(2, 3, 4),
        dtype="uint8",
    )
    arr[:] = np.arange(4 * 6 * 8, dtype=np.uint8).reshape(4, 6, 8)

    volume = vesuvius_loader.FastVesuviusVolume(str(zarr_path))
    patch = volume[1:3, 2:5, 3:7]

    assert patch.shape == (2, 3, 4)
    np.testing.assert_allclose(patch.numpy(), arr[1:3, 2:5, 3:7] / 255.0)
