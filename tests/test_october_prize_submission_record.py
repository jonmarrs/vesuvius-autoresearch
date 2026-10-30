"""The filed October entry, its redacted record and the frozen preparation agree.

The record binds the received answers to the private receipt by hash. These checks
bind the public copy of those answers to the record, and both to the prepared
entry, so that an edit to any of the three shows here.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = json.loads(
    (ROOT / "reports/evidence/october_prize_submission_2026-10-30.json").read_text()
)
FILED = (ROOT / "docs/PRIZE_FILING_2026-10_SUBMITTED.md").read_text()
PREPARED = (ROOT / "docs/PRIZE_FILING_2026-10_FORM_ANSWERS.md").read_text()
URLS = RECORD["submitted_public_fields"]["urls"]
CONTRIBUTION = RECORD["submitted_public_fields"]["contribution"]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def section(markdown, heading):
    """The body under a level-2 heading, up to the next one."""
    body = markdown.split(f"\n## {heading}\n", 1)[1]
    return body.split("\n## ", 1)[0].strip()


def plain(markdown):
    """Prepared markdown as typed into the form: a line per paragraph or list
    item, without emphasis or code marks."""
    blocks = []
    for paragraph in re.split(r"\n\s*\n", markdown):
        items: list[str] = []
        for line in paragraph.split("\n"):
            if line.startswith("- ") or not items:
                items.append(line.strip())
            else:
                items[-1] += " " + line.strip()
        blocks.append("\n".join(items))
    return "\n\n".join(blocks).replace("**", "").replace("`", "")


def test_the_filed_document_shows_the_recorded_answers():
    urls, contribution = re.findall(r"```text\n(.*?)\n```", FILED, re.S)
    assert urls.split("\n") == URLS
    assert contribution == CONTRIBUTION


def test_the_record_hashes_are_its_public_answers():
    verification = RECORD["verification"]
    assert verification["text_hash_scope"].startswith("UTF-8 text with LF newlines")
    assert sha(CONTRIBUTION + "\n") == verification["submitted_contribution_txt_sha256"]
    assert sha("\n".join(URLS) + "\n") == verification["submitted_urls_txt_sha256"]


def test_the_submitted_answers_are_the_frozen_preparation():
    prepared_urls = re.findall(
        r"```text\n(.*?)\n```", section(PREPARED, "URL field"), re.S
    )
    assert prepared_urls == ["\n".join(URLS)]
    assert plain(section(PREPARED, "What is your contribution?")) == CONTRIBUTION
    for path, digest in RECORD["preparation"]["source_document_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_the_counts_prs_and_times_agree():
    assert len(CONTRIBUTION.split()) == RECORD["contribution_words"] == 371
    assert "**371 words**" in FILED
    assert [
        f"https://github.com/ScrollPrize/villa/pull/{n}"
        for n in RECORD["merged_villa_prs"]
    ] == URLS[:3]
    receipt = RECORD["receipt"]
    utc = datetime.fromisoformat(receipt["date_utc"])
    assert utc == datetime.fromisoformat(receipt["date_pacific"])
    assert utc.strftime("%H:%M:%S") == "04:40:33" and "04:40:33 UTC" in FILED
    assert "9:40:33 p.m. Pacific" in FILED
    deadline = datetime.fromisoformat(RECORD["deadline_utc"])
    assert deadline == datetime.fromisoformat(RECORD["deadline_pacific"])
    assert RECORD["receipt_precedes_deadline"] is (utc < deadline) is True
    assert RECORD["research_entry"]["status"] == "NOT_SUBMITTED_IN_THIS_WORKFLOW"
