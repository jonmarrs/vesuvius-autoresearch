"""Tests for the calibrated consensus re-test, written before triplet C exists.

Two things go wrong in this family of studies and both are guarded here:

* a gate calibrated on too little data rejecting a real arm (that voided the
  previous run);
* re-reporting a comparison whose answer is already known, under a threshold
  widened afterwards.

The second is why A-vs-B is structurally retired rather than merely omitted.
"""

import inspect
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_consensus_retest as mod  # noqa: E402


def test_the_registered_numbers_are_constants():
    assert mod.PREDICTED == 0.877
    assert mod.CONFIRM == (0.85, 0.91)
    assert mod.PARTIAL == (0.79, 0.85)
    assert mod.REFUTE_BELOW == 0.79


def test_the_gate_is_the_six_arm_prediction_interval():
    lo, hi = mod.GATE_INK
    assert (lo, hi) == (2_398_918.0, 3_639_084.0)
    # it must contain every arm the process has actually produced, s6 included --
    # rejecting one of those is what voided the previous study
    for measured in (2_841_071, 2_904_520, 2_992_717, 3_019_583, 3_454_937):
        assert lo <= measured <= hi, f"{measured:,} is an arm this process made"


def test_A_vs_B_is_retired_and_not_among_the_comparisons():
    assert frozenset({"A", "B"}) in mod.RETIRED
    for a, b in mod.COMPARISONS:
        assert frozenset({a, b}) not in mod.RETIRED
    assert set(mod.COMPARISONS) == {("A", "C"), ("B", "C")}


def test_both_forward_comparisons_involve_the_new_triplet():
    """A comparison between two already-seen triplets is not a forward test."""
    for a, b in mod.COMPARISONS:
        assert "C" in (a, b)


@pytest.mark.parametrize(
    "r,expected",
    [
        (0.95, "BETTER THAN PREDICTED"),
        (0.90, "CONFIRMED"),
        (0.877, "CONFIRMED"),
        (0.85, "CONFIRMED"),
        (0.82, "PARTIAL"),
        (0.79, "PARTIAL"),
        (0.78, "REFUTED"),
    ],
)
def test_the_band_is_applied_mechanically(r, expected):
    assert mod.verdict_one(r) == expected


def test_disagreement_is_INCONSISTENT_and_claims_neither():
    tag, why = mod.combine(["CONFIRMED", "REFUTED"])
    assert tag == "INCONSISTENT"
    assert "Neither is claimed" in why
    assert "not to let one be picked" in why


def test_agreement_confirms_only_when_both_are_good():
    assert mod.combine(["CONFIRMED", "CONFIRMED"])[0] == "CONFIRMED"
    assert mod.combine(["CONFIRMED", "BETTER THAN PREDICTED"])[0] == "CONFIRMED"
    assert mod.combine(["REFUTED", "REFUTED"])[0] == "REFUTED"
    assert mod.combine(["PARTIAL", "CONFIRMED"])[0] == "INCONSISTENT"


def test_a_refutation_says_withdraw_not_qualify():
    assert "WITHDRAWN" in mod.combine(["REFUTED", "REFUTED"])[1]


def test_the_gate_is_not_an_input_to_the_per_comparison_verdict():
    assert set(inspect.signature(mod.verdict_one).parameters) == {"r"}


def test_a_partial_sample_is_refused(tmp_path):
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_REPO, "reports/consensus_retest_verdict.json")),
    reason="re-test still running",
)
def test_the_published_verdict_never_reports_the_retired_pair():
    d = json.load(open(os.path.join(_REPO, "reports/consensus_retest_verdict.json")))
    pairs = {c["pair"] for c in d["comparisons"]}
    assert "A-B" not in pairs and "B-A" not in pairs
    assert pairs == {"A-C", "B-C"}
