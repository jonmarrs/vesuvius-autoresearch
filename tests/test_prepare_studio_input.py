"""CPU-only byte-for-byte adapter tests; no model or checkpoint imports."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts import prepare_studio_input as prep


@pytest.fixture
def source(tmp_path):
    array = np.arange(31 * 6 * 7, dtype=np.uint16).reshape(31, 6, 7).astype(np.uint8)
    path = tmp_path / "render.npy"
    np.save(path, array)
    return path, array


def export(path, out, **changes):
    args = {
        "first_plane": 23,
        "depth_step": -1,
        "crop": (1, 5, 2, 7),
        "depth_order_note": "synthetic plane order",
        "max_block_bytes": 10,
    }
    args.update(changes)
    return prep.export_input(path, out, **args)


@pytest.mark.parametrize("first,step", [(23, -1), (0, 1)])
def test_order_crop_and_exact_bytes(source, tmp_path, first, step):
    path, array = source
    out = tmp_path / "out"
    record = export(path, out, first_plane=first, depth_step=step)
    indices = [first + step * i for i in range(16)]
    expected = array[indices, 1:5, 2:7]
    actual = np.load(out / "planes.npy", mmap_mode="r", allow_pickle=False)
    assert actual.shape == (16, 4, 5)
    assert actual.dtype == np.uint8
    np.testing.assert_array_equal(actual, expected)
    assert record == json.loads((out / "input.json").read_text())
    assert record["planes_in_model_order"] == indices
    assert record["source"]["shape"] == [31, 6, 7]
    assert record["source"]["path"] == str(path)
    assert record["crop_half_open"] == {"rows": [1, 5], "cols": [2, 7]}
    assert (
        record["selected_payload_sha256"]
        == hashlib.sha256(expected.tobytes()).hexdigest()
    )
    assert record["selected_plane_sha256_in_model_order"] == [
        hashlib.sha256(a.tobytes()).hexdigest() for a in expected
    ]
    assert (
        record["output"]["file_sha256"]
        == hashlib.sha256((out / "planes.npy").read_bytes()).hexdigest()
    )
    np.testing.assert_array_equal(np.load(path), array)


@pytest.mark.parametrize(
    "change",
    [
        {"first_plane": 14},
        {"first_plane": 31},
        {"depth_step": 0},
        {"crop": (-1, 2, 0, 1)},
        {"crop": (0, 7, 0, 1)},
        {"crop": (0, 2, 0, 8)},
        {"crop": (1, 1, 0, 1)},
        {"crop": (0, 1, 3, 2)},
        {"depth_order_note": " "},
        {"max_output_bytes": 319},
        {"max_output_bytes": 0},
        {"max_block_bytes": 4},
        {"max_block_bytes": 0},
        {"array_key": "0"},
    ],
)
def test_bad_plan_creates_nothing(source, tmp_path, change):
    path, _ = source
    with pytest.raises(ValueError):
        export(path, tmp_path / "out", **change)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "shape,dtype",
    [
        ((31, 6, 7), "uint16"),
        ((31, 6, 7), "float32"),
        ((31, 6, 7), "int8"),
        ((31, 6), "uint8"),
        ((1, 31, 6, 7), "uint8"),
        ((31, 0, 7), "uint8"),
    ],
)
def test_no_implicit_dtype_or_axis_conversion(tmp_path, shape, dtype):
    path = tmp_path / "source.npy"
    np.save(path, np.zeros(shape, dtype=dtype))
    with pytest.raises(ValueError):
        export(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_existing_destination_untouched(source, tmp_path, kind):
    path, _ = source
    out = tmp_path / "out"
    if kind == "directory":
        out.mkdir()
        (out / "planes.npy").write_bytes(b"sentinel")
    elif kind == "file":
        out.write_bytes(b"sentinel")
    else:
        out.symlink_to(tmp_path / "absent")
    with pytest.raises(FileExistsError):
        export(path, out)
    if kind == "directory":
        assert (out / "planes.npy").read_bytes() == b"sentinel"
    elif kind == "file":
        assert out.read_bytes() == b"sentinel"
    else:
        assert out.is_symlink()


def test_input_cannot_be_output(source):
    path, array = source
    with pytest.raises(ValueError, match="outside"):
        export(path, path)
    np.testing.assert_array_equal(np.load(path), array)


def test_read_failure_removes_partial_output(source, tmp_path, monkeypatch):
    path, array = source

    class Broken:
        ndim, dtype, shape = array.ndim, array.dtype, array.shape
        reads = 0

        def __getitem__(self, key):
            self.reads += 1
            if self.reads > 1:
                raise OSError("synthetic read failure")
            return array[key]

    monkeypatch.setattr(prep, "open_source", lambda *args: (Broken(), path))
    with pytest.raises(OSError, match="synthetic"):
        export(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    np.testing.assert_array_equal(np.load(path), array)


def test_reads_are_small_and_in_requested_order(source, tmp_path, monkeypatch):
    path, array = source
    reads = []

    class Recording:
        ndim, dtype, shape = array.ndim, array.dtype, array.shape

        def __getitem__(self, key):
            value = array[key]
            reads.append((key, value.nbytes))
            return value

    monkeypatch.setattr(prep, "open_source", lambda *args: (Recording(), path))
    export(path, tmp_path / "out")
    assert len(reads) == 32
    assert all(size <= 10 for _, size in reads)
    assert [key[0] for key, _ in reads] == [
        p for p in range(23, 7, -1) for _ in range(2)
    ]


def test_cli_round_trip_without_model_packages(source, tmp_path):
    path, array = source
    command = [
        sys.executable,
        str(Path(prep.__file__)),
        "--source",
        str(path),
        "--output",
        str(tmp_path / "out"),
        "--first-plane",
        "23",
        "--depth-step",
        "-1",
        "--crop",
        "0",
        "6",
        "0",
        "7",
        "--depth-order-note",
        "synthetic only",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "no inference run" in result.stdout
    np.testing.assert_array_equal(np.load(tmp_path / "out/planes.npy"), array[23:7:-1])
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode == 2
    assert "INPUT_PREPARATION_REFUSED" in result.stderr


def test_object_input_is_never_unpickled(tmp_path):
    path = tmp_path / "source.npy"
    np.save(path, np.array([{"bad": "object"}], dtype=object))
    with pytest.raises(ValueError):
        export(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()
