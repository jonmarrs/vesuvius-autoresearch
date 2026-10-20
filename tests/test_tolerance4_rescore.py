"""scripts/tolerance4_rescore.py: our tracer and connected components at tolerance 4, beside villa's neural tracer."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tolerance4_rescore as t4  # noqa: E402

PEN = "erl_merge_penalized"
ALL, S3, INS = t4.f91.ALL, t4.f91.S3, t4.f91.IN_SAMPLE
ROW = {
    "n_pred_instances": 7,
    "pred_length": 100.0,
    "gt_length": 50.5,
    "n_gt_fibers": 3,
    "erl": 1.0,
}


def test_a_labelling_must_reproduce_its_published_rows_fixed_fields():
    assert (
        t4.identity_problems(ROW, {**ROW, "erl": 9.0}) == []
    )  # the scores themselves move with the tolerance
    for k in t4.SAME:
        bad = t4.identity_problems(ROW, {**ROW, k: ROW[k] + 1})
        assert len(bad) == 1 and bad[0].startswith(k), bad


def test_the_labellings_are_finding_80s_and_finding_83s():
    assert (
        t4.tracer_labelling("s1_00497_01497_03997_256")
        == t4.RESCORE / "s1_00497_01497_03997_256_instances.npy"
    )
    assert (
        t4.tracer_labelling("s3_00994_00494_01994_512")
        == t4.HELDOUT / "s3_00994_00494_01994_512_instances.npy"
    )
    assert t4.tracer_labelling("s5_13497_01497_02497_256").parent == t4.HELDOUT
    assert {c for c in ALL if t4.tracer_labelling(c).parent == t4.RESCORE} == set(INS)


def _rows(v):
    return {c: ({PEN: x} if x is not None else None) for c, x in v.items()}


def _verdict(neural, tracer):
    return t4.verdict(_rows(neural), _rows(tracer))


def test_both_hold():
    v = _verdict({c: (5.0 if c in S3 else 1.0) for c in ALL}, {c: 2.0 for c in ALL})
    assert v["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": True,
        "P2_in_sample_trails_tracer_on_9_of_11": True,
    }
    assert v["s3_leading_tracer"] == [8, 8] and v["in_sample_trailing_tracer"] == [
        11,
        11,
    ]
    assert v["readings"] == [
        "the Scroll-3 lead holds at tolerance 4",
        "the in-sample deficit holds at tolerance 4",
    ]


def test_the_thresholds_and_ties():
    neural = (
        {c: 2.0 for c in ALL} | {c: 5.0 for c in S3[:6]} | {c: 1.0 for c in INS[:9]}
    )
    v = _verdict(neural, {c: 2.0 for c in ALL})  # ties neither lead nor trail
    assert v["s3_leading_tracer"] == [6, 8] and v["in_sample_trailing_tracer"] == [
        9,
        11,
    ]
    assert all(v["predictions"].values())
    neural = (
        {c: 2.0 for c in ALL} | {c: 5.0 for c in S3[:5]} | {c: 1.0 for c in INS[:8]}
    )
    v = _verdict(neural, {c: 2.0 for c in ALL})
    assert not any(v["predictions"].values())
    assert v["readings"] == [
        "the Scroll-3 lead is tolerance-dependent: recommend a ScrollGT note where the lead is claimed",
        "the in-sample deficit is tolerance-dependent: recommend a ScrollGT note where the deficit is claimed",
    ]


def test_too_few_cubes_leave_a_prediction_unevaluated():
    tracer = (
        {c: 2.0 for c in ALL} | {c: None for c in S3[:3]} | {c: None for c in INS[:3]}
    )
    v = _verdict({c: 5.0 for c in ALL}, tracer)
    assert v["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": None,
        "P2_in_sample_trails_tracer_on_9_of_11": None,
    }


@pytest.mark.parametrize(
    "identity, s3_none, status",
    [
        ({"x": ["n_pred_instances=1"]}, 0, "IDENTITY_FAILED"),
        ({}, 3, "INCOMPLETE"),
        ({}, 0, "OK"),
    ],
)
def test_the_status(identity, s3_none, status):
    tracer = {c: 2.0 for c in ALL} | {c: None for c in S3[:s3_none]}
    got, reading = t4.outcome(identity, _rows({c: 5.0 for c in ALL}), _rows(tracer))
    assert got == status and (reading is None) == (status == "IDENTITY_FAILED")
