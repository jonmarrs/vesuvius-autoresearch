"""The fit tree's provenance must stay verifiable, and stay honest about being
a mix of two commits.

`villa-spiral-current/` has no `.git`. Asking git about it returns a commit from
the enclosing workspace repo -- an unrelated project -- which is how a wrong
version reached a published report. These tests pin the recovered answer so a
later copy or upgrade cannot silently change what the arms ran on.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import identify_fit_tree_provenance as mod  # noqa: E402

_TREE = Path("/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current")
_VILLA = _REPO / "villa"
_needs = pytest.mark.skipif(
    not (_TREE.is_dir() and (_VILLA / ".git").exists()),
    reason="fit tree or villa submodule not present",
)


@_needs
def test_the_tree_is_a_copy_not_a_checkout():
    """If this ever fails, the tree gained its own .git and should be asked
    directly rather than fingerprinted."""
    assert not (_TREE / ".git").exists()


@_needs
def test_asking_git_about_it_gives_a_misleading_answer():
    """Pins the trap itself. git -C answers about the enclosing repo, and the
    commit it returns has nothing to do with villa."""
    out = subprocess.run(
        ["git", "-C", str(_TREE), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        pytest.skip("git declined; the trap is not reachable here")
    sha = out.stdout.strip()
    inside = subprocess.run(
        ["git", "-C", str(_VILLA), "cat-file", "-e", sha],
        capture_output=True,
        check=False,
    )
    assert inside.returncode != 0, (
        "the commit git reports for the fit tree happens to exist in villa; "
        "the trap this guards has changed shape and the test needs rewriting"
    )


@_needs
@pytest.mark.parametrize(
    "subtree,commit",
    [
        ("spiral-fitting", "be09a8503"),
        ("lasagna", "d8c5f488a"),
        ("vesuvius", "d8c5f488a"),
    ],
)
def test_each_subtree_matches_the_commit_the_reports_claim(subtree, commit):
    match, total, diffs = mod.compare(_VILLA, _TREE, commit, subtree)
    assert total > 0, f"{subtree} not present at {commit}"
    assert match == total, (
        f"{subtree} differs from {commit} in {len(diffs)}+ files: {diffs}"
    )


@_needs
def test_the_tree_really_is_two_refs_not_one():
    """The point of the correction. A single-commit provenance statement cannot
    be right for this tree."""
    fit, _, _ = mod.compare(_VILLA, _TREE, "be09a8503", "spiral-fitting")
    fit_n = len(mod.tracked_files(_VILLA, "be09a8503", "spiral-fitting"))
    las, las_n, _ = mod.compare(_VILLA, _TREE, "be09a8503", "lasagna")
    assert fit == fit_n, "spiral-fitting should match be09a8503"
    assert las < las_n, "lasagna must NOT match be09a8503, or the correction was wrong"


@_needs
def test_the_arms_all_postdate_the_tree_being_written():
    """Validity of every current-code comparison rests on this: the tree was
    written once and no arm ran before it."""
    newest = max(
        p.stat().st_mtime
        for sub in ("spiral-fitting", "lasagna")
        for p in (_TREE / sub).rglob("*.py")
        if ".venv" not in p.parts
    )
    spiral_out = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
    arms = [
        d
        for d in spiral_out.glob("*_s?")
        if d.is_dir() and any(t in d.name for t in ("curbase", "nosamecur"))
    ]
    if not arms:
        pytest.skip("arm directories not present")
    for a in arms:
        assert a.stat().st_mtime > newest, (
            f"{a.name} predates the tree it claims to use"
        )
