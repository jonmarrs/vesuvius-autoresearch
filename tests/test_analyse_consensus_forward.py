"""Tests for the consensus forward test, written before the arms exist.

Two rules carry the weight, and they are deliberately separate:

* the VALIDITY GATE decides whether the comparison means anything;
* the DECISION RULE decides what the number says, given that it does.

`reports/the_sanity_check_caught_a_false_positive.md` records a decision rule
reporting a significant artefact three times over, which is why a gate failure
must produce VOID and never a null.
"""

import inspect
import json
import os
import sys

import numpy as np
import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_consensus_forward as mod  # noqa: E402
import compare_ink_in_volume as vol  # noqa: E402


def test_the_registered_numbers_are_constants():
    assert mod.PREDICTED == 0.884
    assert mod.BAND == (0.884, 0.904)
    assert mod.CONFIRM == (0.86, 0.92)
    assert mod.REFUTE_BELOW == 0.80
    assert mod.TRIPLET_A == ("curbase_s1", "curbase_s2", "curbase_s3")
    assert mod.TRIPLET_B == ("curbase_s4", "curbase_s5", "curbase_s6")


def test_the_two_triplets_share_no_arm():
    """What makes this a forward test rather than a re-analysis."""
    assert not set(mod.TRIPLET_A) & set(mod.TRIPLET_B)


@pytest.mark.parametrize(
    "r,expected",
    [
        (0.95, "BETTER THAN PREDICTED"),
        (0.90, "CONFIRMED"),
        (0.884, "CONFIRMED"),
        (0.86, "CONFIRMED"),
        (0.83, "PARTIAL"),
        (0.80, "PARTIAL"),
        (0.79, "REFUTED"),
        (0.5, "REFUTED"),
    ],
)
def test_the_decision_rule_matches_the_registration(r, expected):
    assert mod.verdict(r)[0] == expected


def test_a_refutation_says_withdraw_not_qualify():
    why = mod.verdict(0.5)[1]
    assert "WITHDRAWN" in why and "not qualified" in why


def test_the_gate_is_not_an_input_to_the_decision_rule():
    """verdict() must not see gate state; a gate failure overrides it entirely
    at the call site, rather than being blended into the verdict."""
    assert set(inspect.signature(mod.verdict).parameters) == {"r"}


def test_a_partial_sample_is_refused(tmp_path):
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


def test_gate_thresholds_bracket_what_has_already_been_measured():
    """Cross-triplet singles should sit where within-triplet singles did
    (0.650-0.730). A gate that excluded the known range would void every run."""
    lo, hi = mod.GATE_SINGLE
    assert lo <= 0.650 and hi >= 0.730
    ink_lo, ink_hi = mod.GATE_INK
    for measured in (2_841_071, 2_904_520, 2_722_693, 2_951_176):
        assert ink_lo <= measured <= ink_hi


def test_load_xyz_returns_None_for_a_missing_arm_instead_of_raising():
    """The generator bug: load_xyz returned a generator, so its try/except never
    fired and a missing arm crashed the caller instead of being reported."""
    assert vol.load_xyz("/nonexistent/arm") is None
    src = inspect.getsource(vol.load_xyz)
    assert "tuple(" in src, "must be eager, or the try/except cannot catch"


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/consensus_forward_verdict.json")),
    reason="study still running",
)
def test_the_published_verdict_records_the_gate_outcome():
    d = json.load(open(os.path.join(_REPO, "reports/consensus_forward_verdict.json")))
    assert "gate_failures" in d
    if d["gate_failures"]:
        assert d["verdict"] == "VOID"
