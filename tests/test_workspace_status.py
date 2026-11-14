"""Read-only setup diagnostics must use training paths without loading research data."""

import json
import os
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


@pytest.mark.parametrize(
    "field,value",
    [
        ("architecture", "resenc_unett"),
        ("architecture", None),
        ("architecture", []),
        ("architecture", 42),
        ("aug_mode", "batchgeneratorv2"),
        ("aug_mode", None),
        ("aug_mode", []),
        ("aug_mode", True),
    ],
)
def test_unknown_training_choices_are_blocked_instead_of_using_another_recipe(
    workspace, field, value
):
    repo = save_config(workspace, **{field: value})
    before = (repo / "config.json").read_bytes()
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert field in check(report, "config")["message"]
    assert (repo / "config.json").read_bytes() == before


@pytest.mark.parametrize("kind", ["split", "checkpoint"])
def test_training_boundary_conflicts_are_reported_without_loading_data(workspace, kind):
    if kind == "split":
        repo = save_config(workspace, uris=["./val/surface_volume.zarr/"])
        name = "training_split"
    else:
        repo = save_config(workspace, checkpoint_out="config.json")
        name = "checkpoint_outputs"
    before = (repo / "config.json").read_bytes()
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert check(report, name)["status"] == "blocked"
    assert (repo / "config.json").read_bytes() == before


def test_checks_files_without_claiming_training_readiness(workspace):
    repo, _ = workspace
    (repo / "best_model.pt").write_bytes(b"invalid checkpoint, never deserialize")
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["training_readiness"] == "not_checked"
    assert report["data_read_policy"] == {
        "training": "legacy_permissive",
        "validation": "strict",
    }
    assert "unvalidated" in check(report, "checkpoint")["message"]
    assert check(report, "validation.labels")["path"] == str(repo / "val/inklabels.png")


def test_existing_uri_like_local_paths_use_the_same_lookup_as_training(workspace):
    repo, _ = workspace
    (repo / "train").rename(repo / "scan:train")
    save_config(workspace, uris=["scan:train/surface_volume.zarr"])
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert check(report, "training[0].labels")["path"] == str(
        repo / "scan:train/inklabels.png"
    )


def test_symlinked_volume_keeps_its_visible_annotation_parent(workspace):
    repo, _ = workspace
    (repo / "visible").mkdir()
    (repo / "visible/surface_volume.zarr").symlink_to(
        repo / "train/surface_volume.zarr", target_is_directory=True
    )
    label = repo / "visible/inklabels.png"
    label.write_bytes(b"visible annotation")
    save_config(
        workspace, uris=["visible/surface_volume.zarr"], checkpoint_out=str(label)
    )
    report = status.inspect_workspace(repo)
    assert check(report, "training[0].labels")["path"] == str(label)
    assert report["setup_status"] == "blocked"
    assert check(report, "checkpoint_outputs")["status"] == "blocked"
    assert label.read_bytes() == b"visible annotation"


@pytest.mark.parametrize("strict", [False, True])
def test_reports_the_explicit_read_policy_without_loading_arrays(workspace, strict):
    repo = save_config(workspace, strict_training_reads=strict)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["data_read_policy"] == {
        "training": "strict" if strict else "legacy_permissive",
        "validation": "strict",
    }
    assert check(report, "read_policy")["status"] == "info"


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_invalid_read_policy_is_not_silently_coerced(workspace, flag):
    repo = save_config(workspace, strict_training_reads=flag)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert (
        "strict_training_reads must be a boolean" in check(report, "config")["message"]
    )


def test_strict_uamt_refuses_unsupported_preprocessing_before_data_loading(workspace):
    repo = save_config(
        workspace,
        strict_training_reads=True,
        use_uamt=True,
        use_lasagna=True,
        unlabeled_uris=["train/surface_volume.zarr"],
    )
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert "unavailable unlabeled Lasagna" in check(report, "config")["message"]
    save_config(workspace, unlabeled_uris=[])
    assert status.inspect_workspace(repo)["setup_status"] == "ok"


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


def test_configuration_fingerprint_uses_the_same_captured_bytes_as_parsing(
    workspace, monkeypatch, capsys
):
    import hashlib

    repo, config = workspace
    path = repo / "config.json"
    original_bytes = path.read_bytes()
    from_json = status.ExperimentConfig.from_json

    def parse(raw):
        path.write_text(json.dumps({**config, "uris": ["changed/volume.zarr"]}))
        return from_json(raw)

    monkeypatch.setattr(status.ExperimentConfig, "from_json", parse)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["config_source"] == {
        "path": str(path.resolve()),
        "bytes": len(original_bytes),
        "sha256": hashlib.sha256(original_bytes).hexdigest(),
    }
    assert path.read_bytes() != original_bytes
    assert check(report, "training[0]")["path"] == str(repo / config["uris"][0])
    path.write_bytes(original_bytes)
    monkeypatch.setattr(status.ExperimentConfig, "from_json", from_json)
    assert status.main(["--repo", str(repo)]) == 0
    assert report["config_source"]["sha256"] in capsys.readouterr().out


def test_default_config_byte_budget_refuses_an_otherwise_valid_large_file(workspace):
    repo, _ = workspace
    path = repo / "config.json"
    path.write_bytes(b" " * (1024**2) + path.read_bytes())
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert "exceeds" in check(report, "config")["message"]
    assert "config_source" not in report


def test_symlinked_config_keeps_repo_relative_paths_and_names_its_actual_source(
    workspace,
):
    repo, _ = workspace
    settings = repo / "settings"
    settings.mkdir()
    source = settings / "selected.json"
    (repo / "config.json").rename(source)
    (repo / "config.json").symlink_to(source)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "ok"
    assert report["config_source"]["path"] == str(source.resolve())
    assert check(report, "training[0]")["path"] == str(
        repo / "train/surface_volume.zarr"
    )


def test_explicit_config_budget_accepts_the_byte_boundary_and_rejects_one_less(
    workspace, capsys
):
    repo, _ = workspace
    size = (repo / "config.json").stat().st_size
    assert status.inspect_workspace(repo, max_config_bytes=size)["setup_status"] == "ok"
    assert (
        status.inspect_workspace(repo, max_config_bytes=size - 1)["setup_status"]
        == "blocked"
    )
    assert (
        status.main(["--repo", str(repo), "--max-config-bytes", str(size), "--json"])
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["config_byte_limit"] == size
    assert report["config_source"]["bytes"] == size


@pytest.mark.parametrize("limit", [0, True, 16 * 1024**2 + 1])
def test_bad_config_budgets_fail_before_process_or_config_reads(
    workspace, monkeypatch, limit
):
    repo, _ = workspace
    monkeypatch.setattr(
        status.loop_control, "running_pid", lambda *a: pytest.fail("invalid budget")
    )
    report = status.inspect_workspace(repo, max_config_bytes=limit)
    assert report["setup_status"] == "blocked"
    assert "max_config_bytes" in check(report, "config")["message"]


@pytest.mark.parametrize("target", ["repository", "config"])
def test_path_resolution_loops_are_structured_blocked_diagnostics(workspace, target):
    repo, _ = workspace
    loop = repo / "loop"
    loop.symlink_to(loop)
    report = (
        status.inspect_workspace(loop)
        if target == "repository"
        else status.inspect_workspace(repo, loop)
    )
    assert report["setup_status"] == "blocked"
    assert "loop" in check(report, target)["message"].lower()


def test_deep_json_is_a_blocked_config_report_instead_of_a_traceback(workspace, capsys):
    repo, _ = workspace
    path = repo / "config.json"
    path.write_text('{"extra":' + "[" * 5000 + "0" + "]" * 5000 + "}")
    assert status.main(["--repo", str(repo), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["setup_status"] == "blocked"
    assert check(report, "config")["status"] == "blocked"


def test_config_bom_stays_a_parse_error_and_has_a_raw_byte_fingerprint(workspace):
    import hashlib

    repo, _ = workspace
    path = repo / "config.json"
    raw = b"\xef\xbb\xbf" + path.read_bytes()
    path.write_bytes(raw)
    report = status.inspect_workspace(repo)
    assert report["setup_status"] == "blocked"
    assert report["config_source"]["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_cli_refuses_a_fifo_config_without_waiting_for_a_writer(workspace):
    repo, _ = workspace
    path = repo / "config.json"
    path.unlink()
    os.mkfifo(path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/workspace_status.py"),
            "--repo",
            str(repo),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["setup_status"] == "blocked"
    assert "regular file" in check(report, "config")["message"]
    assert "Traceback" not in result.stderr
