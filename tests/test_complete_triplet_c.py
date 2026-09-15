"""Guards on the triplet-completion waiter.

It sits idle for hours and then starts a multi-hour render unattended, so the two
properties that matter are: it waits on a CONDITION rather than a process name, and
it cannot mistake itself for the job it is waiting on.

Four variants of the self-match bug have bitten this project -- a driver that waited
two hours for its own reflection, a `pkill -f` that killed the shell issuing it, a
guard that matched the shell that wrote it via heredoc, and a guard that counted the
shell invoking it. The waiter must key on `guard_heavy_analysis.py --fail-if-any`,
which matches argv[0] and the containerised renderer, not on a grep for its own name.
"""

from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "repro"
    / "spiral_render"
    / "complete_triplet_c.sh"
)


def test_script_exists_and_is_executable():
    assert SCRIPT.exists() and SCRIPT.stat().st_mode & 0o111


def _code_lines(src: str) -> str:
    """Comments are where the pgrep lesson is WRITTEN DOWN; only code matters here."""
    return "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))


def test_waits_via_the_guard_not_pgrep():
    src = SCRIPT.read_text()
    assert "--fail-if-any" in src, "must wait on the guard's presence check"
    code = _code_lines(src)
    assert "pgrep" not in code, (
        "pgrep -f matches any command line containing the string"
    )
    assert "pkill" not in code


def test_pins_villa_and_ref_so_the_recovery_matches_the_corpus():
    """An unpinned ref is how the corpus got split across two render trees."""
    src = SCRIPT.read_text()
    assert 'VILLA_REF="${VILLA_REF:-be09a8503}"' in src
    assert 'VILLA="${VILLA:-$REPO/villa}"' in src


def test_passes_all_three_arms_relying_on_idempotency():
    """run_arm_sequence.sh skips scored arms and existing fits, so naming all
    three renders exactly what is missing rather than redoing work."""
    src = SCRIPT.read_text()
    for arm in ("curbase_s7", "curbase_s8", "curbase_s9"):
        assert arm in src


def test_deadline_is_sized_for_never_finishing_not_for_slow():
    """s8 took 3h14m while thrashing; a tight deadline would have killed it."""
    src = SCRIPT.read_text()
    assert 'DEADLINE_H="${DEADLINE_H:-24}"' in src


def test_refuses_to_start_if_the_deadline_passes_with_a_job_running():
    """Starting a second render alongside one is how the box gets swapped flat."""
    src = SCRIPT.read_text()
    assert "NOT starting" in src
