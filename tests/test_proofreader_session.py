"""Input receipts and actual pinned progress JSON, without importing GUI code."""

import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import zarr

from scripts import check_proofreader_session as check, launch_proofreader as launcher
from vesuvius_autoresearch.core import proofreader_session as sessions

PROOFREADER = launcher.ROOT / "villa/segmentation/vc_proofreader/main.py"


@pytest.fixture
def inputs(tmp_path):
    ct, labels = tmp_path / "ct.zarr", tmp_path / "labels.zarr"
    for path, dtype in ((ct, "u2"), (labels, "u1")):
        array = zarr.open(
            str(path), mode="w", shape=(8, 16, 16), chunks=(4, 8, 8), dtype=dtype
        )
        array[:] = 7 if path == ct else 1
    return ct, labels, tmp_path / "session"


def _launch(inputs, monkeypatch, child=None, extra=(), returncode=0):
    ct, labels, out = inputs
    configs = []

    def run(command, **kwargs):
        config = json.loads(Path(command[command.index("--config") + 1]).read_text())
        configs.append(config)
        if child:
            child(config)
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    result = launcher.main(
        [
            "--volume",
            str(ct),
            "--predictions",
            str(labels),
            "--patch-size",
            "8",
            "--out-dir",
            str(out),
            "--record-session",
            *extra,
        ]
    )
    return result, configs


def _pinned_progress(config):
    """Execute only pinned update_progress, using its real serializer unchanged."""
    root = Path(config["dataset_out_path"])
    root.mkdir(exist_ok=True)
    selected = config["volumes"]["Autoresearch_Prediction"]
    state = {
        "save_progress": True,
        "progress_file": config["progress_file"],
        "patch_size": config["patch_size"],
        "image_zarr": selected["volume_path"],
        "label_zarr": selected["label_path"],
        "image_volume": zarr.open(selected["volume_path"], mode="r"),
        "dataset_out_path": str(root),
        "images_out_dir": str(root / "imagesTr"),
        "labels_out_dir": str(root / "labelsTr"),
        "progress_log": [
            {
                "index": 0,
                "coords": (0, 0, 0),
                "percentage": 100.0,
                "status": "approved",
            },
            {"index": 1, "coords": (0, 0, 8), "percentage": 100.0, "status": "pending"},
        ],
    }
    node = next(
        n
        for n in ast.parse(PROOFREADER.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "update_progress"
    )
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {
        "state": state,
        "json": json,
        "datetime": datetime,
        "init_volume": SimpleNamespace(
            volume_selection=SimpleNamespace(value="Autoresearch_Prediction")
        ),
    }
    exec(compile(module, str(PROOFREADER), "exec"), namespace)
    namespace["update_progress"]()


def _all_bytes(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_pinned_progress_loader_accepts_wrong_source_but_checker_refuses(
    inputs, monkeypatch
):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["metadata"]["image_zarr"] = "/different/ct.zarr"
    path.write_text(json.dumps(progress))
    state = {"save_progress": True, "progress_file": str(path)}
    node = next(
        n
        for n in ast.parse(PROOFREADER.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "load_progress"
    )
    namespace = {"state": state, "json": json, "os": os}
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(PROOFREADER), "exec"),
        namespace,
    )
    namespace["load_progress"]()
    assert state["progress_log"] == progress["progress_log"]
    assert state["current_index"] == 2
    with pytest.raises(ValueError, match="context differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


def test_record_binds_actual_launch_and_verifies_actual_pinned_progress(
    inputs, monkeypatch
):
    before = [_all_bytes(path) for path in inputs[:2]]
    result, configs = _launch(inputs, monkeypatch, _pinned_progress)
    assert result == 0
    config = configs[0]
    record = json.loads((inputs[2] / sessions.RECORD_NAME).read_text())
    assert record["config"] == config
    assert config["progress_file"] == str(inputs[2] / "progress.json")
    assert config["output_label_zarr"] == str(inputs[2] / "edited_labels.zarr")
    all_before = _all_bytes(inputs[2].parent)
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["input_record_matches"]
    assert (
        report["input_record_sha256"]
        == hashlib.sha256((inputs[2] / sessions.RECORD_NAME).read_bytes()).hexdigest()
    )
    assert (
        report["progress"]["captured_sha256"]
        == hashlib.sha256((inputs[2] / "progress.json").read_bytes()).hexdigest()
    )
    assert report["progress"]["status_counts"] == {
        "approved": 1,
        "skipped": 0,
        "auto-skipped": 0,
        "pending": 1,
    }
    assert not report["resume_supported"]
    assert not report["approved_patch_files_verified"]
    assert not report["ink_training_ingestion_supported"]
    assert _all_bytes(inputs[2].parent) == all_before
    assert [_all_bytes(path) for path in inputs[:2]] == before


@pytest.mark.parametrize("returncode", [0, 23])
def test_receipt_is_an_initial_record_even_if_gui_has_no_progress(
    inputs, monkeypatch, returncode
):
    result, _ = _launch(inputs, monkeypatch, returncode=returncode)
    assert result == returncode
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["progress"] == {"present": False, "status_counts": None}
    assert "completion" not in json.loads(
        (inputs[2] / sessions.RECORD_NAME).read_text()
    )


def test_progress_hash_and_counts_use_the_same_captured_bytes(inputs, monkeypatch):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    before = path.read_bytes()
    original = sessions.capture_bytes

    def capture(source, limit):
        result = original(source, limit)
        if Path(source) == path:
            changed = json.loads(before)
            changed["progress_log"][0]["status"] = "skipped"
            path.write_text(json.dumps(changed))
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    report = sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)
    assert report["progress"]["captured_sha256"] == hashlib.sha256(before).hexdigest()
    assert (
        report["progress"]["captured_sha256"]
        != hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert report["progress"]["status_counts"]["approved"] == 1


@pytest.mark.parametrize("role", [0, 1])
@pytest.mark.parametrize("change", ["chunk", "metadata", "add", "remove"])
def test_changed_source_bytes_or_inventory_refuse_verification(
    inputs, monkeypatch, role, change
):
    assert _launch(inputs, monkeypatch)[0] == 0
    root = inputs[role]
    if change == "chunk":
        zarr.open(str(root), mode="r+")[0, 0, 0] = 19
    elif change == "metadata":
        zarr.open(str(root), mode="r+").attrs["origin"] = [1, 2, 3]
    elif change == "add":
        (root / "new_metadata").write_text("new")
    else:
        (root / "0.0.0").unlink()
    with pytest.raises(ValueError, match="source differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("patch_size", 4),
        ("image_zarr", "/other.zarr"),
        ("volume_shape", [8, 16, 15]),
        ("coordinate_system", "other"),
        ("dataset_out_path", "/other"),
    ],
)
def test_wrong_progress_context_is_not_accepted(inputs, monkeypatch, field, value):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["metadata"][field] = value
    path.write_text(json.dumps(progress))
    with pytest.raises(ValueError, match="context differs"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("coords", [-1, 0, 0]),
        ("coords", [0, 0, 16]),
        ("index", True),
        ("index", 4),
        ("percentage", 101),
        ("status", "unknown"),
    ],
)
def test_invalid_progress_entries_fail_closed(inputs, monkeypatch, field, value):
    assert _launch(inputs, monkeypatch, _pinned_progress)[0] == 0
    path = inputs[2] / "progress.json"
    progress = json.loads(path.read_text())
    progress["progress_log"][0][field] = value
    path.write_text(json.dumps(progress))
    with pytest.raises(ValueError, match="invalid proofreader progress"):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "extra",
    [
        ("--max-source-bytes", "1"),
        ("--max-file-bytes", "1"),
        ("--max-entries", "1"),
        ("--max-entries", "0"),
    ],
)
def test_source_budgets_fail_before_receipt_or_gui(inputs, monkeypatch, extra):
    result, configs = _launch(inputs, monkeypatch, extra=extra)
    assert result == 1 and not configs and not inputs[2].exists()


@pytest.mark.parametrize("kind", ["symlink", "directory_link", "hardlink", "fifo"])
def test_links_and_special_sources_are_not_followed(inputs, monkeypatch, kind):
    ct, _, out = inputs
    target = ct / "extra"
    if kind == "symlink":
        target.symlink_to(ct / "0.0.0")
    elif kind == "directory_link":
        target.symlink_to(inputs[1], target_is_directory=True)
    elif kind == "hardlink":
        os.link(ct / "0.0.0", target)
    elif not hasattr(os, "mkfifo"):
        pytest.skip("FIFO unavailable")
    else:
        os.mkfifo(target)
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and not out.exists()


def test_source_change_during_capture_refuses_publication(inputs, monkeypatch):
    original = sessions.capture_bytes

    def capture(path, limit):
        result = original(path, limit)
        if Path(path) == inputs[0] / ".zarray":
            (inputs[0] / "new").write_text("mutation")
        return result

    monkeypatch.setattr(sessions, "capture_bytes", capture)
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and not inputs[2].exists()


def test_record_cannot_raise_checker_limits_or_change_pinned_code(
    inputs, monkeypatch, tmp_path
):
    assert _launch(inputs, monkeypatch)[0] == 0
    with pytest.raises(ValueError, match="max_source_bytes"):
        sessions.verify_record(
            inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS | {"max_source_bytes": 1}
        )
    other = tmp_path / "other.py"
    other.write_text("# changed source")
    with pytest.raises(ValueError, match="pinned proofreader source differs"):
        sessions.verify_record(inputs[2], other, sessions.DEFAULT_LIMITS)


@pytest.mark.parametrize(
    "replacement",
    ['{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}', "[]"],
)
def test_malformed_receipt_is_rejected(inputs, monkeypatch, replacement):
    assert _launch(inputs, monkeypatch)[0] == 0
    (inputs[2] / sessions.RECORD_NAME).write_text(replacement)
    with pytest.raises(ValueError):
        sessions.verify_record(inputs[2], PROOFREADER, sessions.DEFAULT_LIMITS)


def test_checker_cli_reports_missing_and_matching_records(inputs, monkeypatch, capsys):
    assert check.main(["--session", str(inputs[2])]) == 1
    assert "check failed" in capsys.readouterr().err
    assert _launch(inputs, monkeypatch)[0] == 0
    capsys.readouterr()
    assert check.main(["--session", str(inputs[2])]) == 0
    assert json.loads(capsys.readouterr().out)["input_record_matches"]


def test_recorded_session_still_cannot_resume_or_overwrite(inputs, monkeypatch):
    assert _launch(inputs, monkeypatch)[0] == 0
    before = _all_bytes(inputs[2])
    result, configs = _launch(inputs, monkeypatch)
    assert result == 1 and not configs and _all_bytes(inputs[2]) == before


def test_checker_help_without_scientific_or_gui_dependencies(tmp_path):
    result = subprocess.run(
        [sys.executable, "-S", str(Path(check.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0 and "Read-only" in result.stdout
