"""Sibling repos (../scrollgt, ../inkdelta, ../inkagree) resolve beside the main checkout.

A linked worktree lives inside the main checkout, at .claude/worktrees/<branch>, so a
path built from the worktree's own parent finds nothing: in a worktree, 38 tests that
check this repo against ScrollGT, inkdelta, inkagree and villa-spiral skipped instead
of running.
"""

import re
import subprocess
from pathlib import Path

import pytest

from scripts.sibling_checkouts import main_checkout

REPO = Path(__file__).resolve().parents[1]
SIBLINGS = ("scrollgt", "inkdelta", "inkagree", "villa-spiral")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo_with_worktree(tmp_path):
    main = tmp_path / "projects" / "repo"
    main.mkdir(parents=True)
    _git(main, "init", "-q")
    _git(
        main,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "init",
    )
    worktree = main / ".claude" / "worktrees" / "branch"
    _git(main, "worktree", "add", "-q", "-b", "branch", str(worktree))
    return main, worktree


def test_the_main_checkout_is_its_own_main_checkout(repo_with_worktree):
    main, _ = repo_with_worktree
    assert main_checkout(main) == main


def test_a_linked_worktree_resolves_to_the_main_checkout(repo_with_worktree):
    main, worktree = repo_with_worktree
    assert main_checkout(worktree) == main


def test_this_checkout_resolves_to_a_main_checkout():
    assert (main_checkout(REPO) / ".git").is_dir()


def _code_lines(path):
    for line in path.read_text().splitlines():
        code = line.split("#")[0]
        if code.strip():
            yield code


# Building a sibling's path from the checkout itself: `REPO.parent / "scrollgt"`,
# `os.path.dirname(_REPO), "scrollgt"`, `REPO_ROOT, "..", "scrollgt"`,
# `parents[2] / "scrollgt"`.
_FROM_CHECKOUT = re.compile(
    r"(\.parent\b|dirname\(|\"\.\.\"|parents\[\d\])[^#]*\"("
    + "|".join(SIBLINGS)
    + r")\""
)


@pytest.mark.parametrize("folder", ["scripts", "tests"])
def test_no_sibling_path_is_built_from_the_checkout_itself(folder):
    offenders = [
        f"{path.relative_to(REPO)}: {code.strip()}"
        for path in sorted((REPO / folder).rglob("*.py"))
        for code in _code_lines(path)
        if _FROM_CHECKOUT.search(code) and "main_checkout()" not in code
    ]
    assert not offenders, "resolve siblings with main_checkout():\n" + "\n".join(
        offenders
    )
