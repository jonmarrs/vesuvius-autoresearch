"""scripts/resample_cube_pitch.py: a cube resampled to the tracer's training pitch, and the way back to the cube."""

import json

import numpy as np
import pytest

from scripts import resample_cube_pitch as rcp

R = rcp.TO_UM / rcp.FROM_UM  # 9.6 / 7.91


def test_the_registered_sizes():
    """A 256^3 cube becomes 212^3 and a 512^3 one 422^3: every source voxel covered, even for the 2x presence."""
    assert (rcp.resampled_length(256, R), rcp.resampled_length(512, R)) == (212, 422)
    for n in (256, 512):
        k = rcp.resampled_length(n, R)
        assert k % 2 == 0 and (k - 2) * R <= n - 1 and k * R > n - 1


def test_sample_j_is_the_source_at_j_times_r():
    """On a linear ramp trilinear interpolation is exact, so output[j] equals j * r wherever j * r is inside."""
    n = 40
    ramp = np.broadcast_to(np.arange(n, dtype=np.float32), (n, n, n)).copy()
    out = rcp.resample(ramp, R)
    j = np.arange(out.shape[2])
    inside = j * R <= n - 1
    np.testing.assert_allclose(out[5, 7, inside], j[inside] * R, atol=1e-4)
    # Past the last source voxel the edge is replicated, never zero (the tracer reads 0 as outside the scan).
    assert np.all(out[5, 7, ~inside] == n - 1) and (~inside).sum() >= 1


def test_a_traced_point_maps_back_to_the_source_cube():
    """A bright voxel at source x shows up in the resampled cube at x / r, and to_source takes it back to x."""
    vol = np.zeros((64, 64, 64), np.float32)
    vol[20, 30, 51] = 1.0  # 51 = 42 * r to within 0.03 voxel
    out = rcp.resample(vol, R)
    peak = np.unravel_index(np.argmax(out), out.shape)
    np.testing.assert_allclose(
        rcp.to_source(np.array(peak), R), [20, 30, 51], atol=R / 2
    )


def test_uint8_ct_stays_uint8_within_its_range():
    rng = np.random.default_rng(0)
    ct = rng.integers(10, 200, (30, 30, 30), dtype=np.uint8)
    out = rcp.resample(ct, R)
    assert out.dtype == np.uint8 and out.min() >= 10 and out.max() <= 199


def test_written_ct_and_probability(tmp_path):
    zarr = pytest.importorskip("zarr")
    src = tmp_path / "src.zarr"
    zarr.open(str(src), mode="w", shape=(24, 24, 24), chunks=(8, 8, 8), dtype="u1")[
        ...
    ] = 7
    np.save(tmp_path / "p.npy", np.full((24, 24, 24), 0.25, np.float32))
    shape = rcp.write_ct(src, tmp_path / "out.zarr", R)
    assert shape == (20, 20, 20)
    meta = json.loads((tmp_path / "out.zarr" / "0" / ".zarray").read_text())
    assert (meta["zarr_format"], meta["dtype"], meta["compressor"]["cname"]) == (
        2,
        "|u1",
        "lz4",
    )
    assert np.all(zarr.open(str(tmp_path / "out.zarr" / "0"), mode="r")[...] == 7)
    assert rcp.write_prob(tmp_path / "p.npy", tmp_path / "q.npy", R) == shape
    q = np.load(tmp_path / "q.npy")
    assert q.dtype == np.float32 and np.allclose(q, 0.25)
    with pytest.raises(FileExistsError):
        rcp.write_ct(src, tmp_path / "out.zarr", R)
    with pytest.raises(FileExistsError):
        rcp.write_prob(tmp_path / "p.npy", tmp_path / "q.npy", R)
    assert not list(tmp_path.glob(".out.zarr.building-*")) and not list(
        tmp_path.glob(".q.npy.*")
    )


def test_a_resumed_run_keeps_what_is_written(tmp_path):
    """The chain reruns the script for a cube whose outputs exist: it keeps them rather than refusing or rewriting."""
    zarr = pytest.importorskip("zarr")
    src = tmp_path / "src.zarr"
    zarr.open(str(src), mode="w", shape=(24, 24, 24), chunks=(8, 8, 8), dtype="u1")[
        ...
    ] = 7
    np.save(tmp_path / "p.npy", np.full((24, 24, 24), 0.25, np.float32))
    args = ["--ct", str(src), "--prob", str(tmp_path / "p.npy"), "--out-ct", str(tmp_path / "o.zarr"),
            "--out-prob", str(tmp_path / "o.npy")]  # fmt: skip
    assert rcp.main(args) == 0
    before = (tmp_path / "o.npy").stat().st_mtime_ns
    assert rcp.main(args) == 0
    assert (tmp_path / "o.npy").stat().st_mtime_ns == before
