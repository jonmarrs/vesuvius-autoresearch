"""The registered continuity ceiling (docs/preregistration/2026-11-01_neural_tracer_continuity_ceiling.md): its
gaps, fills, joins, bounds, checks and verdict, on synthetic fibers scored by the vendored ScrollGT definition."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import afv_to_labels  # noqa: E402
import neural_tracer_confidence_stops as cs  # noqa: E402
import neural_tracer_continuity_ceiling as cc  # noqa: E402

from vesuvius_autoresearch.fibers.eval_trace import (  # noqa: E402
    _dilate_labels,
    _fiber_runs,
    score_tracing,
)
from vesuvius_autoresearch.fibers.skeleton_io import Fiber, Skeleton  # noqa: E402

SIZE = 48


def line_z(z0, z1, y=20.0, x=20.0, fid=1):
    p = np.array([(z, y, x) for z in np.arange(z0, z1 + 1e-9, 2.0)], float)
    edges = np.array([[i, i + 1] for i in range(len(p) - 1)], np.int64)
    return Fiber(
        id=fid, name=str(fid), node_ids=np.arange(len(p)), coords=p, edges=edges
    )


def skeleton(*fibers):
    return Skeleton(fibers=list(fibers), origin_zyx=(0, 0, 0))


def paint(labels, label, z0, z1, y=20, x=20):
    labels[z0 : z1 + 1, y, x] = label


def score(gt, vol):
    return score_tracing(gt, vol, tolerance=0.0)


def records(gt, grown, stops):
    """stops: (own label, point, outward direction); each walked along the reference as the script does."""
    ref = cs.Reference(gt.fibers, SIZE)
    out = []
    for own, point, direction in stops:
        _, i = ref.tree.query(point)
        k, j = (int(v) for v in ref.keys[i])
        walked, _ = ref.walk(
            k, j, cs.sign_along(ref, k, np.asarray(direction, float)), grown
        )
        out.append(cc.record(ref, walked, own))
    return out


def two_traces(tol=2.0):
    """One fiber z 4..44; trace 1 covers z 4..14, trace 2 z 26..44, so a gap z 17..23 lies between them."""
    gt = skeleton(line_z(4, 44))
    lab = np.zeros((SIZE,) * 3, np.int32)
    paint(lab, 1, 4, 14)
    paint(lab, 2, 26, 44)
    return gt, lab, _dilate_labels(lab, tol)


def test_the_continuation_skips_its_own_label_and_stops_at_another():
    walked = [
        ("a", 1, 0.5),
        ("b", 0, 0.5),
        ("c", 1, 0.5),
        ("d", 0, 0.5),
        ("e", 3, 0.5),
        ("f", 0, 0.5),
    ]
    keys, other, at = cc.continuation(walked, own=1)
    assert keys == {"b": (0.5, 1.0), "d": (0.5, 2.0)}
    assert (other, at) == (3, 2.5)
    keys, other, at = cc.continuation(walked[:4], own=1)
    assert (other, at) == (0, None) and list(keys) == ["b", "d"]


def test_filling_and_joining_one_split_recovers_the_whole_fiber():
    gt, lab, grown = two_traces()
    recs = records(gt, grown, [(1, (14, 20, 20), (1, 0, 0))])
    assert recs[0]["other"] == 2
    base = score(gt, grown)
    assert base.erl == pytest.approx(score_tracing(gt, lab, tolerance=2.0).erl)
    gap = sum(dl for dl, _, _ in recs[0]["keys"].values())
    assert gap == pytest.approx(7.0, abs=0.51)  # z 16.5 .. 23.5
    filled = score(gt, cc.edited(grown, recs, join=False))
    assert filled.coverage * filled.gt_length == pytest.approx(
        base.coverage * base.gt_length + gap
    )
    assert filled.splits == base.splits == 1
    joined = score(gt, cc.edited(grown, recs))
    assert joined.splits == 0 and joined.coverage == pytest.approx(1.0)
    assert joined.erl_merge_penalized == pytest.approx(
        joined.gt_length
    )  # one run over the whole fiber
    assert (
        joined.erl_merge_penalized
        > filled.erl_merge_penalized
        > base.erl_merge_penalized
    )


def test_the_ceiling_zeroes_merging_traces_and_refuses_their_joins():
    gt = skeleton(line_z(4, 44), line_z(4, 44, y=36.0, fid=2))
    lab = np.zeros((SIZE,) * 3, np.int32)
    paint(lab, 1, 4, 14)
    paint(lab, 2, 26, 44)
    paint(lab, 2, 4, 44, y=36)  # trace 2 also covers the second fiber: it merges
    grown = _dilate_labels(lab, 2.0)
    zero = cc.merging_labels(gt, grown, _fiber_runs)
    assert zero == {2} and score(gt, grown).merged_instances == 1
    recs = records(gt, grown, [(1, (14, 20, 20), (1, 0, 0))])
    none = score(gt, cc.edited(grown, [], zero=zero))
    assert (
        none.erl == score(gt, grown).erl_merge_penalized
    )  # U with no edits is the baseline ERLpen, exactly
    u = score(gt, cc.edited(grown, recs, zero=zero))
    first = score(gt, grown).run_lengths[
        0
    ]  # trace 1's run, where the walk of the first fiber starts
    run = first + sum(
        dl for dl, _, _ in recs[0]["keys"].values()
    )  # filled up to trace 2, which is zeroed
    assert u.erl == pytest.approx(run * run / u.gt_length, rel=1e-9)
    naive = score(gt, cc.edited(grown, recs))
    assert (
        naive.erl_merge_penalized == 0.0
    )  # joining a merging trace zeroes the stopping trace's runs too
    assert naive.erl_merge_penalized <= u.erl


def test_bounded_continuation_fills_k_voxels_and_joins_only_within_k():
    gt, lab, grown = two_traces()
    recs = records(gt, grown, [(1, (14, 20, 20), (1, 0, 0))])
    at = recs[0]["at"]
    short = cc.edited(grown, recs, k=4.0)
    filled = [v for _, s, v in recs[0]["keys"].values() if s <= 4.0]
    assert filled and all(short[v] == 1 for v in filled)
    beyond = {v for _, s, v in recs[0]["keys"].values() if s > 4.0} - set(
        filled
    )  # samples 0.5 apart share voxels
    assert beyond and all(short[v] == 0 for v in beyond)
    assert np.array_equal(
        np.unique(short), [0, 1, 2]
    )  # no join: the next trace starts beyond 4 voxels
    full = cc.edited(grown, recs, k=at)
    assert np.array_equal(np.unique(full), [0, 1]) and np.array_equal(
        full, cc.edited(grown, recs)
    )


def test_a_gap_two_stops_share_is_painted_by_the_first():
    gt, lab, grown = two_traces()
    recs = records(
        gt, grown, [(1, (14, 20, 20), (1, 0, 0)), (2, (26, 20, 20), (-1, 0, 0))]
    )
    assert set(recs[0]["keys"]) == set(recs[1]["keys"])
    vol = cc.edited(grown, recs, join=False)
    assert all(vol[v] == 1 for _, _, v in recs[0]["keys"].values())


def test_the_bounds_hold_on_a_cube_with_merges():
    gt = skeleton(
        line_z(4, 44), line_z(4, 44, y=36.0, fid=2), line_z(4, 44, y=8.0, fid=3)
    )
    lab = np.zeros((SIZE,) * 3, np.int32)
    paint(lab, 1, 4, 14)
    paint(lab, 2, 26, 44)
    paint(lab, 3, 4, 14, y=36)
    paint(lab, 4, 20, 44, y=36)
    paint(lab, 4, 30, 40, y=8)  # trace 4 merges fibers 2 and 3
    paint(lab, 5, 4, 20, y=8)
    grown = _dilate_labels(lab, 2.0)
    recs = records(gt, grown, [(1, (14, 20, 20), (1, 0, 0)), (3, (14, 36, 20), (1, 0, 0)),
                               (5, (20, 8, 20), (1, 0, 0))])  # fmt: skip
    out = cc.ceiling(gt, grown, recs, score, _fiber_runs)
    assert cc.bound_problems(out) == []
    assert out["U"]["value"] >= out["fill_join"]["value"]
    assert out["U"]["value"] >= out["fill"]["value"] >= out["base"]["value"] - 1e-12
    assert out["U_none"]["value"] == out["base"]["value"]
    assert out["counts"] == {
        "stops": 3,
        "splits": 3,
        "joins_unmerged": 1,
        "own_merging": 0,
        "other_merging": 2,
    }


def test_bound_problems_name_each_violation():
    rows = {"base": 1.0, "U_none": 1.0, "U_fill": 2.0, "U": 3.0, "fill": 2.5, "fill_join": 3.0,
            "U_10": 1.5, "U_20": 2.0, "U_50": 2.5}  # fmt: skip
    out = {k: {"value": v} for k, v in rows.items()}
    assert cc.bound_problems(out) == []
    out["U_20"]["value"] = 1.4
    assert cc.bound_problems(out) == ["U_10 <= U_20"]
    out["U_20"]["value"] = 2.0
    out["fill_join"]["value"] = 3.5
    assert cc.bound_problems(out) == ["fill_join <= U"]
    small = {k: out[k] for k in ("base", "U_none", "U", "fill_join")}
    small["fill_join"]["value"] = 2.0
    assert cc.bound_problems(small) == []


def _out(base=1.0, covered=100.0, d_covered=20.0, union=20.0, misaligned=0):
    return {"base": {"value": base, "covered": covered}, "U_none": {"value": base}, "U": {"value": base},
            "fill": {"value": base, "covered": covered + d_covered}, "union_length": union,
            "misaligned": misaligned, "counts": {}}  # fmt: skip


def test_the_checks_name_each_failure():
    row = {f: 1.0 for f in cc.ROW_FIELDS}
    recorded = dict(row, gap_length=20.0)
    assert (
        cc.check_problems(
            _out(), row, recorded, merging=int(row["merged_instances"]), filled="fill"
        )
        == []
    )
    assert cc.check_problems(_out(), dict(row, splits=2), recorded, 1, "fill") == [
        "row:splits"
    ]
    assert cc.check_problems(_out(), row, recorded, 2, "fill") == ["merging"]
    assert cc.check_problems(
        _out(union=19.0, d_covered=19.0), row, recorded, 1, "fill"
    ) == ["union_length"]
    assert cc.check_problems(_out(d_covered=31.0), row, recorded, 1, "fill") == [
        "covered"
    ]
    assert (
        cc.check_problems(_out(d_covered=29.0), row, recorded, 1, "fill") == []
    )  # within 10 voxels
    assert cc.check_problems(_out(misaligned=1), row, recorded, 1, "fill") == [
        "misaligned"
    ]
    bad = _out()
    bad["U_none"]["value"] = 1.0 + 1e-9
    assert cc.check_problems(bad, row, recorded, 1, "fill") == ["U_none"]


def test_a_failed_gate_gives_no_verdict():
    cubes = {c: {"U": 0.5, "U_20": 0.5, "fill_join": 0.5} for c in cc.HELD_OUT}
    gate = {c: [] for c in cc.ALL}
    gate[cc.IN_SAMPLE[0]] = ["covered"]
    assert cc.verdict(cubes, gate)["status"] == "GATE_FAILED"
    assert cc.verdict(cubes, {c: [] for c in cc.HELD_OUT})["status"] == "GATE_FAILED"


def test_a_missing_held_out_cube_is_partial():
    cubes = {c: {"U": 0.5, "U_20": 0.5, "fill_join": 0.5} for c in cc.HELD_OUT[1:]}
    assert cc.verdict(cubes, {c: [] for c in cc.ALL})["status"] == "PARTIAL"


@pytest.mark.parametrize(
    "u, u20, join, decision, p2, p3",
    [(0.09, 0.05, 0.08, "close", False, True), (0.10, 0.10, 0.04, "open", True, False),
     (0.30, 0.02, 0.15, "open", False, True)],
)  # fmt: skip
def test_the_decision_rule(u, u20, join, decision, p2, p3):
    cubes = {c: {"U": u, "U_20": u20, "fill_join": join} for c in cc.HELD_OUT}
    v = cc.verdict(cubes, {c: [] for c in cc.ALL})
    assert (v["status"], v["decision"], v["P1"], v["P2"], v["P3"]) == (
        "OK",
        decision,
        decision == "open",
        p2,
        p3,
    )
    assert v["reading"] == cc.READINGS[decision]


def test_the_constants_are_the_registrations():
    assert (cc.TOL, cc.L, cc.EDGE) == (cs.TOL, cs.L, cs.EDGE) == (2.0, 20.0, 6.0)
    assert cc.KS == (10.0, 20.0, 50.0)
    assert cc.TOLS == (2.0, 4.0)
    assert (cc.GAIN_BAR, cc.P3_FRACTION) == (0.10, 0.5)
    assert cc.COVERED_SLACK == (0.05, 10.0)
    assert cc.HELD_OUT == cs.HELD_OUT and len(cc.HELD_OUT) == 10 and len(cc.ALL) == 21
    assert set(cc.ROW_FIELDS) == {
        "erl",
        "erl_merge_penalized",
        "erl_covered",
        "erl_merge_penalized_covered",
        "coverage",
        "splits",
        "merges",
        "merged_instances",
        "gt_length",
        "n_gt_fibers",
    }


def test_a_refused_join_leaves_the_stopping_trace_its_own_label():
    gt = skeleton(line_z(4, 44), line_z(4, 44, y=36.0, fid=2))
    lab = np.zeros((SIZE,) * 3, np.int32)
    paint(lab, 2, 4, 14)
    paint(lab, 1, 26, 44)
    paint(lab, 1, 4, 44, y=36)  # the next trace, 1, merges
    grown = _dilate_labels(lab, 2.0)
    recs = records(gt, grown, [(2, (14, 20, 20), (1, 0, 0))])
    assert recs[0]["other"] == 1
    vol = cc.edited(grown, recs, zero=frozenset({1}))
    assert np.array_equal(np.unique(vol), [0, 2])
    assert all(vol[v] == 2 for _, _, v in recs[0]["keys"].values())


def test_only_finding_101s_stops_are_walked():
    gt = skeleton(line_z(4, 44))
    ref = cs.Reference(gt.fibers, SIZE)

    def poly(z0, z1, y=20.0):
        return np.array([(z, y, 20.0) for z in np.arange(z0, z1 + 1e-9, 1.0)])

    fibers = {
        10: poly(4, 14),
        11: poly(26, 40),
        12: poly(16, 22, y=24.0),
        13: poly(30, 34, y=20.0),
    }
    meta = {
        10: (
            ["confidence", "confidence"],
            [-1, -1],
        ),  # z 4 is 4 voxels from the face; z 14 is the one stop
        11: (
            ["owned_or_live", "confidence"],
            [-1, -1],
        ),  # z 40 goes on only 4 voxels: censored, not continuing
        12: (
            ["confidence", "confidence"],
            [-1, -1],
        ),  # 4 voxels off the reference: more than τ
        13: (["confidence", "confidence"], [7, 7]),  # linked
    }
    lab = afv_to_labels.rasterize(fibers, (SIZE,) * 3)
    grown = _dilate_labels(lab, 2.0)
    recs = cc.confidence_gaps(ref, grown, fibers, meta, SIZE, 2.0)
    assert [r["own"] for r in recs] == [1] and recs[0]["other"] == 2
