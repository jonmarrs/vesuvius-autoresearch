"""The filing's upstream-contribution claims must match the recorded gh state.

Written 2026-09-22, after the submit-ready text was found asserting "four merged
fixes, zero pending" while #1842 had been open for three days and #1866 had just
been posted. The measurement figures were already bound to artifacts by
``test_filing_numbers_match_sources``; the *contribution* claims were not, so the
one number describing our relationship with upstream was the one nothing checked.

A second defect is pinned here. The filing and my notes both cited ``reviews: 0``
as evidence the two bot-closed PRs were "never looked at". That field is 0 on all
eight PRs, **including the four that merged** -- villa merges without a review
record -- so it never discriminated anything. A negative check keeps it from
coming back, because it reads as compelling evidence and is not.

Refresh ``reports/villa_pr_state.json`` with scripts/refresh_villa_pr_state.py.
"""

import json
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_STATE = _REPO / "reports/villa_pr_state.json"
_SUBMIT = _REPO / "docs/PRIZE_FILING_2026-09_SUBMIT.md"

pytestmark = pytest.mark.skipif(
    not (_STATE.exists() and _SUBMIT.exists()),
    reason="filing or pr-state artifact absent",
)

_WORD = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def _state() -> dict:
    return json.loads(_STATE.read_text())


def _text() -> str:
    return _SUBMIT.read_text()


def test_headline_counts_match_the_artifact():
    st, txt = _state(), _text()
    expect = (
        f"**What is upstream: {_WORD[st['n_merged']]} merged fixes, "
        f"{_WORD[st['n_open']]} awaiting review, "
        f"{_WORD[st['n_closed_unmerged']]} closed unmerged.**"
    )
    # "auto-closed unreviewed" was true until 2026-09-23, when a maintainer closed #1866
    # with a reason. Pin that the headline does not quietly call every close automatic.
    maintainer_closed = [
        n
        for n, p in st["prs"].items()
        if p["state"] == "CLOSED" and p["comments_human"] >= 2
    ]
    if maintainer_closed:
        assert "auto-closed unreviewed" not in txt, (
            f"{maintainer_closed} were closed with a human comment; not all closes are automatic"
        )
    assert expect in txt, f"filing headline does not match gh state; expected: {expect}"


def test_total_pr_count_matches():
    st, txt = _state(), _text()
    expect = f"**This is {_WORD[st['total']]} PRs against a merged total of {_WORD[st['n_merged']]}.**"
    assert expect in txt, f"expected: {expect}"


def test_every_pr_in_the_table_has_the_right_state():
    st, txt = _state(), _text()
    table = [
        ln
        for ln in txt.splitlines()
        if ln.startswith("| ") and re.search(r"#\d{4}", ln)
    ]
    seen = set()
    for ln in table:
        num = re.search(r"#(\d{4})", ln).group(1)
        if num not in st["prs"]:
            continue
        seen.add(int(num))
        actual = st["prs"][num]["state"]
        claims_merged = "MERGED" in ln
        claims_closed = "CLOSED" in ln
        if actual == "MERGED":
            assert claims_merged, (
                f"#{num} merged upstream but the row does not say so: {ln}"
            )
        elif actual == "CLOSED":
            assert claims_closed and not claims_merged, (
                f"#{num} is closed; row says: {ln}"
            )
        else:
            assert not claims_merged and not claims_closed, (
                f"#{num} is open; row says: {ln}"
            )
    missing = set(st["prs"]) - {str(n) for n in seen}
    assert not missing, f"PRs absent from the filing's table: {sorted(missing)}"


def test_merge_dates_are_quoted_correctly():
    st, txt = _state(), _text()
    for num, pr in st["prs"].items():
        if pr["state"] != "MERGED":
            continue
        day = pr["mergedAt"][:10]
        row = next(
            (ln for ln in txt.splitlines() if ln.startswith("| ") and f"#{num}" in ln),
            None,
        )
        assert row is not None, f"#{num} has no row"
        assert day in row, f"#{num} merged {day} but its row reads: {row}"


def test_reviews_zero_is_not_offered_as_evidence():
    """reviews==0 holds for the merged PRs too, so it proves nothing."""
    st = _state()
    assert all(p["reviews"] == 0 for p in st["prs"].values()), (
        "a PR now carries a review record -- this negative check assumed none did; "
        "re-derive what actually discriminates before re-enabling it"
    )
    txt = _text()
    for bad in ("reviews: 0", "reviews:0", "no review,", ", no review"):
        assert bad not in txt, (
            f"filing cites {bad!r}; that field is 0 on all eight PRs including the four "
            "that merged, so it does not distinguish ignored from accepted"
        )


def test_the_zero_pending_claim_cannot_return():
    txt = _text()
    assert "zero pending" not in txt, (
        "'zero pending' was false when written -- #1842 had been open three days"
    )
