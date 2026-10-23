"""Bind the concise October filing to the dated GitHub and measurement evidence."""

import datetime as dt
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "docs/PRIZE_FILING_2026-10_FORM_ANSWERS.md").read_text()
REVIEW = json.loads((ROOT / "reports/evidence/october_prize_readiness_2026-10-23.json").read_text())


def test_url_field_contains_the_confirmed_own_merges():
    urls = TEXT.split("```text\n", 1)[1].split("```", 1)[0].splitlines()
    confirmed = REVIEW["merged_contributions"]
    assert urls == [row["url"] for row in confirmed] + [
        "https://github.com/jonmarrs/vesuvius-autoresearch"]
    assert all(row["merged"] is True for row in confirmed)


def test_stated_merge_dates_use_pacific_calendar_dates():
    for row in REVIEW["merged_contributions"]:
        when = dt.datetime.fromisoformat(row["merged_at"].replace("Z", "+00:00"))
        pacific = when.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        assert re.search(rf"#{row['number']} \(merged {pacific}(?: Pacific)?\)", TEXT)


def test_memory_claims_match_the_measured_pr_record():
    source = (ROOT / "docs/VILLA_DRAFT_ink_metrics_sequential_folds.md").read_text()
    rows = [line.split("|") for line in source.splitlines() if line.startswith("| w120–w129")]
    assert len(rows) == 2
    assert rows[0][3].strip() == "OOM-killed 70 s in, while all three folds ran"
    assert rows[0][4].strip() == "≥ 27.6 GB"
    assert rows[1][4].strip() == "13.8 GB" and rows[1][5].strip() == "1,009 s"
    flat = " ".join(TEXT.split())
    assert "OOM-killed 70 seconds in at at least 27.6 GB" in flat
    assert "at 13.8 GB in 1,009 seconds under a 26 GiB memory limit" in flat
    assert "not a claim that the complete GPU scorer is deterministic" in flat


def test_deadline_and_unsubmitted_state_are_explicit():
    deadline = dt.datetime.fromisoformat(REVIEW["deadline_pacific"])
    assert deadline.astimezone(dt.timezone.utc).isoformat() == REVIEW["deadline_utc"]
    assert deadline.strftime("%Y-%m-%d") == "2026-10-31"
    assert "11:59 p.m. Pacific, October 31, 2026" in TEXT
    assert REVIEW["form"]["url"] in TEXT
    assert "not submitted" in TEXT and REVIEW["submitted"] is False
