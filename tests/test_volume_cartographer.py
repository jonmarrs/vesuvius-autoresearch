import numpy as np
import pytest

from volume_cartographer_wrapper.volume import FastLocalVolume, VolumeCartographerVolume


def test_fast_local_volume_reads_grid_and_voxel_chunks(tmp_path):
    zarr = pytest.importorskip("zarr")
    path = tmp_path / "volume.zarr"
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data

    vol = FastLocalVolume(path)

    assert vol.shape == data.shape
    assert vol.chunks == (2, 3, 4)
    assert vol.backend == "volume-cartographer-zarr"
    np.testing.assert_array_equal(vol.get_chunk(1, 1, 1), data[2:4, 3:6, 4:8])
    np.testing.assert_array_equal(vol.get_chunk(1, 2, 3, 2, 3, 4), data[1:3, 2:5, 3:7])


def test_fast_local_volume_requires_complete_voxel_dimensions(tmp_path):
    zarr = pytest.importorskip("zarr")
    path = tmp_path / "volume.zarr"
    arr = zarr.open(str(path), mode="w", shape=(4, 6, 8), chunks=(2, 3, 4), dtype="float32")
    arr[:] = 0

    vol = FastLocalVolume(path)

    with pytest.raises(ValueError, match="depth, height, and width"):
        vol.get_chunk(0, 0, 0, 1)


def test_volume_cartographer_volume_accepts_file_url(tmp_path):
    zarr = pytest.importorskip("zarr")
    path = tmp_path / "volume.zarr"
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data

    vol = VolumeCartographerVolume(url=f"file://{path}")

    assert vol.backend == "volume-cartographer-zarr"
    np.testing.assert_array_equal(vol.get_chunk(0, 0, 0, 2, 3, 4), data[:2, :3, :4])


def test_fast_vesuvius_volume_uses_volume_cartographer_wrapper(tmp_path):
    zarr = pytest.importorskip("zarr")
    from vesuvius_loader import FastVesuviusVolume

    path = tmp_path / "volume.zarr"
    data = np.arange(4 * 6 * 8, dtype=np.float32).reshape(4, 6, 8)
    arr = zarr.open(str(path), mode="w", shape=data.shape, chunks=(2, 3, 4), dtype="float32")
    arr[:] = data

    volume = FastVesuviusVolume(str(path))

    assert volume.vol.backend == "volume-cartographer-zarr"
    np.testing.assert_allclose(volume[1:3, 2:5, 3:7].numpy(), data[1:3, 2:5, 3:7])
