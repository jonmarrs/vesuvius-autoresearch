"""Tripwire: the decoupling must never be described as holding on current villa.

Written 2026-09-12, the day the re-measurement failed.

Four pre-registered studies on villa-spiral `6847063f` showed `satisfied_area`
and `total_fg_pixels` moving independently. The registered attempt to extend that
to current villa produced an ink null and a geometry move in the direction the
registration itself declared uninterpretable -- so the extension failed, and the
claim is a claim about superseded code.

The failure mode this guards is not a lie; it is attrition. Every outward
document wants the short version, the short version is "the metrics decouple",
and the qualifier is the first thing a rewrite drops. So the qualifier is pinned
here instead of trusted to prose.
"""

import pathlib
import re

import pytest

_REPO = pathlib.Path(__file__).resolve().parent.parent

# Documents that state the decoupling and are read by someone outside this repo.
_OUTWARD = (
    "FINDINGS.md",
    "README.md",
    "reports/SPIRAL_FINDINGS_SUMMARY.md",
    "docs/PRIZE_FILING_2026-09_DRAFT.md",
    "docs/VILLA_DRAFT_metrics_disagree.md",
)

_VERDICT = "reports/decoupling_does_not_cleanly_reproduce.md"


def test_the_verdict_report_exists_and_says_the_extension_failed():
    t = (_REPO / _VERDICT).read_text()
    assert "does not" in t.lower()
    # The load-bearing asymmetry: a FALL was evidence, a RISE is not.
    assert "uninterpretable" in t
    assert "0.0175" in t and "2,890,443" in t


@pytest.mark.parametrize("rel", _OUTWARD)
def test_outward_docs_carry_the_failed_extension(rel):
    p = _REPO / rel
    if not p.exists():  # drafts may be deleted once filed
        pytest.skip(f"{rel} not present")
    t = p.read_text()
    assert "6847063f" in t, (
        f"{rel} states results without naming the tree they are from"
    )
    hits = ("did not", "does not", "FAILED", "failed", "not extend")
    assert any(h in t for h in hits), (
        f"{rel} names the tree but never says the extension to current code failed"
    )


@pytest.mark.parametrize("rel", _OUTWARD)
def test_no_doc_claims_the_decoupling_on_current_code(rel):
    """Reject sentences that put 'decoupl' and 'current' in the same breath
    without a negation between them."""
    p = _REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} not present")
    # Strip inline code and link targets first: the registration's own FILENAME
    # is `..._decoupling_on_current_code.md`, which contains both tokens and
    # asserts nothing. A path is not a claim.
    text = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", p.read_text())
    for sent in re.split(r"(?<=[.!?])\s+", text):
        low = sent.lower()
        if "decoupl" not in low or "current" not in low:
            continue
        assert any(
            n in low for n in ("not", "no ", "fail", "never", "cannot", "weaker")
        ), (
            f"{rel} appears to claim the decoupling on current code:\n  {sent.strip()[:200]}"
        )
