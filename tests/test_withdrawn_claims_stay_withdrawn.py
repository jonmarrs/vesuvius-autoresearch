"""A withdrawn claim must not survive anywhere as a live assertion.

Retracting a number means editing every document that repeats it, and on
2026-09-13 that propagation missed a file: `decoupling_does_not_cleanly_reproduce.md`
still read "current-code seed noise is 4.1x tighter" after the ratio had been
withdrawn. It was found by grepping for the digits, which is not a method --
`4.1x` also appears legitimately in two fibers reports as a speedup.

So this matches the CLAIM, not the digits: phrases that only make sense as an
assertion of the withdrawn fact. A paragraph may still contain such a phrase if it
also names the correction, because that is what a retraction looks like.

Each entry names that correction: the replacement figure, or the retraction's own
words. Any withdrawal word used to clear a paragraph, and that was too coarse. On
2026-10-22 FINDINGS.md still said two flattens "land on surfaces 7.15 vx apart" in a
paragraph that said "superseded" about something else. A report still said two seeds
catch a 5% gain "75% of the time", beside "the superseded tree" and a withdrawn
99.2%; that figure became 44% on 2026-09-19.

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

# (regex, what it asserts, what replaced it, what a paragraph quoting it must also say)
_CLAIMS = [
    (
        # also the rounded "4x quieter", which outlived the exact figure in the summary
        r"\b4(\.1)?\s*[x×]\s*(tighter|quieter)",
        "current code is 4.1x quieter than the pinned tree",
        "2.0x, F(18,6)=3.83, p=0.104 -- not established",
        r"2\.0\s*[x×]|\[withdrawn|retraction",
    ),
    (
        r"seed noise is\s*\**0\.0125",
        "current-tier seed CV is 0.0125",
        "0.0536 at df=11",
        r"0\.0536",
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
        r"0\.0536",
    ),
    (
        r"resolves?\s*(about\s*)?\**~?2\.9%",
        "the current-code loop resolves 2.9%",
        "about 12%",
        r"12(\.3)?%",
    ),
    (
        r"resolves?\s*(about\s*)?\**~?6%\s*at three",
        "the current-code loop resolves about 6% at three fits per arm",
        "about 12% -- reports/six_unused_seeds_double_the_current_floor.md",
        r"12(\.3)?%",
    ),
    (
        r"99\.2%\s*of the time",
        "two seeds catch a 5% gain 99.2% of the time",
        "44.0%",
        r"44(\.0)?%|overstated",
    ),
    (
        r"\b75(\.0)?%\s*of the time",
        "two seeds catch a 5% gain 75% of the time",
        "44.0%",
        r"44(\.0)?%",
    ),
    # 2026-09-20: the flatten is stochastic; the scorer is 0.0032%.
    (
        r"deterministic to 1\.4\d?%",
        "the pipeline is deterministic to 1.4%",
        "3.04% render+score on one tree; 0.0014% with the flatten fixed",
        r"3\.04%|0\.0014%|one draw",
    ),
    (
        r"explains\s*\**59%\s*\**\s*of the",
        "the render pair explains 59% of the seed CV",
        "one pair cannot apportion it; df=1 CI on the share spans 3-100%",
        r"cannot apportion|3\s*[–-]\s*100%|originally read",
    ),
    (
        r"\b153\s*MB",
        "the scrollgt image is 153 MB",
        "660 MB, measured by building it",
        r"660\s*MB",
    ),
    (
        r"20 core tests pass",
        "20 core tests pass offline in the container",
        "all 206 pass offline, verified 8m02s",
        r"\b206\b",
    ),
    # 2026-09-27: the current-code same-winding null's interval rested on three
    # control seeds at CV 0.0124 -- reports/control_sensitivity.md
    (
        r"(exclude[sd]?|excluding|bounds?|bounded)\W+(\w+\W+){0,6}?±\s*3%|±\s*3%\s*(bound|null)",
        "the current-code null bounds the ink effect at ±3%",
        "−4.41% [−12.18%, +3.37%] against the render-matched control seeds",
        r"4\.41%|12\.18%|three (unusually )?tight|0\.0124|control[- ]seeds?|happened to land tight",
    ),
    # 2026-09-22: the 7.15 vx is a nearest-neighbour distance between two samplings
    # of one sheet; along the normal they are 0.25 vx apart.
    # reports/the_flatten_moves_the_grid_not_the_surface.md
    (
        # "surfaces sit 7.15 vx apart", "a re-solve that moved the surface 7.15 vx",
        # "surface movement | **7.15 vx mean**", and the reverse order, "6.6-7.3 vx
        # from *both* stock surfaces" or "7 vx on the surface"
        r"(surfaces?|lands?|landed|landing|sits?|sitting|mov\w*\s+the\s+surface)"
        r"\W+(\w+\W+){0,3}?~?7(\.\d+)?\s*(vx|voxels?)\b"
        r"|\b7(\.\d+)?\s*(vx|voxels?)\s+(apart\s+)?(from|on)\W+(\w+\W+){0,3}?surfaces?\b",
        "two stock flattens land on surfaces 7.15 vx apart",
        "the same surface, 0.25 vx apart along the normal; ~7 vx is the grid's in-plane offset",
        # not "nearest-neighbour": the uncorrected report used that word itself
        r"0\.2[3-6]\s*vx|same surface|re-?parametri[sz]",
    ),
]


def _cleared(para: str, required: str) -> bool:
    return re.search(required, para, re.I) is not None


# Read as current, not as records: corrected where they say a thing, never by a head note.
_LIVE = {
    _REPO / "README.md",
    _REPO / "FINDINGS.md",
    _REPO / "reports" / "SPIRAL_FINDINGS_SUMMARY.md",
}


def _head(text: str) -> str:
    """A document's opening, before its first section: where a dated report is
    corrected as a whole ("CORRECTED ...: the title's claim is wrong")."""
    return text.split("\n## ", 1)[0]


@pytest.mark.parametrize(
    "pattern,asserts,replacement,required",
    _CLAIMS,
    ids=[c[1][:34] for c in _CLAIMS],
)
def test_withdrawn_claim_appears_only_beside_its_withdrawal(
    pattern, asserts, replacement, required
):
    rx = re.compile(pattern, re.I)
    offenders = []
    for doc in _DOCS:
        if not doc.exists():
            continue
        text = doc.read_text()
        # a correction at the head of a dated document covers the record below it;
        # FINDINGS, the README and the summary are corrected where they say it
        if doc not in _LIVE and _cleared(_head(text), required):
            continue
        for para in re.split(r"\n\s*\n", text):
            if not rx.search(para):
                continue
            if _cleared(para, required):
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
    assert rx.search("villa's fits just got 4× quieter")
    assert not rx.search("a 14x quieter scorer")


def test_a_withdrawal_paragraph_is_allowed_to_name_the_old_number():
    # look the claim up by its text: positional indexing broke the first time
    # a withdrawal was inserted above it
    pattern, _, _, required = next(c for c in _CLAIMS if "75%" in c[1])
    rx = re.compile(pattern, re.I)
    para = '"Two seeds catch a 5% gain 75% of the time" becomes 44%.'
    assert rx.search(para) and _cleared(para, required)
    # a withdrawal word about something else does not clear it
    stale = "two seeds detect a 5% gain 75% of the time against the superseded tree"
    assert rx.search(stale) and not _cleared(stale, required)


def test_every_claim_names_its_correction():
    assert all(len(c) == 4 and c[3] for c in _CLAIMS)


def test_a_claim_with_a_named_correction_is_not_cleared_by_any_withdrawal_word():
    pattern, _, _, required = next(c for c in _CLAIMS if "7.15 vx" in c[1])
    rx = re.compile(pattern, re.I)
    stale = (
        "two runs land on surfaces **7.15 vx apart** and move the count 3.04%. "
        "Older seed estimates are superseded."
    )
    assert rx.search(stale) and not _cleared(stale, required)
    fixed = (
        "they lay the same surface out on grids ~7 vx apart, 0.25 vx along the normal"
    )
    assert _cleared(fixed, required)
    for live in (
        "their surfaces sit **7.15 vx apart** in the outer region",
        "a re-solve that moved the surface 7.15 vx in the outer region",
        "a flattener that lands 7 vx apart every run",
        "the same input that landed 7.15 vx apart under stock settings",
        "two runs land on surfaces 7.2 vx apart",
        "surfaces sitting about 7 vx apart",
        "| flatten's own run-to-run surface movement | **7.15 vx mean** |",
        "the deterministic surface sits 6.6–7.3 vx from *both* stock surfaces",
        "3.04% on the objective, 7 vx on the surface",
    ):
        assert rx.search(live), live
    assert not _cleared(
        "land on surfaces 7.15 vx apart by nearest-neighbour distance", required
    )
    assert set(_DOCS) >= _LIVE
    assert not rx.search("the median patch spans 7 bands")
