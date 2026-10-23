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

A pattern must also survive the markup around a figure. "**75%** of the time"
outlived the plain "75% of the time" for the same reason, and so did the
summary's "Current villa is **0.0263 (df=6)**".

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
        r"\b(4(\.1)?\s*[x×]|four\s+times)\s*(tighter|quieter)",
        "current code is 4.1x quieter than the pinned tree",
        "1.0x on all nine seeds, F(18,11)=0.92, p=0.84",
        # the bracket is the original paragraph's own withdrawal stamp
        r"1\.0\s*[x×]|F\(18,\s*11\)|\[withdrawn 2026-09-13",
    ),
    # 2026-09-19: the replacement ratio went the way of the replacement CV
    (
        r"F\(18,\s*6\)\s*=\s*3\.83|\b2\.0\s*[x×]\s*(tighter|quieter)",
        "current code is 2.0x quieter than the pinned tree, not established",
        "1.0x on all nine seeds, F(18,11)=0.92, p=0.84",
        r"1\.0\s*[x×]|F\(18,\s*11\)|0\.0536",
    ),
    (
        r"(seed (noise|CV)(\W+(\w+\W+){0,3}?(is|of))?|current villa is|current[- ]tier (pooled )?CV( is)?)"
        r"\s*\**~?0\.0125",
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
        r"(seed (noise|CV)(\W+(\w+\W+){0,3}?(is|of))?|current villa is|current[- ]tier (pooled )?CV( is)?)"
        r"\s*\**~?0\.0263",
        "current-tier seed CV is 0.0263",
        "0.0536 at df=11",
        r"0\.0536",
    ),
    (
        r"(resolves?|sees)\s*(about\s*)?\**~?2\.9\s*%",
        "the current-code loop resolves 2.9%",
        "12.3% at three fits per arm",
        r"(?<![\d.])12\.3\s*%",
    ),
    (
        r"(resolves?|sees)\s*(about\s*)?\**~?6(\.0)?\s*%",
        "the current-code loop resolves about 6% at three fits per arm",
        "12.3% -- reports/six_unused_seeds_double_the_current_floor.md",
        r"(?<![\d.])12\.3\s*%",
    ),
    (
        r"99\.2\s*%\s*\**\s*of the time",
        "two seeds catch a 5% gain 99.2% of the time",
        "44.0%",
        r"(?<![\d.])44(\.0)?\s*%|overstated",
    ),
    (
        r"\b75(\.0)?\s*%\s*\**\s*of the time",
        "two seeds catch a 5% gain 75% of the time",
        "44.0%",
        r"(?<![\d.])44(\.0)?\s*%",
    ),
    # 2026-09-20: the flatten is stochastic; the scorer is 0.0032%.
    (
        # also the floor tables' "pipeline non-determinism | **1.42%**"
        r"(deterministic|non-?determinism)\W+(\w+\W+){0,3}?\**1\.4\d?\s*%",
        "the pipeline is deterministic to 1.4%",
        "one draw; a same-tree repeat gave 3.04%, and 0.0014% with the flatten fixed",
        # or the second pair's 890x; not 3.04% alone, which the flatten paragraphs
        # quote about other things
        r"one draw|\b890\s*[x×]",
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
        r"all 206|206 (tests? )?pass",
    ),
    # 2026-09-27: the current-code same-winding null's interval rested on three
    # control seeds at CV 0.0124 -- reports/control_sensitivity.md
    (
        r"(exclude[sd]?|excluding|bounds?|bounded|rules? out|within)\W+(\w+\W+){0,6}?"
        r"(±|\+/-)\s*3(\.0)?\s*%|(±|\+/-)\s*3(\.0)?\s*%\s*(bound|null)",
        "the current-code null bounds the ink effect at ±3%",
        "−4.41% [−12.18%, +3.37%] against the render-matched control seeds",
        # not "control seeds" or 0.0124: a paragraph can name the seeds and still state the bound
        r"4\.41%|12\.18%|three (unusually )?tight|happened to land tight",
    ),
    # 2026-09-27: the count's 1.2% was the CV of curbase_s1-s3, three seeds since found
    # unusually tight -- reports/control_sensitivity.md
    (
        # `total_fg_pixels` is the count; two placement reports named it so
        r"\b(count|total_fg_pixels)\W+(\w+\W+){0,4}?\**(?<![\d.])1\.2\s*%",
        "fits differing only by seed agree on the ink count to 1.2%",
        "6.4% across all nine seeds of the configuration (1.2% is three tight seeds)",
        # 7.4% is the s4-s9 seeds' own count CV
        r"(?<![\d.])(6\.4|7\.4)\s*%|0\.0644|three (unusually )?tight",
    ),
    # the outer floor at n=4; pooled over the pinned tier's 24 outer fits at df=18 the
    # inner floor is about 2.1x too wide -- reports/noise_floor_by_tier.md
    (
        # and the outer report's own "two and a half times quieter"
        r"(?<![\d.])2\.6\s*\**\s*[x×]\s*\**\s*(too wide|wider)"
        r"|two and a half times\s+\**(quieter|wider|too wide)",
        "the inner floor is 2.6x too wide for the outer windings",
        "about 2.1x against the outer CV pooled at df=18",
        # not df=18 alone: a paragraph can name the pooling and keep the 2.6x
        r"(?<![\d.])2\.1\s*[x×]|about twice at df\s*=\s*18",
    ),
    # ~12% is the pinned-tier design MDE, not what the nulls' data exclude
    (
        r"\b(bounded|bounds?)\s+(at\s+)?(about\s+)?\**~?(?<![\d.])12\s*%",
        "the pinned-tier ink nulls are bounded at ~12%",
        "~12% is the design MDE; the intervals are [−18.4%, +16.7%] and [−20.7%, +13.1%]",
        # saying what 12% is, not naming the design MDE beside it
        r"\bis\s+the\s+(pinned[- ]tier('s)?\s+)?design\s+MDE",
    ),
    # 2026-10-23: smooth moves the extreme windows 6-7x the control bound
    (
        r"\b7\s*(to|[–-])\s*20\s*(\**\s*[x×]|\s+times)",
        "smooth interpolation moves the extreme windows 7-20x the control bound",
        "6-7x the 2.8% bound, 7-13x each window's own largest control",
        r"6\s*[–-]\s*7\s*[x×]",
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


def _claim(text):
    return next(c for c in _CLAIMS if text in c[1])


@pytest.mark.parametrize(
    "claim,live",
    [
        # each outlived its entry because the pattern wanted the plain form
        ("75%", "two seeds catch a 5% gain\n**75%** of the time"),
        ("0.0263", "Current villa is **0.0263 (df=6)**"),
        ("0.0263", "gives a\nseed CV of **0.0263** on `total_fg_pixels`"),
        (
            "0.0263",
            "villa's seed noise on `total_fg_pixels` is\n**0.0263** — 8.7× quieter",
        ),
        ("0.0125", "using the current tier's seed CV\nof 0.0125"),
        ("about 6%", "At 3v3 a current-code study sees **6.0%**."),
        ("about 6%", "so at three fits per arm the loop resolves about **6%**."),
        ("1.4%", "| pipeline non-determinism | **1.42%** | two renders |"),
        ("1.4%", "the applicable floor is pipeline non-determinism at 1.42%"),
        ("1.4%", "the pipeline is deterministic to within 1.4%"),
        ("2.0x", "**2.0× quieter, NOT established** (F(18,6)=3.83, p=0.104)"),
        ("4.1x", "current code is four times quieter"),
        ("±3%", "the null rules out anything beyond ±3.0%"),
        ("±3%", "an ink effect within +/-3%"),
        ("count to 1.2%", "the count\nreproduces to **1.2%**, and the mechanism"),
        (
            "count to 1.2%",
            "seeds agree on `total_fg_pixels` to 1.2% and on ink placement",
        ),
        ("2.6x", "is 2.6x too wide for the outer ones"),
        ("2.6x", "the inner floor is **2.6×** wider than the outer"),
        ("2.6x", "It is **0.0421**, two and a half times **quieter**."),
        ("bounded at ~12%", "both ink nulls are bounded at ~12%, not zero"),
        ("bounded at ~12%", "the pinned null bounds **~12%** at three fits"),
        ("7-20x", "smooth moves the two extreme windows by **7–20×** that"),
        ("7-20x", "moves them 7 to 20 times the control bound"),
    ],
)
def test_the_pattern_sees_through_markup_and_rewording(claim, live):
    pattern, _, _, required = _claim(claim)
    assert re.search(pattern, live, re.I) and not _cleared(live, required)


def test_a_marker_is_the_figure_not_its_digits():
    # 0.44% and 144% are not 44%; a line number is not the 206-test count
    assert not _cleared("a 0.44% shift, 144% of baseline", _claim("75%")[3])
    assert not _cleared("see line 206", _claim("20 core tests")[3])
    # 3.04% is quoted beside the flatten for other reasons; only "one draw" corrects 1.42%
    assert not _cleared("the flatten moves ink 3.04%", _claim("1.4%")[3])
    assert not _cleared(
        "about 12% at three fits, 112.3% of baseline", _claim("about 6%")[3]
    )
    assert not _cleared("the three control seeds", _claim("±3%")[3])
    assert not _cleared("a 16.4% shift", _claim("count to 1.2%")[3])
    # naming the pooling, or the MDE, beside the old figure is not correcting it
    assert not _cleared("pooled at df=18, 12.1x the bound", _claim("2.6x")[3])
    assert not _cleared("the design MDE is 12%", _claim("bounded at ~12%")[3])
    assert _cleared("~12% is the design MDE", _claim("bounded at ~12%")[3])
    assert not re.search(_claim("2.6x")[0], "a 12.6x wider window", re.I)
    for figure in ("resolves 60%", "resolves 16%", "sees 6.5%"):
        assert not re.search(_claim("about 6%")[0], figure, re.I)
