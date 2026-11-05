"""Separate virtual mappings must not let response writes alter the CT input."""

import os
import tempfile

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import detection, streaming


def mapped_volume(path, raw, file_kind):
    if file_kind == "npy":
        np.save(path, raw)
        return np.load(path, mmap_mode="r")
    raw.tofile(path)
    return np.memmap(path, dtype=raw.dtype, mode="r", shape=raw.shape)


def mapped_output(path, shape, file_kind):
    if file_kind == "npy":
        return np.load(path, mmap_mode="r+")
    return np.memmap(path, dtype=np.float32, mode="r+", shape=shape)


LAYOUTS = [
    "memmap",
    "ndarray",
    "reversed",
    "buffer",
    "strided",
    "strided_source",
    "strided_target",
]


def view(array, layout, role):
    if layout in ("strided", f"strided_{role}"):
        # Identity strides are valid; the wrapper still inserts a DummyArray.
        return np.lib.stride_tricks.as_strided(
            np.asarray(array), shape=array.shape, strides=array.strides
        )
    if layout == "buffer":
        return np.frombuffer(memoryview(array), dtype=array.dtype).reshape(array.shape)
    if layout == "ndarray":
        return np.asarray(array)
    if layout == "reversed":
        return np.asarray(array)[::-1, :, ::-1]
    return array


@pytest.mark.parametrize("file_kind", ["npy", "raw"])
@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("layout", LAYOUTS)
def test_same_backing_file_refused_before_transfer(tmp_path, file_kind, alias, layout):
    source = tmp_path / "ct.npy"
    raw = np.random.default_rng(4090).random((17, 19, 21)).astype(np.float32)
    volume = mapped_volume(source, raw, file_kind)
    target = source
    if alias != "direct":
        target = tmp_path / "alias.npy"
        if alias == "symlink":
            target.symlink_to(source)
        else:
            os.link(source, target)
    output = mapped_output(target, raw.shape, file_kind)
    volume, output = view(volume, layout, "source"), view(output, layout, "target")
    assert not np.shares_memory(volume, output)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="different backing files"):
        streaming.filter_into(
            volume,
            output,
            filter_name="vesselness",
            block_size=8,
            halo=10,
            to_device=lambda block: pytest.fail("transferred an aliased CT block"),
        )
    assert source.read_bytes() == before


@pytest.mark.parametrize("file_kind", ["npy", "raw"])
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("filter_name", ["ridges", "vesselness"])
def test_distinct_mapped_files_keep_exact_response(
    tmp_path, file_kind, layout, filter_name
):
    source, target = tmp_path / "ct.npy", tmp_path / "response.npy"
    raw = np.random.default_rng(4090).random((17, 19, 21)).astype(np.float32)
    volume = mapped_volume(source, raw, file_kind)
    mapped_volume(target, np.zeros_like(raw), file_kind)
    output = mapped_output(target, raw.shape, file_kind)
    before = source.read_bytes()
    volume, output = view(volume, layout, "source"), view(output, layout, "target")
    expected = getattr(detection, f"detect_{filter_name}_tiled")(
        np.array(volume), block_size=8, halo=10
    ).astype(np.float32)
    streaming.filter_into(
        volume, output, filter_name=filter_name, block_size=8, halo=10
    )
    np.testing.assert_array_equal(output, expected)
    assert source.read_bytes() == before


def test_memmap_copy_is_an_independent_in_memory_output(tmp_path):
    source = tmp_path / "ct.npy"
    raw = np.random.default_rng(4090).random((9, 11, 13)).astype(np.float32)
    volume = mapped_volume(source, raw, "npy")
    output = volume.copy()
    assert isinstance(output, np.memmap) and output.filename is None
    before = source.read_bytes()
    streaming.filter_into(
        volume, output, filter_name="vesselness", block_size=8, halo=10
    )
    np.testing.assert_array_equal(
        output,
        detection.detect_vesselness_tiled(raw.copy(), block_size=8, halo=10).astype(
            np.float32
        ),
    )
    assert source.read_bytes() == before


def test_unidentifiable_mapped_storage_fails_before_transfer():
    shape = (3, 3, 3)
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as target:
        source.truncate(4 * np.prod(shape))
        target.truncate(4 * np.prod(shape))
        volume = np.memmap(source, mode="r", dtype=np.float32, shape=shape)
        output = np.memmap(target, mode="r+", dtype=np.float32, shape=shape)
        assert volume.filename is None and output.filename is None
        with pytest.raises(ValueError, match="identifiable backing files"):
            streaming.filter_into(
                volume,
                output,
                filter_name="vesselness",
                to_device=lambda block: pytest.fail("transferred unverified storage"),
            )


def test_missing_backing_path_fails_before_transfer(tmp_path):
    raw = np.ones((3, 3, 3), dtype=np.float32)
    source, target = tmp_path / "ct.npy", tmp_path / "response.npy"
    volume = mapped_volume(source, raw, "npy")
    mapped_volume(target, raw, "npy")
    output = mapped_output(target, raw.shape, "npy")
    source.unlink()
    with pytest.raises(ValueError, match="accessible backing files"):
        streaming.filter_into(
            volume,
            output,
            filter_name="vesselness",
            to_device=lambda block: pytest.fail("transferred unverified storage"),
        )


@pytest.mark.parametrize("copy_on_write_role", ["source", "target"])
def test_same_file_copy_on_write_maps_are_conservatively_refused(
    tmp_path, copy_on_write_role
):
    path = tmp_path / "ct.npy"
    np.save(path, np.ones((3, 3, 3), dtype=np.float32))
    volume = np.load(path, mmap_mode="c" if copy_on_write_role == "source" else "r")
    output = np.load(path, mmap_mode="c" if copy_on_write_role == "target" else "r+")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="different backing files"):
        streaming.filter_into(
            volume,
            output,
            filter_name="vesselness",
            to_device=lambda block: pytest.fail("transferred same-file storage"),
        )
    assert path.read_bytes() == before


def test_disjoint_regions_of_one_file_are_conservatively_refused(tmp_path):
    path = tmp_path / "ct.raw"
    shape = (3, 3, 3)
    raw = np.ones(shape, dtype=np.float32)
    path.write_bytes(raw.tobytes() * 2)
    volume = np.memmap(path, dtype=np.float32, mode="r", shape=shape)
    output = np.memmap(
        path, dtype=np.float32, mode="r+", shape=shape, offset=raw.nbytes
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match="different backing files"):
        streaming.filter_into(
            volume,
            output,
            filter_name="vesselness",
            to_device=lambda block: pytest.fail("transferred same-file storage"),
        )
    assert path.read_bytes() == before
