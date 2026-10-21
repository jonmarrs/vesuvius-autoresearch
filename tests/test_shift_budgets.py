"""The loop's cycle budget per shift. Owner's decision 2026-10-20: nights run 15-minute cycles, as days do (the
cycle-length study, replicated 2026-10-19, found no measurable gain from 60 minutes)."""

import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def loop():
    import run_autoresearch_loop

    return run_autoresearch_loop


def test_both_shifts_run_15_minute_cycles(loop):
    assert loop.SHIFT_BUDGETS == {"DAY SHIFT": 900, "NIGHT SHIFT": 900}


@pytest.mark.parametrize(
    "hour, shift",
    [
        (0, "NIGHT SHIFT"),
        (6, "NIGHT SHIFT"),
        (7, "DAY SHIFT"),
        (18, "DAY SHIFT"),
        (19, "NIGHT SHIFT"),
        (23, "NIGHT SHIFT"),
    ],
)
def test_the_shift_by_hour(loop, hour, shift):
    assert loop.shift_for_hour(hour) == (shift, loop.SHIFT_BUDGETS[shift])


def test_the_longest_run_follows_the_budgets(loop):
    """A loop's own run past this is stopped as past any cycle's timeout (budget + 300 s in main)."""
    assert loop.LONGEST_RUN_SECONDS == max(loop.SHIFT_BUDGETS.values()) + 300 == 1200


def test_main_takes_its_budget_from_the_table(loop):
    src = inspect.getsource(loop.main)
    assert (
        "shift_for_hour(" in src
        and "default_budget = 3600" not in src
        and "default_budget = 900" not in src
    )


def test_the_docs_state_the_budgets():
    readme = " ".join((ROOT / "README.md").read_text().split())
    program = " ".join((ROOT / "docs/program.md").read_text().split())
    assert (
        "(default 15 mins for both shifts" in readme
        and "60 mins for Night Shift" not in readme
    )
    assert "(900s for both shifts" in program and "3600s for Night Shift" not in program


def test_main_ends_the_sprint_by_the_same_table(loop):
    """The sprint ends when the hour leaves the shift it started in, by shift_for_hour, not a second copy of its
    hours."""
    src = inspect.getsource(loop.main)
    assert "_shift_over = shift_for_hour(_hr)[0] != shift_name" in src
    assert "7 <= _hr < 19" not in src


@pytest.mark.parametrize(
    "doc",
    [
        "README.md",
        "docs/program.md",
        "METHOD.md",
        "docs/RESEARCH_PAPER.md",
        "CONTRIBUTING.md",
        ".github/README_SKELETON.md",
    ],
)
def test_the_other_docs_date_the_60_minute_nights(doc):
    """Each gave 60-minute nights in the present tense after #159; nights ran 60 minutes only from 2026-04-29."""
    text = " ".join((ROOT / doc).read_text().split())
    assert "from 2026-04-29 to 2026-10-20" in text
    for old in (
        "60 at night.",
        "60-minute cycles, runs",
        "60-min cycles)",
        "3600 s/cycle).",
    ):
        assert old not in text, old
