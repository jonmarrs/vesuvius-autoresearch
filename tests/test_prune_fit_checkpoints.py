"""Tests for the checkpoint pruner.

The test that earns its place is `test_a_referenced_arm_is_never_dropped`. This
project once asserted checkpoints were stale, was told to clear them, checked
first, and found every one cited by a live report. The reference check is the
whole safety property, so it is pinned directly rather than trusted.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import prune_fit_checkpoints as mod  # noqa: E402


def _arm(spiral_out, name, size=16):
    d = spiral_out / name
    d.mkdir(parents=True)
    (d / mod.CKPT).write_bytes(b"x" * size)
    (d / "satisfaction_metrics_fitted.json").write_text("{}")
    return d


def _repo(tmp_path, mentions=()):
    r = tmp_path / "repo"
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "a_report.md").write_text(
        "\n".join(f"see {m} for detail" for m in mentions) or "nothing here"
    )
    _git(r, "init", "-q")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "fixture")
    return r


def _git(repo, *args):
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        env=env,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _main(monkeypatch, repo, root, *extra):
    monkeypatch.setattr(
        sys, "argv", ["prune", "--repo", str(repo), "--spiral-out", str(root), *extra]
    )
    return mod.main()


def test_finds_checkpoints_and_their_sizes(tmp_path):
    so = tmp_path / "spiral_out"
    _arm(so, "2026-01-01_x-patch_alpha", size=32)
    _arm(so, "2026-01-02_x-patch_beta", size=8)
    found = mod.find_checkpoints(str(so))
    assert [f[0] for f in found] == [
        "2026-01-01_x-patch_alpha",
        "2026-01-02_x-patch_beta",
    ]
    assert [f[2] for f in found] == [32, 8]


def test_an_arm_named_in_a_report_is_referenced(tmp_path):
    repo = _repo(tmp_path, mentions=["2026-01-01_x-patch_alpha/checkpoint_fitted.ckpt"])
    ref, needle = mod.is_referenced(str(repo), "2026-01-01_x-patch_alpha")
    assert ref
    assert needle == "2026-01-01_x-patch_alpha"


def test_an_arm_referred_to_by_short_tag_alone_is_referenced(tmp_path):
    """Reports sometimes cite `baseline01`, not the full dated directory."""
    repo = _repo(tmp_path, mentions=["the baseline01 fit"])
    ref, needle = mod.is_referenced(str(repo), "2026-08-28_s1_slice-x-patch_baseline01")
    assert ref
    assert needle == "baseline01"


def test_an_unmentioned_arm_is_not_referenced(tmp_path):
    repo = _repo(tmp_path, mentions=["something else entirely"])
    ref, _ = mod.is_referenced(str(repo), "2026-01-02_x-patch_beta")
    assert not ref


def test_a_referenced_arm_is_never_dropped(tmp_path, monkeypatch):
    """End to end: the cited checkpoint survives --delete, the other does not."""
    so = tmp_path / "spiral_out"
    keep = _arm(so, "2026-01-01_x-patch_baseline01")
    drop = _arm(so, "2026-01-02_x-patch_gap133")
    repo = _repo(tmp_path, mentions=["baseline01"])
    assert _main(monkeypatch, repo, so, "--delete") == 0
    assert (keep / mod.CKPT).exists(), "a referenced checkpoint was deleted"
    assert not (drop / mod.CKPT).exists()
    assert (drop / "satisfaction_metrics_fitted.json").exists(), (
        "analysis inputs must survive; only the checkpoint is pruned"
    )


def test_dry_run_is_the_default(tmp_path, monkeypatch):
    so = tmp_path / "spiral_out"
    a = _arm(so, "2026-01-02_x-patch_gap133")
    repo = _repo(tmp_path)
    assert _main(monkeypatch, repo, so) == 0
    assert (a / mod.CKPT).exists(), "dry run must not delete"


def test_logs_are_not_searched_for_references(tmp_path):
    """A training log naming an arm is not a dependency on its checkpoint;
    searching logs would protect everything forever and defeat the tool."""
    assert "logs" not in mod.SEARCH_SUBDIRS
    assert set(mod.SEARCH_SUBDIRS) <= {"reports", "docs", "scripts", "repro", "tests"}


@pytest.mark.parametrize(
    "script", ["prune_fit_checkpoints.py", "reclaim_fit_checkpoints.py"]
)
def test_cleanup_help_from_another_cwd_is_standard_library_only(tmp_path, script):
    code = """
import importlib.abc, runpy, sys
class NoML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy', 'torch', 'scipy', 'wandb'}:
            raise AssertionError('heavy import: ' + fullname)
sys.meta_path.insert(0, NoML())
sys.argv = [sys.argv[1], '--help']
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(Path(_REPO) / "scripts" / script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "--spiral-out" in result.stdout


def test_committed_logs_remain_outside_the_reference_scope(tmp_path, monkeypatch):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_logonly")
    repo = _repo(tmp_path)
    (repo / "logs").mkdir()
    (repo / "logs/README.md").write_text("logonly")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "log")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert not (arm / mod.CKPT).exists()


def test_missing_committed_blobs_are_unknown_and_are_not_lazy_fetched(
    tmp_path, monkeypatch
):
    server = _repo(tmp_path, ["unused"])
    _git(server, "config", "uploadpack.allowFilter", "true")
    clone = tmp_path / "partial"
    _git(
        tmp_path,
        "clone",
        "--quiet",
        "--filter=blob:none",
        "--no-checkout",
        server.as_uri(),
        str(clone),
    )
    blob = _git(server, "rev-parse", "HEAD:reports/a_report.md")
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    result = _main(monkeypatch, clone, root, "--delete")
    assert (arm / mod.CKPT).exists(), (
        "an unavailable committed reference permitted deletion"
    )
    assert result == 1
    lookup = subprocess.run(
        ["git", "-C", str(clone), "cat-file", "-e", blob],
        env=mod._git_env(),
        capture_output=True,
    )
    assert lookup.returncode != 0, (
        "the read-only reference check fetched a missing object"
    )


def test_a_timed_out_search_is_unknown_and_leaves_all_checkpoints(
    tmp_path, monkeypatch
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    repo = _repo(tmp_path)
    run = mod.subprocess.run

    def timeout(command, **kwargs):
        if "grep" in command:
            raise subprocess.TimeoutExpired(command, 30)
        return run(command, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", timeout)
    assert _main(monkeypatch, repo, root, "--delete") == 1
    assert (arm / mod.CKPT).exists()


@pytest.mark.parametrize("kind", ["missing", "not git"])
def test_unknown_reference_repository_never_permits_deletion(
    tmp_path, monkeypatch, kind
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    repo = tmp_path / "missing"
    if kind == "not git":
        (repo / "reports").mkdir(parents=True)
        (repo / "reports/note.md").write_text("unrelated")
    result = _main(monkeypatch, repo, root, "--delete")
    assert (arm / mod.CKPT).exists(), "unknown reference state permitted deletion"
    assert result == 1


def test_a_committed_reference_survives_an_uncommitted_removal(tmp_path, monkeypatch):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_baseline01")
    repo = _repo(tmp_path, ["baseline01"])
    (repo / "reports/a_report.md").write_text("reference removed only in the worktree")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists(), "HEAD's reference was ignored"


def test_an_untracked_report_also_protects_a_checkpoint(tmp_path, monkeypatch):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_working")
    repo = _repo(tmp_path)
    (repo / "reports/new.md").write_text("working")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists()


@pytest.mark.parametrize(
    "code,stderr", [(2, "read failed"), (1, "read failed"), (0, "read failed")]
)
def test_reference_search_errors_never_become_no_match(
    tmp_path, monkeypatch, code, stderr
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    repo = _repo(tmp_path)
    run = mod.subprocess.run

    def broken(command, **kwargs):
        if "grep" in command:
            return subprocess.CompletedProcess(command, code, "", stderr)
        return run(command, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", broken)
    result = _main(monkeypatch, repo, root, "--delete")
    assert (arm / mod.CKPT).exists(), "failed search permitted deletion"
    assert result == 1


def test_inherited_git_locators_cannot_redirect_the_reference_scan(
    tmp_path, monkeypatch
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_baseline01")
    repo = _repo(tmp_path, ["baseline01"])
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q")
    _git(other, "commit", "--allow-empty", "-qm", "unrelated")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists()


@pytest.mark.parametrize(
    "variable", ["GIT_LITERAL_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_GLOB_PATHSPECS"]
)
def test_inherited_pathspec_settings_cannot_narrow_the_reference_scope(
    tmp_path, monkeypatch, variable
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_topref")
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("topref")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "top-level reference")
    monkeypatch.setenv(variable, "1")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists(), "an inherited pathspec hid a committed reference"


def test_symlink_arm_directories_are_not_traversed(tmp_path):
    outside = _arm(tmp_path / "external", "fit-patch_unused")
    root = tmp_path / "fits"
    root.mkdir()
    (root / "alias").symlink_to(outside, target_is_directory=True)
    assert mod.find_checkpoints(root) == []
    assert (outside / mod.CKPT).exists()


@pytest.mark.parametrize("change", ["file", "directory"])
def test_replaced_targets_are_refused_before_deletion(tmp_path, monkeypatch, change):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    outside = _arm(tmp_path / "external", "external")
    repo = _repo(tmp_path)
    original = mod.is_referenced
    changed = []

    def check(*args, **kwargs):
        if not changed:
            if change == "file":
                (arm / mod.CKPT).write_bytes(b"new fit checkpoint")
            else:
                arm.rename(root / "saved")
                arm.symlink_to(outside, target_is_directory=True)
            changed.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(mod, "is_referenced", check)
    result = _main(monkeypatch, repo, root, "--delete")
    assert changed == [True]
    if change == "file":
        assert (arm / mod.CKPT).read_bytes() == b"new fit checkpoint"
    assert (outside / mod.CKPT).exists(), "a changed parent redirected deletion"
    assert result == 1


def test_new_commit_during_planning_prevents_deletion(tmp_path, monkeypatch):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    repo = _repo(tmp_path)
    original = mod.is_referenced
    changed = []

    def check(*args, **kwargs):
        result = original(*args, **kwargs)
        if not changed:
            (repo / "reports/new.md").write_text("unused")
            _git(repo, "add", ".")
            _git(repo, "commit", "-qm", "new dependency")
            changed.append(True)
        return result

    monkeypatch.setattr(mod, "is_referenced", check)
    result = _main(monkeypatch, repo, root, "--delete")
    assert (arm / mod.CKPT).exists(), "a moved HEAD's reference was ignored"
    assert result == 1


def test_json_dry_run_records_the_checked_commit_without_deleting(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_unused")
    repo = _repo(tmp_path)
    assert _main(monkeypatch, repo, root, "--json") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["reference_commit"] == _git(repo, "rev-parse", "HEAD")
    assert report["mode"] == "dry_run"
    assert report["deleted_count"] == report["deleted_bytes"] == 0
    assert report["checkpoints"][0]["action"] == "WOULD_DELETE"
    assert (arm / mod.CKPT).exists()


def test_json_apply_counts_only_successful_removals(tmp_path, monkeypatch, capsys):
    root = tmp_path / "fits"
    keep = _arm(root, "fit-patch_baseline01")
    drop = _arm(root, "fit-patch_unused", size=37)
    repo = _repo(tmp_path, ["baseline01"])
    assert _main(monkeypatch, repo, root, "--delete", "--json") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["deleted_count"] == 1 and report["deleted_bytes"] == 37
    assert (keep / mod.CKPT).exists() and not (drop / mod.CKPT).exists()
    assert (drop / "satisfaction_metrics_fitted.json").exists()


def test_a_staged_reference_survives_its_removal_from_the_worktree(
    tmp_path, monkeypatch
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_staged")
    repo = _repo(tmp_path)
    report = repo / "reports/a_report.md"
    report.write_text("staged")
    _git(repo, "add", ".")
    report.write_text("removed from the worktree")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists()


@pytest.mark.parametrize("name", ["README.md", "FINDINGS.md", "config.json"])
def test_top_level_document_and_config_references_are_protected(
    tmp_path, monkeypatch, name
):
    root = tmp_path / "fits"
    arm = _arm(root, "fit-patch_topref")
    repo = _repo(tmp_path)
    (repo / name).write_text("topref")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "reference")
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists()


def test_a_late_search_failure_aborts_the_entire_set_before_first_deletion(
    tmp_path, monkeypatch
):
    root = tmp_path / "fits"
    arms = [_arm(root, f"fit-patch_unused{n}") for n in (1, 2)]
    repo = _repo(tmp_path)
    check = mod.is_referenced
    calls = 0

    def search(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise ValueError("injected late search error")
        return check(*args, **kwargs)

    monkeypatch.setattr(mod, "is_referenced", search)
    assert _main(monkeypatch, repo, root, "--delete") == 1
    assert calls == 4
    assert all((arm / mod.CKPT).exists() for arm in arms)


def test_partial_deletion_failure_is_nonzero_and_reports_actual_count(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "fits"
    first = _arm(root, "fit-patch_unused1", size=11)
    second = _arm(root, "fit-patch_unused2", size=19)
    repo = _repo(tmp_path)
    remove = mod.os.remove

    def unlink(path):
        if Path(path).parent == second:
            raise OSError("injected unlink failure")
        return remove(path)

    monkeypatch.setattr(mod.os, "remove", unlink)
    assert _main(monkeypatch, repo, root, "--delete", "--json") == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PARTIAL"
    assert report["deleted_count"] == 1 and report["deleted_bytes"] == 11
    assert not (first / mod.CKPT).exists() and (second / mod.CKPT).exists()
    assert report["checkpoints"][1]["action"] == "REFUSED"


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_special_checkpoint_files_block_the_plan(tmp_path, monkeypatch, kind):
    if kind == "fifo" and not hasattr(os, "mkfifo"):
        pytest.skip("POSIX FIFO")
    root = tmp_path / "fits"
    safe = _arm(root, "fit-patch_unused1")
    special = _arm(root, "fit-patch_unused2")
    target = special / mod.CKPT
    target.unlink()
    sentinel = tmp_path / "keep"
    sentinel.write_bytes(b"keep")
    if kind == "symlink":
        target.symlink_to(sentinel)
    else:
        os.mkfifo(target)
    repo = _repo(tmp_path)
    assert _main(monkeypatch, repo, root, "--delete") == 1
    assert sentinel.read_bytes() == b"keep"
    assert (safe / mod.CKPT).exists() and os.path.lexists(target)


def test_leading_dash_names_are_literal_reference_patterns(tmp_path, monkeypatch):
    root = tmp_path / "fits"
    arm = _arm(root, "-named")
    repo = _repo(tmp_path, ["-named"])
    assert _main(monkeypatch, repo, root, "--delete") == 0
    assert (arm / mod.CKPT).exists()
