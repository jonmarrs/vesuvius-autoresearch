"""Bind the concise October filing to the dated GitHub and measurement evidence."""

import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "docs/PRIZE_FILING_2026-10_FORM_ANSWERS.md").read_text()
REVIEW = json.loads(
    (ROOT / "reports/evidence/october_prize_readiness_2026-10-23.json").read_text()
)


def test_url_field_contains_the_confirmed_own_merges():
    urls = TEXT.split("```text\n", 1)[1].split("```", 1)[0].splitlines()
    confirmed = REVIEW["merged_contributions"]
    assert urls == [row["url"] for row in confirmed] + [
        "https://github.com/jonmarrs/vesuvius-autoresearch"
    ]
    assert all(row["merged"] is True for row in confirmed)


def test_stated_merge_dates_use_pacific_calendar_dates():
    for row in REVIEW["merged_contributions"]:
        when = dt.datetime.fromisoformat(row["merged_at"].replace("Z", "+00:00"))
        pacific = when.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
        assert re.search(rf"#{row['number']} \(merged {pacific}(?: Pacific)?\)", TEXT)


def test_memory_claims_match_the_measured_pr_record():
    source = (ROOT / "docs/VILLA_DRAFT_ink_metrics_sequential_folds.md").read_text()
    rows = [
        line.split("|")
        for line in source.splitlines()
        if line.startswith("| w120–w129")
    ]
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
    plan = " ".join(
        (ROOT / "docs/PRIZE_PLAN_2026-10_FINAL_WEEK.md").read_text().split()
    )
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


def _pacific_date(stamp):
    return (
        dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        .astimezone(ZoneInfo("America/Los_Angeles"))
        .date()
    )


def _deadline_date(text):  # "11:59pm Pacific, July 31st, 2026"
    month, day, year = re.fullmatch(
        r"11:59pm Pacific, (\w+) (\d+)\w\w, (\d{4})", text
    ).groups()
    return dt.datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()


def test_the_rollover_note_is_the_record():
    """villa's rollover PR replaces the page's form before October closes; the note says when earlier ones landed."""
    rec = json.loads(
        (ROOT / "reports/evidence/october_form_rollover_2026-10-26.json").read_text()
    )
    text = " ".join(TEXT.split())
    rows = {row["number"]: row for row in rec["rollover_prs"]}
    pending = rows[2301]
    assert (
        pending["state"] == "OPEN"
        and _pacific_date(pending["created_at"]).isoformat() == "2026-10-25"
    )
    assert pending["deadline_before"] == "11:59pm Pacific, October 31st, 2026"
    assert _deadline_date(pending["deadline_after"]) == dt.date(2026, 11, 30)
    assert pending["form_before"] == REVIEW["form"]["url"]
    assert (
        "[villa #2301](https://github.com/ScrollPrize/villa/pull/2301), open since 2026-10-25,"
        in text
    )
    assert "sets the page's deadline to November 30 and links November's form," in text

    november = rec["open_rollover_forms"]["2301"]
    assert (
        november["url"] == pending["form_after"]
        and november["title"] == "November 2026 Progress Prizes"
    )
    assert not november["accepting_responses"] and november["final_url"].endswith(
        "/closedform"
    )
    assert (
        f"which was closed on {_pacific_date(rec['checked_at_utc']).isoformat()}."
        in text
    )

    filing = rec["filing_form"]
    assert filing["url"] == REVIEW["form"]["url"] and filing["accepting_responses"]
    assert f"still says “{filing['title']}” and accepts responses" in text

    merged = [row for row in rows.values() if row["merged_at"]]
    by_maintainer = [row for row in merged if row["merged_by"] != "app/github-actions"]
    assert all(
        _pacific_date(row["merged_at"]) > _deadline_date(row["deadline_before"])
        for row in by_maintainer
    )
    numbers = ", ".join(f"#{row['number']}" for row in by_maintainer)
    assert (
        f"The three earlier rollovers a maintainer merged landed after the month's deadline ({numbers})."
        in text
    )
    assert len(by_maintainer) == 3
    (automatic,) = [row for row in merged if row["merged_by"] == "app/github-actions"]
    landed = _pacific_date(automatic["merged_at"])
    assert landed < _deadline_date(automatic["deadline_before"]) and automatic["deadline_before"].startswith("11:59pm Pacific, July")  # fmt: skip
    assert (
        f"#{automatic['number']}, merged by GitHub Actions, landed on {landed}, while July's round was open."
        in text
    )

    draft = " ".join((ROOT / "docs/PRIZE_FILING_2026-10_DRAFT.md").read_text().split())
    research = " ".join(
        (ROOT / "docs/PRIZE_FILING_2026-10_RESEARCH_FORM_ANSWERS.md")
        .read_text()
        .split()
    )
    assert (
        "Once villa #2301 (November's rollover) merges, that page links November's form, not October's"
        in draft
    )
    assert "in the October form that the engineering bundle links" in research
