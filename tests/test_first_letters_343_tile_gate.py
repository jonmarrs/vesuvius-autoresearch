"""Finding 117's tile gate: the per-tile score, the distance to the published winding, the AUC, the floor and the table."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/pherc343/tile_gate"


def _load():
    spec = importlib.util.spec_from_file_location(
        "tile_gate_under_test", HERE / "tile_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tg = _load()


class Sheets:
    """Predicted sheets are the planes x = 14 k, one voxel thick either side; distance positive outside."""

    def at(self, xyz):
        x = xyz[:, 0]
        return np.abs(x - 14.0 * np.round(x / 14.0)) - 1.0


def _grid(x_of_col, rows=57, cols=228, step=20.0):
    r, c = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
    xyz = np.stack([x_of_col(c).astype(float), c * step, r * step], -1)
    return xyz, np.ones((rows, cols), bool)


def test_the_auc_counts_ties_half_and_needs_both_labels():
    assert (
        tg.auc(np.array([3.0, 2.0, 1.0, 0.0]), np.array([True, True, False, False]))
        == 1.0
    )
    assert tg.auc(np.array([1.0, 1.0]), np.array([True, False])) == 0.5
    assert tg.auc(np.array([1.0, 2.0]), np.array([True, True])) is None


def test_the_distance_is_along_the_published_normal_and_none_beyond_the_sideways_limit():
    fit, valid = _grid(lambda c: np.zeros_like(c), rows=5, cols=8)
    near, near_valid = _grid(lambda c: np.full(c.shape, 1.5), rows=5, cols=8)
    d = tg.distance_to(fit, valid, near, near_valid)
    assert np.nanmax(np.abs(d - 1.5)) < 1e-9
    far = near.copy()
    far[..., 1] += 1000.0
    assert np.isnan(tg.distance_to(fit, valid, far, near_valid)).all()


def test_tiles_on_the_published_sheet_score_high_and_tiles_between_sheets_low():
    # tile columns 0-5 on the sheet x = 0 (where the published winding is), 6-11 at x = 7, between sheets
    fit, valid = _grid(lambda c: np.where(c < 6 * tg.TILE, 0, 7))
    pub, pub_valid = _grid(lambda c: np.zeros_like(c))
    readings = tg.node_readings(Sheets(), fit, valid)
    distance = tg.distance_to(fit, valid, pub, pub_valid)
    ts = tg.tiles(readings, distance, valid)
    assert len(ts) == 3 * 12
    for t in ts:
        on = t["col"] < 6
        assert t["within"] == (1.0 if on else 0.0)
        # the tile just past the step has one column of tilted normals
        assert t["tile_excess"] > 0.9 if on else t["tile_excess"] < -0.9
    for t in ts:
        t["winding"] = "w047"
    summary = tg.summarise(ts)
    assert (summary["right"], summary["wrong"], summary["auc"]) == (18, 18, 1.0)
    assert summary["floor"]["shifts"] == 11 and summary["floor"]["p95"] < 1.0
    assert (
        summary["share_right_at_line"] == 1.0 and summary["share_right_overall"] == 0.5
    )
    assert tg.verdict(summary) == "LOCAL_GATE_WORKS"


def test_the_table():
    base = {
        "right": 20,
        "wrong": 20,
        "share_right_overall": 0.5,
        "share_right_at_line": 0.8,
        "floor": {"p95": 0.55},
    }
    assert tg.verdict(None) == "DOES_NOT_RUN"
    assert tg.verdict({**base, "wrong": 14, "auc": 0.9}) == "DOES_NOT_RUN"
    assert tg.verdict({**base, "auc": 0.55}) == "LOCAL_GATE_FAILS"
    assert (
        tg.verdict({**base, "auc": 0.58, "floor": {"p95": 0.5}}) == "LOCAL_GATE_FAILS"
    )
    assert tg.verdict({**base, "auc": 0.70}) == "LOCAL_GATE_WEAK"
    assert tg.verdict({**base, "auc": 0.80}) == "LOCAL_GATE_WORKS"
    assert (
        tg.verdict({**base, "auc": 0.80, "share_right_at_line": 0.6})
        == "LOCAL_GATE_WEAK"
    )
    assert (
        tg.verdict({**base, "auc": 0.80, "floor": {"p95": 0.85}}) == "LOCAL_GATE_FAILS"
    )


def test_a_tile_with_too_few_scored_or_covered_nodes_is_dropped():
    fit, valid = _grid(lambda c: np.zeros_like(c), rows=19, cols=19)
    readings = tg.node_readings(Sheets(), fit, valid)
    assert readings["scored"].sum() == 17 * 17
    distance = np.full(valid.shape, np.nan)
    assert tg.tiles(readings, distance, valid) == []
    distance[:] = 0.0
    assert len(tg.tiles(readings, distance, valid)) == 1
    readings["scored"][:, :12] = False
    assert tg.tiles(readings, distance, valid) == []


def test_it_is_measured_once(tmp_path):
    out = tmp_path / "out.json"
    out.write_text(json.dumps({}))
    assert tg.main([str(out), "sdt", "fit", "published"]) == 2


# Added by the design review of 2026-11-16: the table, the floor and the tile rules at their bounds.

REGISTRATION = " ".join(
    (ROOT / "docs/preregistration/2026-11-15_first_letters_343_tile_gate.md")
    .read_text()
    .split()
)


def test_the_registration_states_the_tile_and_the_lines_the_code_uses():
    assert f"{tg.TILE} nodes of the fitted grid" in REGISTRATION
    assert f"within {tg.WITHIN:g} voxels of the published winding" in REGISTRATION
    assert f"at least {tg.EXCESS_LINE:g} that are right" in REGISTRATION


BOUND = {
    "right": 15,
    "wrong": 15,
    "auc": 0.80,
    "share_right_overall": 0.5,
    "share_right_at_line": 0.65,  # 0.5 + 0.15 is exactly 0.65 in floating point
    "floor": {"p95": 0.55},
}


@pytest.mark.parametrize(
    ("change", "verdict"),
    [
        ({}, "LOCAL_GATE_WORKS"),  # 15 of each label, and the share exactly 0.15 above
        ({"right": 14}, "DOES_NOT_RUN"),
        ({"auc": 0.55}, "LOCAL_GATE_FAILS"),  # on the floor
        (
            {"auc": 0.80, "floor": {"p95": 0.80}},
            "LOCAL_GATE_FAILS",
        ),  # on a floor above 0.75
        ({"auc": 0.60, "floor": {"p95": 0.5}}, "LOCAL_GATE_WEAK"),
        ({"auc": 0.5999, "floor": {"p95": 0.5}}, "LOCAL_GATE_FAILS"),
        ({"auc": 0.75}, "LOCAL_GATE_WORKS"),
        ({"auc": 0.7499}, "LOCAL_GATE_WEAK"),
        ({"share_right_at_line": 0.6499}, "LOCAL_GATE_WEAK"),
    ],
)
def test_the_table_at_its_bounds(change, verdict):
    assert tg.verdict({**BOUND, **change}) == verdict


def _tiles(rows):
    """Tiles of winding w047 in one row: (tile_excess, within) for each column."""
    return [
        {"winding": "w047", "row": 0, "col": c, "tile_excess": s, "within": w}
        for c, (s, w) in enumerate(rows)
    ]


def test_a_tile_half_on_the_sheet_is_right_and_one_at_the_line_is_counted():
    summary = tg.summarise(_tiles([(0.07, 0.5), (0.0699, 0.4999), (0.2, 1.0)]))
    assert (summary["right"], summary["wrong"]) == (2, 1)
    assert summary["tiles_at_line"] == 2 and summary["share_right_at_line"] == 1.0


def test_the_floor_slides_each_winding_by_its_own_width():
    # worked by hand from the docstring: shifts 1 to 4; the two-tile winding sits out shifts 2 and 4
    five = _tiles([(5, 1.0), (4, 1.0), (3, 0.5), (2, 0.0), (1, 0.0)])
    two = [{**t, "winding": "w048"} for t in _tiles([(10, 1.0), (0, 0.0)])]
    floor = tg.slid_floor(five + two)
    assert floor == {"shifts": 4, "p95": 0.475, "max": 0.5}


def _readings(scored):
    return {
        "inside": np.where(scored, 1.0, np.nan),
        "displaced": np.where(scored, 0.0, np.nan),
        "scored": scored.copy(),
    }


def test_a_tile_is_kept_from_200_scored_nodes_and_half_its_valid_nodes_covered():
    valid = np.ones((tg.TILE, tg.TILE), bool)
    scored = np.zeros(valid.shape, bool)
    scored.flat[:200] = True
    distance = np.zeros(valid.shape)
    assert len(tg.tiles(_readings(scored), distance, valid)) == 1
    valid.flat[-1] = False  # 360 valid nodes
    distance.flat[:180] = np.nan  # 180 of them covered: exactly half
    assert len(tg.tiles(_readings(scored), distance, valid)) == 1
    distance.flat[180] = np.nan
    assert tg.tiles(_readings(scored), distance, valid) == []


def test_within_counts_the_line_and_only_the_covered_nodes():
    valid = np.ones((tg.TILE, tg.TILE), bool)
    distance = np.full(valid.shape, 2.0)
    distance[:, :7] = np.nan  # 7 of 19 columns have no published partner
    (tile,) = tg.tiles(_readings(valid), distance, valid)
    assert tile["within"] == 1.0
    distance[:, 7:9] = 2.0001
    (tile,) = tg.tiles(_readings(valid), distance, valid)
    assert tile["within"] == pytest.approx(10 / 12)


def test_only_whole_tiles_are_read():
    valid = np.ones((tg.TILE + 11, tg.TILE), bool)
    ts = tg.tiles(_readings(valid), np.zeros(valid.shape), valid)
    assert [(t["row"], t["col"]) for t in ts] == [(0, 0)]


def test_a_partner_exactly_at_the_sideways_limit_counts():
    fit = np.array([[[1.5, 90.0, 40.0]]])
    pub, pub_valid = _grid(lambda c: np.zeros_like(c), rows=5, cols=5)
    d = tg.distance_to(fit, np.ones((1, 1), bool), pub, pub_valid)
    # the nearest published node with a normal is (0, 60, 40): 30 voxels sideways, 1.5 along
    assert d[0, 0] == 1.5


def test_the_distance_is_the_least_over_the_nearest_nodes_with_a_normal():
    # two flat pieces of one published grid with a missing column between them: x = 0 left, x = 10 right
    pub, pub_valid = _grid(lambda c: np.where(c < 5, 0, 10), rows=5, cols=11, step=5.0)
    pub_valid[:, 5] = False
    pub[:, 5] = -1.0
    fit = np.array([[[9.0, 20.0, 10.0]]])
    d = tg.distance_to(fit, np.ones((1, 1), bool), pub, pub_valid)
    # the nearest node with a normal is on the left piece, 9 along; one on the right piece, 15 sideways, is 1
    assert d[0, 0] == 1.0


class Face:
    """No distance where x is above 3; on the face (0) at x = 0; outside (1) everywhere else."""

    def at(self, xyz):
        x = xyz[:, 0]
        return np.where(x > 3, np.nan, np.where(x == 0, 0.0, 1.0))


def test_a_node_on_the_face_is_inside_and_a_node_needs_all_three_readings():
    fit, valid = _grid(lambda c: np.zeros_like(c), rows=5, cols=6)
    readings = tg.node_readings(Face(), fit, valid)
    # the copies moved +6 along the normal have no distance, so no node is scored
    assert not readings["scored"].any()

    class Inside(Face):
        def at(self, xyz):
            return np.nan_to_num(super().at(xyz), nan=1.0)

    readings = tg.node_readings(Inside(), fit, valid)
    scored = readings["scored"]
    assert scored.sum() == 3 * 4
    assert (readings["inside"][scored] == 1.0).all()
    assert (readings["displaced"][scored] == 0.0).all()
