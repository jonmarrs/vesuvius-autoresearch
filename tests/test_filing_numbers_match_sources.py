"""Every number the prize filing quotes must match the artifact it came from.

The filing is the one outward-facing document with a deadline, and in the 24
hours before this test existed three of its figures were withdrawn and rewritten:
the current-tier CV (0.0125 -> 0.0263), the MDE it implies (2.9% -> 6.0%) and a
two-seed power figure (99.2% -> 75.0%). Each had to be chased by hand through
several files, and one survived the first pass in a section I had not thought to
grep.

Nothing bound the filing's prose to the json artifacts that produce those
numbers, so a re-run or a retraction changed the reports and left the filing
stale and confident.

Two kinds of check here:

* **positive** -- a quoted figure must equal the artifact, to the precision it is
  quoted at;
* **negative** -- a WITHDRAWN figure must not appear except beside an explicit
  withdrawal. That half matters more: a stale number does not announce itself,
  and the filing reads perfectly well with the wrong value in it.
"""

import json
import re
from math import comb
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_FILING = _REPO / "docs/PRIZE_FILING_2026-09_DRAFT.md"
# The SUBMIT file is the text that actually gets pasted into the form, so it
# needs the same guarantees as the draft -- arguably more, since nobody
# re-reads it before submitting.
_SUBMIT = _REPO / "docs/PRIZE_FILING_2026-09_SUBMIT.md"
_REPORTS = _REPO / "reports"

pytestmark = pytest.mark.skipif(not _FILING.exists(), reason="filing draft removed")

_MINUS = "−"  # the prose uses a typographic minus; artifacts emit ASCII "-"


def _text() -> str:
    return _FILING.read_text().replace(_MINUS, "-")


def _artifact(name: str) -> dict:
    return json.loads((_REPORTS / name).read_text())


def test_the_anchor_ablation_effect_and_interval_match_the_artifact():
    a = _artifact("anchor_ablation_verdict.json")
    t = _text()
    assert f"{a['ink']['rel_diff']:.2%}" in t, "anchor point estimate not quoted"
    ci = a["ink_relative_ci"]
    assert f"{ci['lo']:.2%}" in t, "lower bound of the anchor CI not quoted"
    assert f"{ci['hi']:+.2%}" in t, "upper bound of the anchor CI not quoted"


def test_the_same_winding_effect_matches_the_artifact():
    a = _artifact("samewinding_current_verdict.json")
    assert f"{a['ink']['rel_diff']:+.2%}" in _text(), "same-winding estimate not quoted"


def test_the_current_tier_cv_and_mde_match_the_noise_floor_artifact():
    n = _artifact("noise_floor_by_tier.json")["current"]
    t = _text()
    assert f"{n['cv']:.4f}" in t, f"filing must quote the current CV {n['cv']:.4f}"
    mde = 2.802 * n["cv"] * (2 / 3) ** 0.5
    assert f"{mde:.0%}" in t, f"filing must quote the implied MDE {mde:.0%}"


@pytest.mark.parametrize(
    "withdrawn,why",
    [
        ("0.0125", "current-tier CV, withdrawn when a third arm moved it to 0.0263"),
        ("2.9%", "MDE implied by the withdrawn CV"),
        ("99.2%", "two-seed power at the withdrawn CV; the real figure is 75.0%"),
        ("4.1x", "quieter-than-pinned ratio, not established at p=0.104"),
    ],
)
def test_withdrawn_figures_appear_only_beside_a_withdrawal(withdrawn, why):
    """The half that matters. A stale number reads perfectly well."""
    body = _text().replace("×", "x")
    for para in re.split(r"\n\s*\n", body):
        if withdrawn not in para:
            continue
        low = para.lower()
        assert any(
            w in low
            for w in (
                "withdrew",
                "withdrawn",
                "retract",
                "no longer",
                "first published",
                "superseded",
                "we published",
            )
        ), f"{withdrawn!r} ({why}) appears with no withdrawal:\n{para.strip()[:200]}"


def test_the_two_seed_rates_are_exact_and_quoted_as_such():
    """1/C(2k,k) is arithmetic, so this is checkable against the formula."""
    t = _text()
    assert "1 in 6" in t or "1/6" in t
    assert "1 in 20" in t or "1/20" in t
    assert 1 / comb(4, 2) == pytest.approx(1 / 6)
    assert 1 / comb(6, 3) == pytest.approx(0.05)


def test_the_filing_names_the_tree_its_pinned_results_came_from():
    assert "6847063f" in _text()


def _submit_text() -> str:
    return _SUBMIT.read_text().replace(_MINUS, "-")


@pytest.mark.skipif(not _SUBMIT.exists(), reason="submit file not prepared")
@pytest.mark.parametrize(
    "withdrawn,why",
    [
        ("0.0125", "current-tier CV, withdrawn when a third arm moved it to 0.0263"),
        ("2.9%", "MDE implied by the withdrawn CV"),
        ("99.2%", "two-seed power at the withdrawn CV"),
        ("153 MB", "scrollgt image size, measured at 660 MB"),
        ("20 core tests", "offline claim, actually all 206"),
    ],
)
def test_the_submit_text_carries_no_withdrawn_figure(withdrawn, why):
    """The draft may name a withdrawn number beside its withdrawal, for the
    record. The SUBMIT text is pasted into a form and has no room for that
    nuance, so the figure must simply not appear."""
    assert withdrawn not in _submit_text(), (
        f"{withdrawn!r} ({why}) is in the submit text"
    )


@pytest.mark.skipif(not _SUBMIT.exists(), reason="submit file not prepared")
def test_the_submit_text_keeps_the_disclosure_and_the_tier():
    t = _submit_text()
    assert "6847063f" in t, "the tier the pinned results came from must be named"
    assert "superseded" in t
    assert "went against us" in t, "the failed re-measurement must stay disclosed"


@pytest.mark.skipif(not _SUBMIT.exists(), reason="submit file not prepared")
def test_the_submit_text_may_cite_the_placement_work_but_never_its_mechanism():
    """The exclusion was CONDITIONAL -- "does not go in a submission until it has
    survived that test" -- and on 2026-09-15 it survived: predicted 0.877, measured
    0.875 and 0.893. So the result is admissible.

    What stays excluded is the part that is still unknown. Why placement reproduces
    at 0.70 while the count reproduces to 1.2% is unexplained after two failed
    tests, and a submission must not imply otherwise."""
    t = _submit_text()
    body = t.lower().split("## do not add")[0]
    # 0.884 was the superseded three-arm prediction; only 0.877 was registered.
    assert "0.884" not in t, "cites the superseded prediction"
    for claim in ("because the fit", "mechanism is", "explained by", "the cause is"):
        assert claim not in body, f"submission implies a mechanism: {claim!r}"


def test_the_spiralcheck_figures_match_the_validation_artifacts():
    """Added 2026-09-24 with the paragraph. The seed CV and the "every p >= 0.10"
    floor both come from the registered verdict and its descriptive companion."""
    v = _artifact("spiralcheck_validation/verdict.json")
    d = _artifact("spiralcheck_validation/descriptive.json")
    assert v["verdict"] == "NOT DISCRIMINATING HERE"
    ps = [m["p"] for q in ("q2_all", "q3_scored") for m in v[q].values()]
    assert min(ps) >= 0.10, "the filing says every p >= 0.10"
    cv = f"{d['cv all violated_bin_fraction']:.1%}"
    for text in (_text(), _submit_text()):
        assert cv in text, f"spiralcheck seed CV {cv} not quoted"
        assert "p ≥ 0.10" in text, "the p floor is not quoted"


@pytest.mark.skipif(not _SUBMIT.exists(), reason="submit file not prepared")
def test_the_submit_text_answers_the_weights_criterion_added_upstream():
    """villa #1887 (2026-09-24) added "This includes releasing model weights and
    training data where applicable" to the Progress criteria. The pre-paste note
    had said the section was byte-identical to the pin; that went false that day."""
    t = _submit_text()
    field3 = t.split("## Field 3")[1].split("## Required disclosure")[0]
    assert "model weights" in field3 and "training data" in field3
    assert "byte-identical between the pin and upstream" not in t
    assert "#1871" in t, "results must be dated against the upstream simplification"


def test_the_upstream_fitter_interval_matches_its_verdict():
    """Added 2026-09-25 when the registered re-measurement landed: the filing's
    "re-measured" sentence must quote the verdict's own interval, in both files."""
    v = _artifact("upstream_fitter_verdict.json")
    assert v["verdict"] == "NO DETECTED CHANGE"
    c = v["relative_ci"]
    for text in (_text(), _submit_text()):
        assert f"{c['rel']:+.2%}" in text
        assert f"{c['lo']:.2%}" in text and f"{c['hi']:+.2%}" in text
        assert "not been re-measured" not in text
