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
)

# (regex, what it asserts, what replaced it)
_CLAIMS = [
    (
        r"4\.1\s*[x×]\s*(tighter|quieter)",
        "current code is 4.1x quieter than the pinned tree",
        "2.0x, F(18,6)=3.83, p=0.104 -- not established",
    ),
    (r"seed noise is\s*\**0\.0125", "current-tier seed CV is 0.0125", "0.0263 at df=6"),
    (
        r"resolves?\s*(about\s*)?\**~?2\.9%",
        "the current-code loop resolves 2.9%",
        "about 6%",
    ),
    (r"99\.2%\s*of the time", "two seeds catch a 5% gain 99.2% of the time", "75.0%"),
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
    rx = re.compile(_CLAIMS[3][0], re.I)
    para = "We first said 99.2% of the time; that figure is withdrawn."
    assert rx.search(para) and any(w in para.lower() for w in _WITHDRAWAL)
