"""The two headline results are quoted in six places; pin them to the artifacts.

`-10.35%`, `+17.66%`, `-0.83%`, `-3.80%` and `+16.24%` appear across the verdict
reports, the findings summary, FINDINGS.md, the README front door, the prize
filing draft and memory. They came from `analyse_patch_bootstrap.py` and
`analyse_stripmatch.py`, which wrote the json artifacts beside the reports.

Nothing bound the prose to those artifacts. The repo's `audit_report_claims.py`
covers exactly one report and binds numbers per paragraph, so pointing it at
these returns "checked 0" -- which reads like a pass and is not one. Rather than
rebuild that auditor, this pins the specific figures that would propagate if they
drifted: a re-run that shifted a number, or an edit that mistyped one, currently
changes six documents and no test.

Deliberately narrow. It checks the headline effect sizes and the verdicts, not
every number in every report.
"""

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_REPORTS = _REPO / "reports"

# (artifact, the .md that must quote it, ink %, geometry %)
CASES = [
    ("patch_bootstrap_verdict.json", "patch_bootstrap_verdict.md", "-0.83%", "17.66%"),
    ("stripmatch_verdict.json", "stripmatch_verdict.md", "-3.80%", "16.24%"),
]

# Documents that quote the headline figures in prose. Prize filings are globbed
# rather than listed: a filing is the one document that leaves the building, and
# a future one must not be able to quote these figures without the caveats simply
# by not being named here. Filings predating these studies quote none of the
# figures, so the checks below are inert for them.
QUOTING_DOCS = [
    _REPORTS / "SPIRAL_FINDINGS_SUMMARY.md",
    _REPO / "FINDINGS.md",
    _REPO / "README.md",
    *sorted((_REPO / "docs").glob("PRIZE_FILING_*.md")),
]


def _artifact(name):
    return json.loads((_REPORTS / name).read_text())


@pytest.mark.parametrize(("art", "md", "ink_pct", "geom_pct"), CASES)
def test_the_report_quotes_its_own_artifact(art, md, ink_pct, geom_pct):
    d = _artifact(art)
    text = (_REPORTS / md).read_text()

    assert f"{d['ink']['rel_diff'] * 100:.2f}%" == ink_pct, (
        f"{art} ink moved to {d['ink']['rel_diff'] * 100:.2f}%; the reports still "
        f"say {ink_pct}. Re-run the analysis and update every quoting document."
    )
    assert ink_pct.lstrip("-") in text, f"{md} does not quote its own ink figure"
    assert f"{d['geometry']['rel_diff'] * 100:.2f}%" == geom_pct
    assert geom_pct in text, f"{md} does not quote its own geometry figure"


@pytest.mark.parametrize(("art", "md", "ink_pct", "geom_pct"), CASES)
def test_the_verdict_is_failure_and_the_prediction_was_met(art, md, ink_pct, geom_pct):
    """Both studies returned FAILURE with the registered prediction met. If a
    re-run ever changes that, every summary saying so becomes wrong at once."""
    d = _artifact(art)
    assert d["verdict"] == "FAILURE"
    assert d["prediction_met"] is True
    assert "FAILURE" in (_REPORTS / md).read_text()


def test_the_geometry_gain_is_never_presented_without_its_caveat():
    """+17.66% and +16.24% are circular by construction. Any document quoting one
    must say so nearby, or a reader takes it for a partial success."""
    for doc in QUOTING_DOCS:
        text = doc.read_text()
        for fig in ("17.66%", "16.24%"):
            if fig in text:
                assert "circular" in text.lower(), (
                    f"{doc.name} quotes {fig} without the word 'circular'. That "
                    "figure is guaranteed by the selection rule and must not read "
                    "as a partial win."
                )


def test_the_nulls_are_never_stated_as_no_effect():
    """Both ink results are bounded at ~10%, not zero. 'No effect' would be a
    stronger claim than three fits per arm can support."""
    for doc in QUOTING_DOCS + [_REPORTS / c[1] for c in CASES]:
        text = doc.read_text().lower()
        if "0.83%" in text or "3.80%" in text:
            assert "bounded" in text or "larger than" in text, (
                f"{doc.name} quotes a null ink result without bounding it"
            )
