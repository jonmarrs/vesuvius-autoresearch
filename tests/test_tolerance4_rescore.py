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
    # The registration's four: instance count, predicted length, ground-truth length and ground-truth fibers.
    assert t4.SAME == ("n_pred_instances", "pred_length", "gt_length", "n_gt_fibers")
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


def test_6_and_9_cubes_scored_are_enough():
    """The registration leaves a prediction unevaluated with fewer than 6 Scroll-3 or 9 in-sample cubes scored."""
    tracer = (
        {c: 2.0 for c in ALL} | {c: None for c in S3[:2]} | {c: None for c in INS[:2]}
    )
    neural = {c: 5.0 for c in S3} | {c: 1.0 for c in INS + t4.f91.S5_HELDOUT}
    v = _verdict(neural, tracer)
    assert v["s3_leading_tracer"] == [6, 6] and v["in_sample_trailing_tracer"] == [9, 9]
    assert all(v["predictions"].values())


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


INDEX = {c: i for i, c in enumerate(ALL)}


def _fixed(cube, name):
    """A cube's tolerance-independent fields for one labelling: its own ground truth, and our tracer's instances and
    length unlike connected components'."""
    gt = {"gt_length": 50.5 + INDEX[cube], "n_gt_fibers": 3 + INDEX[cube]}
    if name == "tracer":
        return {"n_pred_instances": 7, "pred_length": 100.0, **gt}
    return {"n_pred_instances": 4, "pred_length": 80.0, **gt}


def _run_main(tmp_path, monkeypatch, bad=(), bad_cc=(), version=3):
    """main() end to end, with ScrollGT's scorer and target stubbed. Each cube's labellings reproduce their own
    published rows, except our tracer's on `bad` and connected components' on `bad_cc`, which have one instance more.
    Our tracer scores 10.0 at tolerance 4, the neural tracer 20.0 on Scroll 3 and 5.0 elsewhere."""
    seen: dict = {"scored": []}

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
            row = _fixed(cube, "cc")
            row["n_pred_instances"] += cube in bad_cc
            return Score({**row, PEN: 3.0})
        assert labels[0] == INDEX[cube]  # the cube's own saved labelling
        row = _fixed(cube, "tracer")
        row["n_pred_instances"] += labels.size - 1
        return Score({**row, PEN: 10.0})

    def load_fiber_target(target):
        cube = target.name.removeprefix("fibers_")
        assert target == t4.f91.SG / "data" / f"fibers_{cube}"
        floors = {
            t4.f91.TRACER: {**_fixed(cube, "tracer"), PEN: 2.0},
            t4.f91.CC: {**_fixed(cube, "cc"), PEN: 1.0},
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
        np.save(path, np.array([INDEX[c]] * (2 if c in bad else 1)))
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
    assert (out["tolerance"], out["scoring_version"]) == (4.0, 3)
    assert seen["scored"] == [(c, 4.0) for c in ALL for _ in range(2)]
    assert out["predictions"] == {
        "P1_s3_leads_tracer_on_6_of_8": True,
        "P2_in_sample_trails_tracer_on_9_of_11": True,
    }
    assert out["readings"] == [
        "the Scroll-3 lead holds at tolerance 4",
        "the in-sample deficit holds at tolerance 4",
    ]
    for c in ALL:
        assert out["rows_tracer"][c] == {**_fixed(c, "tracer"), PEN: 10.0}
        assert out["rows_cc"][c] == {**_fixed(c, "cc"), PEN: 3.0}
        assert out["published_tracer"][c] == {**_fixed(c, "tracer"), PEN: 2.0}
        assert out["published_cc"][c] == {**_fixed(c, "cc"), PEN: 1.0}
        assert out["rows_neural"][c] == {PEN: 20.0 if c in S3 else 5.0}
        assert out["published_neural"][c] == {PEN: 1.0}
    assert out["groups"] == {
        "in_sample": INS,
        "s3": S3,
        "s5_held_out": t4.f91.S5_HELDOUT,
    }

    for kind, one in (("tracer", INS[0]), ("cc", S3[0])):
        bad = {"bad": (one,)} if kind == "tracer" else {"bad_cc": (one,)}
        rc, out, _ = _run_main(tmp_path / f"id_{kind}", monkeypatch, **bad)
        assert (rc, out["status"]) == (1, "IDENTITY_FAILED")
        published = _fixed(one, kind)["n_pred_instances"]
        assert out["identity_problems"] == {
            f"{kind} {one}": [
                f"n_pred_instances={published + 1}, published {published}"
            ]
        }
        assert "predictions" not in out

    with pytest.raises(SystemExit, match="version 3"):
        _run_main(tmp_path / "v4", monkeypatch, version=4)
