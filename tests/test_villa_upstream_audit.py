import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.archive import audit_villa_upstream as audit

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_audit_villa_upstream_groups_prize_relevant_changes(monkeypatch, tmp_path):
    villa_dir = tmp_path / "villa"
    villa_dir.mkdir()

    def fake_git(args, cwd):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "local"
        if args[:2] == ["rev-parse", "origin/main"]:
            return "upstream"
        if args[:1] == ["merge-base"]:
            return "base"
        if args[:2] == ["rev-list", "--count"]:
            if args[2] == "base..origin/main":
                return "5"
            if args[2] == "base..local":
                return "2"
        if args[0] == "log":
            return "abc123 upstream change"
        raise AssertionError(args)

    def fake_changed_paths(villa_dir, base_ref, head_ref):
        if (base_ref, head_ref) == ("base", "origin/main"):
            return [
                "lasagna/README.md",
                "ink-detection/optimized_inference/runtime_contracts.py",
                "deprecated/ink-detection/train_resnet3d_3d_decoder.py",
                "volume-cartographer/apps/VC3D/CWindow.cpp",
                "vesuvius/src/vesuvius/scripts/build_chunk_occupancy.py",
                "scrollprize.org/docs/34_prizes.md",
                "README.md",
            ]
        if (base_ref, head_ref) == ("base", "local"):
            return [
                "foundation/datasets/fibers-dataset/tools.py",
                "volume-cartographer/scripts/local_patch.sh",
            ]
        if (base_ref, head_ref) == ("local", "origin/main"):
            return [
                "lasagna/README.md",
                "volume-cartographer/apps/VC3D/CWindow.cpp",
                "foundation/datasets/fibers-dataset/tools.py",
            ]
        raise AssertionError((base_ref, head_ref))

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(audit, "_check_own_repository", lambda villa_dir: None)
    monkeypatch.setattr(audit, "_changed_paths", fake_changed_paths)

    report = audit.audit_villa_upstream(villa_dir=villa_dir)

    assert report["behind"] is True
    assert report["diverged"] is True
    assert report["upstream_ahead_commits"] == 5
    assert report["local_ahead_commits"] == 2
    assert report["changed_files"] == 7
    assert report["direct_tree_changed_files"] == 3
    assert report["local_changed_files"] == 2
    assert report["prize_relevant_areas"]["lasagna"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["optimized_inference"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["resnet3d_decoder"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["vesuvius_data"]["changed_files"] == 1
    assert report["prize_relevant_areas"]["prize_docs"]["changed_files"] == 1
    assert (
        report["local_prize_relevant_areas"]["volume_cartographer"]["changed_files"]
        == 1
    )


def test_audit_villa_upstream_handles_fast_forward_pin(monkeypatch, tmp_path):
    villa_dir = tmp_path / "villa"
    villa_dir.mkdir()

    def fake_git(args, cwd):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "base"
        if args[:2] == ["rev-parse", "origin/main"]:
            return "upstream"
        if args[:1] == ["merge-base"]:
            return "base"
        if args[:2] == ["rev-list", "--count"]:
            if args[2] == "base..origin/main":
                return "1"
            if args[2] == "base..base":
                return "0"
        if args[0] == "log":
            return "abc123 upstream change"
        raise AssertionError(args)

    def fake_changed_paths(villa_dir, base_ref, head_ref):
        if (base_ref, head_ref) == ("base", "origin/main"):
            return ["volume-cartographer/apps/VC3D/CWindow.cpp"]
        if (base_ref, head_ref) == ("base", "base"):
            return []
        raise AssertionError((base_ref, head_ref))

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(audit, "_check_own_repository", lambda villa_dir: None)
    monkeypatch.setattr(audit, "_changed_paths", fake_changed_paths)

    report = audit.audit_villa_upstream(villa_dir=villa_dir)

    assert report["behind"] is True
    assert report["diverged"] is False
    assert report["local_ahead_commits"] == 0
    assert report["prize_relevant_areas"]["volume_cartographer"]["changed_files"] == 1


@pytest.fixture
def isolated_git(monkeypatch):
    """Real git without a hook's locator variables or the user's config."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    for name in audit._GIT_LOCATORS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(cwd, *args):
        return subprocess.run(
            [
                "git",
                "-C",
                str(cwd),
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    return git


def test_an_uninitialised_villa_is_refused(tmp_path, isolated_git):
    """An uninitialised submodule is an empty directory; git run there reads the
    enclosing repository, whose HEAD the audit reported as villa's."""
    isolated_git(tmp_path, "init", "-q")
    isolated_git(tmp_path, "commit", "-q", "--allow-empty", "-m", "outer")
    (tmp_path / "villa").mkdir()
    with pytest.raises(RuntimeError, match="not a villa checkout of its own"):
        audit.audit_villa_upstream(villa_dir=tmp_path / "villa")


def test_a_hook_exported_git_dir_does_not_redirect_the_audit(
    tmp_path, isolated_git, monkeypatch
):
    outer = tmp_path / "outer"
    outer.mkdir()
    isolated_git(outer, "init", "-q")
    isolated_git(outer, "commit", "-q", "--allow-empty", "-m", "outer")
    villa = tmp_path / "villa"
    villa.mkdir()
    isolated_git(villa, "init", "-q")
    isolated_git(villa, "commit", "-q", "--allow-empty", "-m", "villa")
    head = isolated_git(villa, "rev-parse", "HEAD")
    isolated_git(villa, "update-ref", "refs/remotes/origin/main", head)
    monkeypatch.setenv("GIT_DIR", str(outer / ".git"))
    report = audit.audit_villa_upstream(villa_dir=villa)
    assert report["local_ref"] == head and report["behind"] is False


def test_every_prize_prefix_is_in_the_pinned_villa(isolated_git):
    """Two prefixes named files villa had moved to deprecated/, so they matched
    nothing; a move cannot go stale silently again."""
    villa = REPO_ROOT / "villa"
    try:
        pin = isolated_git(REPO_ROOT, "ls-tree", "HEAD", "villa").split()[2]
        isolated_git(villa, "cat-file", "-e", f"{pin}^{{tree}}")
    except (subprocess.CalledProcessError, IndexError):
        pytest.skip("the pinned villa commit is not available here")
    missing = []
    for area in audit.PRIZE_AREAS.values():
        for prefix in area["prefixes"]:
            parent, _, stem = prefix.rstrip("/").rpartition("/")
            where = [f"{parent}/"] if parent else []
            names = isolated_git(villa, "ls-tree", "--name-only", pin, *where)
            if not any(Path(n).name.startswith(stem) for n in names.splitlines()):
                missing.append(prefix)
    assert missing == []
