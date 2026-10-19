"""scripts/check_filing_upstream_claims.py --month: every merge of the month is cited, with its date.

From October the filing has no tally sentence or PR table, so the September claims
cannot be located in it and the script could only fail. What the October draft does
state is each villa merge, as "[villa #N](url) (merged YYYY-MM-DD)", and its checklist
says to list every merge of the month first. These pin that a merge of the month
without such a claim is an error, never a pass, and that each stated date is the
Pacific date of the live merge.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import check_filing_upstream_claims as cf  # noqa: E402

# gh state on 2026-10-18, plus one September merge.
PRS = [
    {"number": 2141, "state": "OPEN", "mergedAt": None},
    {"number": 2044, "state": "MERGED", "mergedAt": "2026-10-12T01:49:09Z"},
    {"number": 2022, "state": "MERGED", "mergedAt": "2026-10-11T23:25:33Z"},
    {"number": 1842, "state": "MERGED", "mergedAt": "2026-09-23T17:00:00Z"},
]
CITED = (
    "[villa #2022](https://github.com/ScrollPrize/villa/pull/2022) (merged 2026-10-11).\n"
    "[villa #2044](https://github.com/ScrollPrize/villa/pull/2044) (**merged 2026-10-11 Pacific**).\n"
)


def _no_lookup(number: int) -> dict:
    raise AssertionError(f"looked up #{number}, which is in the PR list")


def _summary(checks):
    return [(name, ok) for name, ok, _ in checks]


def test_merge_dates_are_pacific():
    # #2044 merged at 01:49 UTC on the 12th, which was the evening of the 11th in Pacific time.
    assert cf.pacific_date("2026-10-12T01:49:09Z") == "2026-10-11"


def test_every_merge_of_the_month_cited_with_its_date_passes():
    checks, missing = cf.month_checks(CITED, PRS, "2026-10", lookup=_no_lookup)
    assert missing == []  # #1842 merged in September and needs no claim
    assert _summary(checks) == [
        ("#2022 merged 2026-10-11", True),
        ("#2044 merged 2026-10-11", True),
    ]


def test_a_merge_of_the_month_left_out_is_an_error_not_a_pass():
    checks, missing = cf.month_checks(
        CITED.splitlines()[0], PRS, "2026-10", lookup=_no_lookup
    )
    assert missing == ["merged claim for #2044 (merged 2026-10-11)"]


def test_a_merge_cited_without_a_date_is_not_located():
    text = CITED.replace(" (**merged 2026-10-11 Pacific**)", " was merged")
    _, missing = cf.month_checks(text, PRS, "2026-10", lookup=_no_lookup)
    assert missing == ["merged claim for #2044 (merged 2026-10-11)"]


def test_an_unlinked_citation_is_located():
    text = "#2022 (merged 2026-10-11) and #2044 (merged 2026-10-11)"
    checks, missing = cf.month_checks(text, PRS, "2026-10", lookup=_no_lookup)
    assert missing == [] and all(ok for _, ok, _ in checks)


def test_a_wrong_date_is_stale():
    text = CITED.replace("(merged 2026-10-11).", "(merged 2026-10-12).")
    checks, _ = cf.month_checks(text, PRS, "2026-10", lookup=_no_lookup)
    assert _summary(checks) == [
        ("#2022 merged 2026-10-12", False),
        ("#2044 merged 2026-10-11", True),
    ]


def test_an_open_pr_claimed_merged_is_stale():
    text = (
        CITED
        + "[villa #2141](https://github.com/ScrollPrize/villa/pull/2141) (merged 2026-10-18)\n"
    )
    checks, _ = cf.month_checks(text, PRS, "2026-10", lookup=_no_lookup)
    assert ("#2141 merged 2026-10-18", False) in _summary(checks)


def test_a_pr_not_ours_is_looked_up():
    text = (
        CITED
        + "[villa #1886](https://github.com/ScrollPrize/villa/pull/1886) (merged 2026-09-25)\n"
    )
    seen = []

    def lookup(number: int) -> dict:
        seen.append(number)
        return {"number": number, "state": "MERGED", "mergedAt": "2026-09-25T18:00:00Z"}

    checks, missing = cf.month_checks(text, PRS, "2026-10", lookup=lookup)
    assert seen == [1886]
    assert missing == [] and all(ok for _, ok, _ in checks)


def test_the_october_draft_states_its_merges_in_the_checked_form():
    text = (_REPO / "docs/PRIZE_FILING_2026-10_DRAFT.md").read_text()
    checks, missing = cf.month_checks(text, PRS, "2026-10", lookup=_no_lookup)
    assert missing == []
    assert checks and all(ok for _, ok, _ in checks), checks
