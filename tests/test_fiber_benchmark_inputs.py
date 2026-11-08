"""Bounded NPY capture preserves the bytes and integer IDs actually scored."""

import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import bench_cli
from vesuvius_autoresearch.fibers.benchmark_artifacts import read_instances


@pytest.mark.parametrize("version", [(1, 0), (2, 0), (3, 0)])
@pytest.mark.parametrize("layout", ["C", "F"])
@pytest.mark.parametrize("dtype", ["<u8", ">u8"])
def test_capture_preserves_npy_versions_layout_byte_order_and_large_ids(
    tmp_path, version, layout, dtype
):
    expected = (np.arange(72, dtype=np.uint64).reshape(3, 3, 8) + 2**63).astype(dtype)
    expected = np.array(expected, order=layout)
    stream = io.BytesIO()
    np.lib.format.write_array(stream, expected, version=version, allow_pickle=False)
    raw = stream.getvalue()
    source = tmp_path / "instances.npy"
    source.write_bytes(raw)
    actual, identity = read_instances(source, expected.shape)
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype.str == expected.dtype.str
    assert not actual.flags.writeable
    assert actual.flags.f_contiguous == expected.flags.f_contiguous
    assert identity["instances_sha256"] == hashlib.sha256(raw).hexdigest()
    assert identity["instances_size_bytes"] == len(raw)


@pytest.mark.parametrize(
    "kind",
    ["negative", "float", "object", "structured", "truncated", "trailing", "npz"],
)
def test_invalid_instance_capture_is_rejected(tmp_path, kind):
    source = tmp_path / "instances.npy"
    value = np.ones((3, 3, 8), np.int32)
    if kind == "negative":
        value[0, 0, 0] = -1
    elif kind == "float":
        value = value.astype(np.float32)
    elif kind == "object":
        value = value.astype(object)
    elif kind == "structured":
        value = np.ones(value.shape, dtype=[("id", "u4")])
    with source.open("wb") as stream:
        if kind == "npz":
            np.savez(stream, labels=value)
        else:
            np.save(stream, value)
    if kind == "truncated":
        source.write_bytes(source.read_bytes()[:-1])
    elif kind == "trailing":
        source.write_bytes(source.read_bytes() + b"trailing")
    with pytest.raises(ValueError):
        read_instances(source, value.shape)


def test_boolean_shape_is_not_an_integer_array_dimension(tmp_path):
    source = tmp_path / "instances.npy"
    with source.open("wb") as stream:
        np.lib.format.write_array_header_1_0(
            stream, {"shape": (True, 3, 8), "fortran_order": False, "descr": "|u1"}
        )
        stream.write(bytes(24))
    with pytest.raises(ValueError, match="shape"):
        read_instances(source, (1, 3, 8))


def test_declared_giant_array_cannot_trigger_an_allocation(tmp_path, monkeypatch):
    source = tmp_path / "instances.npy"
    shape = (10**12, 1, 1)
    with source.open("wb") as stream:
        np.lib.format.write_array_header_1_0(
            stream, {"shape": shape, "fortran_order": False, "descr": "|u1"}
        )
        stream.write(b"x")
    monkeypatch.setattr(np, "frombuffer", lambda *a, **k: pytest.fail("array exposed"))
    with pytest.raises(ValueError, match="payload size"):
        read_instances(source, shape)


@pytest.mark.parametrize("kind", ["oversize", "fifo", "directory"])
def test_capture_refuses_oversize_or_nonregular_sources(tmp_path, kind):
    source = tmp_path / "input"
    if kind == "oversize":
        source.write_bytes(b"too many bytes")
    elif kind == "fifo":
        os.mkfifo(source)
    else:
        source.mkdir()
    with pytest.raises(ValueError, match="exceeds|regular file"):
        read_instances(source, (3, 3, 8), limit=1)


@pytest.mark.parametrize("value", ["0", "-1", str(sys.maxsize)])
def test_bad_byte_limits_are_usage_errors_before_data(tmp_path, monkeypatch, value):
    monkeypatch.setattr(bench_cli, "_load_cube", lambda *a: pytest.fail("data loaded"))
    with pytest.raises(SystemExit) as exc:
        bench_cli.main(
            [
                "score",
                "--cube",
                "cube",
                "--instances",
                str(tmp_path / "missing.npy"),
                "--max-instance-bytes",
                value,
            ]
        )
    assert exc.value.code == 2


def test_snapshot_capture_remains_usable_without_an_editable_install(tmp_path):
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "source").write_text("captured")
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); from scripts.text_snapshot import capture_bytes; print(capture_bytes(sys.argv[2], 16)[1].decode())",
            str(root),
            str(tmp_path / "source"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    assert result.stdout.strip() == "captured"


def test_cli_collision_has_a_concise_error_before_reading_cube_inputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "labels.npy"
    np.save(source, np.ones((3, 3, 8), np.uint8))
    original = source.read_bytes()
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vesuvius_autoresearch.fibers.bench_cli",
            "--data-dir",
            str(tmp_path),
            "score",
            "--cube",
            "cube",
            "--instances",
            str(source),
            "--json-out",
            str(source),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Fiber benchmark failed: artifact collision" in result.stderr
    assert "Traceback" not in result.stderr
    assert source.read_bytes() == original


@pytest.mark.parametrize("shape", [(3, 3, 9), (3, 8, 3), (1, 3, 3, 8)])
def test_instances_must_have_the_cubes_own_shape(tmp_path, shape):
    # A well-formed NPY for another cube is still the wrong input. Before #378,
    # `score` refused a shape mismatch; the capture must keep refusing it.
    source = tmp_path / "instances.npy"
    np.save(source, np.ones((3, 3, 8), np.int32))
    with pytest.raises(ValueError, match="must match cube shape"):
        read_instances(source, shape)
