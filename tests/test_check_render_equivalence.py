"""Tests for the render-equivalence checker.

It answers the question that follows the monitor's: the monitor says whether the
hot path changed, this says whether that change can reach a render. On
2026-09-14 those had different answers.

The dangerous failure is a false INTERCHANGEABLE -- declaring two refs equivalent
when a render would differ -- because it would let a corpus split silently, which
is exactly what happened on 2026-09-11 and took mtime archaeology to find. So the
tests weight that direction.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import check_render_equivalence as mod  # noqa: E402

_VILLA = _REPO / "villa"
_needs = pytest.mark.skipif(
    not (_VILLA / ".git").exists(), reason="villa submodule absent"
)


def test_it_checks_exactly_what_setup_workdir_extracts():
    """If these drift apart, the checker is inspecting paths the render does not
    use, or missing ones it does."""
    setup = (_REPO / "repro/spiral_render/setup_workdir.sh").read_text()
    for p in mod.EXTRACTED:
        assert p in setup, f"{p} is checked but not extracted by setup_workdir.sh"


def test_the_entry_points_are_the_two_the_pipeline_runs():
    assert mod.ENTRY_POINTS == (
        "spiral-fitting/render_ink.py",
        "spiral-fitting/get_ink_metrics.py",
    )


@_needs
def test_a_ref_against_itself_is_interchangeable():
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "be09a8503",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" in out.stdout


@_needs
@pytest.mark.parametrize("ref", ["38c2b4278", "bfef6abe0", "3b398f7cc", "d82e13edf"])
def test_the_four_cleared_refs_still_read_interchangeable(ref):
    """These were cleared by hand on 2026-09-14. If the checker ever disagrees,
    either it broke or one of those clearances was wrong."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            ref,
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" in out.stdout, f"{ref} no longer reads as interchangeable"


@_needs
def test_the_one_real_hot_path_change_is_NOT_called_interchangeable():
    """The load-bearing test. d9d70bef1 changes tifxyz.py, which render_ink
    imports. A checker that called this interchangeable would let a corpus split
    silently."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "d9d70bef1",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" not in out.stdout
    assert "NEEDS A HUMAN" in out.stdout
    assert "tifxyz.py" in out.stdout


@_needs
def test_the_old_09_11_split_would_have_been_caught():
    """The bump that actually split the corpus. If the checker had existed, this
    is the verdict it would have given -- lasagna and vesuvius/src both differ."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "d8c5f488a",
            "--to-ref",
            "be09a8503",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" not in out.stdout
    assert "lasagna" in out.stdout and "DIFFERS" in out.stdout


@_needs
def test_imports_of_finds_a_known_import():
    mods = mod.imports_of(str(_VILLA), "be09a8503", "spiral-fitting/render_ink.py")
    assert "tifxyz" in mods, "render_ink.py imports tifxyz; the tracer missed it"


def test_lasagna_is_treated_as_a_pipeline_stage_not_a_library():
    """The bug this tool shipped with. `lasagna` is the flatten, invoked by
    run_render.sh as its own step, so NOTHING in ENTRY_POINTS imports it. The
    first version only flagged files the entry points import, so a commit titled
    "lasagna flatten memory" that rewrote 571 lines of it came back with only
    tifxyz.py named -- and a lasagna-ONLY change would have read RENDER-INERT.

    A false INTERCHANGEABLE is the failure that lets a corpus split silently,
    which is what happened on 2026-09-11.
    """
    assert "lasagna" in mod.STAGE_PATHS
    assert not any("lasagna" in e for e in mod.ENTRY_POINTS), (
        "if an entry point ever imports lasagna, the stage/library split needs "
        "rethinking rather than both applying"
    )


@_needs
def test_a_lasagna_change_is_never_called_inert():
    """1f544fa71 changes lasagna/fit.py, fit2tifxyz.py, model.py and optimizer.py.
    Whatever else it reports, it must not report that a render is unaffected."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "1f544fa71",
        ],
        capture_output=True,
        text=True,
    )
    assert "RENDER-INERT" not in out.stdout
    assert "INTERCHANGEABLE" not in out.stdout
    assert "lasagna/fit.py" in out.stdout, "the flatten must be named explicitly"


def test_test_files_are_excluded_from_suspects():
    """43 changed files reduced to 1 only because tests are dropped. If that
    stopped working the output would be unusable rather than wrong."""
    src = (_REPO / "scripts/check_render_equivalence.py").read_text()
    assert '"/tests/" not in f' in src
    assert 'startswith("test_")' in src
