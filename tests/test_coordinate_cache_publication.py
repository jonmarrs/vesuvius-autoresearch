"""Interrupted coordinate-cache writes must not poison future dataset reads."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import numpy as np
import pytest
import zarr
from PIL import Image

from vesuvius_autoresearch.core import patch_catalog, vesuvius_loader


@pytest.fixture
def fragment(tmp_path):
    source = tmp_path / "ct.zarr"
    volume = zarr.open(
        str(source), mode="w", shape=(4, 32, 32), chunks=(4, 16, 16), dtype="u1"
    )
    volume[:] = 64
    labels = tmp_path / "labels.png"
    pixels = np.zeros((32, 32), np.uint8)
    pixels[:16, :16] = 255
    Image.fromarray(pixels).save(labels)
    cache = tmp_path / "cache"

    def build():
        return vesuvius_loader.VesuviusLabeledDataset(
            str(source),
            str(labels),
            cache_dir=str(cache),
            patch_size=16,
            num_layers=4,
            require_ink=True,
            jitter=False,
            strict_reads=True,
        )

    return build, cache


@pytest.mark.parametrize(
    "damage",
    [
        "empty_file",
        "partial_header",
        "partial_payload",
        "non_npy",
        "empty_coords",
        "wrong_shape",
        "float_coords",
        "negative",
        "beyond_grid",
        "unsigned_overflow",
        "npz",
        "partial_zip",
    ],
)
def test_invalid_cache_is_rebuilt_and_reused(fragment, monkeypatch, damage):
    build, cache = fragment
    expected = build()
    path = next(cache.glob("valid_coords_*.npy"))
    valid_bytes = path.read_bytes()
    if damage == "empty_file":
        path.write_bytes(b"")
    elif damage == "partial_header":
        path.write_bytes(valid_bytes[:32])
    elif damage == "partial_payload":
        path.write_bytes(valid_bytes[:-1])
    elif damage == "non_npy":
        path.write_bytes(b"interrupted array")
    elif damage == "npz":
        with path.open("wb") as stream:
            np.savez(stream, coords=expected.valid_coords)
    elif damage == "partial_zip":
        path.write_bytes(b"PK\x03\x04")
    else:
        invalid = {
            "empty_coords": np.empty((0, 2), np.int32),
            "wrong_shape": np.array([0, 0], np.int32),
            "float_coords": np.array([[0.5, 0]], np.float32),
            "negative": np.array([[-1, 0]], np.int32),
            "beyond_grid": np.array([[17, 0]], np.int32),
            "unsigned_overflow": np.array([[2**64 - 1, 0]], np.uint64),
        }[damage]
        np.save(path, invalid, allow_pickle=False)

    repaired = build()
    np.testing.assert_array_equal(repaired.valid_coords, expected.valid_coords)
    assert repaired[0][1].sum() == 256
    np.testing.assert_array_equal(
        np.load(path, allow_pickle=False), expected.valid_coords
    )

    def no_search(**kwargs):
        pytest.fail("a repaired cache should be reused")

    monkeypatch.setattr(patch_catalog, "find_valid_patches", no_search)
    np.testing.assert_array_equal(build().valid_coords, expected.valid_coords)


def _partial_write(destination):
    if hasattr(destination, "write"):
        destination.write(b"partial array")
        destination.flush()
    else:
        Path(destination).write_bytes(b"partial array")


@pytest.mark.parametrize("existing", [False, True])
def test_failed_write_never_publishes_partial_cache(fragment, monkeypatch, existing):
    build, cache = fragment
    before = {}
    if existing:
        build()
        path = next(cache.glob("valid_coords_*.npy"))
        path.write_bytes(b"interrupted old array")
        before[path.name] = path.read_bytes()

    def fail_save(destination, *args, **kwargs):
        _partial_write(destination)
        raise OSError("injected disk failure")

    monkeypatch.setattr(np, "save", fail_save)
    with pytest.raises(OSError, match="injected disk failure"):
        build()
    assert {p.name: p.read_bytes() for p in cache.iterdir()} == before


def test_reader_during_write_only_observes_complete_cache(fragment, monkeypatch):
    build, cache = fragment
    entered, release = Event(), Event()
    save = np.save

    def paused_save(destination, *args, **kwargs):
        if not entered.is_set():
            _partial_write(destination)
            entered.set()
            if not release.wait(timeout=10):
                raise TimeoutError("reader did not finish during bounded write probe")
            if hasattr(destination, "seek"):
                destination.seek(0)
                destination.truncate()
        return save(destination, *args, **kwargs)

    monkeypatch.setattr(np, "save", paused_save)
    with ThreadPoolExecutor(max_workers=1) as pool:
        writer = pool.submit(build)
        try:
            assert entered.wait(timeout=10)
            reader = build()
        finally:
            release.set()
        completed = writer.result(timeout=10)
    np.testing.assert_array_equal(reader.valid_coords, completed.valid_coords)
    np.testing.assert_array_equal(reader.valid_coords, [[0, 0]])
    assert reader[0][1].sum() == 256
    assert len(list(cache.iterdir())) == 1


def test_cache_permission_error_is_not_hidden(fragment, monkeypatch):
    build, cache = fragment
    build()
    path = next(cache.glob("valid_coords_*.npy"))
    load = np.load

    def denied(source, *args, **kwargs):
        if str(source) == str(path):
            raise PermissionError("injected read denial")
        return load(source, *args, **kwargs)

    monkeypatch.setattr(np, "load", denied)
    with pytest.raises(PermissionError, match="injected read denial"):
        build()


@pytest.mark.parametrize(
    "invalid",
    [
        # Two-dimensional, so only the column count refuses it; __getitem__
        # would otherwise fail on the first sample rather than here.
        np.array([[0, 0, 0]], np.int32),
        np.array([[0, 17]], np.int32),  # x past the last patch start, y in range
    ],
    ids=["three_columns", "x_beyond_grid"],
)
def test_a_cache_of_the_wrong_width_or_x_range_is_rebuilt(fragment, invalid):
    build, cache = fragment
    expected = build()
    path = next(cache.glob("valid_coords_*.npy"))
    np.save(path, invalid, allow_pickle=False)
    repaired = build()
    np.testing.assert_array_equal(repaired.valid_coords, expected.valid_coords)
    np.testing.assert_array_equal(
        np.load(path, allow_pickle=False), expected.valid_coords
    )
