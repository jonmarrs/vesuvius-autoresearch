"""Bind the separate research answer and Finding 99 filing claims to the measured artifacts."""

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = (ROOT / "docs/PRIZE_FILING_2026-10_RESEARCH_FORM_ANSWERS.md").read_text()
DRAFT = " ".join((ROOT / "docs/PRIZE_FILING_2026-10_DRAFT.md").read_text().split())


def test_research_context_claims_are_the_two_completed_studies():
    docs = [
        json.loads((ROOT / f"reports/{name}.json").read_text())
        for name in ("neural_tracer_ct_context", "neural_tracer_ct_context_512")
    ]
    assert [len(d["rows_tol2"]) for d in docs] == [10, 11]
    text = " ".join(RESEARCH.split())
    for d, size in zip(docs, (256, 512), strict=True):
        factors = [
            r["coverage"] / d["finding_91_rows_tol2"][c]["coverage"]
            for c, r in d["rows_tol2"].items()
        ]
        phrase = f"{min(factors):.2f}–{max(factors):.2f}× on all {('ten' if size == 256 else 'eleven')} {size}³ cubes"
        assert phrase in text
    assert "other entrants remain cube-only" in text
    assert "not a new model" in text


def test_finding_99_scope_and_angles_are_the_recorded_results():
    d = json.loads((ROOT / "reports/neural_tracer_heading_residual.json").read_text())
    cubes = d["cubes"]
    small = [r for c, r in cubes.items() if c.endswith("_256")]
    held = [
        cubes[c]["near_gt"]["disagree"]
        for c in ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
    ]
    assert (
        f"all {sum(r['classified'] for r in small):,} dots on the ten 256³ cubes"
        in DRAFT
    )
    assert f"a fixed sample of {d['sample_512']:,} on each 512³ cube" in DRAFT
    assert all(
        r["counts"][k] == 0
        for r in cubes.values()
        for k in ("edge", "no_normal", "ambiguous")
    )
    angles = [r["median_presence_to_gt"] for r in held]
    assert f"a median {min(angles):.0f}–{max(angles):.0f}° from its tangent" in DRAFT
    assert {round(r["median_ct_axis_to_gt"]) for r in held} == {58}
    assert "while the CT family axis is 58°" in DRAFT
    assert "finding 99, exploratory: not pre-registered" in DRAFT
    assert "No tracing or coverage improvement was measured here" in DRAFT
    assert "does not classify the unsampled dots" in DRAFT


def test_submissions_have_separate_scope_and_are_still_drafts():
    assert "not submitted" in RESEARCH
    assert (
        "three merged Villa fixes; those fixes are not credited again here"
        in " ".join(RESEARCH.split())
    )
    assert "11:59 p.m. Pacific" in RESEARCH and "October 31, 2026" in RESEARCH
    assert (
        "production Villa and the published benchmark rows are unchanged"
        in " ".join(RESEARCH.split())
    )
    assert "credited to him" in RESEARCH


def test_memory_claim_is_a_reproduction_not_a_new_quality_result():
    d = json.loads(
        (ROOT / "reports/evidence/scrollgt_memory_2026-10-25.json").read_text()
    )
    cases = [r for r in d["cases"] if r["variant"] == "after"]
    assert len(cases) == 2 and all(r["exact_metric_match"] for r in cases)
    assert {len(r["scorecard"]["metrics"]) for r in cases} == {15}
    large = next(r for r in cases if r["cube"].endswith("_512"))
    rss = large["measurement"]["peak_rss_kib"] / 1024**2
    assert f"at {rss:.2f} GiB peak RSS" in " ".join(RESEARCH.split())
    assert large["measurement"]["address_space_limit_bytes"] == 7 * 1024**3
    assert "under a 7 GiB address-space budget" in " ".join(RESEARCH.split())
    assert d["real_array_identity"]["raw_score_fields_identical"] is True
    assert "later usability patch" in RESEARCH


def test_completed_heading_pilot_is_scoped_and_its_failed_prediction_is_kept():
    d = json.loads((ROOT / "reports/neural_tracer_steep_heading.json").read_text())
    text = " ".join(RESEARCH.split())
    base, rows = d["baseline_rows_tol2"], d["rows_tol2"]["sheet"]
    s5 = [
        c
        for c in base
        if c.startswith("s5_")
        and c.endswith("_256")
        and c in ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
    ]
    factors = [rows[c]["coverage"] / base[c]["coverage"] for c in s5]
    assert (
        f"{min(factors):.2f}–{max(factors):.2f}× coverage on the two held-out Scroll-5 cubes"
        in text
    )
    s3 = [c for c in base if c.startswith("s3_")]
    med = statistics.median(rows[c]["coverage"] / base[c]["coverage"] for c in s3)
    assert d["status"] == "OK" and d["verdict"]["prediction_P2"] is False
    assert f"the median is only {med:.3f}×, below the registered 1.05×" in text
    assert "does not establish tilt as the cause" in text


def test_the_erl_example_and_finding_99s_status_are_the_drafts():
    """The ERL example is the draft's deletion of short instances, not one deletion, and finding 99 is labelled
    exploratory where the answer says the linked context studies were pre-registered."""
    text = " ".join(RESEARCH.split())
    assert (
        "deleting our tracer's instances under 400 voxels raised the old ERL from 35.39 to 41.46 while coverage "
        "fell from 0.62 to 0.38" in text
    )
    assert (
        "Deleting our tracer's instances under 400 voxels raised it 17% (35.39 → 41.46) while coverage fell from "
        "0.62 to 0.38" in DRAFT
    )
    assert "one deletion" not in text
    d = json.loads((ROOT / "reports/neural_tracer_heading_residual.json").read_text())
    assert d["status"].startswith("exploratory,")
    assert "Finding 99, exploratory and not pre-registered, identifies" in text
