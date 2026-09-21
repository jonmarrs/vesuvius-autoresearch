"""A withdrawn claim must not survive anywhere as a live assertion.

Retracting a number means editing every document that repeats it, and on
2026-09-13 that propagation missed a file: `decoupling_does_not_cleanly_reproduce.md`
still read "current-code seed noise is 4.1x tighter" after the ratio had been
withdrawn. It was found by grepping for the digits, which is not a method --
`4.1x` also appears legitimately in two fibers reports as a speedup.

So this matches the CLAIM, not the digits: phrases that only make sense as an
assertion of the withdrawn fact. A paragraph may still contain such a phrase if it
also says the claim was withdrawn, because that is what a retraction looks like.

Scope note: this guards claims retracted in-session, where the retraction is
recent enough that stale copies are likely. It is not a general fact-checker.
"""

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_DOCS = sorted(
    list((_REPO / "reports").glob("*.md"))
    + list((_REPO / "docs").glob("*.md"))
    + [_REPO / "README.md", _REPO / "FINDINGS.md"]
)

_WITHDRAWAL = (
    "withdrew",
    "withdrawn",
    "retract",
    "no longer",
    "first published",
    "superseded",
    "we published",
    "corrected",
    "originally said",
    "stale",
    # added 2026-09-21: retraction paragraphs the guard failed to recognise as
    # retractions, once the ledger was extended to this session's withdrawals
    "becomes",  # '"...75% of the time" becomes 44%'
    "is not established",
    "too small",  # 'the floor ... is too small by at least 2x'
    "one draw",  # 'this is ONE DRAW' -- the report undercutting its own title
    "do not edit or file",
)

# (regex, what it asserts, what replaced it)
_CLAIMS = [
    (
        r"4\.1\s*[x×]\s*(tighter|quieter)",
        "current code is 4.1x quieter than the pinned tree",
        "2.0x, F(18,6)=3.83, p=0.104 -- not established",
    ),
    (
        r"seed noise is\s*\**0\.0125",
        "current-tier seed CV is 0.0125",
        "0.0536 at df=11",
    ),
    # WITHDRAWN A SECOND TIME, 2026-09-19. 0.0263 was itself the replacement for
    # 0.0125, and this ledger still named it as the correct value while it sat in
    # the submit-ready September filing for two days. Six unused curbase seeds
    # doubled it to 0.0536. A replacement value in this table is NOT exempt from
    # later withdrawal -- reports/six_unused_seeds_double_the_current_floor.md.
    (
        r"seed noise is\s*\**0\.0263",
        "current-tier seed CV is 0.0263",
        "0.0536 at df=11",
    ),
    (
        r"resolves?\s*(about\s*)?\**~?2\.9%",
        "the current-code loop resolves 2.9%",
        "about 12%",
    ),
    (
        r"resolves?\s*(about\s*)?\**~?6%\s*at three",
        "the current-code loop resolves about 6% at three fits per arm",
        "about 12% -- reports/six_unused_seeds_double_the_current_floor.md",
    ),
    (r"99\.2%\s*of the time", "two seeds catch a 5% gain 99.2% of the time", "44.0%"),
    (
        r"\b75(\.0)?%\s*of the time",
        "two seeds catch a 5% gain 75% of the time",
        "44.0%",
    ),
    # 2026-09-20: the flatten is stochastic; the scorer is 0.0032%.
    (
        r"deterministic to 1\.4\d?%",
        "the pipeline is deterministic to 1.4%",
        "3.04% render+score on one tree; 0.0014% with the flatten fixed",
    ),
    (
        r"explains\s*\**59%\s*\**\s*of the",
        "the render pair explains 59% of the seed CV",
        "one pair cannot apportion it; df=1 CI on the share spans 3-100%",
    ),
    (r"\b153\s*MB", "the scrollgt image is 153 MB", "660 MB, measured by building it"),
    (
        r"20 core tests pass",
        "20 core tests pass offline in the container",
        "all 206 pass offline, verified 8m02s",
    ),
]


@pytest.mark.parametrize(
    "pattern,asserts,replacement", _CLAIMS, ids=[c[1][:34] for c in _CLAIMS]
)
def test_withdrawn_claim_appears_only_beside_its_withdrawal(
    pattern, asserts, replacement
):
    rx = re.compile(pattern, re.I)
    offenders = []
    for doc in _DOCS:
        if not doc.exists():
            continue
        for para in re.split(r"\n\s*\n", doc.read_text()):
            if not rx.search(para):
                continue
            if any(w in para.lower() for w in _WITHDRAWAL):
                continue
            offenders.append(f"{doc.relative_to(_REPO)}: {para.strip()[:140]}")
    assert not offenders, (
        f"'{asserts}' is withdrawn (now: {replacement}) but asserted live in:\n  "
        + "\n  ".join(offenders)
    )


def test_the_guard_matches_claims_not_bare_digits():
    """`4.1x` appears legitimately as a speedup in the fibers reports. A guard
    that fired on the digits would be routed around within a week."""
    rx = re.compile(_CLAIMS[0][0], re.I)
    assert not rx.search("CuPy gave a 4.1x speedup over NumPy")
    assert rx.search("current-code seed noise is 4.1x tighter")


def test_a_withdrawal_paragraph_is_allowed_to_name_the_old_number():
    # look the claim up by its text: positional indexing broke the first time
    # a withdrawal was inserted above it
    pattern = next(c[0] for c in _CLAIMS if "99.2%" in c[1])
    rx = re.compile(pattern, re.I)
    para = "We first said 99.2% of the time; that figure is withdrawn."
    assert rx.search(para) and any(w in para.lower() for w in _WITHDRAWAL)
