"""scripts/make_tracer_presence.py: fiber_hz_vt probabilities -> the tracer's uint8 presence level."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import zarr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import make_tracer_presence as m  # noqa: E402


def test_each_voxel_is_the_scaled_mean_of_its_block():
    rng = np.random.default_rng(0)
    prob = rng.random((8, 6, 4)).astype(np.float32)
    got = m.presence_level(prob)
    want = np.rint(
        prob.astype(np.float64).reshape(4, 2, 3, 2, 2, 2).mean(axis=(1, 3, 5)) * 255
    )
    assert got.dtype == np.uint8 and got.shape == (4, 3, 2)
    assert np.array_equal(got, want.astype(np.uint8))


def test_slabs_do_not_change_the_result(monkeypatch):
    prob = np.random.default_rng(1).random((12, 4, 4)).astype(np.float32)
    whole = m.presence_level(prob)
    monkeypatch.setattr(m, "SLAB", 4)  # 2 grid slices per pass, 3 passes
    assert np.array_equal(m.presence_level(prob), whole)


def test_a_full_block_reaches_255_and_an_empty_one_0():
    prob = np.zeros((4, 2, 2), dtype=np.float32)
    prob[:2] = 1.0
    assert m.presence_level(prob).ravel().tolist() == [255, 0]


@pytest.mark.parametrize(
    "prob",
    [
        np.zeros((3, 4, 4)),  # odd
        np.zeros((4, 4)),  # 2-D
        np.full((2, 2, 2), 1.5),  # above 1
        np.full((2, 2, 2), np.nan),
    ],
)
def test_refuses_what_is_not_a_probability_cube(prob):
    with pytest.raises(ValueError):
        m.presence_level(prob)


def test_writes_one_integer_named_level_and_no_coarser_one(tmp_path):
    prob = np.random.default_rng(2).random((8, 8, 8)).astype(np.float32)
    np.save(tmp_path / "p.npy", prob)
    target = m.write_presence(tmp_path / "p.npy", tmp_path / "presence.zarr")
    # The tracer's own rule (tracing/volume.py tile_weights): int(name) + 1 beside it.
    assert int(target.name) == 1
    assert not (target.parent / str(int(target.name) + 1)).exists()
    stored = zarr.open(str(target), mode="r")
    assert stored.dtype == np.uint8 and stored.shape == (4, 4, 4)
    assert np.array_equal(stored[...], m.presence_level(prob))
    with pytest.raises(FileExistsError):
        m.write_presence(tmp_path / "p.npy", tmp_path / "presence.zarr")
