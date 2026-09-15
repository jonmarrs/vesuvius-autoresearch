"""Guards on the render-provenance reconstructor.

The reconstruction intersects an arm's `[render]` timestamp with the `origin/main`
reflog. That is only meaningful for arms built WITHOUT an explicit `VILLA_REF`: a
pinned arm never consulted `origin/main`, so the reflog says nothing about it.

Validating the method against a pinned arm reported a MISMATCH that was an artefact
of the check rather than a fault in the method -- which is how the distinction got
found. These tests keep the two kinds of arm apart, and keep the tool honest when
nothing validates it.
"""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "rrp",
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "reconstruct_render_provenance.py",
)
assert SPEC and SPEC.loader
rrp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rrp)

UTC = timezone.utc
MOVES = [
    (datetime(2026, 9, 7, 10, 9, tzinfo=UTC), "d8c5f488a"),
    (datetime(2026, 9, 8, 8, 39, tzinfo=UTC), "5bcc4dd0f"),
    (datetime(2026, 9, 11, 5, 11, tzinfo=UTC), "be09a8503"),
]


def test_resolve_picks_the_sha_held_at_that_moment():
    sha, _ = rrp.resolve(MOVES, datetime(2026, 9, 7, 21, 26, tzinfo=UTC))
    assert sha == "d8c5f488a"


def test_resolve_is_exclusive_at_the_boundary():
    """One minute after a move belongs to the NEW sha, not the old one."""
    sha, _ = rrp.resolve(MOVES, datetime(2026, 9, 8, 8, 40, tzinfo=UTC))
    assert sha == "5bcc4dd0f"


def test_resolve_reports_the_margin_to_the_next_move():
    """A tight margin is the difference between evidence and a guess."""
    _, note = rrp.resolve(MOVES, datetime(2026, 9, 8, 8, 19, tzinfo=UTC))
    assert "next move in 20 min" in note


def test_resolve_refuses_to_guess_before_the_reflog_starts():
    sha, note = rrp.resolve(MOVES, datetime(2026, 5, 1, tzinfo=UTC))
    assert sha == "?" and "no reflog" in note


def test_logged_separates_a_pinned_arm_from_an_unpinned_one(tmp_path):
    """The regression: a pinned arm must not be scored against the reflog."""
    for arm, line in (
        ("pinnedarm", "[setup_workdir] villa be09a8503 -> be09a85035059fd8"),
        ("floatarm", "[setup_workdir] villa origin/main -> bfef6abe073510ee"),
    ):
        (tmp_path / f"x_{arm}_render.log").write_text(line + "\n")
    sha, ref = rrp.logged(str(tmp_path), "pinnedarm")
    assert sha == "be09a8503" and ref == "be09a8503"
    sha, ref = rrp.logged(str(tmp_path), "floatarm")
    assert sha == "bfef6abe0" and ref == "origin/main"


def test_logged_returns_nothing_for_an_arm_with_no_record(tmp_path):
    assert rrp.logged(str(tmp_path), "ghost") == (None, None)


def test_exit_code_2_when_nothing_validated_the_method(tmp_path, capsys, monkeypatch):
    """No logged arm means no validation, and that is not a pass."""
    monkeypatch.setattr(rrp, "reflog", lambda villa: MOVES)
    (tmp_path / "sequence_a1.log").write_text("[render] a1 2026-09-07T21:26:04+00:00\n")
    monkeypatch.setattr(
        "sys.argv",
        ["x", "a1", "--spiral-out", str(tmp_path), "--villa", str(tmp_path)],
    )
    assert rrp.main() == 2
    assert "nothing validated the method" in capsys.readouterr().out
