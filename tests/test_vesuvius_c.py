
import os

import numpy as np

import pytest

vesuvius_c = pytest.importorskip("vesuvius_c_wrapper.vesuvius_c")
FastLocalVolume = vesuvius_c.FastLocalVolume


def test_fast_local_volume_falls_back_to_zarr(tmp_path):
    zarr = pytest.importorskip("zarr")
    path = tmp_path / "volume.zarr"
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data

    vol = FastLocalVolume(path, prefer_native=False)

    assert vol.shape == data.shape
    assert vol.chunks == (2, 3, 4)
    assert vol.backend == "zarr"
    np.testing.assert_array_equal(vol.get_chunk(1, 1, 1), data[2:4, 3:6, 4:8])
    np.testing.assert_array_equal(vol.get_chunk(1, 2, 3, 2, 3, 4), data[1:3, 2:5, 3:7])


def test_fast_local_volume_requires_complete_voxel_dimensions(tmp_path):
    zarr = pytest.importorskip("zarr")
    path = tmp_path / "volume.zarr"
    arr = zarr.open(str(path), mode="w", shape=(4, 6, 8), chunks=(2, 3, 4), dtype="float32")
    arr[:] = 0

    vol = FastLocalVolume(path, prefer_native=False)

    with pytest.raises(ValueError, match="depth, height, and width"):
        vol.get_chunk(0, 0, 0, 1)


def test_fast_vesuvius_volume_slice_uses_voxel_chunk_signature(tmp_path):
    zarr = pytest.importorskip("zarr")
    from vesuvius_loader import FastVesuviusVolume

    path = tmp_path / "volume.zarr"
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data

    volume = FastVesuviusVolume(str(path))

    np.testing.assert_allclose(volume[1:3, 2:5, 3:7].numpy(), data[1:3, 2:5, 3:7] / 255.0)


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
