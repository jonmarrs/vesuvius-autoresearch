"""Preflight must not reject a submodule checkout.

`preflight.sh` guards multi-hour renders, so a false FAIL is expensive in a
specific way: it blocks a study that was fine, and the natural response to a
preflight that cries wolf is to stop running it.

It tested `[ -d "$VILLA/.git" ]`. For a **submodule**, `.git` is a FILE
containing `gitdir: ...`, not a directory, so the check rejected
`projects/vesuvius-autoresearch/villa` -- the very checkout the current-code
study reads -- while every git command against it worked.
"""

import pathlib
import subprocess

import pytest

_REPO = pathlib.Path(__file__).resolve().parent.parent
_PREFLIGHT = _REPO / "repro/spiral_render/preflight.sh"
_VILLA = _REPO / "villa"


def test_preflight_no_longer_tests_for_a_git_DIRECTORY():
    t = _PREFLIGHT.read_text()
    assert '-d "$VILLA/.git"' not in t, (
        "the -d test rejects submodules, whose .git is a gitlink FILE"
    )
    assert "rev-parse --git-dir" in t, "ask git, do not infer from the layout"


@pytest.mark.skipif(not _VILLA.exists(), reason="villa submodule not present")
def test_the_villa_checkout_is_exactly_the_shape_that_broke_it():
    """Pins WHY the fix was needed. If villa ever becomes a normal clone this
    test should fail loudly rather than quietly stop testing anything."""
    dotgit = _VILLA / ".git"
    assert dotgit.exists()
    assert dotgit.is_file(), "expected a submodule gitlink file, not a directory"
    assert dotgit.read_text().startswith("gitdir:")


@pytest.mark.skipif(not _VILLA.exists(), reason="villa submodule not present")
def test_git_recognises_it_even_though_the_old_check_did_not():
    old_check_would_pass = (_VILLA / ".git").is_dir()
    new_check = subprocess.run(
        ["git", "-C", str(_VILLA), "rev-parse", "--git-dir"],
        capture_output=True,
        check=False,
    )
    assert not old_check_would_pass, "the old check would have passed; fix is moot"
    assert new_check.returncode == 0, "git must recognise the submodule work tree"


def test_a_non_repo_directory_is_still_rejected(tmp_path):
    """The fix must not make the check accept anything at all."""
    r = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "--git-dir"],
        capture_output=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert r.returncode != 0
