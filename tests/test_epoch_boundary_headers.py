"""The epoch-boundary reports and the cycle-length study read every cycle in their windows.

#135 found that the sprint-log parser dropped a cycle headed `CRASHED (OOM)` and gave its minutes to the next
cycle's overhead. Its review could not check the published reports, because the October sprint logs are not
committed. They are in the loop checkout: every header in these windows parses under both #126's pattern and #135's,
and none is an OOM crash, so no published row changes. Skipped where the logs are absent.
"""

import glob
import json
import re
from pathlib import Path

import pytest

from scripts.sibling_checkouts import main_checkout

ROOT = Path(__file__).resolve().parents[1]
LOGS = main_checkout()
OLD = re.compile(r"Cycle (\d+): (\S+) \((\w+)\)$")  # #126
NEW = re.compile(r"Cycle (\d+): (\S+) \((\w+)( \(OOM\))?\)$")  # #135
WINDOWS = {
    "sprint_logs/sprint_log_2026-10-1[345]_*.md": 151,  # epoch_boundary_overhead_inline.json
    "sprint_logs/sprint_log_2026-10-1[67]_*.md": 92,  # _workers, _restarts, and _persistent's one log
    "sprint_logs/sprint_log_2026-10-18_*.md": 54,  # the cycle-length study's 10-18 day and night
}


def test_the_windows_are_the_ones_the_reports_read():
    src = {
        name: json.loads(
            (ROOT / f"reports/epoch_boundary_overhead_{name}.json").read_text()
        )["sources"]["sprint_logs"]
        for name in ("inline", "workers", "restarts", "persistent")
    }
    assert src["inline"] == "sprint_logs/sprint_log_2026-10-1[345]_*.md"
    assert (
        src["workers"] == src["restarts"] == "sprint_logs/sprint_log_2026-10-1[67]_*.md"
    )
    assert (
        src["persistent"] == "sprint_logs/sprint_log_2026-10-17_19-10-03_night_shift.md"
    )
    replication = json.loads(
        (ROOT / "reports/cycle_length_gain_replication_2026-10-19.json").read_text()
    )
    assert [s for s in replication["sources"]["sprint_logs"] if "2026-10-18_" in s] == [
        "sprint_logs/sprint_log_2026-10-18_07-35-03_day_shift.md",
        "sprint_logs/sprint_log_2026-10-18_19-10-03_night_shift.md",
    ]


@pytest.mark.parametrize("pattern", sorted(WINDOWS))
def test_every_cycle_header_in_the_window_parses(pattern):
    logs = sorted(glob.glob(str(LOGS / pattern)))
    if not logs:
        pytest.skip(f"no sprint logs at {LOGS / pattern}")
    heads = [
        line[3:].strip()
        for log in logs
        for line in open(log)
        if line.startswith("## Cycle")
    ]
    assert len(heads) == WINDOWS[pattern]
    assert all(OLD.match(h) and NEW.match(h) for h in heads), [
        h for h in heads if not OLD.match(h)
    ]
    assert not any("(OOM)" in h for h in heads)


def test_the_review_states_the_counts():
    review = " ".join(
        (ROOT / "docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-19_CYCLE_LENGTH_AND_FILING.md")
        .read_text()
        .split()
    )
    assert (
        "(151 on 10-13 to 15, 92 on 10-16/17)" in review
        and "cycle-length study's 10-18 logs (54)" in review
    )
