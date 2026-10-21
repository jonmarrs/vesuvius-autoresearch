"""scripts/tolerance4_rescore.py: our tracer and connected components at tolerance 4, beside villa's neural tracer."""

import json
import sys
import types
from pathlib import Path

import numpy as np
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


TRACER_ROW = {
    "n_pred_instances": 7,
    "pred_length": 100.0,
    "gt_length": 50.5,
    "n_gt_fibers": 3,
}
CC_ROW = {**TRACER_ROW, "n_pred_instances": 4, "pred_length": 80.0}


def _run_main(tmp_path, monkeypatch, bad=(), version=3):
    """main() end to end, with ScrollGT's scorer and target stubbed. Each cube's labellings reproduce their published
    rows (our tracer's and connected components' differ), except our tracer's on `bad`, which has one instance more.
    Our tracer scores 10.0 at tolerance 4, the neural tracer 20.0 on Scroll 3 and 5.0 elsewhere."""
    seen: dict = {"scored": []}
    index = {c: i for i, c in enumerate(ALL)}

    class Score:
        def __init__(self, row):
            self.row = row

        def as_row(self):
            return self.row

    def score_tracing(skel, labels, tolerance):
        cube = skel[1]
        seen["scored"].append((cube, tolerance))
        if isinstance(labels, tuple):  # connected components of the cube's own mask
            assert labels == ("cc", ("mask", cube))
            return Score({**CC_ROW, PEN: 3.0})
        assert labels[0] == index[cube]  # the cube's own saved labelling
        return Score({**TRACER_ROW, "n_pred_instances": 6 + labels.size, PEN: 10.0})

    def load_fiber_target(target):
        cube = target.name.removeprefix("fibers_")
        assert target == t4.f91.SG / "data" / f"fibers_{cube}"
        floors = {
            t4.f91.TRACER: {**TRACER_ROW, PEN: 2.0},
            t4.f91.CC: {**CC_ROW, PEN: 1.0},
        }
        return ("skel", cube), ("mask", cube), {"floors": floors}

    ev = types.ModuleType("scrollgt.fibers.eval_trace")
    ev.SCORING_VERSION = version
    ev.score_tracing = score_tracing
    ev.floor_connected_components = lambda mask: ("cc", mask)
    tg = types.ModuleType("scrollgt.fibers.target")
    tg.load_fiber_target = load_fiber_target
    for name, module in (("scrollgt", types.ModuleType("scrollgt")),
                         ("scrollgt.fibers", types.ModuleType("scrollgt.fibers")),
                         ("scrollgt.fibers.eval_trace", ev), ("scrollgt.fibers.target", tg)):  # fmt: skip
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", list(sys.path))  # main() prepends ScrollGT's src
    monkeypatch.setattr(t4.f91, "SG", tmp_path / "sg")
    monkeypatch.setattr(t4, "RESCORE", tmp_path / "rescore")
    monkeypatch.setattr(t4, "HELDOUT", tmp_path / "heldout")
    for c in ALL:
        path = tmp_path / ("rescore" if c in INS else "heldout") / f"{c}_instances.npy"
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, np.array([index[c]] * (2 if c in bad else 1)))
    neural = {c: {"tracer": {PEN: 20.0 if c in S3 else 5.0}} for c in ALL}
    entrant = {
        "descriptive_tolerance_4": neural,
        "neural_rows": {c: {PEN: 1.0} for c in ALL},
    }
    (tmp_path / "entrant.json").write_text(json.dumps(entrant))
    out = tmp_path / "out.json"
    argv = ["t4", "--entrant", str(tmp_path / "entrant.json"), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    rc = t4.main()
    return rc, json.loads(out.read_text()), seen


def test_main_scores_each_labelling_against_its_own_published_row(
    tmp_path, monkeypatch
):
    rc, out, seen = _run_main(tmp_path / "ok", monkeypatch)
    assert (rc, out["status"], out["identity_problems"]) == (0, "OK", {})
    assert seen["scored"] == [(c, 4.0) for c in ALL for _ in range(2)]
    assert out["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": True,
        "P2_in_sample_trails_tracer_on_9_of_11": True,
    }
    assert out["rows_tracer"][S3[0]] == {**TRACER_ROW, PEN: 10.0}
    assert out["rows_cc"][S3[0]] == {**CC_ROW, PEN: 3.0}
    assert (
        out["published_tracer"][S3[0]][PEN] == 2.0
        and out["published_cc"][S3[0]][PEN] == 1.0
    )
    assert out["rows_neural"][S3[0]] == {PEN: 20.0} and out["published_neural"][
        S3[0]
    ] == {PEN: 1.0}
    assert out["groups"] == {
        "in_sample": INS,
        "s3": S3,
        "s5_held_out": t4.f91.S5_HELDOUT,
    }

    one = INS[0]
    rc, out, _ = _run_main(tmp_path / "id", monkeypatch, bad=(one,))
    assert (rc, out["status"]) == (1, "IDENTITY_FAILED")
    assert out["identity_problems"] == {
        f"tracer {one}": ["n_pred_instances=8, published 7"]
    }
    assert "predictions" not in out

    with pytest.raises(SystemExit, match="version 3"):
        _run_main(tmp_path / "v4", monkeypatch, version=4)
