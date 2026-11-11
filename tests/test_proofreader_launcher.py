"""Verify the launcher/config contract without importing Napari or opening a GUI."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import zarr

from scripts import launch_proofreader as launcher


def _volumes(tmp_path, shape=(8, 16, 16), label_dtype="u1"):
    ct, labels = tmp_path / "ct.zarr", tmp_path / "labels.zarr"
    for path, dtype in ((ct, "u1"), (labels, label_dtype)):
        zarr.open(str(path), mode="w", shape=shape, dtype=dtype)
    return ct, labels


def _arguments(ct, labels):
    return ["--volume", str(ct), "--predictions", str(labels), "--patch-size", "8"]


@pytest.mark.parametrize("returncode", [0, 23])
def test_launch_from_another_directory_uses_valid_config_and_propagates_exit(
    tmp_path, monkeypatch, returncode
):
    ct, labels = _volumes(tmp_path)
    monkeypatch.chdir(tmp_path)
    previous = tmp_path / "proofreader_config.json"
    previous.write_text("unrelated existing config")
    configs = []

    def run(command, **kwargs):
        assert command[0] == sys.executable
        assert (
            Path(command[1])
            == launcher.ROOT / "villa/segmentation/vc_proofreader/main.py"
        )
        assert kwargs["cwd"] == launcher.ROOT
        config_path = Path(command[command.index("--config") + 1])
        configs.append(config_path)
        config = json.loads(config_path.read_text())
        assert config["patch_size"] == 8
        assert config["min_z"] == 0
        assert config["dataset_out_path"] == str(
            tmp_path / "local_data/Proofread_Patches"
        )
        assert config["volumes"]["Autoresearch_Prediction"] == {
            "volume_path": str(ct),
            "label_path": str(labels),
        }
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    assert launcher.main(_arguments(ct, labels)) == returncode
    assert previous.read_text() == "unrelated existing config"
    assert not configs[0].exists()


@pytest.mark.parametrize(
    "failure",
    ["shape", "float_labels", "patch_size", "overlap", "same_input", "existing_output"],
)
def test_invalid_handoffs_fail_without_launch_or_output(
    tmp_path, monkeypatch, capsys, failure
):
    ct, labels = _volumes(
        tmp_path, label_dtype="f4" if failure == "float_labels" else "u1"
    )
    monkeypatch.chdir(tmp_path)
    argv = _arguments(ct, labels)
    if failure == "shape":
        zarr.open(str(labels), mode="w", shape=(1, 16, 16), dtype="u1")
    elif failure == "patch_size":
        argv[-1] = "64"
    elif failure == "overlap":
        argv.extend(["--out-dir", str(ct / "patches")])
    elif failure == "same_input":
        argv[argv.index("--predictions") + 1] = str(ct)
    elif failure == "existing_output":
        output = tmp_path / "old_session"
        output.mkdir()
        (output / "progress.json").write_text("previous session")
        argv.extend(["--out-dir", str(output)])
    monkeypatch.setattr(
        launcher.subprocess, "run", lambda *a, **k: pytest.fail("GUI launched")
    )
    assert launcher.main(argv) == 1
    assert "Proofreader launch failed:" in capsys.readouterr().err
    assert not (tmp_path / "local_data").exists()


def test_help_does_not_load_scientific_or_gui_dependencies(tmp_path):
    result = subprocess.run(
        [sys.executable, "-S", str(Path(launcher.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "categorical" in result.stdout


@pytest.mark.parametrize(
    ("dtype", "values", "accepted"),
    [
        ("u2", [0, 255], True),
        ("u2", [256], False),
        ("u2", [300], False),
        ("u2", [65535], False),
        ("i2", [-1], False),
        ("i2", [-32768], False),
        ("i2", [0, 255], True),
        ("u8", [2**64 - 1], False),
        ("u1", [0, 255], True),
        ("b1", [False, True], True),
    ],
)
def test_label_range_is_lossless_before_launch_and_preserves_inputs(
    tmp_path, monkeypatch, capsys, dtype, values, accepted
):
    ct, labels = _volumes(tmp_path, shape=(66, 8, 8), label_dtype=dtype)
    array = zarr.open(str(labels), mode="r+")
    array[0, 0, 0] = values[0]
    array[-1, -1, -1] = values[-1]  # Beyond the first bounded scan block.
    before_values = array[:]
    before = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    launched = []

    def run(command, **kwargs):
        launched.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    monkeypatch.chdir(tmp_path)
    assert launcher.main(_arguments(ct, labels)) == (0 if accepted else 1)
    assert len(launched) == int(accepted)
    if not accepted:
        assert "0..255" in capsys.readouterr().err
    np.testing.assert_array_equal(zarr.open(str(labels), mode="r")[:], before_values)
    assert {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_label_range_checks_every_axis_with_bounded_reads(tmp_path, monkeypatch, axis):
    from volume_cartographer_wrapper.volume import FastLocalVolume

    shape = [8, 8, 8]
    shape[axis] = 66
    ct, labels = _volumes(tmp_path, shape=tuple(shape), label_dtype="u2")
    zarr.open(str(labels), mode="r+")[-1, -1, -1] = 300
    before = zarr.open(str(labels), mode="r")[:]
    reads = []
    original = FastLocalVolume.get_chunk

    def read(self, z, y, x, depth, height, width):
        reads.append(((z, y, x), (depth, height, width)))
        assert max(depth, height, width) <= 64
        return original(self, z, y, x, depth, height, width)

    monkeypatch.setattr(FastLocalVolume, "get_chunk", read)
    with pytest.raises(ValueError, match="0..255"):
        launcher._inputs(ct, labels, tmp_path / "out", 8)
    assert any(origin[axis] == 64 for origin, _ in reads)
    np.testing.assert_array_equal(zarr.open(str(labels), mode="r")[:], before)
