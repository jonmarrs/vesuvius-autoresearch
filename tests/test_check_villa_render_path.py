"""Tests for the villa render-path equivalence checker.

The tool exists because the weaker check passed and the stronger one did not: the
908aa7f06 bump moved no path our code reads, and still changed lasagna/fit.py,
the flatten step that decides the geometry a render is scored on.

A checker that cannot fail is worthless, so the tests that matter here are the
ones pinning that it reports a real difference and exits nonzero, and that its
"identical" verdict is reachable.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import check_villa_render_path as mod  # noqa: E402

_VILLA = _REPO / "villa"
requires_villa = pytest.mark.skipif(
    not (_VILLA / ".git").exists(), reason="villa submodule not checked out"
)


def _has(ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(_VILLA), "cat-file", "-e", f"{ref}^{{commit}}"],
            capture_output=True,
        ).returncode
        == 0
    )


def test_the_extracted_trees_match_what_setup_workdir_pulls():
    """If setup_workdir.sh starts extracting another tree and this list does not
    follow, the checker silently stops covering part of the render path."""
    script = (_REPO / "repro" / "spiral_render" / "setup_workdir.sh").read_text()
    archive = [ln for ln in script.splitlines() if "git -C" in ln and "archive" in ln]
    assert archive, "setup_workdir.sh no longer has a git archive line"
    for tree in mod.EXTRACTED_TREES:
        assert tree in archive[0], f"{tree} not in setup_workdir's archive line"


def test_the_hot_path_files_are_inside_the_extracted_trees():
    for p in mod.HOT_PATH:
        assert any(p.startswith(t + "/") for t in mod.EXTRACTED_TREES), p


@requires_villa
def test_a_ref_compared_with_itself_is_identical():
    """The 'no difference' verdict must be reachable, or the tool always cries
    wolf and gets ignored."""
    changed, added, removed = mod.compare(_VILLA, "HEAD", "HEAD")
    assert (changed, added, removed) == ([], [], [])


@requires_villa
def test_it_exits_zero_when_the_refs_match():
    rc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "check_villa_render_path.py"),
            "HEAD",
            "HEAD",
        ],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "identical" in rc.stdout


@requires_villa
@pytest.mark.skipif(not _has("5479453a"), reason="5479453a not in this checkout")
def test_it_catches_the_change_that_motivated_it():
    """lasagna/fit.py differs between the render source ref and the current pin.
    This is the concrete regression the tool was written for; if it ever stops
    reporting it, the tool has broken rather than the world having healed."""
    changed, _, _ = mod.compare(_VILLA, "5479453a", "HEAD")
    assert "lasagna/fit.py" in changed


@requires_villa
@pytest.mark.skipif(not _has("5479453a"), reason="5479453a not in this checkout")
def test_it_exits_nonzero_on_a_real_difference():
    rc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "check_villa_render_path.py"),
            "5479453a",
            "HEAD",
        ],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 1, rc.stdout
    assert "HOT PATH CHANGED" in rc.stdout
    assert "not comparable" in rc.stdout


@requires_villa
@pytest.mark.skipif(not _has("5479453a"), reason="5479453a not in this checkout")
@pytest.mark.skipif(not _has("be09a8503"), reason="be09a8503 not in this checkout")
def test_the_scorer_and_renderer_themselves_are_unchanged():
    """Documents the shape of the divergence: up to the render ref every pinned
    study uses (VILLA_REF=be09a8503), it is confined to the flatten side. If
    spiral-fitting/ moves there too, serial_folds.patch and every scoring
    comparison need re-checking, so this failing is informative.

    It compared against the submodule HEAD until the 9afddaf0f bump, which moves
    all three files. That failure was acted on: the patch tests now bind to the
    render ref, and no registered comparison renders from the new pin."""
    changed, _, _ = mod.compare(_VILLA, "5479453a", "be09a8503")
    for p in (
        "spiral-fitting/render_ink.py",
        "spiral-fitting/get_ink_metrics.py",
        "spiral-fitting/tifxyz.py",
    ):
        assert p not in changed, f"{p} changed; re-check the scoring comparisons"


def test_a_missing_checkout_is_refused_clearly(tmp_path):
    rc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "check_villa_render_path.py"),
            "--repo",
            str(tmp_path / "nope"),
        ],
        capture_output=True,
        text=True,
    )
    assert rc.returncode != 0
    assert "no villa checkout" in rc.stderr + rc.stdout


# --- documentation is not the render path -------------------------------------
#
# Our own merged docs PR (villa#1721, autoresearch.md) flipped the verdict to
# DIFFERS on 2026-09-07. A markdown change cannot alter a render, and a gate that
# fires on documentation trains its reader to ignore it -- which is exactly how
# the 908aa7f06 case it was built for would slip past.


def test_markdown_and_images_are_classified_as_docs():
    for p in (
        "spiral-fitting/autoresearch.md",
        "spiral-fitting/README.txt",
        "lasagna/docs/diagram.png",
        "vesuvius/src/x.SVG",
    ):
        assert mod.is_docs(p), p


def test_code_is_not_classified_as_docs():
    for p in (
        "spiral-fitting/get_ink_metrics.py",
        "lasagna/fit.py",
        "vesuvius/src/tifxyz.cpp",
        "spiral-fitting/run.sh",
    ):
        assert not mod.is_docs(p), p


def test_a_hot_path_file_is_never_treated_as_docs():
    """Defence in depth: nothing in HOT_PATH may be excused as documentation."""
    for p in mod.HOT_PATH:
        assert not mod.is_docs(p), p


# --- what the gate sees, in a throwaway villa-shaped repository -----------------

_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}
_FILES = (
    "spiral-fitting/render_ink.py",
    "lasagna/fit.py",
    "vesuvius/src/a.py",
    "volume-cartographer/core/x.cpp",
    "volume-cartographer/apps/src/vc_render_tifxyz.cpp",
)


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        env=_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def villa_like(tmp_path):
    repo = tmp_path / "villa"
    for path in _FILES:
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(f"{path}\n")
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "old")
    return repo


def _gate(repo, old="HEAD~1", new="HEAD"):
    return subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "check_villa_render_path.py")]
        + ["--repo", str(repo), old, new],
        env=_ENV,
        capture_output=True,
        text=True,
    )


def test_a_file_moved_off_the_sampler_path_is_reported(villa_like):
    """git diff lists a rename only where the file went, here outside the image
    path, so the move that took it off the sampler's build went unreported."""
    _git(
        villa_like, "mv", "volume-cartographer/core/x.cpp", "volume-cartographer/x.cpp"
    )
    _git(villa_like, "commit", "-q", "-m", "move")
    r = _gate(villa_like)
    assert "IMAGE PATH CHANGED" in r.stdout, r.stdout
    assert "volume-cartographer/core/x.cpp" in r.stdout


def test_a_name_git_would_quote_is_reported_as_it_is(villa_like):
    """core.quotePath writes "volume-cartographer/core/\\303..." and a space split
    the name: neither then matched the image path."""
    name = "volume-cartographer/core/ünï code.cpp"
    (villa_like / name).write_text("x\n")
    _git(villa_like, "add", ".")
    _git(villa_like, "commit", "-q", "-m", "add")
    r = _gate(villa_like)
    assert "IMAGE PATH CHANGED (1)" in r.stdout, r.stdout
    assert name in r.stdout


def test_a_removed_tree_is_a_difference_not_an_error(villa_like):
    """ls-tree <ref>:lasagna fails where lasagna is gone, so the largest change the
    render path can have ended the gate with a git error and no verdict."""
    _git(villa_like, "rm", "-q", "-r", "lasagna")
    _git(villa_like, "commit", "-q", "-m", "drop lasagna")
    r = _gate(villa_like)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "REMOVED (1)" in r.stdout and "lasagna/fit.py" in r.stdout
    assert "DIFFERS" in r.stdout


def test_a_mode_change_is_a_change(villa_like):
    """Same content, now executable: the blob hash alone says nothing moved."""
    _git(villa_like, "update-index", "--chmod=+x", "spiral-fitting/render_ink.py")
    _git(villa_like, "commit", "-q", "-m", "chmod")
    r = _gate(villa_like)
    assert r.returncode == 1, r.stdout
    assert "HOT PATH CHANGED (1)" in r.stdout


def test_identical_refs_still_pass(villa_like):
    r = _gate(villa_like, "HEAD", "HEAD")
    assert r.returncode == 0 and "identical" in r.stdout, r.stdout + r.stderr


def test_it_exits_2_when_it_cannot_compare(villa_like, tmp_path):
    """1 means the render path differs; a bad ref or no checkout is neither answer."""
    r = _gate(villa_like, "HEAD", "no-such-ref")
    assert r.returncode == 2 and "failed" in r.stderr, r.stdout + r.stderr
    r = _gate(tmp_path / "nope", "HEAD", "HEAD")
    assert r.returncode == 2 and "no villa checkout" in r.stderr


def test_a_tree_that_appears_differs_too(villa_like):
    """Reversed, the removed-tree case lists only added files, which alone do not
    set the verdict: the gate said identical."""
    _git(villa_like, "rm", "-q", "-r", "lasagna")
    _git(villa_like, "commit", "-q", "-m", "drop lasagna")
    r = _gate(villa_like, "HEAD", "HEAD~1")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "TREE ADDED: lasagna" in r.stdout and "DIFFERS" in r.stdout


def test_a_tree_at_neither_ref_cannot_be_compared(villa_like):
    _git(villa_like, "rm", "-q", "-r", "lasagna")
    _git(villa_like, "commit", "-q", "-m", "drop lasagna")
    _git(villa_like, "commit", "-q", "--allow-empty", "-m", "again")
    r = _gate(villa_like)
    assert r.returncode == 2 and "lasagna: at neither ref" in r.stderr, r.stdout


def test_a_directory_git_answers_around_is_refused(villa_like):
    """An uninitialised submodule is an empty directory, where git answers for
    the repository around it."""
    empty = villa_like / "spiral-fitting" / "empty"
    empty.mkdir()
    r = _gate(empty)
    assert r.returncode == 2 and "not a repository of its own" in r.stderr, r.stdout


def test_an_inherited_git_dir_is_ignored(villa_like, tmp_path):
    """A hook exports GIT_DIR, which would point every call at its repository."""
    other = tmp_path / "other"
    _git(tmp_path, "init", "-q", "-b", "main", str(other))
    _git(other, "commit", "-q", "--allow-empty", "-m", "elsewhere")
    _git(villa_like, "update-index", "--chmod=+x", "lasagna/fit.py")
    _git(villa_like, "commit", "-q", "-m", "chmod")
    r = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "check_villa_render_path.py")]
        + ["--repo", str(villa_like), "HEAD~1", "HEAD"],
        env=_ENV | {"GIT_DIR": str(other / ".git"), "GIT_GLOB_PATHSPECS": "1"},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1 and "HOT PATH CHANGED (1)" in r.stdout, r.stdout + r.stderr


def test_refs_that_differ_only_in_docs_and_elsewhere_are_identical(villa_like):
    (villa_like / "lasagna" / "README.md").write_text("docs\n")
    (villa_like / "unrelated.py").write_text("x\n")
    _git(villa_like, "add", ".")
    _git(villa_like, "commit", "-q", "-m", "docs")
    (villa_like / "lasagna" / "README.md").write_text("more docs\n")
    _git(villa_like, "commit", "-q", "-am", "docs again")
    r = _gate(villa_like)
    assert r.returncode == 0 and "identical" in r.stdout, r.stdout + r.stderr
    assert "documentation changed (1)" in r.stdout


def test_names_are_read_as_they_are(villa_like):
    """-z: without it git quotes a name like this one in every listing."""
    name = 'lasagna/ünï "x".py'
    (villa_like / name).write_text("x\n")
    _git(villa_like, "add", ".")
    _git(villa_like, "commit", "-q", "-m", "add")
    assert name in mod.blobs(villa_like, "HEAD", "lasagna")


def test_a_name_that_is_not_utf8_is_compared_not_a_crash(villa_like):
    name = os.fsdecode(b"lasagna/caf\xe9.py")
    (villa_like / name).write_text("x\n")
    _git(villa_like, "add", ".")
    _git(villa_like, "commit", "-q", "-m", "add")
    (villa_like / name).write_text("y\n")
    _git(villa_like, "commit", "-q", "-am", "change")
    r = _gate(villa_like)
    assert r.returncode == 1 and "Traceback" not in r.stderr, r.stderr
    assert "lasagna/caf\\udce9.py" in r.stdout
