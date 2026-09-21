"""A quotation attributed to villa's autoresearch.md must appear in it verbatim.

Two overstatements in one hour (2026-09-21) were both claims about what villa's
loop doc says, and both would have been refuted by anyone who had read it. The
guard-fires claim misread a directional rule; the two-seed claim asserted villa
"attributes all of it to the fit" when line 52 names CUDA non-determinism. A
sweep then found two literal misquotations -- a dropped "roughly" inside quote
marks, and "Run two seeds" presented as villa's phrase when the doc says "robust
across seeds/runs". Both drifted in the direction that flattered the argument.

This checks the literal quotations. It cannot check paraphrase, which is where
the first two errors lived; that needs a re-read, and this test is the reminder.

A quotation counts only when its paragraph attributes it: the paragraph names
`autoresearch.md` AND the quote is introduced by says/prescribes/names/reads/
line N. Quoting my OWN withdrawn phrasing beside its retraction is not an
attribution and is skipped.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "villa" / "spiral-fitting" / "autoresearch.md"
DOCS = sorted(
    list((REPO / "reports").glob("*.md")) + list((REPO / "docs").glob("*.md"))
)
ATTRIB = re.compile(
    r"(autoresearch\.md|villa'?s? (own )?(loop )?doc)[^.\n]{0,80}?"
    r"(says?|prescribes?|names?|reads?|states?|line \d+)[^\"“]{0,40}[\"“]([^\"”]{10,160})[\"”]",
    re.I | re.S,
)


def _norm(s: str) -> str:
    s = s.replace("**", "").replace("`", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip().lower()


def attributed_quotes():
    out = []
    for f in DOCS:
        text = f.read_text(errors="ignore")
        for para in re.split(r"\n\s*\n", text):
            for m in ATTRIB.finditer(para):
                out.append((f.relative_to(REPO), m.group(5)))
    return out


@pytest.mark.skipif(not SOURCE.exists(), reason="villa submodule not checked out")
def test_every_attributed_quotation_is_verbatim():
    src = _norm(SOURCE.read_text())
    missing = [(f, q) for f, q in attributed_quotes() if _norm(q) not in src]
    assert not missing, (
        "quotations attributed to autoresearch.md but not in it:\n  "
        + "\n  ".join(f"{f}: {q[:100]!r}" for f, q in missing)
    )


def test_the_pattern_catches_a_dropped_word():
    """The actual defect: 'roughly' dropped inside quote marks."""
    para = 'the loop `autoresearch.md` says "lifts total while holding fraction steady is a real win".'
    m = ATTRIB.search(para)
    assert m and "holding fraction steady" in m.group(5)
    assert (
        _norm(m.group(5)) not in _norm(SOURCE.read_text()) if SOURCE.exists() else True
    )


def test_the_pattern_ignores_my_own_retraction_quotes():
    """Quoting a withdrawn claim beside its correction is not an attribution."""
    para = 'An earlier draft said the loop "attributes all of it to the fit"; that was wrong.'
    assert ATTRIB.search(para) is None


def test_the_sweep_finds_at_least_the_known_good_quotes():
    """Sanity: the checker actually sees quotations, so a clean pass is not vacuous."""
    qs = [q for _, q in attributed_quotes()]
    assert any("cuda non-determinism" in _norm(q) for q in qs), qs
