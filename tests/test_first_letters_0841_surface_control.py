"""Finding 111's instruments: the label score, the floor, the choice of depth and the registered table."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/pherc0841"
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-13_first_letters_0841_surface_control.md"
).read_text()


def _load():
    spec = importlib.util.spec_from_file_location(
        "surface_control_under_test", HERE / "surface_control.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sc = _load()


def test_auc_is_one_half_for_noise_one_for_a_perfect_score_and_handles_ties():
    rng = np.random.default_rng(0)
    label = rng.random(20000) < 0.3
    assert abs(sc.auc(rng.normal(size=label.size), label) - 0.5) < 0.02
    assert sc.auc(label.astype(float) + 0.01 * rng.random(label.size), label) == 1.0
    assert sc.auc(-label.astype(float), label) == 0.0
    assert sc.auc(np.zeros(label.size), label) == 0.5
    assert sc.auc(np.arange(4.0), np.zeros(4, bool)) is None


def test_auc_matches_the_pair_count_on_a_small_case():
    score = np.array([0.1, 0.4, 0.4, 0.8, 0.9])
    label = np.array([False, True, False, True, False])
    pairs = [(p, n) for p in score[label] for n in score[~label]]
    expected = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p, n in pairs) / len(
        pairs
    )
    assert sc.auc(score, label) == pytest.approx(expected)


def test_cells_are_scored_only_where_supervised_rendered_and_unambiguous():
    ink = np.array([[1.0, 0.5, 0.2, 0.0], [1.0, 0.0, 0.0, 1.0]])
    supervised = np.array([[1.0, 1.0, 1.0, 1.0], [0.5, 1.0, 1.0, 1.0]])
    render = np.array([[True, True, True, True], [True, False, True, True]])
    scored, is_ink = sc.cell_classes(ink, supervised, render)
    assert scored.tolist() == [[True, True, False, True], [False, False, True, True]]
    assert is_ink.tolist() == [[True, True, False, False], [True, False, False, True]]


def _letters(shape=(600, 600), period=40):
    rows, cols = np.indices(shape)
    return ((rows // period + cols // period) % 2 == 0) & (rows % period < 12)


def test_the_slid_floor_is_near_chance_for_a_map_that_scores_high_in_place():
    rng = np.random.default_rng(1)
    ink = _letters()
    ok = np.ones(ink.shape, bool)
    score = ink + 0.5 * rng.normal(size=ink.shape)
    assert sc.auc(score[ok], ink[ok]) > 0.9
    floor = sc.slid_floor(score, ok, ok, ink)
    # 128 cells is not a multiple of the 40-cell pattern, so the slid map no longer lines up
    assert set(floor) == {"down", "up", "right", "left", "largest"}
    assert floor["largest"] < 0.75
    assert floor["largest"] < sc.auc(score[ok], ink[ok]) - 0.2


def test_the_slid_floor_leaves_out_cells_the_slid_map_does_not_cover():
    ink = _letters((400, 400))
    ok = np.ones(ink.shape, bool)
    score = ink.astype(float)
    scored = np.zeros(ink.shape, bool)
    scored[: sc.SLIDE_CELLS] = True  # only rows the map slid down cannot reach
    floor = sc.slid_floor(score, ok, scored, ink)
    assert floor["down"] is None
    assert floor["up"] is not None


def test_choose_takes_the_highest_auc_then_the_depth_nearest_zero_then_reverse():
    table = [
        {"depth": 3, "side": "forward", "auc": 0.7},
        {"depth": -1, "side": "forward", "auc": 0.7},
        {"depth": -1, "side": "reverse", "auc": 0.7},
        {"depth": 0, "side": "reverse", "auc": 0.6},
        {"depth": 5, "side": "reverse", "auc": None},
    ]
    assert sc.choose(table) == {"depth": -1, "side": "reverse", "auc": 0.7}
    assert sc.choose([{"depth": 0, "side": "reverse", "auc": None}]) is None


def _reading(value, floor):
    out = {"auc": value, "slid_floor": {"largest": floor}}
    out["p1"], out["p2"] = sc.p1_holds(out), sc.p2_holds(out)
    return out


GATE = {
    "render_a": {"exit": 0},
    "ink_a": {"exit": 0},
    "render_b": {"exit": 0},
    "ink_b": {"exit": 0},
}


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ((0.80, 0.55), (0.76, 0.52), "LETTER_LEVEL_SIGNAL"),
        ((0.80, 0.55), (0.70, 0.52), "BLOB_LEVEL_SIGNAL"),
        ((0.62, 0.52), (0.61, 0.50), "BLOB_LEVEL_SIGNAL"),
        ((0.80, 0.55), (0.59, 0.50), "NO_SIGNAL"),
        (
            (0.80, 0.78),
            (0.80, 0.50),
            "NO_SIGNAL",
        ),  # high, but no better than the slid map
        ((0.80, None), (0.80, 0.50), "NO_SIGNAL"),
    ],
)
def test_the_registered_table(a, b, expected):
    readings = {"a": _reading(*a), "b": _reading(*b)}
    assert sc.verdict(GATE, readings)["verdict"] == expected


def test_a_failed_or_missing_step_decides_before_any_reading():
    readings = {"a": _reading(0.9, 0.5), "b": _reading(0.9, 0.5)}
    failed = {**GATE, "ink_b": {"exit": 1}}
    assert sc.verdict(failed, readings) == {
        "verdict": "DOES_NOT_RUN",
        "failed_steps": ["ink_b"],
    }
    assert sc.verdict({**GATE, "render_a": {"exit": None}}, readings)["verdict"] == (
        "DOES_NOT_RUN"
    )
    assert sc.verdict({}, readings)["verdict"] == "DOES_NOT_RUN"
    assert sc.verdict(GATE, None)["verdict"] == "DOES_NOT_RUN"


def test_read_gate_counts_a_missing_record_as_not_run(tmp_path):
    (tmp_path / "render_s1.json").write_text('{"exit": 0, "seconds": 5}\n')
    gate = sc.read_gate(tmp_path, ["s1"])
    assert gate["render_s1"]["exit"] == 0
    assert gate["ink_s1"] == {"exit": None}


def test_mesh_agreement_is_zero_for_a_centre_aligned_refinement_and_sees_a_shift():
    factor = 4
    rows, cols = 30, 40
    hy, hx = np.mgrid[0 : rows * factor, 0 : cols * factor].astype(float)
    # a tilted plane; the fine grid's node (y, x) sits at coarse coordinate (y + 0.5) / f - 0.5
    cy, cx = (hy + 0.5) / factor - 0.5, (hx + 0.5) / factor - 0.5
    fine = np.stack([20 * cx, 20 * cy, 0.3 * 20 * cx + 500], -1)
    ly, lx = np.mgrid[0:rows, 0:cols].astype(float)
    coarse = np.stack([20 * lx, 20 * ly, 0.3 * 20 * lx + 500], -1)
    ok_c, ok_f = np.ones((rows, cols), bool), np.ones(fine.shape[:2], bool)
    same = sc.mesh_agreement(coarse, ok_c, fine, ok_f)
    assert abs(same["normal_median"]) < 1e-6 and same["lateral_median"] < 1e-6
    lifted = fine + np.array([0.0, 6.0, 0.0])  # along y, which lies in the plane
    assert sc.mesh_agreement(coarse, ok_c, lifted, ok_f)["lateral_median"] == (
        pytest.approx(6.0, abs=1e-6)
    )


def test_the_registration_states_the_constants_the_code_uses():
    for text in (
        f"AUC of at least {sc.P1_AUC:.2f}",
        f"at least {sc.P1_MARGIN:.2f} above",
        f"AUC of at least {sc.P2_AUC:.2f}",
        f"{sc.SLIDE_CELLS * 4} render pixels",
        "`LETTER_LEVEL_SIGNAL`",
        "`BLOB_LEVEL_SIGNAL`",
        "`NO_SIGNAL`",
        "`DOES_NOT_RUN`",
    ):
        assert text in REGISTRATION, text
    env = (HERE / "env.sh").read_text()
    assert "D_MIN=-8" in env and "D_MAX=8" in env
    assert "depths −8 to +8" in REGISTRATION
    assert "20260220213127-w00" in REGISTRATION


def test_the_scripts_refuse_to_measure_twice():
    source = (HERE / "surface_control.py").read_text()
    assert "exists: this is measured once" in source
    assert "exists: a step is run once" in (HERE / "run_render.sh").read_text()
    json.dumps(sc.verdict(GATE, None))
