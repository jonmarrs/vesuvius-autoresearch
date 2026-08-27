"""The exhaustion claim must be re-checkable, not measured once.

The 2026-08-14 claim-vs-test audit found that this project's failures were never in
metric code -- they were properties measured once and never re-checked. The finding that
registered-GT training data is exhausted on Scroll-1 gates a published benchmark, so its
classification logic is pinned here and its live half is re-run by the probe.
"""

import json
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from probe_labeled_segment_availability import (  # noqa: E402
    RETIRED_NON_SCORING,
    classify,
    labeled_segments,
    placements_on_disk,
)

# The 2026-08-15 survey, recorded so a regression is visible as a diff.
LABELED = [
    "20230702185753",
    "20230820203112",
    "20230826170124",
    "20230903193206",
    "20231005123336",
    "20231210121321",
]
PRESENT = ["20230702185753", "20231005123336", "20231210121321"]
ABSENT = ["20230820203112", "20230826170124", "20230903193206"]
UNLABELED_2023 = [
    "20230929220926",
    "20231007101619",
    "20231012184424",
    "20231016151002",
    "20231022170901",
    "20231031143852",
    "20231106155351",
    "20231221180251",
]
BUCKET_2023 = sorted(PRESENT + UNLABELED_2023)


def test_classify_partitions_labelled_segments_by_availability():
    out = classify(LABELED, BUCKET_2023, {}, gate_px=48.0)
    assert out["present"] == PRESENT
    assert out["absent"] == ABSENT
    assert out["unlabeled_2023"] == UNLABELED_2023


def test_clearing_the_gate_is_necessary_but_not_sufficient():
    """20230702185753 clears the gate by 1.4px and is still unusable.

    It was retired as non-scoring on 2026-08-14 because its worst tile reaches ~1.9x the
    512um analysis window. A probe that counted it would report exhausted=False and
    contradict the report it exists to support.
    """
    placements = {
        "20230702185753": 46.6,
        "20231005123336": 57.5,
        "20231210121321": 32.0,
    }
    out = classify(
        LABELED, BUCKET_2023, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["in_gate"] == ["20230702185753", "20231210121321"]
    assert out["measured_passing"] == ["20231210121321"]
    assert out["exhausted"] is True


def test_a_second_well_placed_segment_would_lift_exhaustion():
    """Guard against the claim silently outliving the condition that produced it.

    Note this hands classify() a placement a freshly published segment would NOT have --
    it models the end state, after someone in this repo has measured it. The step before
    that is covered by the next test.
    """
    bucket = BUCKET_2023 + ["20230820203112"]
    placements = {"20231210121321": 32.0, "20230820203112": 30.0}
    out = classify(
        LABELED, bucket, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["measured_passing"] == ["20230820203112", "20231210121321"]
    assert out["exhausted"] is False
    assert out["status"] == "not_exhausted"


def test_publication_alone_does_not_lift_exhaustion_but_does_change_state():
    """The case the suite used to mask: a bucket segment present WITHOUT a placement.

    Placement is read from measurements committed in this repo, so a segment upstream
    published yesterday arrives unmeasured and cannot flip `exhausted` by itself. That is
    correct -- publication is necessary, not sufficient -- but it makes `exhausted`
    sticky-true, so the probe has to show the change some other way or a re-run after
    publication looks identical to a re-run before it.
    """
    published = ["20230820203112", "20230826170124", "20230903193206"]
    bucket = sorted(BUCKET_2023 + published)
    placements = {"20231210121321": 32.0, "20230702185753": 46.6}
    before = classify(
        LABELED, BUCKET_2023, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    after = classify(
        LABELED, bucket, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )

    # Still exhausted, and honestly so: nothing new has been measured.
    assert after["exhausted"] is True
    assert after["measured_passing"] == ["20231210121321"]

    # But the state visibly moved, in the fields the report tells readers to watch.
    assert before["absent"] == published and after["absent"] == []
    assert len(after["present"]) == len(before["present"]) + 3
    assert set(after["unmeasured"]) == set(published) | {"20231005123336"}
    assert before["status"] == after["status"] == "exhausted_pending_measurement"


def test_status_separates_no_candidate_from_awaiting_our_measurement():
    """`exhausted: true` conflates two different situations; `status` must not."""
    no_candidate = classify(
        LABELED,
        ["20231210121321"],
        {"20231210121321": 32.0},
        retired=RETIRED_NON_SCORING,
        gate_px=48.0,
    )
    assert no_candidate["unmeasured"] == []
    assert no_candidate["status"] == "exhausted_no_candidate"

    awaiting_us = classify(
        LABELED,
        ["20231210121321", "20230820203112"],
        {"20231210121321": 32.0},
        retired=RETIRED_NON_SCORING,
        gate_px=48.0,
    )
    assert awaiting_us["unmeasured"] == ["20230820203112"]
    assert awaiting_us["status"] == "exhausted_pending_measurement"


def test_a_retired_segment_is_not_reported_as_awaiting_measurement():
    """20230702185753 is measured and retired; it is not a candidate in either sense."""
    out = classify(LABELED, BUCKET_2023, {}, retired=RETIRED_NON_SCORING, gate_px=48.0)
    assert "20230702185753" not in out["unmeasured"]


def test_survey_date_is_the_run_date_not_a_frozen_constant():
    """A stale stamp on freshly listed bucket contents is the failure mode this probe
    exists to prevent, so `surveyed` defaults to today rather than to a literal."""
    import datetime

    out = classify(LABELED, BUCKET_2023, {}, gate_px=48.0)
    assert out["surveyed"] == datetime.date.today().isoformat()
    assert classify(LABELED, BUCKET_2023, {}, surveyed="2026-08-15")["surveyed"] == (
        "2026-08-15"
    )


def test_offline_runs_are_distinguishable_from_live_ones():
    assert classify(LABELED, BUCKET_2023, {})["survey_mode"] == "live"
    assert (
        classify(LABELED, BUCKET_2023, {}, mode="offline")["survey_mode"] == "offline"
    )


def test_fragments_of_other_objects_are_not_counted_as_scroll1_segments():
    """train_scrolls/ also holds PHercParis2Fr47 and PHercParis2Fr143.

    Those are fragments of a different object, retained for the GP-winner reproduction.
    Counting them would inflate the Scroll-1 survey from 6 to 8.
    """
    root = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
    if not root.is_dir():
        pytest.skip("villa/ink-detection/train_scrolls not present")
    got = labeled_segments(root)
    assert not [s for s in got if not s.isdigit()]
    assert "PHercParis2Fr47" not in got and "PHercParis2Fr143" not in got


def test_placements_are_read_from_committed_validation_json():
    got = placements_on_disk(REPO_ROOT / "reports" / "detector")
    assert got["20231210121321"] == pytest.approx(32.0, abs=0.1)
    assert got["20230702185753"] == pytest.approx(46.6, abs=0.1)


def test_labeled_segments_matches_the_recorded_survey():
    root = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
    if not root.is_dir():
        pytest.skip("villa/ink-detection/train_scrolls not present")
    assert labeled_segments(root) == LABELED


def test_probe_json_if_present_agrees_with_the_recorded_survey():
    out = REPO_ROOT / "reports" / "detector" / "labeled_segment_availability.json"
    if not out.exists():
        pytest.skip("probe has not been run yet")
    d = json.loads(out.read_text())
    assert d["absent"] == ABSENT
    # The stamp must be present and well-formed, not equal to a literal: pinning the date
    # would fail whoever re-runs the probe, which is the one thing the report asks for.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["surveyed"])
    assert d["survey_mode"] in ("live", "offline")


def test_placements_are_read_from_both_shapes():
    """The fix. Measurements live in *_validation.json gate blocks AND in
    gt_finetune_prep.json regions. Reading only the first made the probe report
    20231005123336 as "present but unmeasured (ours to measure)" when it has been
    measured since 2026-08-15 at 57.5 px against a 48 px gate. That invented an
    unblock path which was already closed, an error pointing the same way as
    wishful thinking."""
    placements = placements_on_disk(REPO_ROOT / "reports" / "detector")
    assert "20231005123336" in placements
    assert 56.0 < placements["20231005123336"] < 58.5


def test_a_segment_with_several_regions_takes_its_worst():
    """A segment is usable only if its regions are. Taking the best offset would
    let one good region hide a bad one."""
    prep = json.loads(
        (REPO_ROOT / "reports" / "detector" / "gt_finetune_prep.json").read_text()
    )
    offsets = [
        r["placement_offset_level2_px"]
        for r in prep.get("regions", [])
        if (r.get("frag_id") or "").startswith("20231005123336")
        and r.get("placement_offset_level2_px") is not None
    ]
    placements = placements_on_disk(REPO_ROOT / "reports" / "detector")
    assert placements["20231005123336"] == max(offsets)


def test_nothing_is_left_to_measure():
    """The state this records. If it ever fails, something upstream published and
    there IS a next thing to try, which is the whole point of keeping the probe
    re-runnable rather than trusting the 2026-08-15 answer."""
    out = json.loads(
        (
            REPO_ROOT / "reports" / "detector" / "labeled_segment_availability.json"
        ).read_text()
    )
    assert out["status"] == "exhausted_no_candidate"
    assert out["unmeasured"] == []
