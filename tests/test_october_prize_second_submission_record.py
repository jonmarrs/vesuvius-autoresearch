"""The second October response, its redacted record and the first response agree.

Villa #2141 and #2259 merged after the October 29 entry was filed, so they went in a
second response that names the first. The owner pasted the response copy into the
session; it carries no date, so the record keeps the owner's reported time. These
checks bind the public copy of the answers to the record, and the second response's
claims to the first record and to the merge times.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = "reports/evidence/october_prize_second_submission_2026-10-31.json"
RECORD = json.loads((ROOT / RECORD_PATH).read_text())
FIRST = json.loads((ROOT / RECORD["first_response"]).read_text())
FILED = (ROOT / "docs/PRIZE_FILING_2026-10_SECOND_SUBMITTED.md").read_text()
URLS = RECORD["submitted_public_fields"]["urls"]
CONTRIBUTION = RECORD["submitted_public_fields"]["contribution"]
PACIFIC = ZoneInfo("America/Los_Angeles")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_the_filed_document_shows_the_recorded_answers():
    urls, contribution = re.findall(r"```text\n(.*?)\n```", FILED, re.S)
    assert urls.split("\n") == URLS
    assert contribution == CONTRIBUTION


def test_the_record_hashes_are_its_public_answers():
    verification = RECORD["verification"]
    assert verification["text_hash_scope"] == FIRST["verification"]["text_hash_scope"]
    assert sha(CONTRIBUTION + "\n") == verification["submitted_contribution_txt_sha256"]
    assert sha("\n".join(URLS) + "\n") == verification["submitted_urls_txt_sha256"]


def test_it_names_the_first_response_and_credits_only_the_later_merges():
    first = FIRST["merged_villa_prs"]
    assert CONTRIBUTION.startswith(
        f"This adds to my October engineering entry of October 29 (Villa #{first[0]}, "
        f"#{first[1]} and #{first[2]})."
    )
    assert RECORD["form"] == FIRST["form"]
    prs = RECORD["merged_villa_prs"]
    assert not set(prs) & set(first)
    assert URLS[:-1] == [f"https://github.com/ScrollPrize/villa/pull/{n}" for n in prs]
    assert URLS[-1] == FIRST["submitted_public_fields"]["urls"][-1]
    first_filed = datetime.fromisoformat(FIRST["receipt"]["date_utc"])
    deadline = datetime.fromisoformat(RECORD["deadline_utc"])
    for n in prs:
        merged = datetime.fromisoformat(RECORD["villa_merged_at_utc"][str(n)])
        assert first_filed < merged < deadline, n
        assert f"#{n} (merged {merged.astimezone(PACIFIC):%Y-%m-%d})" in CONTRIBUTION
        assert f"{merged.astimezone(PACIFIC):%-I:%M}" in FILED.replace("\n", " ")


def test_the_counts_and_times_agree():
    assert len(CONTRIBUTION.split()) == RECORD["contribution_words"] == 335
    assert "**335-word**" in FILED
    receipt = RECORD["receipt"]
    assert receipt["date_utc"] is None and receipt["private_original_retained"] is False
    reported = datetime.fromisoformat(receipt["reported_submitted_by_pacific"])
    deadline = datetime.fromisoformat(RECORD["deadline_utc"])
    assert deadline == datetime.fromisoformat(FIRST["deadline_utc"])
    assert RECORD["reported_time_precedes_deadline"] is (reported < deadline) is True
    assert f"by {reported:%-I:%M} p.m. Pacific" in FILED
    checked = datetime.fromisoformat(
        receipt["form_accepting_responses_checked_pacific"]
    )
    assert checked < reported and f"{checked:%-I:%M}" in FILED.replace("\n", " ")
    assert RECORD["research_entry"] == FIRST["research_entry"]


def test_the_public_copies_hold_no_contact_details():
    for text in (FILED, (ROOT / RECORD_PATH).read_text()):
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)


def test_the_first_record_points_to_the_second():
    first_doc = (ROOT / "docs/PRIZE_FILING_2026-10_SUBMITTED.md").read_text()
    assert "(PRIZE_FILING_2026-10_SECOND_SUBMITTED.md)" in first_doc
