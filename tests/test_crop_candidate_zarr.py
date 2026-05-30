import numpy as np
import zarr

from scripts.crop_candidate_zarr import crop_candidate_zarr


def test_crop_candidate_zarr_writes_bounded_crop(tmp_path):
    src_path = tmp_path / "source.zarr"
    dst_path = tmp_path / "crop.zarr"
    src = zarr.open(
        str(src_path), mode="w", shape=(10, 20, 30), chunks=(5, 10, 10), dtype="u1"
    )
    data = np.arange(10 * 20 * 30, dtype=np.uint32).reshape(10, 20, 30) % 255
    src[:] = data.astype("u1")

    shape = crop_candidate_zarr(
        src_path, dst_path, z=2, y=6, x=8, depth=4, height=5, width=6
    )

    assert shape == (4, 5, 6)
    dst = zarr.open(str(dst_path), mode="r")
    np.testing.assert_array_equal(dst[:], src[2:6, 6:11, 8:14])
    assert dst.attrs["source_start_zyx"] == [2, 6, 8]
    assert dst.attrs["crop_shape_zyx"] == [4, 5, 6]


def test_crop_candidate_zarr_clamps_to_source_bounds(tmp_path):
    src_path = tmp_path / "source.zarr"
    dst_path = tmp_path / "crop.zarr"
    src = zarr.open(
        str(src_path), mode="w", shape=(10, 20, 30), chunks=(5, 10, 10), dtype="u1"
    )
    src[:] = 1

    crop_candidate_zarr(src_path, dst_path, z=9, y=19, x=29, depth=4, height=5, width=6)

    dst = zarr.open(str(dst_path), mode="r")
    assert dst.shape == (4, 5, 6)
    assert dst.attrs["source_start_zyx"] == [6, 15, 24]
