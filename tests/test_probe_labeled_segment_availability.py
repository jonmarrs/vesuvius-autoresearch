"""The exhaustion claim must be re-checkable, not measured once.

The 2026-08-14 claim-vs-test audit found that this project's failures were never in
metric code -- they were properties measured once and never re-checked. The finding that
registered-GT training data is exhausted on Scroll-1 gates a published benchmark, so its
classification logic is pinned here and its live half is re-run by the probe.
"""

import json
import pathlib
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
        "20231005123336": 55.1,
        "20231210121321": 32.0,
    }
    out = classify(
        LABELED, BUCKET_2023, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["in_gate"] == ["20230702185753", "20231210121321"]
    assert out["measured_passing"] == ["20231210121321"]
    assert out["exhausted"] is True


def test_a_second_well_placed_segment_would_lift_exhaustion():
    """Guard against the claim silently outliving the condition that produced it."""
    bucket = BUCKET_2023 + ["20230820203112"]
    placements = {"20231210121321": 32.0, "20230820203112": 30.0}
    out = classify(
        LABELED, bucket, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["measured_passing"] == ["20230820203112", "20231210121321"]
    assert out["exhausted"] is False


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
    assert d["surveyed"] == "2026-08-15"
