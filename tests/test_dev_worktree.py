"""scripts/dev_worktree.sh, run against a throwaway repo with a villa submodule."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dev_worktree.sh"
# Hooks export GIT_DIR and friends; the throwaway repos must not inherit them.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "protocol.file.allow",
    "GIT_CONFIG_VALUE_0": "always",
}


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def main_repo(tmp_path):
    villa = tmp_path / "villa-upstream"
    villa.mkdir()
    git(villa, "init", "-q", "-b", "main")
    (villa / "README").write_text("villa\n")
    git(villa, "add", "README")
    git(villa, "commit", "-q", "-m", "villa")
    main = tmp_path / "main"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    git(main, "submodule", "add", "-q", str(villa), "villa")
    (main / "scripts").mkdir()
    shutil.copy(SCRIPT, main / "scripts" / "dev_worktree.sh")
    (main / ".gitignore").write_text(
        ".venv\n/local_data\n/checkpoints\n/models\n.claude/\n"
    )
    git(main, "add", ".")
    git(main, "commit", "-q", "-m", "main")
    (main / ".venv").mkdir()
    (main / "local_data").mkdir()
    (main / "checkpoints").mkdir()
    (main / "models").mkdir()
    return main


def run(main, *args):
    return subprocess.run(
        ["bash", str(main / "scripts" / "dev_worktree.sh"), *args],
        env=ENV,
        check=True,
        capture_output=True,
        text=True,
    )


def test_add_links_the_environment_and_checks_out_villa_at_the_pin(main_repo):
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    assert (wt / ".venv").resolve() == (main_repo / ".venv").resolve()
    assert (wt / "local_data").resolve() == (main_repo / "local_data").resolve()
    assert (wt / "checkpoints").resolve() == (main_repo / "checkpoints").resolve()
    assert (wt / "models").resolve() == (main_repo / "models").resolve()
    pin = git(main_repo, "ls-tree", "HEAD", "villa").split()[2]
    assert git(wt / "villa", "rev-parse", "HEAD") == pin
    assert (wt / "villa" / "README").read_text() == "villa\n"
    assert git(wt, "status", "--porcelain") == ""
    assert git(wt, "branch", "--show-current") == "feature"


def test_remove_leaves_main_and_its_villa_intact(main_repo):
    run(main_repo, "add", "feature", "main")
    run(main_repo, "remove", "feature")
    assert not (main_repo / ".claude" / "worktrees" / "feature").exists()
    for shared in (".venv", "local_data", "checkpoints", "models"):
        assert (main_repo / shared).is_dir()
    assert (main_repo / "villa" / "README").exists()
    assert "feature" not in git(main_repo, "worktree", "list")
    assert len(git(main_repo / "villa", "worktree", "list").splitlines()) == 1


def test_remove_refuses_a_villa_with_local_changes(main_repo):
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    (wt / "villa" / "README").write_text("edited\n")
    with pytest.raises(subprocess.CalledProcessError):
        run(main_repo, "remove", "feature")
    assert (wt / "villa" / "README").read_text() == "edited\n"


def enable_worktree_config(main):
    """villa as this checkout has it: extensions.worktreeConfig on, with the
    submodule's core.worktree in both the shared config and config.worktree."""
    git(main / "villa", "config", "extensions.worktreeConfig", "true")
    git(main / "villa", "config", "--worktree", "core.worktree", "../../../villa")


def test_villa_is_its_own_work_tree_when_worktree_config_is_on(main_repo):
    enable_worktree_config(main_repo)
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    # Without its own core.worktree, git takes villa's git directory for the
    # work tree: every file reads as deleted and the git internals as untracked.
    assert (
        Path(git(wt / "villa", "rev-parse", "--show-toplevel"))
        == (wt / "villa").resolve()
    )
    assert git(wt / "villa", "status", "--porcelain") == ""
    assert (
        Path(git(main_repo / "villa", "rev-parse", "--show-toplevel"))
        == (main_repo / "villa").resolve()
    )
    assert git(main_repo / "villa", "status", "--porcelain") == ""


def test_remove_works_when_worktree_config_is_on(main_repo):
    enable_worktree_config(main_repo)
    run(main_repo, "add", "feature", "main")
    run(main_repo, "remove", "feature")
    assert not (main_repo / ".claude" / "worktrees" / "feature").exists()
    assert (main_repo / "villa" / "README").exists()
    assert len(git(main_repo / "villa", "worktree", "list").splitlines()) == 1


def test_add_leaves_villas_shared_config_alone(main_repo):
    # Without extensions.worktreeConfig, `git config --worktree` writes the
    # shared config, which would point every villa checkout at this worktree.
    shared = main_repo / ".git" / "modules" / "villa" / "config"
    before = shared.read_text()
    run(main_repo, "add", "feature", "main")
    assert shared.read_text() == before
    assert (
        Path(git(main_repo / "villa", "rev-parse", "--show-toplevel"))
        == (main_repo / "villa").resolve()
    )


def test_remove_refuses_local_changes_when_worktree_config_is_on(main_repo):
    enable_worktree_config(main_repo)
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    (wt / "villa" / "README").write_text("edited\n")
    with pytest.raises(subprocess.CalledProcessError):
        run(main_repo, "remove", "feature")
    assert (wt / "villa" / "README").read_text() == "edited\n"
