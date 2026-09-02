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
def test_the_scorer_and_renderer_themselves_are_unchanged():
    """Documents the shape of the current divergence: it is confined to the
    flatten side. If spiral-fitting/ ever moves too, serial_folds.patch and every
    scoring comparison need re-checking, so this failing is informative."""
    changed, _, _ = mod.compare(_VILLA, "5479453a", "HEAD")
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
