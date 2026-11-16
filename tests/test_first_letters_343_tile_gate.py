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
