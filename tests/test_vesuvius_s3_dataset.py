from collections import defaultdict

import numpy as np
import pytest
import torch
import zarr

import vesuvius_autoresearch.core.vesuvius_loader as vesuvius_loader


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


@pytest.mark.parametrize(
    "dtype, value, expected",
    [
        ("uint8", 255, 1.0),
        ("<u2", 65535, 1.0),
        # Big-endian, as some scroll volumes are: it compared unequal to np.uint16
        # and fell to the unknown-dtype /255, so 65535 reached the model as 257.
        (">u2", 65535, 1.0),
        (">u2", 4096, 4096 / 65535),
        (">f4", 0.5, 0.5),
    ],
)
def test_read_ct_normalises_by_dtype_whatever_its_byte_order(
    tmp_path, monkeypatch, dtype, value, expected
):
    """FastVesuviusVolume.read_ct is what the unlabeled dataset and inference read
    through; the labeled dataset already handled a big-endian volume."""
    warnings = defaultdict(int)
    monkeypatch.setattr(vesuvius_loader, "_WARNING_COUNTS", warnings)
    path = tmp_path / "volume.zarr"
    arr = zarr.open(str(path), mode="w", shape=(2, 4, 4), chunks=(2, 4, 4), dtype=dtype)
    arr[:] = np.full((2, 4, 4), value, dtype=dtype)
    volume = vesuvius_loader.FastVesuviusVolume(str(path))
    ct = volume.read_ct(0, 0, 0, 2, 4, 4)
    assert ct.dtype == np.float32 and ct.dtype.isnative
    np.testing.assert_allclose(ct, expected, rtol=1e-6)
    np.testing.assert_allclose(volume[0:2, 0:4, 0:4].numpy(), expected, rtol=1e-6)
    assert "ct_unknown_dtype" not in warnings


def _grid(monkeypatch, shape, patch_size):
    class Volume(DummyVolume):
        pass

    Volume.shape = shape
    monkeypatch.setattr(
        vesuvius_loader, "FastVesuviusVolume", lambda *args, **kwargs: Volume()
    )
    dataset = vesuvius_loader.VesuviusS3Dataset(
        uri="s3://example/scroll.zarr/0", patch_size=patch_size, num_layers=4
    )
    return [tuple(c) for c in dataset.valid_coords.tolist()]


def test_the_unlabeled_grid_reaches_the_far_edges(monkeypatch):
    """The grid stopped one stride short: on 24 x 24 at patch 8 it ended at 12,
    so rows and columns 20-23 were never read."""
    starts = [0, 4, 8, 12, 16]
    assert _grid(monkeypatch, (12, 24, 24), 8) == [
        (y, x) for y in starts for x in starts
    ]
    # Not a multiple of the stride: the last patch is flush with the edge.
    assert {x for _, x in _grid(monkeypatch, (12, 8, 26), 8)} == {
        0,
        4,
        8,
        12,
        16,
        18,
    }


def test_a_volume_one_patch_across_gives_that_patch(monkeypatch):
    """It gave an empty catalogue."""
    assert _grid(monkeypatch, (12, 8, 8), 8) == [(0, 0)]


def test_a_volume_smaller_than_a_patch_gives_none(monkeypatch):
    assert _grid(monkeypatch, (12, 6, 30), 8) == []
