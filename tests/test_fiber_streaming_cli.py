"""A tiled filter must not transfer the entire volume or corrupt its artifacts."""

import errno
import io
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vesuvius_autoresearch.core.file_modes import current_umask
from vesuvius_autoresearch.fibers import cli, detection, streaming


def arguments(source, output, *extra):
    return ["--input", str(source), "--output", str(output), "--device", "cpu", *extra]


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "ct.npy"
    np.save(path, np.random.default_rng(4).random((19, 23, 29)).astype(np.float32))
    return path


@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("role", ["output", "preview"])
def test_input_aliases_fail_before_filtering(
    source, tmp_path, monkeypatch, alias, role
):
    original = source.read_bytes()
    alias_path = source
    if alias != "direct":
        alias_path = tmp_path / f"alias_{role}.npy"
        if alias == "symlink":
            alias_path.symlink_to(source)
        else:
            os.link(source, alias_path)
    output = alias_path if role == "output" else tmp_path / "response.npy"
    extra = ["--preview", str(alias_path)] if role == "preview" else []
    monkeypatch.setattr(cli, "_backend", lambda *args: pytest.fail("allocated backend"))
    with pytest.raises(ValueError, match="collision|symlink"):
        cli.main(arguments(source, output, *extra))
    assert source.read_bytes() == original


def test_response_and_preview_cannot_share_an_output(source, tmp_path, monkeypatch):
    output = tmp_path / "result.npy"
    monkeypatch.setattr(cli, "_backend", lambda *args: pytest.fail("allocated backend"))
    with pytest.raises(ValueError, match="collision"):
        cli.main(arguments(source, output, "--preview", str(output)))
    assert not output.exists()


def test_exact_output_name_does_not_get_a_hidden_numpy_suffix(source, tmp_path):
    output = tmp_path / "response.exact"
    assert cli.main(arguments(source, output)) == 0
    assert output.is_file() and not output.with_suffix(".exact.npy").exists()
    np.testing.assert_allclose(
        np.load(output),
        detection.detect_vesselness(np.load(source)),
        atol=1e-7,
    )


def test_failed_numpy_serialization_preserves_previous_output(
    source, tmp_path, monkeypatch
):
    output = tmp_path / "response.npy"
    output.write_bytes(b"previous complete array")

    def fail(stream, *args, **kwargs):
        stream.write(b"partial array")
        raise OSError("disk full")

    monkeypatch.setattr(np.lib.format, "write_array", fail)
    with pytest.raises(OSError, match="disk full"):
        cli.main(arguments(source, output))
    assert output.read_bytes() == b"previous complete array"


@pytest.mark.parametrize("filter_name", ["ridges", "vesselness"])
@pytest.mark.parametrize("dtype", [np.uint16, np.float32, np.float64])
def test_streaming_matches_existing_tiled_filter(tmp_path, filter_name, dtype):
    rng = np.random.default_rng(42)
    raw = rng.integers(0, 60000, (21, 25, 29)).astype(dtype)
    source = tmp_path / "ct.npy"
    output = tmp_path / "response.npy"
    np.save(source, raw)
    reference = getattr(detection, f"detect_{filter_name}_tiled")(
        raw,
        block_size=8,
        halo=10,
    ).astype(np.float32)
    before = source.read_bytes()
    assert (
        cli.main(
            arguments(
                source,
                output,
                "--filter",
                filter_name,
                "--tiled",
                "--block-size",
                "8",
                "--halo",
                "10",
            )
        )
        == 0
    )
    result = np.load(output)
    assert result.shape == raw.shape and result.dtype == np.float32
    np.testing.assert_array_equal(result, reference)
    reference_file = tmp_path / "reference.npy"
    np.save(reference_file, reference, allow_pickle=False)
    assert output.read_bytes() == reference_file.read_bytes()
    assert source.read_bytes() == before


def test_tiled_transfer_is_bounded_by_halo_blocks(source, tmp_path, monkeypatch):
    shape = (29, 31, 33)
    np.save(source, np.ones(shape, np.float32))
    calls = []

    def transfer(volume):
        calls.append(volume.shape)
        assert all(value <= 28 for value in volume.shape), "transferred the full volume"
        return np.asarray(volume)

    fake = SimpleNamespace(asarray=transfer, asnumpy=np.asarray)
    # Model a working GPU's transfer boundary; numeric filtering remains CPU.
    monkeypatch.setattr(
        cli, "_array_backend", lambda device: (fake, "gpu"), raising=False
    )
    monkeypatch.setattr(
        cli, "_backend", lambda *args: pytest.fail("used dense transfer")
    )
    output = tmp_path / "response.npy"
    assert (
        cli.main(
            arguments(
                source,
                output,
                "--tiled",
                "--block-size",
                "8",
                "--halo",
                "10",
            )
        )
        == 0
    )
    assert len(calls) == 2 * 4 * 4 * 5  # range pass, then filter pass
    assert shape not in calls
    np.testing.assert_array_equal(np.load(output), np.zeros(shape, np.float32))


def test_tiled_cli_memory_maps_input_and_output(source, tmp_path, monkeypatch):
    from vesuvius_autoresearch.fibers import streaming

    original = streaming.filter_into
    seen = []

    def inspect(volume, output, **kwargs):
        assert isinstance(volume, np.memmap) and volume.mode == "r"
        assert isinstance(output, np.memmap)
        seen.append(True)
        return original(volume, output, **kwargs)

    monkeypatch.setattr(streaming, "filter_into", inspect)
    assert cli.main(arguments(source, tmp_path / "out.npy", "--tiled")) == 0
    assert seen


def test_invalid_halo_fails_before_backend_allocation(source, tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli, "_backend", lambda *args: pytest.fail("allocated dense GPU")
    )
    monkeypatch.setattr(
        cli, "_array_backend", lambda *args: pytest.fail("probed GPU"), raising=False
    )
    with pytest.raises(ValueError, match="halo"):
        cli.main(arguments(source, tmp_path / "out.npy", "--tiled", "--halo", "1"))


@pytest.mark.parametrize("where", ["input", "filter response"])
def test_nonfinite_late_block_never_replaces_previous_output(
    source, tmp_path, monkeypatch, where
):
    volume = np.random.default_rng(5).random((31, 33, 35)).astype(np.float32)
    if where == "input":  # refused by the input check, before any block
        volume[-1, -1, -1] = np.nan
    else:  # every earlier block filters cleanly; the last one does not
        count = sum(1 for _ in streaming.blocks(volume.shape, 8, 16))
        calls, real = [], streaming.detect_vesselness

        def late_nan(block, **kwargs):
            calls.append(None)
            result = real(block, **kwargs)
            if len(calls) == count:
                result[...] = np.nan
            return result

        monkeypatch.setattr(streaming, "detect_vesselness", late_nan)
    np.save(source, volume)
    output = tmp_path / "out.npy"
    output.write_bytes(b"previous complete array")
    with pytest.raises(ValueError, match="finite"):
        cli.main(arguments(source, output, "--tiled", "--block-size", "8"))
    assert output.read_bytes() == b"previous complete array"


@pytest.mark.parametrize("tiled", [False, True])
@pytest.mark.parametrize("readonly", [False, True])
def test_preview_matches_the_published_response_and_permissions(
    source, tmp_path, tiled, readonly
):
    from matplotlib import pyplot as plt
    from PIL import Image

    output, preview = tmp_path / "array.exact", tmp_path / "image.exact"
    extra = ["--tiled", "--block-size", "8", "--halo", "10"] if tiled else []
    args = arguments(source, output, "--preview", str(preview), *extra)
    assert cli.main(args) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o666 & ~current_umask()
    assert stat.S_IMODE(preview.stat().st_mode) == 0o666 & ~current_umask()
    reference = io.BytesIO()
    plt.imsave(reference, np.load(output).mean(axis=0), cmap="magma", format="png")
    reference.seek(0)
    with Image.open(preview) as actual, Image.open(reference) as expected:
        assert actual.format == "PNG"
        np.testing.assert_array_equal(np.asarray(actual), np.asarray(expected))
    output_mode = 0o444 if readonly else 0o640
    preview_mode = 0o400 if readonly else 0o604
    output.chmod(output_mode)
    preview.chmod(preview_mode)
    assert cli.main(args) == 0
    assert stat.S_IMODE(output.stat().st_mode) == output_mode
    assert stat.S_IMODE(preview.stat().st_mode) == preview_mode
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "array.exact",
        "ct.npy",
        "image.exact",
    ]


def test_failed_preview_serialization_keeps_both_previous_artifacts(
    source, tmp_path, monkeypatch
):
    from vesuvius_autoresearch.fibers import filter_artifacts

    output, preview = tmp_path / "array.npy", tmp_path / "preview.png"
    output.write_bytes(b"old complete response")
    preview.write_bytes(b"old complete preview")

    def fail(path, projection):
        path.write_bytes(b"partial PNG")
        raise OSError("preview save failed")

    monkeypatch.setattr(filter_artifacts, "write_preview", fail)
    with pytest.raises(OSError, match="preview save failed"):
        cli.main(arguments(source, output, "--preview", str(preview), "--tiled"))
    assert output.read_bytes() == b"old complete response"
    assert preview.read_bytes() == b"old complete preview"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "array.npy",
        "ct.npy",
        "preview.png",
    ]


@pytest.mark.parametrize("failure", ["response", "preview"])
def test_publication_failure_cannot_leave_the_old_requested_preview(
    source, tmp_path, monkeypatch, failure
):
    from vesuvius_autoresearch.fibers import filter_artifacts

    output, preview = tmp_path / "array.npy", tmp_path / "preview.png"
    output.write_bytes(b"old response")
    preview.write_bytes(b"old preview")
    replace = filter_artifacts.os.replace

    def fail(src, dst):
        if Path(dst) == (output if failure == "response" else preview):
            raise OSError("rename failed")
        return replace(src, dst)

    monkeypatch.setattr(filter_artifacts.os, "replace", fail)
    with pytest.raises(OSError, match="rename failed"):
        cli.main(arguments(source, output, "--preview", str(preview), "--tiled"))
    assert not preview.exists()
    if failure == "response":
        assert output.read_bytes() == b"old response"
    else:
        assert np.load(output).shape == np.load(source).shape
    assert sorted(path.name for path in tmp_path.iterdir()) == ["array.npy", "ct.npy"]


def test_source_changes_refuse_publication(source, tmp_path, monkeypatch):
    from vesuvius_autoresearch.fibers import streaming

    output = tmp_path / "out.npy"
    output.write_bytes(b"old response")
    original = streaming.filter_into

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        info = source.stat()
        os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
        return result

    monkeypatch.setattr(streaming, "filter_into", changed)
    with pytest.raises(ValueError, match="input CT changed"):
        cli.main(arguments(source, output, "--tiled"))
    assert output.read_bytes() == b"old response"


@pytest.mark.parametrize("role", ["response", "preview"])
def test_output_aliases_created_during_filtering_are_rechecked(
    source, tmp_path, monkeypatch, role
):
    from vesuvius_autoresearch.fibers import streaming

    output, preview = tmp_path / "out.npy", tmp_path / "preview.png"
    before = source.read_bytes()
    original = streaming.filter_into

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        (output if role == "response" else preview).symlink_to(source)
        return result

    monkeypatch.setattr(streaming, "filter_into", changed)
    with pytest.raises(ValueError, match="symlink|collision"):
        cli.main(arguments(source, output, "--preview", str(preview), "--tiled"))
    assert source.read_bytes() == before


@pytest.mark.parametrize("kind", ["directory", "fifo", "broken_symlink"])
@pytest.mark.parametrize("role", ["response", "preview"])
def test_nonregular_outputs_fail_before_device_resolution(
    source, tmp_path, monkeypatch, kind, role
):
    invalid = tmp_path / "invalid"
    if kind == "directory":
        invalid.mkdir()
    elif kind == "fifo":
        os.mkfifo(invalid)
    else:
        invalid.symlink_to(tmp_path / "absent")
    monkeypatch.setattr(cli, "_array_backend", lambda *args: pytest.fail("probed GPU"))
    output = invalid if role == "response" else tmp_path / "out.npy"
    preview = invalid if role == "preview" else tmp_path / "preview.png"
    with pytest.raises(ValueError, match="regular file|symlink"):
        cli.main(arguments(source, output, "--preview", str(preview), "--tiled"))


def test_tiled_allocation_failure_is_not_retried_on_cpu(source, tmp_path, monkeypatch):
    output = tmp_path / "out.npy"
    output.write_bytes(b"old response")
    calls = []

    def fail(volume):
        calls.append(volume.shape)
        raise MemoryError("GPU out of memory")

    fake = SimpleNamespace(asarray=fail, asnumpy=np.asarray)
    monkeypatch.setattr(cli, "_array_backend", lambda *args: (fake, "gpu"))
    with pytest.raises(MemoryError, match="GPU out of memory"):
        cli.main(arguments(source, output, "--tiled"))
    assert len(calls) == 1
    assert output.read_bytes() == b"old response"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["ct.npy", "out.npy"]


def test_fortran_order_streaming_preserves_the_response(source, tmp_path):
    volume = np.asfortranarray(np.load(source))
    np.save(source, volume)
    output = tmp_path / "out.npy"
    assert (
        cli.main(
            arguments(source, output, "--tiled", "--block-size", "8", "--halo", "10")
        )
        == 0
    )
    expected = detection.detect_vesselness_tiled(volume, block_size=8, halo=10).astype(
        np.float32
    )
    np.testing.assert_array_equal(np.load(output), expected)


def test_output_reservation_failure_happens_before_device_transfer(
    source, tmp_path, monkeypatch
):
    from vesuvius_autoresearch.fibers import filter_artifacts

    output = tmp_path / "out.npy"
    output.write_bytes(b"old response")

    def fail(*args):
        raise OSError(errno.ENOSPC, "disk full")

    fake = SimpleNamespace(
        asarray=lambda *args: pytest.fail("transferred a block"),
        asnumpy=np.asarray,
    )
    monkeypatch.setattr(cli, "_array_backend", lambda *args: (fake, "gpu"))
    monkeypatch.setattr(filter_artifacts.os, "posix_fallocate", fail, raising=False)
    with pytest.raises(OSError, match="disk full"):
        cli.main(arguments(source, output, "--tiled"))
    assert output.read_bytes() == b"old response"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["ct.npy", "out.npy"]


def test_unsupported_reservation_keeps_filesystem_compatibility(
    source, tmp_path, monkeypatch
):
    from vesuvius_autoresearch.fibers import filter_artifacts

    def unsupported(*args):
        raise OSError(errno.EOPNOTSUPP, "not supported")

    monkeypatch.setattr(
        filter_artifacts.os, "posix_fallocate", unsupported, raising=False
    )
    output = tmp_path / "out.npy"
    assert cli.main(arguments(source, output, "--tiled")) == 0
    assert np.isfinite(np.load(output)).all()
