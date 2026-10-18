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
                "ink-detection/optimized_inference/model_resnet3d_3d_decoder.py",
                # Deprecated upstream (villa #1486): counted in no area.
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
    monkeypatch.setattr(audit, "_tree_paths", lambda villa_dir, ref: [])
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
    monkeypatch.setattr(audit, "_tree_paths", lambda villa_dir, ref: [])
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


def _outer_with_empty_villa(tmp_path, git):
    """A repository whose villa/ is an empty directory, with its own origin/main:
    the old audit exited 0 here and reported this repository as villa."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "outer")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    (tmp_path / "villa").mkdir()
    return tmp_path / "villa"


def test_an_uninitialised_villa_is_refused(tmp_path, isolated_git):
    villa = _outer_with_empty_villa(tmp_path, isolated_git)
    with pytest.raises(RuntimeError, match="uninitialised submodule"):
        audit.audit_villa_upstream(villa_dir=villa)


def test_an_uninitialised_villa_is_refused_under_a_hook_git_dir(
    tmp_path, isolated_git, monkeypatch
):
    villa = _outer_with_empty_villa(tmp_path, isolated_git)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / ".git"))
    with pytest.raises(RuntimeError, match="not a villa checkout of its own"):
        audit.audit_villa_upstream(villa_dir=villa)


def test_a_villa_whose_work_tree_is_its_git_dir_is_sent_to_repair(
    tmp_path, monkeypatch
):
    """A dev worktree made before #119: git takes .git/modules/villa for its top."""
    (tmp_path / "villa").mkdir()
    found = subprocess.CompletedProcess([], 0, f"{tmp_path}/.git/modules/villa\n", "")
    monkeypatch.setattr(audit.subprocess, "run", lambda *a, **k: found)
    with pytest.raises(RuntimeError, match="dev_worktree.sh repair"):
        audit._check_own_repository(tmp_path / "villa")


def test_git_s_own_refusal_is_shown(tmp_path, monkeypatch):
    (tmp_path / "villa").mkdir()
    refused = subprocess.CompletedProcess(
        [], 128, "", "fatal: detected dubious ownership in repository at x\n"
    )
    monkeypatch.setattr(audit.subprocess, "run", lambda *a, **k: refused)
    with pytest.raises(RuntimeError, match="dubious ownership"):
        audit._check_own_repository(tmp_path / "villa")


def _villa_repo(path, git):
    path.mkdir()
    git(path, "init", "-q")
    (path / "a").mkdir()
    (path / "a" / "x.py").write_text("x\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "pin")
    return git(path, "rev-parse", "HEAD")


def test_a_file_moved_out_of_an_area_is_counted_and_reported_stale(
    tmp_path, isolated_git, monkeypatch
):
    """With rename detection a move was listed only at its new path, so the area
    it left counted nothing in the range that moved it."""
    villa = tmp_path / "villa"
    pin = _villa_repo(villa, isolated_git)
    isolated_git(villa, "mv", "a", "b")
    isolated_git(villa, "commit", "-q", "-m", "move")
    isolated_git(villa, "update-ref", "refs/remotes/origin/main", "HEAD")
    isolated_git(villa, "checkout", "-q", "--detach", pin)
    monkeypatch.setattr(
        audit, "PRIZE_AREAS", {"a": {"prefixes": ("a/",), "prize_use": ""}}
    )
    report = audit.audit_villa_upstream(villa_dir=villa)
    assert report["prize_relevant_areas"]["a"]["changed_files"] == 1
    assert report["stale_prefixes"] == {"local": [], "upstream": ["a/"]}


def test_a_hook_exported_git_dir_does_not_redirect_the_audit(
    tmp_path, isolated_git, monkeypatch
):
    outer = tmp_path / "outer"
    outer.mkdir()
    isolated_git(outer, "init", "-q")
    isolated_git(outer, "commit", "-q", "--allow-empty", "-m", "outer")
    villa = tmp_path / "villa"
    head = _villa_repo(villa, isolated_git)
    isolated_git(villa, "update-ref", "refs/remotes/origin/main", head)
    monkeypatch.setenv("GIT_DIR", str(outer / ".git"))
    report = audit.audit_villa_upstream(villa_dir=villa)
    assert report["local_ref"] == head and report["behind"] is False


def test_a_symlinked_villa_is_its_own_checkout(tmp_path, isolated_git):
    head = _villa_repo(tmp_path / "real", isolated_git)
    isolated_git(tmp_path / "real", "update-ref", "refs/remotes/origin/main", head)
    (tmp_path / "villa").symlink_to(tmp_path / "real", target_is_directory=True)
    assert audit.audit_villa_upstream(villa_dir=tmp_path / "villa")["local_ref"] == head


def test_every_prize_prefix_matches_a_file_in_the_pinned_villa(isolated_git):
    """Two prefixes named files villa had deprecated, so they matched nothing. This
    checks the pin only, and where its objects are here; the audit's own
    stale_prefixes checks the upstream tree on every run."""
    villa = REPO_ROOT / "villa"
    try:
        pin = isolated_git(REPO_ROOT, "ls-tree", "HEAD", "villa").split()[2]
        # A timeout: in a partial clone a missing object is fetched lazily.
        paths = subprocess.run(
            ["git", "-C", str(villa), "ls-tree", "-r", "--name-only", pin],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError):
        pytest.skip("the pinned villa commit is not available here")
    assert audit._stale_prefixes(paths) == []
