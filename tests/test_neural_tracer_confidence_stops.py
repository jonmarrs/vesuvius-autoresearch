"""The registered confidence-stop analysis (docs/preregistration/2026-11-01_neural_tracer_confidence_stops.md):
its walk along the reference, its classes, gaps and verdict, on synthetic fibers."""

import sys
from collections import namedtuple
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import neural_tracer_confidence_stops as cs  # noqa: E402

Fiber = namedtuple("Fiber", "coords edges")


def chain(points):
    """A ground-truth fiber through `points` (z, y, x), one edge between consecutive points."""
    p = np.asarray(points, float)
    return Fiber(p, np.array([[i, i + 1] for i in range(len(p) - 1)]))


def line_z(z0, z1, y=20.0, x=20.0, spacing=2.0):
    return chain([(z, y, x) for z in np.arange(z0, z1 + 1e-9, spacing)])


def start_at(ref, point, direction):
    d, i = ref.tree.query(point)
    k, j = ref.keys[i]
    return int(k), int(j), cs.sign_along(ref, int(k), np.asarray(direction, float))


def walk_length(walked):
    return sum(dl for _, _, dl in walked)


def test_the_walk_runs_to_the_fiber_end_both_ways():
    ref = cs.Reference([line_z(10, 50)], 64)
    labels = np.zeros((64,) * 3, np.int32)
    for direction, expect in (((1, 0, 0), 20.0), ((-1, 0, 0), 20.0)):
        k, j, s = start_at(ref, (30, 20, 20), direction)
        walked, why = ref.walk(k, j, s, labels)
        assert why == "fiber_end"
        assert walk_length(walked) == pytest.approx(expect, abs=0.51)


def test_the_walk_stops_where_the_fiber_leaves_the_cube():
    ref = cs.Reference([line_z(10, 90)], 64)
    labels = np.zeros((64,) * 3, np.int32)
    k, j, s = start_at(ref, (30, 20, 20), (1, 0, 0))
    walked, why = ref.walk(k, j, s, labels)
    assert why == "left_cube"
    assert (
        33.0 <= walk_length(walked) <= 34.0
    )  # z 30 -> 63.5, where rounding leaves the cube
    assert not (
        ref.pts >= 63.5
    ).any()  # the reference keeps only samples inside the cube


def test_the_walk_takes_the_aligned_branch():
    stem = [(z, 20.0, 20.0) for z in np.arange(10, 31, 2.0)]
    on = [(z, 20.0, 20.0) for z in np.arange(32, 41, 2.0)]
    side = [
        (30.0, y, 20.0) for y in np.arange(22, 25, 2.0)
    ]  # 4 voxels: shorter than the aligned branch
    coords = np.array(stem + on + side)
    n_stem, n_on = len(stem), len(on)
    node = n_stem - 1  # z = 30
    edges = [[i, i + 1] for i in range(n_stem - 1)]
    edges += [[node, n_stem]] + [[n_stem + i, n_stem + i + 1] for i in range(n_on - 1)]
    edges += [[node, n_stem + n_on]] + [
        [n_stem + n_on + i, n_stem + n_on + i + 1] for i in range(len(side) - 1)
    ]
    ref = cs.Reference([Fiber(coords, np.array(edges))], 64)
    labels = np.zeros((64,) * 3, np.int32)
    k, j, s = start_at(ref, (20, 20, 20), (1, 0, 0))
    walked, why = ref.walk(k, j, s, labels)
    assert why == "fiber_end"
    assert walk_length(walked) == pytest.approx(
        20.0, abs=0.51
    )  # 20 -> 30 -> 40 along z, not out along y


def test_the_walk_stops_at_the_cap():
    ref = cs.Reference([line_z(2, 62)], 64)
    labels = np.zeros((64,) * 3, np.int32)
    k, j, s = start_at(ref, (10, 20, 20), (1, 0, 0))
    walked, why = ref.walk(k, j, s, labels, cap=15.0)
    assert why == "cap" and walk_length(walked) == pytest.approx(15.0, abs=0.51)


def test_the_walk_counts_each_node_once():
    ref = cs.Reference([line_z(10, 50)], 64)
    labels = np.zeros((64,) * 3, np.int32)
    k, j, s = start_at(ref, (30, 20, 20), (1, 0, 0))
    walked, _ = ref.walk(k, j, s, labels)
    keys = [key for key, _, _ in walked]
    assert len(keys) == len(set(keys))
    assert len(walked) == pytest.approx(40, abs=1)  # 20 voxels at 0.5


@pytest.mark.parametrize(
    "length, why, expect",
    [
        (25.0, "fiber_end", "continues"),
        (20.0, "left_cube", "continues"),
        (400.0, "cap", "continues"),
        (12.0, "fiber_end", "fiber_ends"),
        (12.0, "left_cube", "censored"),
    ],
)
def test_classes(length, why, expect):
    assert cs.classify(length, why, 20.0) == expect


def test_the_gap_runs_to_another_trace_and_skips_its_own():
    walked = [(("e", 0, i), lab, 0.5) for i, lab in enumerate([3, 3, 0, 0, 0, 7, 0])]
    keys, split = cs.gap(walked, own=3)
    assert set(keys) == {("e", 0, 2), ("e", 0, 3), ("e", 0, 4)} and split is True
    keys, split = cs.gap(walked[:4], own=3)
    assert len(keys) == 2 and split is False


def test_stops_take_each_ends_reason_and_outward_direction():
    poly = np.array([(z, 20.0, 20.0) for z in np.arange(10, 41, 2.0)])
    ends = cs.stops(poly, ["confidence", "owned_or_live"], [-1, 5], 64)
    assert [e["reason"] for e in ends] == ["confidence", "owned_or_live"]
    assert [e["link"] for e in ends] == [-1, 5]
    assert np.allclose(ends[0]["point"], (10, 20, 20)) and np.allclose(
        ends[1]["point"], (40, 20, 20)
    )
    assert np.allclose(ends[0]["direction"], (-1, 0, 0)) and np.allclose(
        ends[1]["direction"], (1, 0, 0)
    )
    assert np.allclose(ends[0]["back"], (30, 20, 20))  # 20 voxels back along the trace
    assert ends[0]["face_distance"] == pytest.approx(10.0)


def _labels_for(spans, size=64, half=2):
    """Label `lab` on z in [z0, z1] within `half` voxels of the line (y, x) = (20, 20): a grown centreline."""
    lab = np.zeros((size,) * 3, np.int32)
    for z0, z1, v in spans:
        lab[z0 : z1 + 1, 20 - half : 21 + half, 20 - half : 21 + half] = v
    return lab


def test_a_gap_between_two_stops_counts_once():
    ref = cs.Reference([line_z(4, 60)], 64)
    labels = _labels_for([(8, 27, 1), (38, 57, 2)])
    fibers = {
        10: np.array([(z, 20.0, 20.0) for z in np.arange(10, 25.1, 1.0)]),
        11: np.array([(z, 20.0, 20.0) for z in np.arange(40, 55.1, 1.0)]),
    }
    meta = {
        10: (["owned_or_live", "confidence"], [-1, -1]),
        11: (["confidence", "owned_or_live"], [-1, -1]),
    }
    out = cs.measure_cube(ref, labels, fibers, meta, 64, tol=2.0, covered=100.0, rng=np.random.default_rng(0),
                          base_n=50)  # fmt: skip
    r = out["settings"]["L20_edge6"]
    conf = r["confidence"]
    assert conf["stops"] == 2 and conf["on_fiber"] == 2 and conf["continues"] == 2
    assert conf["splits"] == 2
    # z 27.5 .. 37.5 uncovered: 21 samples of 0.5, once, not twice
    assert r["gap_length"] == pytest.approx(10.5, abs=0.6)
    assert r["G"] == pytest.approx(r["gap_length"] / 100.0)


def test_a_stop_that_left_the_fiber_first():
    ref = cs.Reference([line_z(4, 30)], 64)
    labels = _labels_for([(8, 30, 1)])
    # on the fiber for z 10..30, then off it towards +y; the stop is 10 voxels off the reference
    pts = [(z, 20.0, 20.0) for z in np.arange(10, 30.1, 1.0)] + [
        (30.0, 20.0 + y, 20.0) for y in range(1, 11)
    ]
    fibers = {0: np.array(pts)[::-1]}
    meta = {0: (["confidence", "bounds"], [-1, -1])}
    out = cs.measure_cube(ref, labels, fibers, meta, 64, tol=2.0, covered=10.0, rng=np.random.default_rng(0),
                          base_n=10)  # fmt: skip
    conf = out["settings"]["L20_edge6"]["confidence"]
    assert conf["stops"] == 1 and conf["on_fiber"] == 0 and conf["left_fiber"] == 1


def test_linked_and_face_ends_are_not_stops():
    ref = cs.Reference([line_z(4, 60)], 64)
    labels = _labels_for([(8, 27, 1)])
    fibers = {
        0: np.array([(z, 20.0, 20.0) for z in np.arange(3, 25.1, 1.0)])
    }  # first end 3 voxels from a face
    meta = {0: (["confidence", "confidence"], [-1, 4])}  # last end linked
    out = cs.measure_cube(ref, labels, fibers, meta, 64, tol=2.0, covered=10.0, rng=np.random.default_rng(0),
                          base_n=10)  # fmt: skip
    assert out["settings"]["L20_edge6"]["confidence"]["stops"] == 0
    assert out["ends"] == {"linked": 1, "face": 1, "interior": 0}


def _cube(G, premature, base=0.9):
    return {"G": G, "premature_share": premature, "base_rate": base}


def _all(G, premature, base=0.9):
    return {c: _cube(G, premature, base) for c in cs.HELD_OUT + cs.IN_SAMPLE}


def test_a_failed_gate_gives_no_verdict():
    gate = {c: [] for c in cs.ALL}
    gate[cs.HELD_OUT[0]] = ["coverage"]
    v = cs.verdict(_all(0.5, 0.9), gate)
    assert v["status"] == "GATE_FAILED" and "decision" not in v and "P3" not in v


def test_an_incomplete_gate_gives_no_verdict():
    gate = {c: [] for c in cs.ALL[:-1]}
    v = cs.verdict(_all(0.5, 0.9), gate)
    assert v["status"] == "GATE_FAILED" and "decision" not in v


def test_partial_samples_are_refused():
    gate = {c: [] for c in cs.ALL}
    cubes = _all(0.5, 0.9)
    del cubes[cs.HELD_OUT[3]]
    assert cs.verdict(cubes, gate)["status"] == "PARTIAL"
    cubes = _all(0.5, 0.9)
    cubes[cs.HELD_OUT[2]]["premature_share"] = None
    assert cs.verdict(cubes, gate)["status"] == "PARTIAL"


@pytest.mark.parametrize(
    "G, premature, decision",
    [
        (0.05, 0.9, "close"),
        (0.20, 0.7, "open"),
        (0.20, 0.3, "mechanism_wrong"),
        (0.10, 0.5, "open"),
    ],
)
def test_the_decision_rule(G, premature, decision):
    gate = {c: [] for c in cs.ALL}
    v = cs.verdict(_all(G, premature), gate)
    assert v["status"] == "OK" and v["decision"] == decision
    assert v["P3"] is (G >= 0.10) and v["P1"] is (premature >= 0.5)


def test_p2_counts_cubes_against_their_base_rate():
    gate = {c: [] for c in cs.ALL}
    cubes = _all(0.2, 0.75, base=0.9)  # 0.75 >= 0.8 * 0.9 = 0.72 on all ten
    assert cs.verdict(cubes, gate)["P2"] is True
    for c in cs.HELD_OUT[:3]:
        cubes[c]["premature_share"] = 0.5
    assert cs.verdict(cubes, gate)["P2"] is False  # 7 of 10


def test_the_constants_are_the_registrations():
    assert (cs.TOL, cs.L, cs.EDGE, cs.CAP, cs.G_BAR, cs.BASE_N, cs.RNG_SEED) == (
        2.0,
        20.0,
        6.0,
        400.0,
        0.10,
        2000,
        0,
    )
    assert (cs.BACK_DIRECTION, cs.BACK_LATE, cs.MARGIN, cs.STEP) == (
        8.0,
        20.0,
        128,
        0.5,
    )
    assert len(cs.HELD_OUT) == 10 and len(cs.IN_SAMPLE) == 11
    assert all(c.startswith("s3_") for c in cs.HELD_OUT[:8])
    assert cs.HELD_OUT[8:] == ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]


def test_gate_problems_name_every_field_that_differs():
    rec = {"coverage": 0.4016, "precision": 0.3259, "splits": 641, "merges": 0, "gt_length": 15639.6,
           "pred_length": 23137.0, "erl": 12.5}  # fmt: skip
    assert cs.gate_problems(dict(rec), rec) == []
    now = dict(rec, splits=640, coverage=0.4017)
    assert cs.gate_problems(now, rec) == ["coverage", "splits"]
