"""The fit tree's provenance must stay verifiable, and stay honest about being
a mix of two commits.

`villa-spiral-current/` has no `.git`. Asking git about it returns a commit from
the enclosing workspace repo -- an unrelated project -- which is how a wrong
version reached a published report. These tests pin the recovered answer so a
later copy or upgrade cannot silently change what the arms ran on.
"""

import os
import shutil
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


@pytest.fixture
def synthetic_trees(tmp_path):
    """Tiny local history; no Villa checkout or original research inputs."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    git("init", "-q")
    for sub in mod.SUBTREES:
        (repo / sub).mkdir()
        (repo / sub / "source.py").write_text("original\n")
    git("add", ".")
    git(
        "-c",
        "user.name=Synthetic Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "original subtrees",
    )
    first = git("rev-parse", "HEAD")
    (repo / "spiral-fitting" / "source.py").write_text("updated\n")
    git("add", ".")
    git(
        "-c",
        "user.name=Synthetic Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "updated fit subtree",
    )
    second = git("rev-parse", "HEAD")
    tree = tmp_path / "copy"
    shutil.copytree(repo, tree, ignore=shutil.ignore_patterns(".git"))

    def run(*commits):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(mod.__file__).resolve()),
                "--repo",
                str(repo),
                "--tree",
                str(tree),
                "--commits",
                *commits,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout

    return tree, first, second, run


@pytest.mark.parametrize("mixed_matches", [False, True])
def test_partial_match_does_not_certify_the_whole_tree(synthetic_trees, mixed_matches):
    tree, first, second, run = synthetic_trees
    (tree / "lasagna" / "source.py").write_text("different\n")
    output = run(first, second) if mixed_matches else run(second)
    assert "Only 2/3 compared subtrees matched a candidate" in output
    assert "lasagna          NONE of the candidates" in output
    for sub, commit in (
        ("spiral-fitting", second),
        ("vesuvius", first if mixed_matches else second),
    ):
        assert f"{sub:16} {commit}" in output
    assert "whole tree matches" not in output
    assert "All 3 compared subtrees match" not in output


def test_complete_match_is_scoped_to_compared_tracked_files(synthetic_trees):
    tree, _, second, run = synthetic_trees
    # Extra local files are outside this tool's tracked-file comparison.
    (tree / "lasagna" / "extra.py").write_text("not in the candidate\n")
    output = run(second)
    assert f"All 3 compared subtrees match tracked files at {second}" in output
    assert "extra local files and absent local subtrees were not checked" in output
    assert "whole tree matches" not in output


def test_absent_local_subtrees_are_not_certified(synthetic_trees):
    tree, _, second, run = synthetic_trees
    shutil.rmtree(tree / "lasagna")
    shutil.rmtree(tree / "vesuvius")
    output = run(second)
    assert f"All 1 compared subtrees match tracked files at {second}" in output
    assert "extra local files and absent local subtrees were not checked" in output
    assert "whole tree matches" not in output


def test_mixed_matches_remain_reported_per_subtree(synthetic_trees):
    _, first, second, run = synthetic_trees
    output = run(first, second)
    assert "Compared subtrees selected different candidate matches" in output
    for sub, commit in (
        ("spiral-fitting", second),
        ("lasagna", first),
        ("vesuvius", first),
    ):
        assert f"{sub:16} {commit}" in output
    assert "whole tree matches" not in output
    # Choosing different first matches does not prove no common ref exists.
    assert "THE TREE IS NOT ONE REF" not in output
    assert f"All 3 compared subtrees match tracked files at {second}" in run(second)


def test_no_matching_candidate_is_reported(synthetic_trees):
    tree, _, second, run = synthetic_trees
    for sub in mod.SUBTREES:
        (tree / sub / "source.py").write_text("different\n")
    output = run(second)
    assert "Only 0/3 compared subtrees matched a candidate" in output
    assert "whole tree matches" not in output


def test_no_supported_local_subtrees_means_nothing_compared(synthetic_trees):
    tree, _, second, run = synthetic_trees
    for sub in mod.SUBTREES:
        shutil.rmtree(tree / sub)
    output = run(second)
    assert "No supported local subtrees found; nothing compared" in output
    assert "whole tree matches" not in output


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


def _committed_repo(root, files):
    repo = root / "repo"
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    git("init", "-q")
    git("add", "-f", ".")
    git(
        "-c",
        "user.name=Synthetic Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    return repo, git("rev-parse", "HEAD")


def test_a_tracked_file_named_like_a_skipped_directory_is_still_compared(tmp_path):
    repo, commit = _committed_repo(
        tmp_path,
        {
            "lasagna/source.py": "same\n",
            "lasagna/build_mesh.py": "original\n",
            "lasagna/build/cache.txt": "generated\n",
        },
    )
    tree = tmp_path / "copy"
    shutil.copytree(repo, tree, ignore=shutil.ignore_patterns(".git"))
    (tree / "lasagna/build_mesh.py").write_text("changed\n")
    match, total, diffs = mod.compare(repo, tree, commit, "lasagna")
    # Only the build/ directory is skipped, not every path containing "build".
    assert (match, total) == (1, 2)
    assert diffs == ["lasagna/build_mesh.py"]
    output = subprocess.run(
        [
            sys.executable,
            str(Path(mod.__file__).resolve()),
            "--repo",
            str(repo),
            "--tree",
            str(tree),
            "--commits",
            commit,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout
    # One of two files matching is not a match.
    assert f"{commit}: 1/2 files identical\n" in output
    assert "lasagna          NONE of the candidates" in output
    assert "Only 0/1 compared subtrees matched a candidate" in output


def test_a_tracked_file_missing_from_the_copy_is_named(tmp_path):
    repo, commit = _committed_repo(
        tmp_path, {"lasagna/source.py": "same\n", "lasagna/other.py": "kept\n"}
    )
    tree = tmp_path / "copy"
    shutil.copytree(repo, tree, ignore=shutil.ignore_patterns(".git"))
    (tree / "lasagna/other.py").unlink()
    assert mod.compare(repo, tree, commit, "lasagna") == (
        1,
        2,
        ["lasagna/other.py (absent locally)"],
    )


def test_an_unknown_commit_is_an_error_not_an_absent_subtree(tmp_path):
    repo, commit = _committed_repo(tmp_path, {"lasagna/source.py": "same\n"})
    tree = tmp_path / "copy"
    shutil.copytree(repo, tree, ignore=shutil.ignore_patterns(".git"))
    (tree / "vesuvius").mkdir()

    def run(*commits):
        return subprocess.run(
            [
                sys.executable,
                str(Path(mod.__file__).resolve()),
                "--repo",
                str(repo),
                "--tree",
                str(tree),
                "--commits",
                *commits,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    known = run(commit)
    assert known.returncode == 0, known.stderr
    # A known commit without the subtree is still reported as absent there.
    assert f"{commit}: subtree absent at this commit" in known.stdout
    unknown = run("0" * 40)
    assert unknown.returncode != 0
    assert "0" * 40 in unknown.stderr
    assert "subtree absent" not in unknown.stdout
