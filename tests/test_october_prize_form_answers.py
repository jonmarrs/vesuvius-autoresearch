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
    assert "OOM-killed 70 seconds in, at a peak of at least 27.6 GB" in flat
    assert "at 13.8 GB in 1,009 seconds under a 26 GiB memory limit" in flat
    assert "not a claim that the complete GPU scorer is deterministic" in flat


def test_deadline_and_unsubmitted_state_are_explicit():
    deadline = dt.datetime.fromisoformat(REVIEW["deadline_pacific"])
    assert deadline.astimezone(dt.timezone.utc).isoformat() == REVIEW["deadline_utc"]
    assert deadline.strftime("%Y-%m-%d") == "2026-10-31"
    assert "11:59 p.m. Pacific, October 31, 2026" in TEXT
    assert REVIEW["form"]["url"] in TEXT
    assert "not submitted" in TEXT and REVIEW["submitted"] is False


def test_hardware_limit_and_agreement_are_the_pr_record():
    source = (ROOT / "docs/VILLA_DRAFT_ink_metrics_sequential_folds.md").read_text()
    assert "one RTX 4090, each run in a 26 GiB memory cgroup" in source
    flat = " ".join(TEXT.split())
    assert "used one RTX 4090" in flat and "under a 26 GiB memory limit" in flat
    # the smaller strip's three modes: stock, default and sequential
    counts = [
        int(line.split("|")[3].split("ok,")[1].strip().replace(",", ""))
        for line in source.splitlines()
        if line.startswith("| w010–w019")
    ]
    assert len(counts) == 3
    assert (max(counts) - min(counts)) / min(counts) < 0.005 / 100
    assert "the three modes' counts agree within 0.005%" in flat


def test_the_readiness_notes_are_the_record():
    draft = " ".join((ROOT / "docs/PRIZE_FILING_2026-10_DRAFT.md").read_text().split())
    plan = " ".join((ROOT / "docs/PRIZE_PLAN_2026-10_FINAL_WEEK.md").read_text().split())
    links = REVIEW["url_checks"]
    assert all(row["status"] == 200 for row in links)
    assert f"all {len(links)} links in the pre-update draft returned HTTP 200" in draft
    assert f"All {len(links)} pre-update links returned HTTP 200." in plan
    assert f"The live form still says “{REVIEW['form']['title']}”." in draft
    (discord,) = [q for q in REVIEW["form"]["questions"] if "Discord" in q["label"]]
    assert REVIEW["form"]["email_required"] and not discord["required"]
    assert all(q["required"] for q in REVIEW["form"]["questions"] if q is not discord)
    assert "Discord display name is optional" in draft
    words = len(TEXT.split("## What is your contribution?", 1)[1].split())
    assert f"The concise contribution answer is {words} words." in plan
