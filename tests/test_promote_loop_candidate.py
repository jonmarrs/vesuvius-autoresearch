"""The manual promotion of a kept loop candidate (scripts/promote_loop_candidate.py) on a synthetic loop checkout."""

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = _load("promote_loop_candidate")
PROTOCOL = "seeded-sample-400-v3+z1-27"
FILES = (
    "best_model.pt",
    "config.json",
    "autoresearch_history.json",
    "results.tsv",
    "prize_readiness.tsv",
)


def _ckpt(config, val_f1, lift=1.2, inputs="abc", protocol=PROTOCOL, weights=None):
    return {
        "model_state_dict": {"w": torch.zeros(2, 3) if weights is None else weights},
        "val_bpb": 0.367, "avg_skel_dist": 1.5, "avg_centerline_dice": 0.4, "avg_cc_diff": 2.0, "avg_mean_ap": 0.3,
        "val_f1": val_f1, "val_f1_threshold": 0.5, "val_protocol": protocol, "ap_prevalence_lift": lift,
        "roc_auc": 0.58, "submittable": True, "window_ok": True, "window_mm": 0.512, "villa_metrics_ok": True,
        "prize_gate_failures": [],
        "validation_diag": {"complete": True, "requested_patches": 400, "scored_patches": 400, "batch_errors": 0,
                            "protocol": protocol, "inputs_sha256": inputs},
        "config": dict(config),
    }  # fmt: skip


def _git(loop, *args):
    return subprocess.run(
        ["git", "-C", str(loop), *args], capture_output=True, text=True, check=True
    ).stdout


def _loop(tmp_path, **cand):
    """A loop checkout: config.json, an incumbent, a candidate with aug_mode tweaked, the logs; stopped."""
    loop = tmp_path / "loop"
    loop.mkdir()
    config = asdict(P.ExperimentConfig())
    config.update(aug_mode="albumentations", depth_band=[1, 27], num_layers=16)
    (loop / "config.json").write_text(json.dumps(config, indent=4))
    torch.save(_ckpt(config, 0.2658), loop / "best_model.pt")
    tweaked = {**config, "aug_mode": "batchgeneratorsv2"}
    candidate = tmp_path / "candidate.pt"
    spec = {"config": tweaked, "val_f1": 0.2710, **cand}
    torch.save(_ckpt(spec.pop("config"), spec.pop("val_f1"), **spec), candidate)
    (loop / "autoresearch_history.json").write_text(
        json.dumps({"features": 2.5, "optimizer": 1.0}, indent=4)
    )
    row = ["2026-10-26 18:49:30", "0.367000", "1.500000", "0.400000", "2.000", "3.000", "0.3000", "0.500000",
           "0.75", "10.227", "9087.7", json.dumps(tweaked)]  # fmt: skip
    other = [*row[:11], json.dumps(config)]
    (loop / "history.tsv").write_text("\t".join(P.HISTORY_COLUMNS) + "\n" + "\t".join(other) + "\n" + "\t".join(row) + "\n")  # fmt: skip
    (loop / "results.tsv").write_text("\t".join(P.RESULTS_COLUMNS) + "\n")
    (loop / "prize_readiness.tsv").write_text(
        "\t".join(P.PRIZE_READINESS_COLUMNS) + "\n"
    )
    (loop / ".loop_paused").write_text("")
    _git(loop, "init", "-q")
    _git(loop, "config", "user.email", "t@example.com")
    _git(loop, "config", "user.name", "t")
    _git(loop, "add", "config.json", "best_model.pt", "autoresearch_history.json")
    _git(loop, "commit", "-q", "-m", "start")
    return loop, candidate


def _run(loop, candidate, *extra, monkeypatch):
    monkeypatch.chdir(loop)
    monkeypatch.setattr(P, "validation_inputs_fingerprint", lambda uri, band: "abc")
    return P.main(["--candidate", str(candidate), "--tweak", "aug_mode=batchgeneratorsv2", "--family", "features",
                   "--reason", "the owner's decision", *extra])  # fmt: skip


def _hashes(loop):
    return {f: hashlib.sha256((loop / f).read_bytes()).hexdigest() for f in FILES}


def test_a_dry_run_checks_everything_and_changes_nothing(tmp_path, monkeypatch, capsys):
    loop, candidate = _loop(tmp_path)
    before, head = _hashes(loop), _git(loop, "rev-parse", "HEAD")
    assert _run(loop, candidate, monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out
    assert "all checks pass" in out and "dry run: nothing changed" in out
    assert _hashes(loop) == before and _git(loop, "rev-parse", "HEAD") == head


@pytest.mark.parametrize(
    "cand, failed",
    [
        ({"val_f1": 0.2650}, "beats the incumbent"),
        ({"lift": 1.01}, "AP lift"),
        ({"inputs": "xyz"}, "validation inputs"),
        ({"protocol": "seeded-sample-400-v2"}, "protocol"),
        ({"weights": torch.zeros(3, 3)}, "architecture"),
    ],
)
def test_a_candidate_failing_a_gate_is_refused(tmp_path, monkeypatch, cand, failed):
    loop, candidate = _loop(tmp_path, **cand)
    before = _hashes(loop)
    with pytest.raises(SystemExit, match=failed):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == before


def test_a_candidate_whose_config_differs_elsewhere_is_refused(tmp_path, monkeypatch):
    config = {
        **asdict(P.ExperimentConfig()),
        "aug_mode": "batchgeneratorsv2",
        "depth_band": [1, 27],
        "num_layers": 16,
        "lr": 0.123,
    }
    loop, candidate = _loop(tmp_path, config=config)
    with pytest.raises(SystemExit, match="config"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)


def test_apply_uses_the_checkpoint_bytes_that_passed_validation(tmp_path, monkeypatch):
    loop, candidate = _loop(tmp_path)
    validated = candidate.read_bytes()
    original_checks = P.checks

    def changed_after_validation(*args, **kwargs):
        result = original_checks(*args, **kwargs)
        candidate.write_bytes(b"replaced after validation")
        return result

    monkeypatch.setattr(P, "checks", changed_after_validation)
    assert _run(loop, candidate, "--apply", monkeypatch=monkeypatch) == 0
    assert (loop / "best_model.pt").read_bytes() == validated
    assert hashlib.sha256(validated).hexdigest() in _git(
        loop, "log", "-1", "--format=%B"
    )


@pytest.mark.parametrize("log", ["results.tsv", "prize_readiness.tsv"])
def test_invalid_log_headers_refuse_before_changing_promotion_files(
    tmp_path, monkeypatch, log
):
    loop, candidate = _loop(tmp_path)
    (loop / log).write_text("wrong header\n")
    before, head = _hashes(loop), _git(loop, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="header"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == before
    assert _git(loop, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("log", ["results.tsv", "prize_readiness.tsv"])
def test_manual_promotion_still_requires_its_existing_log_files(
    tmp_path, monkeypatch, log
):
    loop, candidate = _loop(tmp_path)
    (loop / log).unlink()
    before = {name: (loop / name).read_bytes() for name in FILES if name != log}
    head = _git(loop, "rev-parse", "HEAD")
    with pytest.raises(FileNotFoundError):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert not (loop / log).exists()
    assert {name: (loop / name).read_bytes() for name in before} == before
    assert _git(loop, "rev-parse", "HEAD") == head


@pytest.mark.parametrize(
    "patch, failed",
    [
        ({"requested_patches": None, "scored_patches": None}, "validation complete"),
        ({"requested_patches": 0, "scored_patches": 0}, "validation complete"),
        ({"requested_patches": 399, "scored_patches": 399}, "validation complete"),
        ({"protocol": "another protocol"}, "protocol"),
    ],
)
def test_inconsistent_validation_diagnostics_are_refused(
    tmp_path, monkeypatch, patch, failed
):
    loop, candidate = _loop(tmp_path)
    saved = torch.load(candidate, weights_only=False)
    saved["validation_diag"].update(patch)
    torch.save(saved, candidate)
    before = _hashes(loop)
    with pytest.raises(SystemExit, match=failed):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == before


def test_apply_holds_the_checkout_lock_during_file_replacement(tmp_path, monkeypatch):
    loop, candidate = _loop(tmp_path)
    original_replace = P._replace
    checked = []

    def require_lock(path, write):
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import fcntl, sys\n"
                "with open(sys.argv[1], 'a+') as stream:\n"
                "    try:\n"
                "        fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
                "    except BlockingIOError:\n"
                "        sys.exit(0)\n"
                "sys.exit(1)\n",
                str(loop / "autoresearch.lock"),
            ],
            check=False,
        )
        assert probe.returncode == 0, "the checkout was not locked during promotion"
        checked.append(path.name)
        original_replace(path, write)

    monkeypatch.setattr(P, "_replace", require_lock)
    assert _run(loop, candidate, "--apply", monkeypatch=monkeypatch) == 0
    assert len(checked) == len(P.PROMOTION_FILES)
    assert set(checked) == set(P.PROMOTION_FILES)


@pytest.mark.parametrize("changed", ["config.json", "best_model.pt"])
def test_apply_refuses_if_checked_files_change_before_the_lock(
    tmp_path, monkeypatch, changed
):
    loop, candidate = _loop(tmp_path)
    original_stopped = P.stopped
    after_change = {}

    def changed_while_stopping(repo, **kwargs):
        original_stopped(repo, **kwargs)
        if kwargs.get("check_lock", True):
            path = repo / changed
            path.write_bytes(path.read_bytes() + b" ")
            after_change.update(_hashes(repo))

    monkeypatch.setattr(P, "stopped", changed_while_stopping)
    head = _git(loop, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="changed after validation"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == after_change
    assert _git(loop, "rev-parse", "HEAD") == head


def test_apply_refuses_if_validation_inputs_change_before_the_lock(
    tmp_path, monkeypatch
):
    loop, candidate = _loop(tmp_path)
    original_stopped = P.stopped

    def changed_while_stopping(repo, **kwargs):
        original_stopped(repo, **kwargs)
        monkeypatch.setattr(
            P, "validation_inputs_fingerprint", lambda uri, band: "changed"
        )

    monkeypatch.setattr(P, "stopped", changed_while_stopping)
    before, head = _hashes(loop), _git(loop, "rev-parse", "HEAD")
    with pytest.raises(SystemExit, match="validation inputs changed"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == before
    assert _git(loop, "rev-parse", "HEAD") == head


def test_apply_refuses_unless_the_loop_is_stopped(tmp_path, monkeypatch):
    loop, candidate = _loop(tmp_path)
    (loop / ".loop_paused").unlink()
    with pytest.raises(SystemExit, match="loop_paused"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    (loop / ".loop_paused").write_text("")
    monkeypatch.setattr(P.loop_control, "running_pid", lambda repo: 4242)
    with pytest.raises(SystemExit, match="4242"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    monkeypatch.setattr(P.loop_control, "running_pid", lambda repo: None)
    (loop / ".best_model.pt.held").write_text("")
    with pytest.raises(SystemExit, match="held"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)


def test_apply_promotes_as_the_loop_does_and_keeps_the_old_files(tmp_path, monkeypatch):
    loop, candidate = _loop(tmp_path)
    old = {f: (loop / f).read_bytes() for f in FILES}
    (loop / "unrelated.txt").write_text("staged by the operator")
    _git(loop, "add", "unrelated.txt")
    assert (
        _run(
            loop,
            candidate,
            "--apply",
            "--stamp",
            "2026-10-27 10:00:00",
            monkeypatch=monkeypatch,
        )
        == 0
    )
    assert (loop / "best_model.pt").read_bytes() == candidate.read_bytes()
    config = json.loads((loop / "config.json").read_text())
    assert (
        config == torch.load(candidate, weights_only=False)["config"]
        and config["aug_mode"] == "batchgeneratorsv2"
    )
    assert json.loads((loop / "autoresearch_history.json").read_text()) == {
        "features": 3.5,
        "optimizer": 1.0,
    }
    results = (loop / "results.tsv").read_text().splitlines()
    history_row = (loop / "history.tsv").read_text().splitlines()[2].split("\t")
    assert results[1].split("\t") == [
        "2026-10-27 10:00:00",
        *history_row[1:6],
        *history_row[7:],
    ]
    prize = (loop / "prize_readiness.tsv").read_text().splitlines()[1].split("\t")
    assert prize == ["2026-10-27 10:00:00", "True", "True", "0.5120", "True", str(config["patch_size"]),
                     *history_row[1:6], history_row[11]]  # fmt: skip
    # the commit: exactly the loop's promotion files; the operator's staged file stays staged
    assert set(_git(loop, "show", "--name-only", "--format=", "HEAD").split()) == set(
        P.PROMOTION_FILES
    )
    assert "aug_mode_batchgeneratorsv2" in _git(loop, "log", "-1", "--format=%B")
    assert _git(loop, "diff", "--cached", "--name-only").split() == ["unrelated.txt"]
    kept = next((loop / "local_data/loop_promotions").iterdir())
    assert {f: (kept / f).read_bytes() for f in FILES} == old
    # again: the candidate is now the incumbent, so it no longer beats it
    with pytest.raises(SystemExit, match="beats the incumbent"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)


def test_the_row_schemas_are_train_pys():
    tree = ast.parse((ROOT / "scripts/training/train.py").read_text())
    got = {
        n.targets[0].id: n.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and getattr(n.targets[0], "id", None)
        in ("HISTORY_COLUMNS", "PRIZE_READINESS_COLUMNS")  # fmt: skip
    }
    history = ast.literal_eval(got["HISTORY_COLUMNS"])
    assert history == P.HISTORY_COLUMNS
    assert ast.literal_eval(got["PRIZE_READINESS_COLUMNS"]) == P.PRIZE_READINESS_COLUMNS
    gates = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and getattr(n.targets[0], "id", None)
        in ("LIFT_MARGIN", "F1_NOISE_TOLERANCE")  # fmt: skip
    }
    assert gates == {
        "LIFT_MARGIN": P.LIFT_MARGIN,
        "F1_NOISE_TOLERANCE": P.F1_NOISE_TOLERANCE,
    }
    assert tuple(c for c in history if c != "avg_mean_ap") == P.RESULTS_COLUMNS
    loop_src = (ROOT / "run_autoresearch_loop.py").read_text()
    assert "PROMOTION_FILES = (CONFIG_FILE, INCUMBENT, HISTORY_FILE)" in loop_src
    assert P.PROMOTION_FILES == (
        "config.json",
        "best_model.pt",
        "autoresearch_history.json",
    )


def test_a_promotion_that_fails_partway_puts_the_old_files_back(tmp_path, monkeypatch):
    """A real append failure after checkpoint replacement restores the original bytes."""
    loop, candidate = _loop(tmp_path)
    original_append = P._append

    def failed_append(path, columns, values, missing_ok=False):
        if path.name == "prize_readiness.tsv":
            raise OSError("simulated append failure")
        original_append(path, columns, values, missing_ok)

    monkeypatch.setattr(P, "_append", failed_append)
    before = _hashes(loop)
    with pytest.raises(OSError, match="simulated append failure"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert _hashes(loop) == before


@pytest.mark.parametrize("name", ["config.json", "autoresearch_history.json"])
def test_a_failed_config_or_history_write_puts_the_old_files_back(
    tmp_path, monkeypatch, name
):
    """They are written after the checkpoint and the logs: a failure there left the new checkpoint beside the old
    config.json, which a restart would train from."""
    loop, candidate = _loop(tmp_path)
    original_replace, failed = P._replace, []

    def replace(path, write):
        if path.name == name and not failed:
            failed.append(path)
            raise OSError("simulated write failure")
        original_replace(path, write)

    monkeypatch.setattr(P, "_replace", replace)
    before, status = _hashes(loop), _git(loop, "status", "--porcelain", "--", *FILES)
    with pytest.raises(OSError, match="simulated write failure"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    assert failed and _hashes(loop) == before
    assert _git(loop, "status", "--porcelain", "--", *FILES) == status


def test_a_failed_git_add_says_where_the_old_files_are(tmp_path, monkeypatch):
    loop, candidate = _loop(tmp_path)
    real = subprocess.run

    def run(cmd, *args, **kwargs):
        if cmd[:1] == ["git"] and cmd[3:4] == ["add"]:
            return subprocess.CompletedProcess(cmd, 128)
        return real(cmd, *args, **kwargs)

    monkeypatch.setattr(P.subprocess, "run", run)
    with pytest.raises(SystemExit, match="not committed; the old files are in"):
        _run(loop, candidate, "--apply", monkeypatch=monkeypatch)
    monkeypatch.undo()
    assert (loop / "best_model.pt").read_bytes() == candidate.read_bytes()
    assert _git(loop, "diff", "--cached", "--name-only") == ""
