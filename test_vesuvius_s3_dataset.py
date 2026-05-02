import numpy as np
import torch

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
    monkeypatch.setattr(vesuvius_loader, "FastVesuviusVolume", lambda *args, **kwargs: DummyVolume())

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
