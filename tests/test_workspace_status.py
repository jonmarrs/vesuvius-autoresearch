"""Read-only setup diagnostics must use training paths without loading research data."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import workspace_status as status

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(status.loop_control, "running_pid", lambda repo: None)
    monkeypatch.setattr(
        status.loop_control, "unsupervised_runs", lambda repo, supervisor=None: []
    )
    for name in ("train", "val"):
        (tmp_path / name / "surface_volume.zarr").mkdir(parents=True)
        (tmp_path / name / "inklabels.png").write_bytes(b"not decoded")
    config = {
        "uris": ["train/surface_volume.zarr"],
        "val_uri": "val/surface_volume.zarr",
        "unlabeled_uris": [],
    }
    (tmp_path / "config.json").write_text(json.dumps(config))
    return tmp_path, config


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


def save_config(workspace, **changes):
    repo, config = workspace
    config.update(changes)
    (repo / "config.json").write_text(json.dumps(config))
    return repo


def test_checks_files_without_claiming_training_readiness(workspace):
    repo, _ = workspace
    (repo / "best_model.pt").write_bytes(b"invalid checkpoint, never deserialize")
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["training_readiness"] == "not_checked"
    assert "unvalidated" in check(report, "checkpoint")["message"]
    assert check(report, "validation.labels")["path"] == str(repo / "val/inklabels.png")


def test_paused_or_running_state_is_separate_from_filesystem(
    workspace, monkeypatch, capsys
):
    repo, _ = workspace
    (repo / ".loop_paused").touch()
    monkeypatch.setattr(status.loop_control, "running_pid", lambda repo: 123)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["process"]["state"] == "running"
    assert report["process"]["watchdog_paused"] is True
    assert "Paused" in check(report, "watchdog")["message"]
    assert status.main(["--repo", str(repo)]) == 0
    output = capsys.readouterr().out
    assert "PID 123" in output and "Paused by .loop_paused" in output


def test_orphan_blocks_and_unknown_process_state_is_not_idle(workspace, monkeypatch):
    repo, _ = workspace
    monkeypatch.setattr(
        status.loop_control,
        "unsupervised_runs",
        lambda repo, supervisor=None: [(42, 100, False)],
    )
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert "PID 42" in check(report, "unsupervised_runs")["message"]

    def broken(repo):
        raise RuntimeError("held lock contains no valid PID")

    monkeypatch.setattr(status.loop_control, "running_pid", broken)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "unknown"
    assert "process" not in report


@pytest.mark.parametrize(
    "contents", ["[]", "null", "{", '{"unknown": 1}', '{"depth_band": [2, 1]}']
)
def test_malformed_config_fails_closed(workspace, contents):
    repo, _ = workspace
    (repo / "config.json").write_text(contents)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert check(report, "config")["status"] == "blocked"


def test_missing_repository_and_config_are_actionable(workspace):
    repo, _ = workspace
    assert status.inspect_workspace(repo / "absent")["setup_status"] == "blocked"
    (repo / "config.json").unlink()
    assert check(status.inspect_workspace(repo), "config")["status"] == "blocked"


def test_legacy_uri_and_label_precedence_match_training(workspace):
    repo, config = workspace
    config.pop("uris")
    save_config(workspace, uri="train/surface_volume.zarr/")
    chosen = repo / "train/inklabels_refined.png"
    chosen.write_bytes(b"preferred")
    (repo / "train/inklabels_filled.png").write_bytes(b"second")
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert check(report, "training[0].labels")["path"] == str(chosen)


def test_pseudo_label_confidence_gate_matches_training(workspace):
    repo = save_config(
        workspace, pseudo_label_dir="pseudo", use_confidence_weight=False
    )
    (repo / "pseudo").mkdir()
    pseudo = repo / "pseudo/train_pseudo.png"
    pseudo.write_bytes(b"pseudo")
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert (
        "use_confidence_weight is off" in check(report, "training[0].labels")["message"]
    )
    save_config(workspace, use_confidence_weight=True)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert check(report, "training[0].labels")["path"] == str(pseudo)
    assert check(report, "validation.labels")["path"] == str(repo / "val/inklabels.png")


def test_data_missing_invalid_and_remote_are_not_ready(workspace):
    repo = save_config(workspace, uris="train/surface_volume.zarr")
    assert status.inspect_workspace(repo)["setup_status"] == "blocked"
    save_config(workspace, uris=["absent.zarr"])
    assert check(status.inspect_workspace(repo), "training[0]")["status"] == "blocked"
    save_config(workspace, uris=["s3://bucket/train.zarr"])
    assert status.inspect_workspace(repo)["setup_status"] == "unknown"


def test_uamt_checks_only_remaining_active_unlabeled_data(workspace):
    repo = save_config(workspace, use_uamt=False, unlabeled_uris=["missing.zarr"])
    assert status.inspect_workspace(repo)["setup_status"] == "ok"
    save_config(workspace, use_uamt=True)
    assert check(status.inspect_workspace(repo), "unlabeled[0]")["status"] == "blocked"
    save_config(workspace, unlabeled_uris=["val/surface_volume.zarr"])
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert check(report, "config_normalization")["status"] == "info"


def test_cli_is_stdlib_only_does_not_write_and_emits_clean_json(workspace):
    repo, config = workspace
    save_config(workspace, unlabeled_uris=[config["val_uri"]])
    (repo / "best_model.pt").write_bytes(b"not a model")
    before = {
        str(p.relative_to(repo)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in repo.rglob("*")
        if p.is_file()
    }
    code = """
import importlib.abc, runpy, sys
class NoML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy', 'torch', 'scipy'} or fullname == 'scripts.training.train':
            raise AssertionError('heavy import: ' + fullname)
sys.meta_path.insert(0, NoML())
sys.argv = [sys.argv[1], '--repo', sys.argv[2], '--json']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(ROOT / "scripts/workspace_status.py"),
            str(repo),
        ],
        cwd=repo.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["setup_status"] == "ok"
    after = {
        str(p.relative_to(repo)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in repo.rglob("*")
        if p.is_file()
    }
    assert after == before


def test_exit_codes_follow_blocked_and_unknown_status(workspace, capsys):
    repo = save_config(workspace, uris=["s3://bucket/remote.zarr"])
    assert status.main(["--repo", str(repo), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["setup_status"] == "unknown"
    save_config(workspace, uris=[])
    assert status.main(["--repo", str(repo), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["setup_status"] == "blocked"
