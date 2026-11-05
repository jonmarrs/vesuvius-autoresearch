"""Bind the November filing draft to the round's rollover record, villa's criteria at the rollover, and the measured
records of each contribution it names."""

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = (ROOT / "docs/PRIZE_FILING_2026-11_DRAFT.md").read_text()
TEXT = " ".join(DRAFT.split())
ROLLOVER = json.loads(
    (ROOT / "reports/evidence/november_form_rollover_2026-11-05.json").read_text()
)
OPENED = "9c343a16494cf61d72727cbc85dc5e12e8773677"  # villa #2301's merge
# villa #2450, merged just before it
CRITERIA = "aa8784bff0b43149374f7d9928b899bc5f7ae30d"
OCTOBER_DEADLINE = dt.datetime(2026, 10, 31, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))  # fmt: skip


def _utc(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _section(heading: str) -> str:
    return DRAFT.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _url_field() -> list:
    block = _section("URL field").split("```", 2)[1]
    return [line.strip() for line in block.splitlines()[1:] if line.strip()]


def test_the_round_s_deadline_and_form_are_the_rollover_s():
    row = {r["number"]: r for r in ROLLOVER["rollover_prs"]}[2301]
    assert row["state"] == "MERGED"
    opened = _utc(row["merged_at"])
    assert f"opened {opened:%Y-%m-%d %H:%M} UTC (2026-11-04 Pacific)" in TEXT
    assert opened.astimezone(ZoneInfo("America/Los_Angeles")).date() == dt.date(2026, 11, 4)  # fmt: skip
    assert f"**deadline {row['deadline_after']}**" in TEXT
    form = ROLLOVER["filing_form"]
    assert form["url"] == row["form_after"]
    assert DRAFT.count(form["url"]) == 2  # the round's form and the filing-day check
    assert ROLLOVER["expected_form_title"] == form["title"] == "November 2026 Progress Prizes"  # fmt: skip
    assert form["accepting_responses"] and ROLLOVER["filing_form_title_matches"]
    checked = _utc(ROLLOVER["checked_at_utc"])
    assert f"passed on {checked:%Y-%m-%d} at {checked:%H:%M} UTC" in TEXT
    assert "--expected-title 'November 2026 Progress Prizes'" in DRAFT


def test_the_url_field_is_exactly_the_november_merges():
    """Each merge in "Merged in November" is cited once in the URL field, with its Pacific date and UTC stamp."""
    merged = re.findall(
        r"\[villa #(\d+)\]\((\S+?)\) \(merged (\d{4}-\d\d-\d\d) Pacific; `(\S+)`",
        " ".join(_section("Merged in November").split()),
    )
    assert merged
    assert _url_field() == [url for _, url, _, _ in merged]
    for number, url, day, stamp in merged:
        assert url == f"https://github.com/ScrollPrize/villa/pull/{number}"
        when = _utc(stamp).astimezone(ZoneInfo("America/Los_Angeles"))
        assert when.date().isoformat() == day
        assert when > OCTOBER_DEADLINE and when.month == 11


def test_2258_s_numbers_are_its_record():
    rows = json.loads(
        (ROOT / "reports/villa_fractional_plane_spacing_2026-10-20.json").read_text()
    )["rows"]
    fractional = [r for r in rows if abs(r["spacing"] - 52.733333) < 1e-5]
    changes = [f"{r['before']['dots']} → {r['after']['dots']}" for r in fractional]
    assert f"seed counts change {', '.join(changes[:-1])} and {changes[-1]}" in TEXT
    worst = max(abs(r["after"]["dots"] - r["before"]["dots"]) / r["before"]["dots"] for r in fractional)  # fmt: skip
    assert f"at most {100 * worst:.2f}%" in TEXT
    assert all(r["identical"] for r in rows if r["spacing"] == 64.0)
    assert "the default 64-voxel seed spacing is unchanged" in TEXT


def _villa(rev: str, path: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT / "villa"), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"villa {rev} not in this checkout's submodule objects")


@pytest.mark.parametrize(
    "quote, path, now",
    [
        ("We discourage standalone analytic, auditing or evaluation tools, and instead encourage work that directly "
         "**advances unwrapping or ink detection**.", "34_prizes.md", True),
        ("Fixes for issues that are theoretically wrong but rarely or never cause problems in practice are unlikely "
         "to be awarded.", "34_prizes.md", True),
        ("Reveal **insightful, actionable** information", "34_prizes.md", False),
        ("facilitated improvements to unwrapping or ink detection", "34_prizes.md", False),
        ("improvements to tooling", "34_prizes.md", True),
        ("several bugfix PRs on our [villa](https://github.com/ScrollPrize/villa) monorepo", "34_prizes.md", False),
        ("This is why better diagnostics matter just as much as better models", "37_2026_open_problems.md", False),
    ],
)  # fmt: skip
def test_each_quoted_criterion_is_villa_s_wording(quote, path, now):
    """Quoted in the draft; present in villa at the rollover when added, and only before #2450 when removed."""
    assert f"“{quote}" in TEXT
    after = _villa(OPENED, f"scrollprize.org/docs/{path}")
    before = _villa(f"{CRITERIA}^", f"scrollprize.org/docs/{path}")
    assert (quote in after, quote in before) == (
        (True, False) if now else (False, True)
    )
