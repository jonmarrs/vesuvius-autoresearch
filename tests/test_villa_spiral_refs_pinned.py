"""Tripwire: the villa-spiral refs the in-flight comparisons are built from.

**This test guards a rule that was previously enforced by nothing.**
`scripts/watch_villa_upstream.sh` is careful never to fetch villa-spiral, and says
so in its header -- but that is one script's good behaviour, not a guarantee. A
manual `git fetch` in that tree, by anyone, moves `origin/main` and silently
changes what every FUTURE work dir contains, because
`repro/spiral_render/setup_workdir.sh` archives `origin/main` by name.

The failure mode is the expensive one: arms rendered before the move and arms
rendered after it are scored by different code, inside a single comparison, with
nothing in the output saying so. The 908aa7f06 bump changed 15 files on this path
including `lasagna/fit.py`, the flatten step that decides the geometry a render is
scored on -- so this is a demonstrated hazard, not a theoretical one.

These constants are NOT sacred. When a study concludes and we deliberately adopt a
new render ref, edit them in the same commit that records the decision. The point
is to make a silent move loud, not to forbid moving.

Pinned for: docs/preregistration/2026-09-03_patch_bootstrap.md (six arms, ~25h),
and comparable with the six baseline arms that preceded it.
"""

import os
import subprocess
from pathlib import Path

import pytest

# villa-spiral is a separate checkout from the `villa` submodule and lives outside
# this repo, so it is absent on most machines. Both are real, and confusing them is
# easy: the submodule was bumped to 23adee047 on 2026-09-03 while villa-spiral
# stayed at 5479453a, and only the latter matters for renders.
_DEFAULT = Path(__file__).resolve().parents[3] / "villa-spiral"
_VILLA_SPIRAL = Path(os.environ.get("VILLA_SPIRAL", _DEFAULT))

# What renders extract: setup_workdir.sh runs `git archive origin/main`.
RENDER_REF = "5479453a76f0db39a8d657434d3d4c4c517f7245"
# What fits run: the working tree, which is only a meaningful pin while it is clean.
FIT_REF = "6847063ffdb4da898ae8d1d494ebf7d71473f509"

requires_villa_spiral = pytest.mark.skipif(
    not (_VILLA_SPIRAL / ".git").exists(),
    reason=f"villa-spiral checkout not present at {_VILLA_SPIRAL}",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(_VILLA_SPIRAL), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@requires_villa_spiral
def test_the_render_ref_has_not_moved():
    got = _git("rev-parse", "origin/main")
    assert got == RENDER_REF, (
        f"villa-spiral origin/main moved {RENDER_REF[:8]} -> {got[:8]}.\n"
        "setup_workdir.sh archives origin/main BY NAME, so every work dir built "
        "from now on contains different render code than the arms already scored.\n"
        "Arms either side of this move are NOT comparable and no output will say so.\n"
        "Either reset origin/main to the pinned ref, or -- if the move was "
        "deliberate and no comparison is in flight -- update RENDER_REF in the same "
        "commit that records that decision, and re-render any arm that needs it.\n"
        "Diff the render path first: scripts/check_villa_render_path.py "
        f"{RENDER_REF[:8]} {got[:8]}"
    )


@requires_villa_spiral
def test_the_fit_ref_has_not_moved():
    got = _git("rev-parse", "HEAD")
    assert got == FIT_REF, (
        f"villa-spiral HEAD moved {FIT_REF[:8]} -> {got[:8]}.\n"
        "Fits run the working tree. Current villa defaults to 2 flow stages after "
        "#1693; arms fitted across that boundary are not comparable."
    )


@requires_villa_spiral
def test_the_fit_tree_is_clean_or_the_fit_ref_means_nothing():
    """'Pinned to the working tree at 6847063f' is only true while the tree
    equals that commit. Uncommitted edits make the fit code unreproducible from
    any ref, which is worse than a moved pin because it leaves no trace at all."""
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    assert dirty == "", (
        "villa-spiral has uncommitted changes to TRACKED files:\n"
        f"{dirty}\n"
        "The registration pins fits to the working tree, so these edits are part "
        "of the fit code and are recorded nowhere. Commit them or revert them."
    )


def test_setup_workdir_still_archives_origin_main():
    """Binds RENDER_REF to the mechanism instead of asserting a number in
    isolation. If setup_workdir.sh stops archiving `origin/main`, RENDER_REF is
    no longer describing what renders actually use, and the tripwire above would
    keep passing while guarding nothing.

    This is the failure pattern the ScrollGT audit found repeatedly: not bugs in
    the checking code, but properties measured once and never re-checked.
    """
    script = (
        Path(__file__).resolve().parent.parent
        / "repro"
        / "spiral_render"
        / "setup_workdir.sh"
    )
    text = script.read_text()
    assert "git archive origin/main" in text or "archive origin/main" in text, (
        "setup_workdir.sh no longer archives `origin/main`. RENDER_REF in this "
        "file pins origin/main, so it now guards something renders do not use. "
        "Update both together."
    )
