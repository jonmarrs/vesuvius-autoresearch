"""Actual local Zarr integration, with synthetic CT bytes only."""

import numpy as np
import pytest
import zarr

from scripts.prepare_studio_input import export_input


def run(source, output, **changes):
    options = {
        "array_key": "0",
        "first_plane": 23,
        "depth_step": -1,
        "crop": (1, 5, 2, 7),
        "depth_order_note": "synthetic test",
        "max_block_bytes": 64,
    }
    options.update(changes)
    return export_input(source, output, **options)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "render.zarr"
    array = np.arange(31 * 6 * 7, dtype=np.uint16).reshape(31, 6, 7).astype(np.uint8)
    group = zarr.open_group(root, mode="w")
    group.create_dataset("0", data=array, chunks=(2, 3, 4))
    return root, array


def test_real_zarr_crop_is_exact(source, tmp_path):
    root, array = source
    record = run(root, tmp_path / "out")
    np.testing.assert_array_equal(
        np.load(tmp_path / "out/planes.npy"), array[23:7:-1, 1:5, 2:7]
    )
    assert record["source"]["array_key"] == "0"
    np.testing.assert_array_equal(zarr.open_array(root / "0", mode="r")[:], array)


def test_direct_array_supported(source, tmp_path):
    root, array = source
    run(root / "0", tmp_path / "out", array_key="")
    np.testing.assert_array_equal(
        np.load(tmp_path / "out/planes.npy"), array[23:7:-1, 1:5, 2:7]
    )


@pytest.mark.parametrize("key", ["", "1", "../render.zarr/0", "/0"])
def test_no_automatic_array_selection_or_escape(source, tmp_path, key):
    root, _ = source
    with pytest.raises((ValueError, OSError)):
        run(root, tmp_path / "out", array_key=key)
    assert not (tmp_path / "out").exists()


def test_resolved_array_escape_refused(source, tmp_path):
    root, _ = source
    (root / "escape").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        run(root, tmp_path / "out", array_key="escape")
    assert not (tmp_path / "out").exists()


def test_output_in_source_refused_through_symlink(source, tmp_path):
    root, _ = source
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        run(root, alias / "out")
    assert not (root / "out").exists()


def test_large_decoded_chunk_refused_before_read(source, tmp_path):
    root, _ = source
    with pytest.raises(ValueError, match="decoded source chunk"):
        run(root, tmp_path / "out", max_block_bytes=8)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"filters": [{"id": "pickle", "protocol": 5}]},
        {"filters": [{"id": "delta", "dtype": "|u1"}]},
        {"compressor": {"id": "pickle", "protocol": 5}},
        {"compressor": {"id": "unknown-custom-codec"}},
        {
            "compressor": {
                "id": "blosc",
                "cname": "zstd",
                "clevel": {},
                "shuffle": 1,
                "blocksize": 0,
            }
        },
        {"zarr_format": 3},
        {"dtype": "|O"},
        {"dtype": [["field", "|u1"]]},
        {"dimension_separator": "/../../"},
    ],
)
def test_unsupported_codecs_refused_before_library_open(
    source, tmp_path, monkeypatch, change
):
    import json

    root, _ = source
    path = root / "0/.zarray"
    metadata = json.loads(path.read_bytes())
    metadata.update(change)
    path.write_text(json.dumps(metadata))

    def forbidden(*args, **kwargs):
        raise AssertionError("unsafe metadata reached Zarr constructor")

    monkeypatch.setattr(zarr, "open_array", forbidden)
    with pytest.raises(ValueError):
        run(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_numeric_pickle_filter_is_rejected(tmp_path, monkeypatch):
    import numcodecs

    root = tmp_path / "pickle.zarr"
    # A benign numeric payload proves that uint8 does not imply no Pickle codec.
    group = zarr.open_group(root, mode="w")
    group.create_dataset(
        "0",
        data=np.ones((31, 6, 7), dtype=np.uint8),
        chunks=(2, 3, 4),
        filters=[numcodecs.Pickle()],
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Pickle decoding must never be reached")

    monkeypatch.setattr(numcodecs.Pickle, "decode", forbidden)
    with pytest.raises(ValueError, match="filters"):
        run(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_raw_uncompressed_zarr_supported(tmp_path):
    root = tmp_path / "raw.zarr"
    array = zarr.open_array(
        root, mode="w", shape=(31, 6, 7), dtype="u1", chunks=(2, 3, 4), compressor=None
    )
    array[:] = 240
    run(root, tmp_path / "out", array_key="")
    assert np.all(np.load(tmp_path / "out/planes.npy") == 240)


def test_oversized_metadata_refused_before_library_open(source, tmp_path, monkeypatch):
    root, _ = source
    (root / "0/.zarray").write_bytes(b" " * (64 * 1024 + 1))

    def forbidden(*args, **kwargs):
        raise AssertionError("oversized metadata reached Zarr")

    monkeypatch.setattr(zarr, "open_array", forbidden)
    with pytest.raises(ValueError, match="64 KiB"):
        run(root, tmp_path / "out")


def test_library_uses_validated_metadata_snapshot(source, tmp_path, monkeypatch):
    import json

    root, array = source
    original_open = zarr.open_array

    def change_metadata_then_open(*args, **kwargs):
        path = root / "0/.zarray"
        metadata = json.loads(path.read_bytes())
        metadata["compressor"] = {"id": "unknown-custom-codec"}
        path.write_text(json.dumps(metadata))
        return original_open(*args, **kwargs)

    monkeypatch.setattr(zarr, "open_array", change_metadata_then_open)
    run(root, tmp_path / "out")
    np.testing.assert_array_equal(
        np.load(tmp_path / "out/planes.npy"), array[23:7:-1, 1:5, 2:7]
    )


_BLOSC = {"id": "blosc", "cname": "zstd", "clevel": 1, "shuffle": 1, "blocksize": 0}


@pytest.mark.parametrize(
    "change",
    [
        {"id": "zlib"},
        {"typesize": 1},
        {"cname": 5},
        {"clevel": 10},
        {"shuffle": True},
        {"shuffle": 3},
        {"blocksize": 0.0},
        {"blocksize": -1},
    ],
    ids=[
        "other_id",
        "extra_key",
        "numeric_cname",
        "clevel_10",
        "boolean_shuffle",
        "shuffle_3",
        "float_blocksize",
        "negative_blocksize",
    ],
)
def test_each_blosc_setting_is_checked_on_its_own(
    source, tmp_path, monkeypatch, change
):
    import json

    root, _ = source
    path = root / "0/.zarray"
    metadata = json.loads(path.read_bytes())
    metadata["compressor"] = {**_BLOSC, **change}
    path.write_text(json.dumps(metadata))

    def forbidden(*args, **kwargs):
        raise AssertionError("unsafe metadata reached Zarr constructor")

    monkeypatch.setattr(zarr, "open_array", forbidden)
    with pytest.raises(ValueError, match="only raw or standard Blosc"):
        run(root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_a_decoded_chunk_exactly_at_the_block_limit_is_accepted(source, tmp_path):
    root, array = source
    # Chunks of 2 x 3 x 4 uint8 voxels decode to 24 bytes.
    run(root, tmp_path / "out", max_block_bytes=24)
    actual = np.load(tmp_path / "out" / "planes.npy", allow_pickle=False)
    np.testing.assert_array_equal(actual, array[23:7:-1, 1:5, 2:7])
