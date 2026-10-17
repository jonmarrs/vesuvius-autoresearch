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


def _probability(tmp_path, seed=3):
    prob = np.random.default_rng(seed).random((128, 128, 128)).astype(np.float32)
    np.save(tmp_path / "p.npy", prob)
    return prob


def _interrupt_writes(monkeypatch, partway):
    """zarr.open whose array runs `partway(array, value)` in place of its full write."""
    real_open = zarr.open

    def wrapped(*args, **kwargs):
        array = real_open(*args, **kwargs)

        class Interrupted:
            def __setitem__(self, key, value):
                partway(array, value)

        return Interrupted()

    monkeypatch.setattr(zarr, "open", wrapped)
    return real_open


def test_a_write_killed_partway_leaves_no_level_to_reuse(tmp_path, monkeypatch):
    """The chain reuses any presence level that exists; a half-written one reads as zero presence where its chunks
    are missing."""
    prob = _probability(tmp_path)
    out = tmp_path / "presence.zarr"

    class Killed(Exception):
        pass

    def die(array, value):
        array[:8] = value[:8]  # part of the only chunk, then the process dies
        raise Killed

    real_open = _interrupt_writes(monkeypatch, die)
    with pytest.raises(Killed):
        m.write_presence(tmp_path / "p.npy", out)
    assert not out.exists()
    monkeypatch.setattr(zarr, "open", real_open)
    target = m.write_presence(tmp_path / "p.npy", out)  # the rerun starts clean
    assert np.array_equal(zarr.open(str(target), mode="r")[...], m.presence_level(prob))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["p.npy", "presence.zarr"]


def test_two_writers_on_one_cube_leave_one_whole_level(tmp_path, monkeypatch):
    """A second chain launched during a presence step: the writer that finishes second must refuse, not hand the
    tracer the other's half-written level (or rename a level with holes over it)."""
    prob = _probability(tmp_path)
    out = tmp_path / "presence.zarr"
    state = {}

    def overtaken(array, value):
        array[:8] = value[:8]
        monkeypatch.setattr(zarr, "open", state["real_open"])
        state["other"] = m.write_presence(
            tmp_path / "p.npy", out
        )  # the other writer, start to finish
        array[...] = value

    state["real_open"] = _interrupt_writes(monkeypatch, overtaken)
    with pytest.raises(FileExistsError, match="another writer"):
        m.write_presence(tmp_path / "p.npy", out)
    stored = zarr.open(str(state["other"]), mode="r")
    assert np.array_equal(stored[...], m.presence_level(prob))
    assert m.level_complete(state["other"])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["p.npy", "presence.zarr"]


def test_a_level_missing_a_chunk_is_not_complete(tmp_path):
    """The chain's check on a level it reuses, including one the in-place writer left before 2026-10-17."""
    _probability(tmp_path)
    whole = m.write_presence(tmp_path / "p.npy", tmp_path / "presence.zarr")
    assert m.level_complete(whole)
    np.save(tmp_path / "zero.npy", np.zeros((128, 128, 128), np.float32))
    empty = m.write_presence(tmp_path / "zero.npy", tmp_path / "zero.zarr")
    assert m.level_complete(empty)  # all-zero chunks are still written
    killed = zarr.open(
        str(tmp_path / "killed.zarr" / "1"),
        mode="w-",
        shape=(64, 64, 64),
        chunks=(32, 32, 32),
        dtype="u1",
    )
    killed[:32] = 7  # half of it written, as an in-place write cut short leaves it
    assert not m.level_complete(tmp_path / "killed.zarr" / "1")
