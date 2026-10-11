"""Volume reads and their timings must refer to an explicit, valid workload."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import zarr

from scripts import benchmark_volume_cartographer as bench
from volume_cartographer_wrapper.volume import (
    FastLocalVolume,
    VolumeCartographerUnavailable,
)

REPO = Path(__file__).resolve().parents[1]


def volume(tmp_path, *, shape=(4, 6, 8), chunks=(2, 3, 4), name="source.zarr"):
    path = tmp_path / name
    data = np.arange(np.prod(shape), dtype=np.uint16).reshape(shape)
    array = zarr.open(str(path), mode="w", shape=shape, chunks=chunks, dtype=data.dtype)
    array[:] = data
    return path, data


@pytest.mark.parametrize(
    "arguments",
    [
        (-1, 0, 0),
        (0, -1, 0),
        (True, 0, 0),
        (0, 1.9, 0),
        (2, 0, 0),
        (0, 100, 0),
        (0, 0, 999),
        (-1, 0, 0, 1, 1, 1),
        (True, 0, 0, 1, 1, 1),
        (0, 0.9, 0, 1, 1, 1),
        (4, 0, 0, 1, 1, 1),
        (0, 0, 0, 0, 1, 1),
        (0, 0, 0, -1, 1, 1),
        (0, 0, 0, True, 1, 1),
        (0, 0, 0, 1.9, 1, 1),
    ],
)
def test_invalid_read_requests_fail_before_payload_read(
    tmp_path, arguments, monkeypatch
):
    path, _ = volume(tmp_path)
    source = FastLocalVolume(path)

    class Forbidden:
        def __getitem__(self, key):
            pytest.fail("invalid request reached payload decoding")

    monkeypatch.setattr(source, "_zarr", Forbidden())
    with pytest.raises(ValueError):
        source.get_chunk(*arguments)


@pytest.mark.parametrize("shape", [(4, 6), (1, 4, 6, 8), (0, 6, 8)])
def test_nonvolume_arrays_are_rejected_at_open(tmp_path, shape):
    path = tmp_path / "bad.zarr"
    zarr.open(str(path), mode="w", shape=shape, dtype="uint16")
    with pytest.raises(ValueError):
        FastLocalVolume(path)


def test_compact_metadata_preserves_actual_chunk_separator(tmp_path):
    path = tmp_path / "nested.zarr"
    zarr.open(
        str(path),
        mode="w",
        shape=(4, 6, 8),
        chunks=(2, 3, 4),
        dtype="uint16",
        dimension_separator="/",
    )
    metadata = path / ".zarray"
    metadata.write_text(
        json.dumps(json.loads(metadata.read_text()), separators=(",", ":"))
    )
    assert FastLocalVolume(path).sep == "/"


def test_percent_encoded_file_uri_opens_the_actual_local_path(tmp_path):
    path, data = volume(tmp_path, name="scan with spaces.zarr")
    source = FastLocalVolume(path.as_uri())
    np.testing.assert_array_equal(source.get_chunk(0, 0, 0, 2, 3, 4), data[:2, :3, :4])


def test_remote_file_authority_is_not_silently_treated_as_local(tmp_path):
    path, _ = volume(tmp_path)
    with pytest.raises(VolumeCartographerUnavailable):
        FastLocalVolume(f"file://another-host{path}")


def test_valid_edge_chunks_and_voxel_clipping_are_explicit(tmp_path):
    path, data = volume(tmp_path, shape=(5, 7, 9))
    source = FastLocalVolume(path)
    np.testing.assert_array_equal(source.get_chunk(2, 2, 2), data[4:, 6:, 8:])
    np.testing.assert_array_equal(
        source.get_chunk(3, 5, 7, 100, 100, 100), data[3:, 5:, 7:]
    )
    np.testing.assert_array_equal(
        source.get_chunk(np.int64(1), np.int64(1), np.int64(1)), data[2:4, 3:6, 4:8]
    )
    assert source.dtype == data.dtype


@pytest.mark.parametrize(
    "argument",
    [
        (float("nan"), 0, 0),
        (float("inf"), 0, 0),
        ("1", 0, 0),
        (0, 0, 0, 1, None, 1),
        (10**100, 0, 0),
    ],
)
def test_invalid_scalar_values_are_refused(tmp_path, argument):
    path, _ = volume(tmp_path)
    with pytest.raises(ValueError):
        FastLocalVolume(path).get_chunk(*argument)


@pytest.mark.parametrize("kind", ["empty_group", "wrong_level", "complex", "text"])
def test_wrong_volume_kinds_are_refused(tmp_path, kind):
    path = tmp_path / "bad.zarr"
    if kind in {"empty_group", "wrong_level"}:
        group = zarr.open_group(str(path), mode="w")
        if kind == "wrong_level":
            group.create_dataset("1", shape=(4, 6, 8), dtype="uint8")
    else:
        zarr.open(
            str(path),
            mode="w",
            shape=(4, 6, 8),
            dtype="complex64" if kind == "complex" else "S4",
        )
    with pytest.raises(ValueError):
        FastLocalVolume(path)


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.invalid/volume.zarr",
        "s3://bucket/data",
        "file:relative",
        "ftp://example.invalid/data",
    ],
)
def test_nonlocal_and_relative_uris_are_refused(uri):
    with pytest.raises(VolumeCartographerUnavailable):
        FastLocalVolume(uri)


def test_group_zero_and_localhost_file_uri_are_explicit(tmp_path):
    path = tmp_path / "root.zarr"
    data = np.arange(192, dtype=np.uint16).reshape(4, 6, 8)
    group = zarr.open_group(str(path), mode="w")
    group.create_dataset("0", data=data, chunks=(2, 3, 4))
    source = FastLocalVolume(f"file://localhost{path}")
    assert source.source_path == path
    assert source.path == path / "0"
    np.testing.assert_array_equal(source.get_chunk(1, 1, 1), data[2:4, 3:6, 4:8])


def test_benchmark_measures_identical_requested_values_and_records_limits(tmp_path):
    path, data = volume(tmp_path)
    report = bench.benchmark(
        path, origin_zyx=(1, 2, 3), shape_zyx=(2, 3, 4), iterations=4, warmup=1
    )
    assert report["shape_zyx"] == [2, 3, 4]
    assert report["origin_zyx"] == [1, 2, 3]
    assert (
        report["payload_sha256"]
        == hashlib.sha256(data[1:3, 2:5, 3:7].tobytes()).hexdigest()
    )
    assert report["bytes_per_read"] == 48
    assert report["backend"] == "volume-cartographer-zarr"
    assert report["native_volume_cartographer_measured"] is False
    for result in report["timings"].values():
        assert len(result["samples_ns"]) == 4
        assert 0 < result["min_ns"] <= result["median_ns"] <= result["max_ns"]
    assert (
        report["direct_over_wrapper_median_ratio"]
        == report["timings"]["direct_zarr"]["median_ns"]
        / report["timings"]["wrapper_zarr"]["median_ns"]
    )
    assert np.isfinite(report["direct_over_wrapper_median_ratio"])


@pytest.mark.parametrize(
    "change",
    [
        {"origin_zyx": (-1, 0, 0)},
        {"origin_zyx": (0.5, 0, 0)},
        {"origin_zyx": (0, 0)},
        {"shape_zyx": (0, 1, 1)},
        {"shape_zyx": (100, 1, 1)},
        {"iterations": 1},
        {"iterations": 3},
        {"iterations": True},
        {"iterations": 1002},
        {"warmup": -1},
        {"warmup": 1001},
        {"max_read_bytes": 47},
        {"max_read_bytes": False},
    ],
)
def test_invalid_benchmark_settings_never_read_payload(tmp_path, monkeypatch, change):
    path, _ = volume(tmp_path)
    args = {
        "origin_zyx": (1, 2, 3),
        "shape_zyx": (2, 3, 4),
        "iterations": 4,
        "warmup": 0,
        **change,
    }

    def forbidden(*args, **kwargs):
        pytest.fail("invalid benchmark reached payload decoding")

    monkeypatch.setattr(zarr.Array, "__getitem__", forbidden)
    with pytest.raises(ValueError):
        bench.benchmark(path, **args)


@pytest.mark.parametrize(
    "failure",
    ["wrong_shape", "wrong_dtype", "different_values", "read_error", "source_mutation"],
)
def test_invalid_benchmark_reads_cannot_produce_a_report(
    tmp_path, monkeypatch, failure
):
    path, _ = volume(tmp_path)
    original = FastLocalVolume.get_chunk
    calls = 0

    def altered(self, *args):
        nonlocal calls
        calls += 1
        result = original(self, *args)
        if failure == "wrong_shape":
            return result[:1]
        if failure == "wrong_dtype":
            return result.astype(np.float32)
        if failure == "different_values":
            return result + 1
        if failure == "read_error":
            raise OSError("controlled read failure")
        if calls == 1:
            writable = zarr.open(str(path), mode="r+")
            writable[1, 2, 3] += 1
        return result

    monkeypatch.setattr(FastLocalVolume, "get_chunk", altered)
    with pytest.raises((OSError, ValueError)):
        bench.benchmark(
            path, origin_zyx=(1, 2, 3), shape_zyx=(2, 3, 4), iterations=4, warmup=0
        )


def test_benchmark_balances_order_and_keeps_validation_outside_timing(
    tmp_path, monkeypatch
):
    path, _ = volume(tmp_path)
    calls, durations = [], []
    original_getitem, original_chunk = zarr.Array.__getitem__, FastLocalVolume.get_chunk
    inside_wrapper = False

    def chunk(self, *args):
        nonlocal inside_wrapper
        inside_wrapper = True
        calls.append("wrapper_zarr")
        try:
            return original_chunk(self, *args)
        finally:
            inside_wrapper = False

    def direct(self, key):
        if not inside_wrapper:
            calls.append("direct_zarr")
        return original_getitem(self, key)

    clock = iter(range(0, 10000, 10))
    monkeypatch.setattr(bench.time, "perf_counter_ns", lambda: next(clock))
    monkeypatch.setattr(zarr.Array, "__getitem__", direct)
    monkeypatch.setattr(FastLocalVolume, "get_chunk", chunk)
    original_hash = bench.hashlib.sha256

    def expensive_hash(*args, **kwargs):
        # A deterministic simulated verification cost must not enter read times.
        next(clock)
        return original_hash(*args, **kwargs)

    monkeypatch.setattr(bench.hashlib, "sha256", expensive_hash)
    report = bench.benchmark(
        path, origin_zyx=(1, 2, 3), shape_zyx=(2, 3, 4), iterations=4, warmup=1
    )
    assert calls == [
        "direct_zarr",
        "wrapper_zarr",
        "wrapper_zarr",
        "direct_zarr",
        "direct_zarr",
        "wrapper_zarr",
        "wrapper_zarr",
        "direct_zarr",
        "direct_zarr",
        "wrapper_zarr",
    ]
    assert all(value["samples_ns"] == [10] * 4 for value in report["timings"].values())
    assert report["initialization_ns"] == {"direct_zarr": 10, "wrapper_zarr": 10}


def test_zero_duration_does_not_become_an_infinite_ratio(tmp_path, monkeypatch):
    path, _ = volume(tmp_path)
    monkeypatch.setattr(bench.time, "perf_counter_ns", lambda: 0)
    with pytest.raises(ValueError, match="positive duration"):
        bench.benchmark(path, origin_zyx=(1, 2, 3), shape_zyx=(2, 3, 4))


def cli_args(source, output):
    return [
        "--input",
        str(source),
        "--shape-zyx",
        "2",
        "3",
        "4",
        "--iterations",
        "4",
        "--warmup",
        "0",
        "--output",
        str(output),
    ]


def test_actual_cli_runs_outside_checkout_and_publishes_a_real_report(tmp_path):
    path, _ = volume(tmp_path)
    output = tmp_path / "timings.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/benchmark_volume_cartographer.py"),
            *cli_args(path, output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == json.loads(output.read_text())
    assert json.loads(output.read_text())["source"] == str(path)


@pytest.mark.parametrize(
    "where", ["source_array", "source_group", "existing", "broken_link", "wrong_suffix"]
)
def test_invalid_report_destinations_are_preserved(tmp_path, where):
    path, _ = volume(tmp_path)
    output = tmp_path / "timings.json"
    if where == "source_array":
        output = path / "timings.json"
    elif where == "source_group":
        group = tmp_path / "group.zarr"
        group.mkdir()
        path.rename(group / "0")
        path = group
        output = path / "timings.json"
    elif where == "existing":
        output.write_text("prior result")
    elif where == "broken_link":
        output.symlink_to(tmp_path / "absent")
    else:
        output = tmp_path / "timings.txt"
    assert bench.main(cli_args(path, output)) == 1
    if where == "existing":
        assert output.read_text() == "prior result"
    elif where == "broken_link":
        assert output.is_symlink()
    else:
        assert not output.exists()


def test_failed_report_write_cleans_up_staging(tmp_path, monkeypatch):
    path, _ = volume(tmp_path)
    output = tmp_path / "timings.json"

    def fail(*args, **kwargs):
        raise OSError("controlled publication failure")

    monkeypatch.setattr(Path, "write_text", fail)
    assert bench.main(cli_args(path, output)) == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".timings-*"))


def test_missing_source_is_an_explicit_cli_failure_and_help_is_usable(tmp_path):
    output = tmp_path / "timings.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/benchmark_volume_cartographer.py"),
            *cli_args(tmp_path / "absent", output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Volume-read benchmark failed" in result.stderr
    assert not output.exists()
    assert not result.stdout
    help_result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/benchmark_volume_cartographer.py"),
            "--help",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0
