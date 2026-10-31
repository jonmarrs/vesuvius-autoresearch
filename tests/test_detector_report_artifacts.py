"""Report generations stay consistent across invalid inputs and filesystem failures."""

import hashlib
import importlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts.check_detector_report import main
from vesuvius_autoresearch.core import report_artifacts as ra
from vesuvius_autoresearch.core.file_modes import current_umask
from vesuvius_autoresearch.detector import eval as evaluation, measure as measurement
from vesuvius_autoresearch.detector.config import DetectorConfig

MARKER = "frag_scorecard.json"
NAMES = ["frag_metrics_by_threshold.csv", "frag_pred_thumb.png", MARKER]


def _evaluate(root):
    label = np.array([[0.0, 1.0], [1.0, 0.0]], np.float32)
    return evaluation.evaluate(
        label, label, np.ones((2, 2), bool), DetectorConfig(reports_dir=str(root))
    )


def _old(root, partial=False):
    root.mkdir(exist_ok=True)
    for index, name in enumerate(NAMES):
        if partial and index == 1:
            continue
        path = root / name
        path.write_bytes(f"previous {name}".encode())
        path.chmod(0o640 if index != 1 else 0o444)
    return _state(root)


def _state(root):
    return {
        path.name: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        for path in root.iterdir()
        if path.is_file()
    }


def test_complete_evaluation_keeps_legacy_names_and_has_verified_hashes(tmp_path):
    card = _evaluate(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(NAMES)
    assert card["val_f1"] == card["pixel_auc"] == 1
    assert card["report_status"] == "COMPLETE"
    assert ra.check_report(tmp_path / MARKER) == card
    for name, identity in card["artifacts"].items():
        data = (tmp_path / name).read_bytes()
        assert identity == {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


@pytest.mark.parametrize(
    "failure", ["thumbnail", "stage write", "stage mutation", "source mutation"]
)
def test_prepublication_failure_preserves_every_old_artifact(
    tmp_path, monkeypatch, failure
):
    before = _old(tmp_path)
    original = ra._write

    def write(path, data):
        if failure == "stage write":
            raise OSError("disk full")
        original(path, data)
        if path.name == MARKER:
            if failure == "stage mutation":
                (path.parent / NAMES[0]).write_bytes(b"changed")
            elif failure == "source mutation":
                (tmp_path / NAMES[0]).write_bytes(b"external edit")

    monkeypatch.setattr(ra, "_write", write)
    if failure == "thumbnail":
        monkeypatch.setattr(
            evaluation.Image.Image,
            "save",
            lambda *a, **k: (_ for _ in ()).throw(OSError("thumbnail write failed")),
        )
    with pytest.raises((OSError, ValueError)):
        _evaluate(tmp_path)
    after = _state(tmp_path)
    if failure == "source mutation":
        # An external edit is preserved; the publisher must not overwrite it.
        assert after[NAMES[0]][0] == b"external edit"
        after.pop(NAMES[0])
        before.pop(NAMES[0])
    assert after == before
    assert not list(tmp_path.glob(".detector-report-*"))


@pytest.mark.parametrize("existing", ["none", "full", "partial"])
@pytest.mark.parametrize("step", range(1, 7))
def test_each_publication_rename_rolls_back_the_previous_set(
    tmp_path, monkeypatch, existing, step
):
    before = {} if existing == "none" else _old(tmp_path, existing == "partial")
    real = os.replace
    count, triggered = 0, False

    def replace(source, target):
        nonlocal count, triggered
        count += 1
        if count == step:
            triggered = True
            raise OSError("injected rename failure")
        return real(source, target)

    monkeypatch.setattr(ra.os, "replace", replace)
    operations = len(before) + 3
    if step <= operations:
        with pytest.raises(OSError, match="injected"):
            _evaluate(tmp_path)
        assert triggered
        assert _state(tmp_path) == before
    else:
        _evaluate(tmp_path)
        assert not triggered
        assert ra.check_report(tmp_path / MARKER)["report_status"] == "COMPLETE"
    assert not list(tmp_path.glob(".detector-report-*"))


def test_exception_after_marker_rename_still_restores_previous_files(
    tmp_path, monkeypatch
):
    before = _old(tmp_path)
    real = os.replace

    def replace(source, target):
        result = real(source, target)
        if Path(source).parent.name == "staged" and Path(source).name == MARKER:
            raise KeyboardInterrupt("after marker moved")
        return result

    monkeypatch.setattr(ra.os, "replace", replace)
    with pytest.raises(KeyboardInterrupt):
        _evaluate(tmp_path)
    assert _state(tmp_path) == before
    assert not list(tmp_path.glob(".detector-report-*"))


def test_failed_rollback_preserves_recovery_data_and_hides_new_marker(
    tmp_path, monkeypatch
):
    before = _old(tmp_path)
    real = os.replace

    def replace(source, target):
        if Path(source).parent.name == "staged" and Path(source).name == NAMES[1]:
            raise OSError("cannot install thumbnail")
        if Path(source).parent.name == "previous":
            raise OSError("cannot restore previous file")
        return real(source, target)

    monkeypatch.setattr(ra.os, "replace", replace)
    with pytest.raises(RuntimeError, match="retain recovery files") as error:
        _evaluate(tmp_path)
    workspaces = list(tmp_path.glob(".detector-report-*"))
    assert len(workspaces) == 1 and str(workspaces[0]) in str(error.value)
    assert not (tmp_path / MARKER).exists()
    for name, (data, mode) in before.items():
        old = workspaces[0] / "previous" / name
        assert old.read_bytes() == data
        assert stat.S_IMODE(old.stat().st_mode) == mode


def test_marker_is_absent_while_payloads_are_replaced(tmp_path, monkeypatch):
    _old(tmp_path)
    real = os.replace
    seen = []

    def replace(source, target):
        if Path(source).parent.name == "staged":
            assert not (tmp_path / MARKER).exists()
            seen.append(Path(source).name)
        return real(source, target)

    monkeypatch.setattr(ra.os, "replace", replace)
    _evaluate(tmp_path)
    assert seen == NAMES


def test_output_rewrite_during_install_is_detected_and_rolled_back(
    tmp_path, monkeypatch
):
    before = _old(tmp_path)
    real = os.replace

    def replace(source, target):
        result = real(source, target)
        if Path(source).parent.name == "staged" and Path(source).name == NAMES[1]:
            (tmp_path / NAMES[0]).write_bytes(b"changed after rename")
        return result

    monkeypatch.setattr(ra.os, "replace", replace)
    with pytest.raises(ValueError, match="changed during publication"):
        _evaluate(tmp_path)
    assert _state(tmp_path) == before


def test_output_rewrite_after_marker_install_is_detected_and_rolled_back(
    tmp_path, monkeypatch
):
    before = _old(tmp_path)
    real = os.replace

    def replace(source, target):
        result = real(source, target)
        if Path(source).parent.name == "staged" and Path(source).name == MARKER:
            (tmp_path / NAMES[0]).write_bytes(b"changed after marker install")
        return result

    monkeypatch.setattr(ra.os, "replace", replace)
    with pytest.raises(ValueError, match="after completion marker"):
        _evaluate(tmp_path)
    assert _state(tmp_path) == before


@pytest.mark.parametrize("target", NAMES)
def test_symlink_targets_are_refused_without_touching_referents(tmp_path, target):
    _old(tmp_path)
    referent = tmp_path / "unrelated.txt"
    referent.write_bytes(b"keep me")
    (tmp_path / target).unlink()
    (tmp_path / target).symlink_to(referent)
    with pytest.raises(ValueError, match="nonsymlink|collision"):
        _evaluate(tmp_path)
    assert referent.read_bytes() == b"keep me"


def test_report_cannot_overwrite_the_named_checkpoint(tmp_path):
    before = _old(tmp_path)
    label = np.array([[0.0, 1.0], [1.0, 0.0]])
    with pytest.raises(ValueError, match="collision"):
        evaluation.evaluate(
            label,
            label,
            np.ones((2, 2)),
            DetectorConfig(reports_dir=str(tmp_path)),
            checkpoint=tmp_path / MARKER,
        )
    assert _state(tmp_path) == before


@pytest.mark.parametrize(
    "fragment", ["../outside", "/outside", "a/b", "a\\b", "\nname", "..", ""]
)
def test_unsafe_fragment_names_fail_before_reading_data_or_loading_models(
    tmp_path, monkeypatch, fragment
):
    from vesuvius_autoresearch.detector import cli, data

    monkeypatch.setattr(
        data.cv2,
        "imread",
        lambda *a, **k: pytest.fail("invalid id must precede data reads"),
    )
    inference = importlib.import_module("vesuvius_autoresearch.detector.infer")
    monkeypatch.setattr(
        inference.DetectorModel,
        "load_from_checkpoint",
        lambda *a, **k: pytest.fail("invalid id must precede checkpoint loading"),
    )
    with pytest.raises(ValueError):
        inference.infer(DetectorConfig(), "missing.ckpt", fragment)
    monkeypatch.setattr(
        inference,
        "infer",
        lambda *a, **k: pytest.fail("invalid id must precede inference"),
    )
    cfg = DetectorConfig(reports_dir=str(tmp_path / "reports"))
    with pytest.raises(ValueError):
        data.read_volume_mask(cfg, fragment)
    with pytest.raises(ValueError):
        cli._eval_fragment(cfg, "missing.ckpt", fragment)
    with pytest.raises(ValueError):
        evaluation.evaluate(
            np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2)), cfg, fragment
        )
    assert not list(tmp_path.iterdir())


def _measure(root, monkeypatch, fail=()):
    def infer(cfg, checkpoint, fid, model=None):
        if fid in fail:
            raise RuntimeError("model failure")
        return np.array([[0.0, 1.0], [1.0, 0.0]])

    monkeypatch.setattr(measurement, "infer", infer)
    monkeypatch.setattr(
        measurement,
        "read_image_mask",
        lambda *a: (None, np.array([[0.0, 1.0], [1.0, 0.0]]), np.ones((2, 2))),
    )
    return measurement.measure(
        DetectorConfig(reports_dir=str(root)), None, [("one", "same"), ("two", "cross")]
    )


@pytest.mark.parametrize(
    "failed,status,exit_code",
    [((), "COMPLETE", 0), (("two",), "PARTIAL", 1), (("one", "two"), "FAILED", 1)],
)
def test_measurement_completion_reports_failures_and_keeps_json_schema(
    tmp_path, monkeypatch, capsys, failed, status, exit_code
):
    rows = _measure(tmp_path, monkeypatch, failed)
    marker = tmp_path / "cross_scroll_measurement_manifest.json"
    record = ra.check_report(marker)
    assert json.loads((tmp_path / "cross_scroll_measurement.json").read_text()) == rows
    assert record["report_status"] == status
    assert record["failure_count"] == len(failed)
    assert main([str(marker)]) == exit_code
    assert json.loads(capsys.readouterr().out)["integrity_verified"] is True


def test_failed_measurement_report_write_preserves_markdown_json_and_marker(
    tmp_path, monkeypatch
):
    _measure(tmp_path, monkeypatch)
    before = _state(tmp_path)
    original = ra._write

    def write(path, data):
        if path.name.endswith("_manifest.json"):
            raise OSError("manifest write failed")
        return original(path, data)

    monkeypatch.setattr(ra, "_write", write)
    with pytest.raises(OSError, match="manifest"):
        _measure(tmp_path, monkeypatch, ("one",))
    assert _state(tmp_path) == before


def test_oversized_existing_artifact_is_refused_before_reading(tmp_path):
    before = _old(tmp_path)
    with (tmp_path / NAMES[0]).open("wb") as stream:
        stream.truncate(ra.MAX_FILE_BYTES + 1)
    with pytest.raises(ValueError, match="bounded"):
        _evaluate(tmp_path)
    assert (tmp_path / MARKER).read_bytes() == before[MARKER][0]
    assert not list(tmp_path.glob(".detector-report-*"))


def test_invalid_report_directory_fails_before_inference(tmp_path, monkeypatch):
    from vesuvius_autoresearch.detector import cli

    inference = importlib.import_module("vesuvius_autoresearch.detector.infer")
    monkeypatch.setattr(
        inference,
        "infer",
        lambda *a, **k: pytest.fail("output preflight must precede inference"),
    )
    monkeypatch.setattr(
        measurement,
        "infer",
        lambda *a, **k: pytest.fail("output preflight must precede inference"),
    )
    path = tmp_path / "reports"
    path.write_bytes(b"unrelated file")
    cfg = DetectorConfig(reports_dir=str(path))
    with pytest.raises(ValueError, match="directory"):
        cli._eval_fragment(cfg, "missing.ckpt", "frag")
    with pytest.raises(ValueError, match="directory"):
        measurement.measure(cfg, None, [("frag", "same")])
    assert path.read_bytes() == b"unrelated file"


@pytest.mark.parametrize(
    "targets",
    [
        [],
        [("same", "one"), ("same", "two")],
        [("ok", "one"), ("../outside", "two")],
        [("ok", "")],
        [("ok",)],
        ["not-a-pair"],
    ],
)
def test_invalid_measurement_plan_preserves_prior_reports(
    tmp_path, monkeypatch, targets
):
    old = tmp_path / "cross_scroll_measurement.json"
    old.write_text("previous report")
    monkeypatch.setattr(
        measurement,
        "infer",
        lambda *a, **k: pytest.fail("plan must precede model work"),
    )
    with pytest.raises(ValueError):
        measurement.measure(DetectorConfig(reports_dir=str(tmp_path)), None, targets)
    assert old.read_text() == "previous report"
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["eval", "--checkpoint", "missing.ckpt", "--fragment", "../outside"],
        ["measure", "--same", "same", "--cross", "same"],
    ],
)
def test_cli_reports_invalid_target_selection_as_a_usage_error(arguments, capsys):
    from vesuvius_autoresearch.detector import cli

    with pytest.raises(SystemExit) as exc:
        cli.main(arguments)
    assert exc.value.code == 2
    assert "invalid target selection" in capsys.readouterr().err


@pytest.mark.parametrize(
    "problem",
    ["payload", "missing", "legacy", "bad hash", "path", "nonfinite", "status"],
)
def test_report_check_rejects_stale_or_malformed_sets(tmp_path, problem):
    _evaluate(tmp_path)
    marker = tmp_path / MARKER
    record = json.loads(marker.read_text())
    if problem == "payload":
        (tmp_path / NAMES[0]).write_bytes(b"changed")
    elif problem == "missing":
        (tmp_path / NAMES[1]).unlink()
    else:
        if problem == "legacy":
            record.pop("artifact_contract")
        elif problem == "bad hash":
            record["artifacts"][NAMES[0]]["sha256"] = "invalid"
        elif problem == "path":
            record["artifacts"]["../outside"] = record["artifacts"].pop(NAMES[0])
        elif problem == "nonfinite":
            record["val_f1"] = float("nan")
        elif problem == "status":
            record["report_status"] = "PARTIAL"
        marker.write_text(json.dumps(record))
    with pytest.raises((ValueError, OSError)):
        ra.check_report(marker)


def test_new_and_replaced_file_modes_follow_the_report_contract(tmp_path):
    before = _old(tmp_path)
    _evaluate(tmp_path)
    for name, (_, mode) in before.items():
        assert stat.S_IMODE((tmp_path / name).stat().st_mode) == mode
    fresh = tmp_path / "new"
    _evaluate(fresh)
    assert stat.S_IMODE((fresh / MARKER).stat().st_mode) == 0o666 & ~current_umask()


def test_checker_runs_from_another_cwd_without_ml_or_image_imports(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    _evaluate(tmp_path)
    script = f"""
import runpy, sys
sys.argv = ['check_detector_report', {str(tmp_path / MARKER)!r}]
try:
    runpy.run_path({str(repo / "scripts/check_detector_report.py")!r}, run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert not {{'numpy', 'torch', 'cv2', 'PIL'}}.intersection(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["report_status"] == "COMPLETE"
