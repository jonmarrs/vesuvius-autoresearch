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
    # Nor the user's global or system config (a signing key, hooks, templates).
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
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


def refused(main, *args):
    with pytest.raises(subprocess.CalledProcessError) as error:
        run(main, *args)
    return error.value


def test_repair_fixes_a_worktree_added_without_its_villa_work_tree(main_repo):
    """A worktree added by the script before #119 lacks villa's core.worktree, and add
    cannot make it again: the branch exists."""
    enable_worktree_config(main_repo)
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    git(wt / "villa", "config", "--worktree", "--unset", "core.worktree")  # as before
    assert (
        Path(git(wt / "villa", "rev-parse", "--show-toplevel"))
        != (wt / "villa").resolve()
    )
    refused(main_repo, "add", "feature", "main")
    shared = main_repo / ".git" / "modules" / "villa" / "config"
    main_own = main_repo / ".git" / "modules" / "villa" / "config.worktree"
    before = shared.read_text(), main_own.read_text()
    assert "Repaired" in run(main_repo, "repair", "feature").stdout
    assert (
        Path(git(wt / "villa", "rev-parse", "--show-toplevel"))
        == (wt / "villa").resolve()
    )
    assert git(wt / "villa", "status", "--porcelain") == ""
    # In this worktree's own config.worktree, and nowhere villa's other checkouts read.
    origin = git(wt / "villa", "config", "--show-origin", "core.worktree")
    own = git(wt / "villa", "rev-parse", "--absolute-git-dir")
    assert "/modules/villa/worktrees/" in own
    assert origin.startswith(f"file:{own}/config.worktree\t")
    assert (shared.read_text(), main_own.read_text()) == before
    run(main_repo, "remove", "feature")
    assert not wt.exists()


def test_repair_is_a_no_op_without_the_extension(main_repo):
    """Without extensions.worktreeConfig git refuses --worktree once villa has a
    second worktree, so repair, like add, leaves the config alone."""
    shared = main_repo / ".git" / "modules" / "villa" / "config"
    run(main_repo, "add", "feature", "main")
    before = shared.read_text()
    assert "Nothing to repair" in run(main_repo, "repair", "feature").stdout
    assert shared.read_text() == before


def test_repair_refuses_a_missing_worktree(main_repo):
    error = refused(main_repo, "repair", "absent")
    assert error.returncode == 1 and "no villa worktree" in error.stderr


@pytest.mark.parametrize("name", ["../..", "/../..", "../../", ".", ".."])
def test_a_path_is_not_a_branch_name(main_repo, name):
    """`repair ../..` named the main checkout, whose villa it then rewrote."""
    enable_worktree_config(main_repo)
    own = main_repo / ".git" / "modules" / "villa" / "config.worktree"
    before = own.read_text()
    error = refused(main_repo, "repair", name)
    assert error.returncode == 2 and "not a branch name" in error.stderr
    assert own.read_text() == before


def test_an_extension_set_outside_villas_own_config_is_ignored(main_repo):
    """Git reads extensions.* from the repository's config only, and refuses
    --worktree without it: a global setting must not make add call it."""
    env = ENV | {
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_1": "extensions.worktreeConfig",
        "GIT_CONFIG_VALUE_1": "true",
    }
    subprocess.run(
        [
            "bash",
            str(main_repo / "scripts" / "dev_worktree.sh"),
            "add",
            "feature",
            "main",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    wt = main_repo / ".claude" / "worktrees" / "feature"
    assert git(wt / "villa", "status", "--porcelain") == ""


LINKS = (".venv", "local_data", "checkpoints", "models")


def test_add_refuses_a_path_in_use_before_making_the_branch(main_repo):
    """Git creates the branch, then refuses the path, and a second add stops on the
    branch."""
    wt = main_repo / ".claude" / "worktrees" / "feature"
    wt.mkdir(parents=True)
    (wt / "left").write_text("x\n")
    error = refused(main_repo, "add", "feature", "main")
    assert error.returncode == 1 and "already exists" in error.stderr
    assert git(main_repo, "branch", "--list", "feature") == ""
    (wt / "left").unlink()  # an empty directory, which git accepts
    run(main_repo, "add", "feature", "main")
    assert git(wt, "branch", "--show-current") == "feature"


def test_an_add_that_stops_part_way_can_be_undone(main_repo):
    """villa's step fails once the outer worktree exists: here, a pin villa lacks.
    remove then stopped on the missing villa worktree, and add on the branch."""
    git(main_repo, "update-index", "--cacheinfo", f"160000,{'1' * 40},villa")
    git(main_repo, "commit", "-q", "-m", "a pin villa does not have")
    error = refused(main_repo, "add", "feature", "HEAD")
    assert "add stopped part-way" in error.stderr and "remove feature" in error.stderr
    run(main_repo, "remove", "feature")
    assert not (main_repo / ".claude" / "worktrees" / "feature").exists()
    assert len(git(main_repo, "worktree", "list").splitlines()) == 1
    git(main_repo, "branch", "-D", "feature")
    run(main_repo, "add", "feature", "HEAD~1")


def test_remove_refuses_before_changing_anything(main_repo):
    """git worktree remove refused an untracked file only after villa's worktree and
    the links were gone, and remove could not then run again."""
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    (wt / "notes.txt").write_text("x\n")
    error = refused(main_repo, "remove", "feature")
    assert error.returncode == 1 and "notes.txt" in error.stderr
    assert "/modules/villa/worktrees/" in git(
        wt / "villa", "rev-parse", "--absolute-git-dir"
    )
    assert all((wt / link).is_symlink() for link in LINKS)
    (wt / "notes.txt").unlink()
    run(main_repo, "remove", "feature")
    assert not wt.exists()


def test_a_stopped_remove_resumes(main_repo):
    """As if a remove was stopped after its first steps."""
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    git(main_repo / "villa", "worktree", "remove", str(wt / "villa"))
    (wt / "villa").mkdir()
    (wt / ".venv").unlink()
    run(main_repo, "remove", "feature")
    assert not wt.exists()
    assert len(git(main_repo / "villa", "worktree", "list").splitlines()) == 1
    assert all((main_repo / link).is_dir() for link in LINKS)


def test_remove_refuses_a_locked_worktree(main_repo):
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    git(main_repo, "worktree", "lock", str(wt))
    error = refused(main_repo, "remove", "feature")
    assert error.returncode == 1 and "locked" in error.stderr
    assert "/modules/villa/worktrees/" in git(
        wt / "villa", "rev-parse", "--absolute-git-dir"
    )
    assert all((wt / link).is_symlink() for link in LINKS)


def test_remove_refuses_what_is_not_a_worktree(main_repo):
    error = refused(main_repo, "remove", "absent")
    assert error.returncode == 1 and "no worktree" in error.stderr
    plain = main_repo / ".claude" / "worktrees" / "plain"
    plain.mkdir(parents=True)  # git answers for the main checkout here
    error = refused(main_repo, "remove", "plain")
    assert error.returncode == 1 and "no worktree" in error.stderr
    assert plain.is_dir()


def test_remove_refuses_a_villa_that_is_not_villas_worktree(main_repo):
    run(main_repo, "add", "feature", "main")
    wt = main_repo / ".claude" / "worktrees" / "feature"
    git(main_repo / "villa", "worktree", "remove", str(wt / "villa"))
    (wt / "villa").mkdir()
    (wt / "villa" / "stray").write_text("x\n")
    error = refused(main_repo, "remove", "feature")
    assert error.returncode == 1 and "not one of villa's worktrees" in error.stderr
    assert (wt / "villa" / "stray").exists()
    assert all((wt / link).is_symlink() for link in LINKS)
