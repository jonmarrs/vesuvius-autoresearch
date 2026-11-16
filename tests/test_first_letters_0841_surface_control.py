"""Finding 111's instruments: the label score, the floor, the choice of depth and the registered table."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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


def _load_describe():
    sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location(
        "describe_under_test", HERE / "describe.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_shift_scan_finds_a_map_that_was_moved_and_the_bootstrap_brackets_the_auc():
    describe = _load_describe()
    rng = np.random.default_rng(2)
    ink = _letters((400, 400))
    ok = np.ones(ink.shape, bool)
    score = ink + 0.5 * rng.normal(size=ink.shape)

    class Segment:
        render_ok, scored = ok, ok

    Segment.ink = ink
    moved = np.roll(score, (-4, 2), axis=(0, 1))
    found = describe.shift_scan(Segment, moved)
    assert (found["rows"], found["cols"]) == (4, -2)
    spread = describe.block_bootstrap(score, ok, ink, rng)
    assert spread["low"] <= sc.auc(score[ok], ink[ok]) <= spread["high"]
    assert spread["blocks"] == 49


# Added by the design review of 2026-11-15: guards of the registered script that the tests above do not reach.


def test_the_registered_lines_are_at_least():
    assert sc.p1_holds({"auc": 0.60, "slid_floor": {"largest": 0.50}})
    assert not sc.p1_holds({"auc": 0.5999, "slid_floor": {"largest": 0.50}})
    # 0.70 + 0.05 is exactly 0.75 in floating point, so this reading sits on the margin
    assert sc.p1_holds({"auc": 0.75, "slid_floor": {"largest": 0.70}})
    assert not sc.p1_holds({"auc": 0.7499, "slid_floor": {"largest": 0.70}})
    assert sc.p2_holds({"auc": 0.75})
    assert not sc.p2_holds({"auc": 0.7499})
    assert not sc.p2_holds({"auc": None})


def test_the_registration_states_the_cell_classes_the_code_uses():
    text = " ".join(REGISTRATION.split())
    assert f"at least {sc.SUPERVISED_MIN:.0%} of it is supervised" in text
    assert f"ink (labelled share at least {sc.INK_MIN:g})" in text
    assert f"bare (labelled share {sc.BARE_MAX:g})" in text


def test_a_cell_is_supervised_from_99_percent_ink_from_one_half_and_bare_only_at_zero():
    ink = np.array([0.0, 0.0, 0.0, 0.5, 0.49, 0.45, 0.05, 0.001])
    supervised = np.array([0.99, 0.989, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0])
    scored, is_ink = sc.cell_classes(ink, supervised, np.ones(8, bool))
    assert scored.tolist() == [True, False, False, True] + [False] * 4
    assert is_ink.tolist() == [False, False, False, True] + [False] * 4


def _covered(hole, dr, dc):
    """Cells whose slid value comes from a rendered cell of the map, not from across its edge."""
    rows, cols = np.indices(hole.shape)
    from_row, from_col = rows - dr, cols - dc
    inside = (
        (from_row >= 0)
        & (from_row < hole.shape[0])
        & (from_col >= 0)
        & (from_col < hole.shape[1])
    )
    out = np.zeros(hole.shape, bool)
    out[inside] = ~hole[from_row[inside], from_col[inside]]
    return out


@pytest.mark.parametrize(
    "label, down, right",
    [("down", 1, 0), ("up", -1, 0), ("right", 0, 1), ("left", 0, -1)],
)
def test_a_slide_moves_the_map_its_own_way_and_scores_only_cells_it_covers(
    label, down, right
):
    rng = np.random.default_rng(3)
    ink = rng.random((400, 400)) < 0.3
    hole = np.zeros(ink.shape, bool)
    hole[190:210, 190:210] = True
    dr, dc = down * sc.SLIDE_CELLS, right * sc.SLIDE_CELLS
    # a map that, slid this way, is the labels where it covers and their opposite everywhere else
    slid = np.where(_covered(hole, dr, dc), ink, ~ink).astype(float)
    score = np.roll(slid, (-dr, -dc), axis=(0, 1))
    floor = sc.slid_floor(score, ~hole, ~hole, ink)
    assert floor[label] == 1.0
    assert floor["largest"] == 1.0
    others = [v for k, v in floor.items() if k not in (label, "largest")]
    assert len(others) == 3 and max(others) < 0.6


def test_a_slide_is_scored_only_on_a_thousand_cells_of_each_class():
    rng = np.random.default_rng(4)
    shape = (200, 200)
    ok = np.ones(shape, bool)
    score = rng.normal(size=shape)
    ink = np.zeros(shape, bool)
    scored = np.zeros(shape, bool)
    scored[128:138] = (
        True  # 2,000 bare cells, all below the rows a slide down cannot reach
    )
    ink[150:155] = True  # and 1,000 ink cells
    scored[150:155] = True
    floor = sc.slid_floor(score, ok, scored, ink)
    assert floor["down"] is not None and floor["largest"] == floor["down"]
    assert floor["up"] is None and floor["right"] is None and floor["left"] is None
    scored[150, 0] = False  # 999 ink cells
    assert sc.slid_floor(score, ok, scored, ink) == {
        "down": None,
        "up": None,
        "right": None,
        "left": None,
        "largest": None,
    }


def _counted_segment(ink_cells, bare_cells):
    """A Segment with these scored cells, and five ink cells outside them."""
    segment = object.__new__(sc.Segment)
    size = ink_cells + bare_cells + 5
    segment.render_ok = np.ones((1, size), bool)
    segment.scored = np.ones((1, size), bool)
    segment.scored[0, -5:] = False
    segment.ink = np.zeros((1, size), bool)
    segment.ink[0, :ink_cells] = True
    segment.ink[0, -5:] = True
    segment.supervised_cells = size
    return segment


def test_a_segment_is_scorable_from_a_thousand_scored_cells_of_each_class():
    assert _counted_segment(1000, 1000).scorable()
    assert not _counted_segment(999, 5000).scorable()
    assert not _counted_segment(5000, 999).scorable()
    assert _counted_segment(1000, 2000).counts() == {
        "lattice": [1, 3005],
        "render_cells": 3005,
        "supervised_cells": 3005,
        "scored_cells": 3000,
        "ink_cells": 1000,
        "bare_cells": 2000,
    }


class _TwoSided:
    """What `held_out_reading` asks of a Segment: one map per side, scored on the left half."""

    def __init__(self, ink, maps):
        self.ink, self.maps = ink, maps
        self.render_ok = np.ones(ink.shape, bool)
        self.scored = self.render_ok.copy()
        self.scored[:, ink.shape[1] // 2 :] = False

    def counts(self):
        return {"scored_cells": int(self.scored.sum())}

    def score_map(self, depth, reading_side):
        return self.maps[depth, reading_side]

    def auc(self, depth, reading_side):
        score = self.score_map(depth, reading_side)
        return sc.auc(score[self.scored], self.ink[self.scored])


def test_a_held_out_reading_scores_the_chosen_side_on_the_scored_cells():
    rng = np.random.default_rng(5)
    ink = rng.random((400, 400)) < 0.3
    reverse = ink + 1.35 * rng.normal(size=ink.shape)
    reverse[:, 200:] = ~ink[:, 200:]  # wrong wherever the cells are not scored
    forward = rng.normal(size=ink.shape)
    segment = _TwoSided(ink, {(-2, True): reverse, (-2, False): forward})

    reading = sc.held_out_reading(segment, -2, "reverse")
    expected = sc.auc(reverse[segment.scored], ink[segment.scored])
    assert 0.65 < expected < 0.74
    assert reading["auc"] == round(expected, 4)
    assert reading["scored_cells"] == 80000
    floor = sc.slid_floor(reverse, segment.render_ok, segment.scored, ink)
    assert reading["slid_floor"] == {k: round(v, 4) for k, v in floor.items()}
    assert reading["slid_floor"]["largest"] < 0.55
    assert abs(reading["other_side_auc"] - 0.5) < 0.02
    assert reading["p1"] is True and reading["p2"] is False

    other = sc.held_out_reading(segment, -2, "forward")
    assert abs(other["auc"] - 0.5) < 0.02
    assert other["other_side_auc"] == reading["auc"]
    assert other["p1"] is False and other["p2"] is False


def test_main_refuses_an_output_that_exists(tmp_path):
    out = tmp_path / "instrument.json"
    out.write_text("kept\n")
    with pytest.raises(SystemExit, match="measured once"):
        sc.main(["instrument", str(out), str(tmp_path / "published"), "segment"])
    assert out.read_text() == "kept\n"


class _Swept:
    """What `sweep` asks of a Segment: the `_reverse` side peaks at depth -1."""

    name = "development"

    def __init__(self, scorable):
        self.is_scorable, self.asked = scorable, []

    def scorable(self):
        return self.is_scorable

    def counts(self):
        return {"ink_cells": 3, "bare_cells": 4}

    def auc(self, depth, reading_side):
        self.asked.append((depth, reading_side))
        return 0.7 - 0.01 * abs(depth + 1) if reading_side else 0.5


def _sweep(out, monkeypatch, segment):
    monkeypatch.setattr(sc, "_segment", lambda values: segment)
    argv = ["sweep", str(out), "--segment", "name", "mesh", "maps", "render", "labels"]
    return sc.main([*argv, "--depths", "-2", "1"])


def test_the_sweep_scores_every_depth_on_both_sides(tmp_path, monkeypatch):
    segment = _Swept(scorable=True)
    out = tmp_path / "sweep.json"
    assert _sweep(out, monkeypatch, segment) == 0
    result = json.loads(out.read_text())
    depths = (-2, -1, 0, 1)
    assert [(row["depth"], row["side"]) for row in result["table"]] == [
        (depth, side) for depth in depths for side in ("reverse", "forward")
    ]
    assert segment.asked == [
        (depth, side) for depth in depths for side in (True, False)
    ]
    assert result["chosen"] == {"depth": -1, "side": "reverse", "auc": 0.7}
    assert result["segment"] == "development"
    assert (result["ink_cells"], result["bare_cells"]) == (3, 4)


def test_the_sweep_refuses_a_segment_with_too_few_scored_cells(tmp_path, monkeypatch):
    out = tmp_path / "sweep.json"
    with pytest.raises(SystemExit, match="too few scored cells"):
        _sweep(out, monkeypatch, _Swept(scorable=False))
    assert not out.exists()


ALL_RAN = {"render_sa": 0, "ink_sa": 0, "render_sb": 0, "ink_sb": 0}
CHOSEN = {"depth": -2, "side": "reverse", "auc": 0.76}


def _confirm(directory, monkeypatch, chosen, exits):
    """`confirm` on stand-in segments a (AUC 0.80) and b (0.70); an exit of None leaves a step without a record."""
    values = {"a": 0.80, "b": 0.70}
    calls = []

    def reading(segment, depth, side):
        calls.append((segment.name, depth, side))
        return _reading(values[segment.name], 0.5)

    monkeypatch.setattr(
        sc, "_segment", lambda v: SimpleNamespace(name=v[0], render=Path(v[3]))
    )
    monkeypatch.setattr(sc, "held_out_reading", reading)
    for step, code in exits.items():
        if code is not None:
            (directory / f"{step}.json").write_text(json.dumps({"exit": code}))
    choice = directory / "sweep.json"
    choice.write_text(json.dumps({"chosen": chosen}))
    out = directory / "confirm.json"
    argv = ["confirm", str(out), "--choice", str(choice), "--gate", str(directory)]
    for name in values:
        argv += ["--segment", name, "mesh", "maps", f"render/s{name}_66.zarr", "labels"]
    assert sc.main(argv) == 0
    return json.loads(out.read_text()), calls


def test_confirm_reads_each_held_out_segment_at_the_chosen_depth_and_side(
    tmp_path, monkeypatch
):
    result, calls = _confirm(tmp_path, monkeypatch, CHOSEN, ALL_RAN)
    assert calls == [("a", -2, "reverse"), ("b", -2, "reverse")]
    assert result["verdict"] == "BLOB_LEVEL_SIGNAL"
    assert result["p1"] == {"a": True, "b": True}
    assert result["p2"] == {"a": True, "b": False}
    assert result["gate"] == {step: {"exit": 0} for step in ALL_RAN}
    assert result["chosen"] == CHOSEN


@pytest.mark.parametrize(
    "chosen, exits, failed",
    [
        (None, ALL_RAN, []),  # the sweep chose nothing
        (CHOSEN, {**ALL_RAN, "ink_sb": 1}, ["ink_sb"]),
        (CHOSEN, {**ALL_RAN, "render_sa": None}, ["render_sa"]),  # never ran
    ],
)
def test_confirm_reads_nothing_without_a_choice_or_with_a_step_that_did_not_run(
    tmp_path, monkeypatch, chosen, exits, failed
):
    result, calls = _confirm(tmp_path, monkeypatch, chosen, exits)
    assert (result["verdict"], result["failed_steps"]) == ("DOES_NOT_RUN", failed)
    assert result["held_out"] is None and calls == []


def _one_surface(factor=4, rows=30, cols=40):
    """A flat surface on a coarse grid and on one `factor` times finer, node centre on node centre."""
    hy, hx = np.mgrid[0 : rows * factor, 0 : cols * factor].astype(float)
    cy, cx = (hy + 0.5) / factor - 0.5, (hx + 0.5) / factor - 0.5
    fine = np.stack([20 * cx, 20 * cy, np.full_like(cx, 500.0)], -1)
    ly, lx = np.mgrid[0:rows, 0:cols].astype(float)
    coarse = np.stack([20 * lx, 20 * ly, np.full_like(lx, 500.0)], -1)
    return coarse, fine


def test_mesh_agreement_leaves_out_invalid_nodes_of_either_mesh():
    coarse, fine = _one_surface()
    ok_c, ok_f = np.ones(coarse.shape[:2], bool), np.ones(fine.shape[:2], bool)
    # a normal needs a neighbour on every side, so the border is never used
    assert sc.mesh_agreement(coarse, ok_c, fine, ok_f)["nodes"] == 28 * 38

    far, half = fine.copy(), ok_f.copy()
    far[:60] += 1000.0  # the top half of the fine mesh is invalid, and far away
    half[:60] = False
    result = sc.mesh_agreement(coarse, ok_c, far, half)
    assert result["nodes"] == 14 * 38
    assert result["normal_p95_abs"] == 0 and result["lateral_p95"] == 0

    off, some = coarse.copy(), ok_c.copy()
    some[1::3, 1::3] = False  # one coarse node in nine is invalid, and far away
    off[~some] += 1000.0
    result = sc.mesh_agreement(off, some, fine, ok_f)
    assert 0 < result["nodes"] < 28 * 38 - 130
    assert result["normal_p95_abs"] == 0 and result["lateral_p95"] == 0


def _instrument(tmp_path, monkeypatch, offsets):
    """`instrument` on stand-in segments whose 2.4 um mesh sits `offsets[name]` voxels off the 9.366 um one."""
    coarse, fine = _one_surface()
    # the 2.4 um mesh is published in its own scan's frame: twice the scale, and moved
    matrix = np.array([[0.5, 0, 0, 7.0], [0, 0.5, 0, -3.0], [0, 0, 0.5, 11.0]])
    published = tmp_path / "published"
    (published / "transform").mkdir(parents=True)
    (published / "transform" / "transform.json").write_text(
        json.dumps({"transformation_matrix": matrix.tolist()})
    )
    asked = []

    def load(path):
        asked.append(str(Path(path).relative_to(published)))
        name = Path(path).parent.parent.name
        if Path(path).name.endswith("-on-20250821151531-9.366um.tifxyz"):
            return coarse, np.ones(coarse.shape[:2], bool)
        in_its_scan = (fine + np.asarray(offsets[name], float) - matrix[:, 3]) / 0.5
        return in_its_scan, np.ones(fine.shape[:2], bool)

    monkeypatch.setattr(sc.analysis, "load_tifxyz", load)
    out = tmp_path / "instrument.json"
    assert sc.main(["instrument", str(out), str(published), *offsets]) == 0
    return json.loads(out.read_text()), asked


def test_the_instrument_carries_the_fine_mesh_with_the_published_transform(
    tmp_path, monkeypatch
):
    result, asked = _instrument(
        tmp_path, monkeypatch, {"111-a": (0, 0, 0), "222-b": (0, 1.5, 0.5)}
    )
    assert asked == [
        "111-a/mesh/111-on-20250821151531-9.366um.tifxyz",
        "111-a/mesh/111-on-20260319124803-2.403um.tifxyz",
        "222-b/mesh/222-on-20250821151531-9.366um.tifxyz",
        "222-b/mesh/222-on-20260319124803-2.403um.tifxyz",
    ]
    assert result["ok"] is True
    assert (
        result["111-a"]["normal_median"] == 0 and result["111-a"]["lateral_median"] == 0
    )
    # positive: the fine mesh sits on the side the coarse mesh's normal points to
    assert result["222-b"]["normal_median"] == 0.5
    assert result["222-b"]["lateral_median"] == 1.5
    assert result["222-b"]["grids"] == [[30, 40], [120, 160]]


@pytest.mark.parametrize(
    "offset, ok",
    [
        ((0, 2.0, 1.0), True),  # on both lines
        ((0, 2.0, -1.0), True),
        ((0, 0, 1.5), False),  # off the surface, on either side of it
        ((0, 0, -1.5), False),
        ((0, 2.5, 0), False),  # on the surface, more than half a lattice cell along it
    ],
)
def test_the_instrument_passes_only_when_every_segment_is_on_its_surface(
    tmp_path, monkeypatch, offset, ok
):
    result, _ = _instrument(
        tmp_path, monkeypatch, {"111-a": (0, 0, 0), "222-b": offset}
    )
    assert result["ok"] is ok
