"""The off-reference location analysis places every off-reference voxel of length exactly once, and its report states
the analysis's record."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "neural_tracer_offref_location", ROOT / "scripts/neural_tracer_offref_location.py"
)
ol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ol)

ENDS = ("confidence|unlinked|interior", "bounds|unlinked|edge")


def line(n: int, step: float = 1.0) -> np.ndarray:
    z = np.arange(n, dtype=float) * step
    return np.stack([z, np.zeros(n), np.zeros(n)], axis=1)


def mask(n: int, on_at) -> np.ndarray:
    m = np.zeros(n, bool)
    m[list(on_at)] = True
    return m


def test_point_weights_share_each_segment_between_its_two_points():
    q = line(5, 2.0)
    assert ol.point_weights(q).tolist() == [1.0, 2.0, 2.0, 2.0, 1.0]
    assert ol.point_weights(q).sum() == pytest.approx(8.0)


def test_a_fiber_with_no_on_reference_point_is_whole_off():
    w = ol.point_weights(line(6))
    assert ol.locate(w, np.zeros(6, bool), np.zeros(6, int), ENDS) == {
        "whole_off": 5.0,
        "whole_off_n": 1,
    }


def test_tails_go_to_their_own_end_and_interior_runs_split_by_reference_fiber():
    n = 12
    w = ol.point_weights(line(n))
    on = mask(n, [2, 3, 5, 6, 9])
    nearest = np.array([0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    out = ol.locate(w, on, nearest, ENDS)
    assert out["tail:" + ENDS[0]] == pytest.approx(0.5 + 1.0)  # points 0, 1
    assert out["tail:" + ENDS[1]] == pytest.approx(1.0 + 0.5)  # points 10, 11
    assert (out["gap_same"], out["gap_same_n"]) == (
        pytest.approx(1.0),
        1,
    )  # point 4, fiber 0 both sides
    assert (out["gap_switch"], out["gap_switch_n"]) == (
        pytest.approx(2.0),
        1,
    )  # points 7, 8: fiber 0 to 1
    places = sum(v for k, v in out.items() if not k.endswith("_n"))
    assert places == pytest.approx(w[~on].sum())


def test_length_outside_the_cube_is_not_placed():
    n = 8
    w = ol.point_weights(line(n))
    w[:2] = 0.0  # the first two points lie outside the cube
    out = ol.locate(w, mask(n, [4, 5]), np.zeros(n, int), ENDS)
    assert out["tail:" + ENDS[0]] == pytest.approx(w[2:4].sum())


@pytest.mark.parametrize(
    "face, link, want",
    [
        (-0.5, -1, "outside_cube"),
        (0.0, -1, "confidence|unlinked|edge"),  # on the face: inside the cube
        (3.0, -1, "confidence|unlinked|edge"),
        (40.0, 7, "confidence|linked|interior"),
    ],
)
def test_end_class(face, link, want):
    assert (
        ol.end_class({"face_distance": face, "link": link, "reason": "confidence"})
        == want
    )


@pytest.mark.parametrize("face", [ol.cs.EDGE - 0.5, ol.cs.EDGE, 40.0])
@pytest.mark.parametrize("link", [-1, 0, 7])
@pytest.mark.parametrize("reason", ["confidence", "owned_or_live"])
def test_the_interior_unlinked_confidence_class_is_exactly_the_screen_s_ends(
    face, link, reason
):
    """The report's "tails behind the screen's ends" must be the ends the stop-trim screen trims."""
    z = np.arange(face, face + 100.0)
    q = np.stack([z, np.full_like(z, 128.0), np.full_like(z, 128.0)], axis=1)
    meta = ((reason, "bounds"), (link, -1))
    first = ol.cs.stops(q, *meta, 256)[0]
    trimmed = ol.ts.trimmed({1: q}, {1: meta}, 256, 20.0)[1] == 1
    assert (ol.end_class(first) == "confidence|unlinked|interior") == trimmed


def fake_scrollgt(monkeypatch, fibers: list) -> None:
    """ScrollGT's fiber target and resampling, stood in: each reference fiber is resampled to its own points."""
    skel = types.SimpleNamespace(
        fibers=[
            types.SimpleNamespace(coords=np.asarray(f, float), edges=None)
            for f in fibers
        ]
    )
    et = types.ModuleType("scrollgt.fibers.eval_trace")
    et._resample_fiber = lambda coords, edges, step: [(p, None) for p in coords]
    tg = types.ModuleType("scrollgt.fibers.target")
    tg.load_fiber_target = lambda path: (skel, None, None)
    for m in (
        types.ModuleType("scrollgt"),
        types.ModuleType("scrollgt.fibers"),
        et,
        tg,
    ):
        monkeypatch.setitem(sys.modules, m.__name__, m)


def test_a_point_exactly_the_tolerance_away_is_on_and_outside_the_cube_nothing_is(
    monkeypatch, tmp_path
):
    size = 16
    fake_scrollgt(monkeypatch, [[(z, 8.0, 8.0) for z in range(size)]])
    fibers = {
        # 2 voxels beside the reference all along: on it at tolerance 2
        1: np.array([(z, 8.0, 10.0) for z in range(2, 13)]),
        # within 2 voxels of the reference only outside the cube, 5 voxels off inside
        2: np.array(
            [(-2, 8, 8), (-1, 8, 8), (0, 8, 13), (1, 8, 13), (2, 8, 13)], float
        ),
    }
    zarr = types.ModuleType("zarr")
    zarr.open = lambda path, mode: np.zeros((4, 4, 4))
    monkeypatch.setitem(sys.modules, "zarr", zarr)
    monkeypatch.setattr(ol.cs, "RUNS", {size: tmp_path})
    monkeypatch.setattr(ol, "CT", {size: tmp_path})
    monkeypatch.setattr(ol.al, "read_afv", lambda path: {k: (v + ol.cs.MARGIN)[:, ::-1] for k, v in fibers.items()})  # fmt: skip
    monkeypatch.setattr(ol.cs, "read_meta", lambda run, afv: ({k: (("confidence",) * 2, (-1, -1)) for k in afv}, []))  # fmt: skip
    out = ol.measure_cube(f"t_{size}")["2"]
    inside = ol.point_weights(fibers[2])[2:].sum()
    assert out["on_reference"] == pytest.approx(10.0)
    assert out["length"] == pytest.approx(10.0 + inside)
    assert (out["place"]["whole_off"], out["place"]["whole_off_n"]) == (
        pytest.approx(inside),
        1,
    )


def test_trilinear_is_exact_on_a_linear_volume_and_peak_on_a_parabola():
    zz, yy, xx = np.meshgrid(*(np.arange(8.0),) * 3, indexing="ij")
    v = 2 * zz + 3 * yy - xx
    p = np.array([[1.25, 2.5, 3.75], [4.0, 0.5, 6.1]])
    assert np.allclose(ol.trilinear(v, p), 2 * p[:, 0] + 3 * p[:, 1] - p[:, 2])
    prof = np.stack([-((ol.SHIFTS - c) ** 2) for c in (0.3, -0.6, 0.0)])
    assert np.allclose(ol.peak(prof), [0.3, -0.6, 0.0])
    assert ol.peak(np.stack([ol.SHIFTS, -ol.SHIFTS, -((ol.SHIFTS - 1.1) ** 2)]))[
        :2
    ] == [None, None]


def test_trilinear_reads_the_boundary_voxel_as_itself():
    """An integer coordinate is that voxel, including the far face and a 1-voxel cube.

    Clipping to shape - 1.001 mixed the last voxel with its neighbour (9 became
    8.973 on a 2-voxel axis). A point past the end stays on the boundary voxel.
    """
    cube = np.zeros((2, 2, 2))
    cube[1, 1, 1] = 9
    assert ol.trilinear(cube, np.array([[1.0, 1.0, 1.0]]))[0] == pytest.approx(9)
    one = np.array([[[4.0]]])
    assert ol.trilinear(
        one, np.array([[0.0, 0.0, 0.0], [3.0, -2.0, 0.5]])
    ) == pytest.approx([4, 4])
    zz, yy, xx = np.meshgrid(*(np.arange(8.0),) * 3, indexing="ij")
    linear = 2 * zz + 3 * yy - xx
    face = np.array([[7.0, 1.25, 2.5]])
    assert ol.trilinear(linear, face)[0] == pytest.approx(2 * 7 + 3 * 1.25 - 2.5)
    past = np.array([[8.4, -1.0, 3.2]])
    assert ol.trilinear(linear, past)[0] == pytest.approx(2 * 7 + 3 * 0 - 3.2)


RECORD = json.loads(
    (
        ROOT / "reports/evidence/neural_tracer_offref_location_2026-11-05.json"
    ).read_text()
)
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_offref_location.md").read_text().split()
)


def test_the_record_is_in_sample_only_places_all_off_length_and_reproduces_scrollgt():
    import neural_tracer_confidence_stops as cs

    assert RECORD["status"] == "OK" and RECORD["proxy_drift"] == []
    assert RECORD["cubes"] == list(cs.IN_SAMPLE) and not set(RECORD["per_cube"]) & set(
        cs.HELD_OUT
    )
    for t in ("tol2", "tol4"):
        s = RECORD["summary"][t]
        assert abs(s["unplaced"]) < 1e-6 * s["off_length"]
        assert (
            abs(s["point_precision"] - s["scrollgt_precision"])
            <= RECORD["proxy_tolerance"]
        )


def _pc(v: float) -> str:
    return f"{100 * v:.1f}%"


def _groups(shares: dict) -> dict:
    tails = sum(v for k, v in shares.items() if k.startswith("tail:"))
    return {
        "beside the same fiber": shares["gap_same"],
        "a whole fiber off the reference": shares["whole_off"],
        "a tail": tails,
        "between two fibers": shares["gap_switch"],
        "departures": tails + shares["gap_switch"],
        "owned": sum(
            v for k, v in shares.items() if k.startswith("tail:owned_or_live")
        ),
        "faces": sum(
            v
            for k, v in shares.items()
            if k.startswith("tail:bounds") or k == "tail:outside_cube"
        ),
    }


@pytest.mark.parametrize("place", ["beside the same fiber", "a whole fiber off the reference", "a tail", "between two fibers"])  # fmt: skip
def test_each_table_row_is_the_record_s_shares(place):
    g2, g4 = (_groups(RECORD["summary"][t]["shares"]) for t in ("tol2", "tol4"))
    assert f"| {place} | {_pc(g2[place])} | {_pc(g4[place])} |" in REPORT


def test_the_prose_figures_are_the_record_s():
    s2, s4 = RECORD["summary"]["tol2"], RECORD["summary"]["tol4"]
    g2, g4 = _groups(s2["shares"]), _groups(s4["shares"])
    for t, s in (("2", s2), ("4", s4)):
        assert (
            f"{s['point_precision']:.4f} against {s['scrollgt_precision']:.4f} at tolerance {t}"
            in REPORT
        )
    assert f"It is {s2['counts']['gap_same_n']:,.0f} short runs" in REPORT
    same = [s["shares"]["gap_same"] * s["off_length"] for s in (s2, s4)]
    assert (
        f"falls from {same[0]:,.0f} voxels at tolerance 2 to {same[1]:,.0f} at tolerance 4"
        in REPORT
    )
    assert (
        f"{s2['counts']['whole_off_n']:,.0f} fibers never come within 2 voxels"
        in REPORT
    )
    assert (
        f"is {_pc(g2['departures'])} at tolerance 2** ({_pc(g4['departures'])} at tolerance 4)"
        in REPORT
    )
    assert (
        f"are {_pc(s2['shares']['tail:confidence|unlinked|interior'])} of the off-reference length"
        in REPORT
    )
    assert f"(`owned_or_live`) are {_pc(g2['owned'])}" in REPORT and f"outside the cube) are {_pc(g2['faces'])}" in REPORT  # fmt: skip
    assert f"rise from {s2['point_precision']:.4f} to {s2['precision_without_departures']:.3f} at tolerance 2, and from {s4['point_precision']:.4f} to {s4['precision_without_departures']:.3f} at tolerance 4" in REPORT  # fmt: skip
    assert (
        f"at most {s2['precision_without_departures'] - s2['point_precision']:.3f} of pooled precision"
        in REPORT
    )
    assert (
        g2["beside the same fiber"] + g2["a whole fiber off the reference"] > 0.6
        and 0.3 < g2["departures"] < 0.37
    )


def test_the_ct_figures_are_the_record_s():
    s = RECORD["summary"]
    traced, ref = s["ct_peak_traced"], s["ct_peak_reference"]
    assert (
        f"peaks within {max(abs(v) for v in traced):.2f} voxel of no shift on every axis"
        in REPORT
    )
    neg = sum(v[1] < 0 for v in s["ct_peak_reference_per_cube"].values())
    assert (
        f"peaks {-ref[1]:.2f} voxel off in y (the same sign on {neg} of 11 cubes)"
        in REPORT
        and ref[1] < 0
    )
    assert f"and within {max(abs(ref[0]), abs(ref[2])):.2f} in z and x" in REPORT


def test_the_screen_s_pointer_states_the_record_s_shares():
    screen = " ".join(
        (ROOT / "reports/neural_tracer_stop_trim_screen.md").read_text().split()
    )
    g = _groups(RECORD["summary"]["tol2"]["shares"])
    want = (f"At tolerance 2, {_pc(g['beside the same fiber'])} lies beside the fiber being followed and "
            f"{_pc(g['a whole fiber off the reference'])} on fibers the reference never passes; departure-shaped length is "
            f"{_pc(g['departures'])}.")  # fmt: skip
    assert "[follow-up](neural_tracer_offref_location.md)" in screen and want in screen
