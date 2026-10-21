"""scripts/octant_crop_rescore.py: the three in-sample 512³ cubes scored in their eight 256³ octants."""

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import octant_crop_rescore as oc  # noqa: E402

PEN = "erl_merge_penalized"


def _fiber(fid, *nodes):
    c = np.asarray(nodes, float)
    return types.SimpleNamespace(
        id=fid,
        name=f"f{fid}",
        node_ids=np.arange(len(c)),
        coords=c,
        edges=np.array([[i, i + 1] for i in range(len(c) - 1)]),
        in_bounds_mask=lambda shape, c=c: np.all(
            (c >= 0) & (c <= np.asarray(shape) - 1), axis=1
        ),
    )


def test_the_octants_tile_the_cube():
    assert len(oc.OCTANTS) == 8 and len(set(oc.OCTANTS)) == 8
    assert all(all(v in (0, 256) for v in o) for o in oc.OCTANTS)


def test_a_cropped_skeleton_is_shifted_and_keeps_fibers_with_two_nodes_inside():
    skel = types.SimpleNamespace(
        fibers=[
            _fiber(
                1, (300, 10, 10), (310, 10, 10), (320, 10, 10)
            ),  # inside the octant at z 256
            _fiber(2, (250, 10, 10), (260, 10, 10)),  # one node inside: dropped
            _fiber(3, (10, 10, 10), (20, 10, 10)),  # in another octant: dropped
            _fiber(
                4, (250, 20, 20), (257, 20, 20), (265, 20, 20)
            ),  # two inside: kept, its outside node kept too
        ],
        scale_um=(7.91,) * 3,
        origin_zyx=(0, 0, 0),
    )
    out = oc.crop_skeleton(skel, (256, 0, 0), 256)
    assert [f.id for f in out.fibers] == [1, 4]
    assert np.allclose(out.fibers[0].coords[:, 0], [44, 54, 64])
    assert np.allclose(out.fibers[1].coords[:, 0], [-6, 1, 9])
    assert out.scale_um == skel.scale_um


def test_a_cropped_labelling_is_the_octants_voxels():
    lab = np.zeros((512, 512, 512), np.int32)
    lab[300, 5, 400] = 7
    c = oc.crop_labels(lab, (256, 0, 256), 256)
    assert c.shape == (256, 256, 256) and c[44, 5, 144] == 7 and c.sum() == 7


def _rows(neural, tracer):
    return {
        f"{c}@{o}": {"neural": {4.0: {PEN: neural}}, "tracer": {4.0: {PEN: tracer}}}
        for c in oc.CUBES
        for o in oc.OCTANTS
    }


def test_the_verdict_thresholds():
    assert oc.verdict(_rows(5.0, 4.0))["reading"].startswith(
        "cropping does not reverse it"
    )
    assert oc.verdict(_rows(3.0, 4.0))["reading"].startswith("cropping reverses it")
    rows = _rows(5.0, 4.0)
    for k in list(rows)[:9]:
        rows[k]["neural"][4.0][PEN] = 3.0  # 15 of 24 lead: neither threshold
    v = oc.verdict(rows)
    assert v["neural_leads_at_4"] == [15, 24] and v["reading"].startswith(
        "inconclusive"
    )
    rows = _rows(5.0, 4.0)
    for k in list(rows)[:8]:
        rows[k]["neural"][4.0][PEN] = 3.0  # 16 of 24: holds, inclusive
    assert oc.verdict(rows)["prediction_P1_leads_on_16_of_24"] is True


def test_ties_do_not_lead():
    assert oc.verdict(_rows(4.0, 4.0))["neural_leads_at_4"] == [0, 24]


@pytest.mark.parametrize(
    "identity, status", [({"x": ["erl"]}, "IDENTITY_FAILED"), ({}, "OK")]
)
def test_the_status(identity, status):
    got, reading = oc.outcome(identity, _rows(5.0, 4.0))
    assert got == status and (reading is None) == (status == "IDENTITY_FAILED")


def test_the_cubes_are_the_in_sample_512_ones():
    assert [c for c in oc.f91.IN_SAMPLE if c.endswith("_512")] == oc.CUBES and len(
        oc.CUBES
    ) == 3


KEEP = ("erl", "coverage", "precision", "merges", "splits", "n_gt_fibers", "gt_length", "n_pred_instances",
        "pred_length")  # fmt: skip


def _row(pen, **fields):
    return {PEN: pen, **{k: 1.0 for k in KEEP}, **fields}


def _run_main(tmp_path, monkeypatch, off=None, version=3):
    """main() end to end, with ScrollGT's scorer and target, the .afv reader and the saved instances stubbed.

    Each labelling marks every octant's first voxel with the octant's index (the neural tracer's from 10, ours from
    50), and each cube's ground truth has one fiber per octant, two nodes from the octant's corner. The whole cubes
    reproduce finding 94's rows, except the entrant and field in `off`. The neural tracer scores 5.0 on an octant and
    our tracer 4.0."""
    seen: dict = {"whole": [], "octants": []}
    marked = {}
    for e, base in (("neural", 10), ("tracer", 50)):
        lab = np.zeros((512, 512, 512), np.uint8)
        for i, (z, y, x) in enumerate(oc.OCTANTS):
            lab[z, y, x] = base + i
        marked[e] = lab

    class Score:
        def __init__(self, row):
            self.row = row

        def as_row(self):
            return self.row

    def score_tracing(skel, labels, tolerance):
        e = "neural" if labels[0, 0, 0] < 50 else "tracer"
        if labels.shape == (512,) * 3:
            seen["whole"].append((skel.cube, e, tolerance))
            row = _row(0.0, pred_length=float(len(skel.cube)))
            if off and off[0] == e:
                row[off[1]] += 1
            return Score(row)
        assert (
            labels.shape == (256,) * 3 and labels.sum() == labels[0, 0, 0]
        )  # one octant's voxels, uncopied marks
        i = int(labels[0, 0, 0]) - (10 if e == "neural" else 50)
        assert [f.id for f in skel.fibers] == [i] and np.allclose(
            skel.fibers[0].coords, [[1] * 3, [2] * 3]
        )
        seen["octants"].append((skel.cube, oc.OCTANTS[i], e, tolerance))
        return Score(_row(5.0 if e == "neural" else 4.0))

    def load_fiber_target(target):
        cube = target.name.removeprefix("fibers_")
        assert target == oc.f91.SG / "data" / f"fibers_{cube}"
        fibers = [
            _fiber(i, np.add(o, 1), np.add(o, 2)) for i, o in enumerate(oc.OCTANTS)
        ]
        return types.SimpleNamespace(cube=cube, fibers=fibers), None, None

    ev = types.ModuleType("scrollgt.fibers.eval_trace")
    ev.SCORING_VERSION = version
    ev.score_tracing = score_tracing
    tg = types.ModuleType("scrollgt.fibers.target")
    tg.load_fiber_target = load_fiber_target
    for name, module in (("scrollgt", types.ModuleType("scrollgt")),
                         ("scrollgt.fibers", types.ModuleType("scrollgt.fibers")),
                         ("scrollgt.fibers.eval_trace", ev), ("scrollgt.fibers.target", tg)):  # fmt: skip
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(sys, "path", list(sys.path))  # main() prepends ScrollGT's src
    monkeypatch.setattr(oc.f91, "SG", tmp_path / "sg")
    monkeypatch.setattr(oc, "NEURAL", tmp_path / "neural")

    def read_afv(path):
        assert path.parent.parent == tmp_path / "neural" and path.name == "fibers.afv"
        return {1: "nodes"}

    def rasterize(fibers, shape):
        assert fibers == {1: ("nodes", (0, 0, 0))} and shape == (512,) * 3
        return marked["neural"]

    monkeypatch.setattr(oc.afv_to_labels, "read_afv", read_afv)
    monkeypatch.setattr(oc.afv_to_labels, "to_cube_zyx", lambda v, origin: (v, origin))
    monkeypatch.setattr(oc.afv_to_labels, "rasterize", rasterize)
    monkeypatch.setattr(oc.t4, "tracer_labelling", lambda c: f"instances of {c}")
    monkeypatch.setattr(oc.np, "load", lambda path: marked["tracer"])
    t94 = {
        f"rows_{e}": {c: _row(0.0, pred_length=float(len(c))) for c in oc.CUBES}
        for e in ("neural", "tracer")
    }
    (tmp_path / "t94.json").write_text(json.dumps(t94))
    out = tmp_path / "out.json"
    monkeypatch.setattr(
        sys, "argv", ["oc", "--t94", str(tmp_path / "t94.json"), "--out", str(out)]
    )
    rc = oc.main()
    return rc, json.loads(out.read_text()), seen


def test_main_scores_each_octant_of_each_cube_on_its_own_crop(tmp_path, monkeypatch):
    rc, out, seen = _run_main(tmp_path, monkeypatch)
    assert (rc, out["status"], out["identity_problems"]) == (0, "OK", {})
    assert seen["whole"] == [
        (c, e, 4.0) for c in oc.CUBES for e in ("neural", "tracer")
    ]
    assert seen["octants"] == [
        (c, o, e, t)
        for c in oc.CUBES
        for o in oc.OCTANTS
        for e in ("neural", "tracer")
        for t in oc.TOLS
    ]
    assert (
        out["neural_leads_at_4"] == [24, 24]
        and out["prediction_P1_leads_on_16_of_24"] is True
    )
    assert out["reading"].startswith("cropping does not reverse it")
    key = f"{oc.CUBES[0]}@256_0_256"
    assert out["octants"][key]["neural"]["2.0"] == _row(5.0)
    assert out["octants"][key]["tracer"]["4.0"] == _row(4.0)
    assert out["whole_cube_tol4"][oc.CUBES[0]]["tracer"] == _row(
        0.0, pred_length=float(len(oc.CUBES[0]))
    )


@pytest.mark.parametrize("entrant, field", [("neural", PEN), ("tracer", "coverage"),
                                            ("neural", "n_pred_instances"), ("tracer", "pred_length")])  # fmt: skip
def test_main_fails_identity_when_a_whole_cube_misses_finding_94(
    tmp_path, monkeypatch, entrant, field
):
    rc, out, _ = _run_main(tmp_path, monkeypatch, off=(entrant, field))
    assert (rc, out["status"]) == (1, "IDENTITY_FAILED")
    assert out["identity_problems"] == {f"{entrant} {c}": [field] for c in oc.CUBES}
    assert "reading" not in out and "neural_leads_at_4" not in out


def test_main_refuses_another_scoring_version(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="version 3"):
        _run_main(tmp_path, monkeypatch, version=4)
