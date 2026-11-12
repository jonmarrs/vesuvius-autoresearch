"""Finding 110's analysis (repro/first_letters/pherc343/mesh_step): the surface distance, the choice of windings,
the ink transfer and the registered decision table, on surfaces and maps built here."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "repro/first_letters/pherc343/mesh_step"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, STEP / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


an = load("mesh_step_analysis")
tm = load("transfer_maps")


def cylinder(radius, rows=40, z0=0.0, theta0=0.0, arc=1.5, step=20.0):
    """A sheet of a cylinder about the z axis: rows step along z, columns along the arc."""
    cols = int(radius * arc / step)
    theta = theta0 + np.arange(cols) * step / radius
    z = z0 + np.arange(rows) * step
    xyz = np.empty((rows, cols, 3))
    xyz[..., 0] = radius * np.cos(theta)[None, :] + 3000
    xyz[..., 1] = radius * np.sin(theta)[None, :] + 3000
    xyz[..., 2] = z[:, None]
    return xyz, np.ones((rows, cols), dtype=bool)


def plane(rows, cols, x0=1000.0, y0=2000.0, z0=500.0, step=20.0, reverse_columns=False):
    """A flat sheet at height y0: rows step along z, columns along x."""
    xyz = np.empty((rows, cols, 3))
    xyz[..., 0] = x0 + np.arange(cols)[None, :] * step
    xyz[..., 1] = y0
    xyz[..., 2] = z0 + np.arange(rows)[:, None] * step
    if reverse_columns:
        xyz = xyz[:, ::-1].copy()
    return xyz, np.ones((rows, cols), dtype=bool)


def write_tifxyz(path: Path, xyz, valid):
    import tifffile

    path.mkdir(parents=True)
    out = xyz.astype(np.float32).copy()
    out[~valid] = -1.0
    for i, axis in enumerate("xyz"):
        tifffile.imwrite(path / f"{axis}.tif", out[..., i])


# --- distance -------------------------------------------------------------------------------------


def test_the_same_sheet_sampled_half_a_step_apart_is_at_distance_zero():
    a, a_valid = cylinder(1000.0)
    b, b_valid = cylinder(1000.0, theta0=0.01, z0=10.0)
    d = an.surface_distance(a[1:-1, 2:-2], a_valid[1:-1, 2:-2], b, b_valid)
    assert d["median"] < 0.1 and d["fraction_within"]["2"] > 0.99
    assert an.p1_holds(d)


def test_the_next_sheet_scores_its_spacing_and_fails_p1():
    a, a_valid = cylinder(1000.0)
    b, b_valid = cylinder(1013.0)
    d = an.surface_distance(a[1:-1, 2:-2], a_valid[1:-1, 2:-2], b, b_valid)
    assert 12.5 < d["median"] < 13.5 and d["signed_median"] < 0
    assert d["fraction_within"]["2"] == 0.0 and d["covered_fraction"] > 0.99
    assert not an.p1_holds(d)


def test_nodes_the_other_surface_does_not_reach_count_as_not_within():
    a, a_valid = cylinder(1000.0, rows=40)
    b, b_valid = cylinder(1000.0, rows=20)
    d = an.surface_distance(a, a_valid, b, b_valid)
    assert 0.45 < d["covered_fraction"] < 0.60
    assert d["median"] < 0.1
    assert d["fraction_within"]["2"] == pytest.approx(d["covered_fraction"], abs=0.02)


def test_missing_nodes_are_ignored_on_both_sides():
    a, a_valid = cylinder(1000.0)
    b, b_valid = cylinder(1000.0)
    a_valid = a_valid.copy()
    a_valid[:, :10] = False
    a[~a_valid] = -1.0
    d = an.surface_distance(a, a_valid, b, b_valid)
    assert d["a_nodes"] == int(a_valid.sum()) and d["median"] < 0.1
    empty = an.surface_distance(a, a_valid, b, np.zeros_like(b_valid))
    assert empty["median"] is None and empty["fraction_within"]["2"] == 0.0
    assert not an.p1_holds(empty)


def test_p1_needs_both_the_share_and_the_median():
    base = {"median": 1.0, "fraction_within": {"2": 0.6}}
    assert an.p1_holds(base)
    assert not an.p1_holds({"median": 1.0, "fraction_within": {"2": 0.49}})
    assert not an.p1_holds({"median": 3.1, "fraction_within": {"2": 0.6}})
    assert (an.WITHIN, an.P1_FRACTION, an.P1_MEDIAN) == (2.0, 0.50, 3.0)


# --- choice ---------------------------------------------------------------------------------------


def score(median, within, covered=1.0):
    return {
        "median": median,
        "fraction_within": {"2": within},
        "covered_fraction": covered,
    }


def test_the_choice_is_the_smallest_median_among_candidates_that_cover_enough():
    scores = {
        "w046": score(13.0, 0.0),
        "w047": score(0.8, 0.9),
        "w048": score(12.9, 0.0),
        "w001": score(0.1, 0.2, covered=0.2),
    }
    assert an.choose(scores) == "w047"
    assert an.choose({"w001": score(0.1, 0.2, covered=0.2)}) is None
    assert an.choose({"w001": score(None, 0.0, covered=0.0)}) is None
    tie = {"w050": score(1.0, 0.7), "w049": score(1.0, 0.8), "w051": score(1.0, 0.7)}
    assert an.choose(tie) == "w049"


def test_select_finds_each_published_sheet_and_says_whether_the_picks_are_neighbours(
    tmp_path,
):
    for index, radius in ((46, 987.0), (47, 1000.0), (48, 1013.0), (49, 1026.0)):
        write_tifxyz(tmp_path / f"ours/w{index:03d}", *cylinder(radius, theta0=0.004))
    xyz47, valid47 = cylinder(1000.0)
    xyz48, valid48 = cylinder(1013.0)
    write_tifxyz(tmp_path / "pub/w047_x", xyz47[1:-1, 2:-2], valid47[1:-1, 2:-2])
    write_tifxyz(tmp_path / "pub/w048_x", xyz48[1:-1, 2:-2], valid48[1:-1, 2:-2])
    result = an.select(
        {"w047": str(tmp_path / "pub/w047_x"), "w048": str(tmp_path / "pub/w048_x")},
        [str(p) for p in sorted((tmp_path / "ours").iterdir())],
    )
    chosen = {name: entry["chosen"] for name, entry in result["published"].items()}
    assert chosen == {"w047": "w047", "w048": "w048"}
    assert an.consecutive(chosen) is True
    assert an.consecutive({"w047": "w047", "w048": "w047"}) is False
    assert an.consecutive({"w047": "w048", "w048": "w047"}) is False
    assert an.consecutive({"w047": "w047", "w048": None}) is None
    assert all(an.p1_holds(e["chosen_score"]) for e in result["published"].values())
    closest = result["published"]["w047"]["three_closest"]
    assert [c["candidate"] for c in closest][0] == "w047" and len(closest) == 3
    with pytest.raises(ValueError, match="exactly two"):
        an.select({"w047": str(tmp_path / "pub/w047_x")}, [])


# --- ink transfer ---------------------------------------------------------------------------------


def test_lattice_points_are_bilinear_and_need_all_four_nodes():
    xyz, valid = plane(6, 8)
    points, ok = an.lattice_points(xyz, valid)
    assert points.shape == (30, 40, 3) and ok.shape == (30, 40)
    assert points[0, 0] == pytest.approx([1001.5, 2000.0, 501.5])
    assert points[7, 11] == pytest.approx([1045.5, 2000.0, 529.5])
    # beyond the last node there is no surface: 5 nodes of rows = 100 voxels = 25 cells
    assert ok[:25, :35].all() and not ok[25:].any() and not ok[:, 35:].any()
    valid = valid.copy()
    valid[2, 3] = False
    _, holed = an.lattice_points(xyz, valid)
    assert not holed[5:15, 10:20].any()
    assert holed[:5, :35].all() and holed[:25, :10].all()


def test_block_mean_drops_the_ragged_edge():
    image = np.arange(9 * 10, dtype=np.float64).reshape(9, 10)
    pooled = an.block_mean(image)
    assert pooled.shape == (2, 2)
    assert pooled[0, 0] == pytest.approx(image[:4, :4].mean())
    assert pooled[1, 1] == pytest.approx(image[4:8, 4:8].mean())


def field(shape, seed):
    rng = np.random.default_rng(seed)
    return ndimage.gaussian_filter(rng.standard_normal(shape), 3.0)


def test_transfer_takes_ink_only_from_points_within_reach():
    pub_xyz, pub_valid = plane(8, 10)
    near_xyz, near_valid = plane(8, 10, x0=1008.0, z0=504.0, y0=2001.0)
    far_xyz, far_valid = plane(8, 10, y0=2013.0)
    pub = an.lattice_points(pub_xyz, pub_valid)
    near = an.lattice_points(near_xyz, near_valid)
    far = an.lattice_points(far_xyz, far_valid)
    which, cell, dist = an.transfer(*pub, [far, near])
    taken = which >= 0
    assert set(np.unique(which)) == {-1, 1}  # the sheet 13 voxels off gives nothing
    assert dist[taken].max() <= an.ACCEPT and dist[taken].min() == pytest.approx(1.0)
    # near is the same lattice moved by (2, 1) cells: cell (r, c) of the published takes (r - 1, c - 2)
    rows, cols = np.nonzero(taken)
    assert (cell[taken] == (rows - 1) * near[1].shape[1] + (cols - 2)).all()
    assert not taken[0].any() and not taken[:, :2].any()
    none, _, _ = an.transfer(*pub, [far])
    assert (none == -1).all()


def test_normals_agree_is_negative_for_a_surface_whose_columns_run_backwards():
    pub = an.lattice_points(*plane(8, 10))
    same = an.lattice_points(*plane(8, 10, y0=2001.0))
    back = an.lattice_points(*plane(8, 10, y0=2001.0, reverse_columns=True))
    which, cell, _ = an.transfer(*pub, [same])
    assert an.normals_agree(pub[0], same[0], which, cell, 0) == pytest.approx(1.0)
    which, cell, _ = an.transfer(*pub, [back])
    assert an.normals_agree(pub[0], back[0], which, cell, 0) == pytest.approx(-1.0)
    assert an.normals_agree(pub[0], back[0], which, cell, 1) is None


def four(base, noise_seed, noise=0.02):
    rng = np.random.default_rng(noise_seed)
    return {m: base + noise * rng.standard_normal(base.shape) for m in an.MODELS}


def frame(shape=(400, 600)):
    accepted = np.ones(shape, dtype=bool)
    accepted[:, :5] = False
    letters = np.zeros(shape, dtype=bool)
    letters[100:220, 150:400] = True
    return accepted, letters


def unit(shape, seed):
    values = field(shape, seed)
    return values / values.std()


def test_agreement_passes_for_the_same_ink_and_fails_for_other_ink():
    shape = (400, 600)
    ink, blind = unit(shape, 1), unit(shape, 7)
    accepted, letters = frame(shape)
    same = an.agreement(four(ink, 2), four(blind, 4), four(ink, 3), accepted, letters)
    assert same["evaluable"] and same["p3"] is True
    assert same["r"] > 0.9
    assert abs(same["control_wrong_side"]) < 0.2
    assert same["control_slid"]["largest_absolute"] < 0.2
    assert set(same["control_slid"]) == {
        "down",
        "up",
        "right",
        "left",
        "largest_absolute",
    }
    assert set(same["per_model_r"]) == set(an.MODELS)
    other = an.agreement(
        four(ink, 2), four(blind, 4), four(unit(shape, 9), 3), accepted, letters
    )
    assert other["evaluable"] and other["p3"] is False and abs(other["r"]) < 0.2
    # the same ink 64 pixels out of place is not agreement
    moved = an.agreement(
        four(ink, 2),
        four(blind, 4),
        four(np.roll(ink, an.SHIFT_CELLS, axis=1), 3),
        accepted,
        letters,
    )
    assert moved["p3"] is False and abs(moved["r"]) < 0.2
    assert moved["control_slid"]["left"] > 0.9


def test_a_shared_background_is_not_agreement():
    """Two maps with the same broad brightness and different strokes agree until the background is taken
    off; the deciding r is the one after."""
    shape = (400, 600)
    rng = np.random.default_rng(11)
    background = ndimage.gaussian_filter(rng.standard_normal(shape), 60.0)
    background *= 2.0 / background.std()
    accepted, letters = frame(shape)
    result = an.agreement(
        four(background + unit(shape, 1), 2, 0.001),
        four(unit(shape, 7), 4, 0.001),
        four(background + unit(shape, 9), 3, 0.001),
        accepted,
        letters,
    )
    assert result["r_all_cells_with_background"] > an.P3_R
    assert abs(result["r"]) < 0.2 and result["p3"] is False


def test_highpass_removes_the_broad_part_and_reads_nothing_outside_the_mask():
    shape = (200, 300)
    strokes = unit(shape, 1)
    ramp = np.linspace(0.0, 40.0, shape[1])[None, :] + np.zeros(shape)
    mask = np.ones(shape, dtype=bool)
    mask[:, 250:] = False
    outside = np.where(mask, strokes + ramp, 1e6)
    kept = an.highpass(outside, mask)
    assert not kept[~mask].any()
    inner = np.zeros(shape, dtype=bool)
    inner[40:160, 40:210] = True
    assert an.pearson(kept[inner], strokes[inner]) > 0.95
    assert abs(an.pearson(kept[inner], ramp[inner])) < 0.2
    assert an.HIGHPASS_CELLS * an.LATTICE == 64


def test_ink_that_reads_the_blind_side_as_well_fails_the_wrong_side_control():
    """Ours agrees with the published reading side at r = 0.78 and with its blind side at 0.62: the fit
    found the sheet but the comparison cannot say it found the written face."""
    shape = (400, 600)
    reading, blind = unit(shape, 1), unit(shape, 7)
    accepted, letters = frame(shape)
    result = an.agreement(
        four(reading, 2, 0.001),
        four(blind, 4, 0.001),
        four(reading + 0.8 * blind, 3, 0.001),
        accepted,
        letters,
    )
    assert result["r"] > an.P3_R
    assert result["control_slid"]["largest_absolute"] < result["r"] / an.P3_RATIO
    assert abs(result["control_wrong_side"]) > result["r"] / an.P3_RATIO
    assert result["p3"] is False
    # the size of the control counts, not its sign: the blind side inverted is still the blind side
    inverted = an.agreement(
        four(reading, 2, 0.001),
        four(blind, 4, 0.001),
        four(reading - 0.8 * blind, 3, 0.001),
        accepted,
        letters,
    )
    assert inverted["r"] > an.P3_R and inverted["control_wrong_side"] < -0.5
    assert inverted["p3"] is False


def test_ink_that_repeats_every_64_pixels_fails_the_slid_control():
    """r alone is not enough: maps that still agree after the 16-cell slide show placement of nothing."""
    shape = (400, 600)
    stripes = np.sin(2 * np.pi * np.arange(shape[1]) / an.SHIFT_CELLS)[
        None, :
    ] + np.zeros(shape)
    accepted, letters = frame(shape)
    result = an.agreement(
        four(stripes, 2, 0.01),
        four(unit(shape, 7), 4, 0.01),
        four(stripes, 3, 0.01),
        accepted,
        letters,
    )
    assert result["r"] > 0.9 and abs(result["control_wrong_side"]) < 0.2
    assert result["control_slid"]["right"] > 0.9
    assert result["control_slid"]["down"] > 0.9
    assert result["p3"] is False
    assert (an.SHIFT_CELLS * an.LATTICE, an.P3_R, an.P3_RATIO) == (64, 0.50, 2.0)


def test_the_slid_control_does_not_read_cells_that_wrapped_round():
    shape = (120, 200)
    ink = unit(shape, 1)
    mask = np.ones(shape, dtype=bool)
    moved = np.roll(ink, -an.SHIFT_CELLS, axis=1)
    moved[:, -an.SHIFT_CELLS :] = 1e3 * unit(shape, 5)[:, : an.SHIFT_CELLS]
    slid = an.slid_control(ink, moved, mask, mask)
    assert slid["right"] == pytest.approx(1.0)
    assert slid["left"] < 0.5 and slid["largest_absolute"] == pytest.approx(1.0)
    # only cells of the target mask are read
    part = mask.copy()
    part[:, 100:] = False
    garbage = moved.copy()
    garbage[:, 100 - an.SHIFT_CELLS : -an.SHIFT_CELLS] = 0.0
    assert an.slid_control(ink, garbage, part, mask)["right"] == pytest.approx(1.0)


def test_weak_agreement_fails_the_floor_even_when_it_beats_both_controls():
    shape = (400, 600)
    ink_here = unit(shape, 1)
    mixed = 0.42 * ink_here + unit(shape, 9)
    accepted, letters = frame(shape)
    result = an.agreement(
        four(ink_here, 2, 0.001),
        four(unit(shape, 7), 4, 0.001),
        four(mixed, 3, 0.001),
        accepted,
        letters,
    )
    assert 0.3 < result["r"] < an.P3_R
    assert result["r"] >= an.P3_RATIO * abs(result["control_wrong_side"])
    assert result["r"] >= an.P3_RATIO * result["control_slid"]["largest_absolute"]
    assert result["p3"] is False


def test_the_deciding_r_is_the_one_inside_the_letter_boxes():
    """Agreement everywhere except in the letters is not a reproduction of the letters."""
    shape = (400, 600)
    ink = unit(shape, 1)
    accepted, letters = frame(shape)
    ours = np.where(letters, unit(shape, 9), ink)
    result = an.agreement(
        four(ink, 2, 0.001),
        four(unit(shape, 7), 4, 0.001),
        four(ours, 3, 0.001),
        accepted,
        letters,
    )
    assert result["r_all_cells"] > an.P3_R
    assert abs(result["r"]) < 0.2 and result["p3"] is False


def test_agreement_refuses_a_verdict_when_the_letters_are_not_covered():
    shape = (120, 200)
    ink, blind = unit(shape, 1), unit(shape, 7)
    letters = np.zeros(shape, dtype=bool)
    letters[30:60, 40:90] = True
    accepted = np.ones(shape, dtype=bool)
    accepted[30:60, 40:70] = False  # 60% of the letter cells get nothing
    result = an.agreement(four(ink, 2), four(blind, 4), four(ink, 3), accepted, letters)
    assert result["letter_box_coverage"] == pytest.approx(0.4)
    assert result["evaluable"] is False and result["p3"] is None and result["r"] is None
    with pytest.raises(ValueError, match="no letter-box cells"):
        an.agreement(
            four(ink, 2), four(blind, 4), four(ink, 3), accepted, np.zeros(shape, bool)
        )


def test_the_ensemble_needs_exactly_the_four_models_and_some_variation():
    shape = (20, 20)
    mask = np.ones(shape, dtype=bool)
    maps = four(field(shape, 1), 2)
    assert an.zscore_ensemble(maps, mask)[mask].mean() == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError, match="four models"):
        an.zscore_ensemble({m: maps[m] for m in an.MODELS[:3]}, mask)
    flat = dict(maps, hecate=np.zeros(shape))
    with pytest.raises(ValueError, match="constant"):
        an.zscore_ensemble(flat, mask)


# --- decision table -------------------------------------------------------------------------------


def gate(fit_config="recipe", **exits):
    return {
        "fit_config": fit_config,
        "steps": {s: {"exit": exits.get(s, 0)} for s in an.GATE_STEPS},
    }


def final(ok47=True, ok48=True, picks=("w047", "w048")):
    good, bad = score(0.6, 0.9), score(12.8, 0.1)
    return {
        "published": {
            "w047": {"chosen": picks[0], "chosen_score": good if ok47 else bad},
            "w048": {"chosen": picks[1], "chosen_score": good if ok48 else bad},
        }
    }


def ink(p3=True, evaluable=True):
    return {"evaluable": evaluable, "p3": p3 if evaluable else None}


@pytest.mark.parametrize(
    ("final_record", "ink_record", "expected"),
    [
        (final(), ink(True), "REPRODUCED"),
        (final(), ink(False), "SAME_SHEETS_NO_LETTERS"),
        (final(), ink(evaluable=False), "SAME_SHEETS_NO_LETTERS"),
        (final(ok48=False), ink(True), "LETTERS_OFF_THE_PUBLISHED_WINDINGS"),
        (final(ok47=False), ink(False), "NOT_REPRODUCED"),
        (final(ok47=False, ok48=False), ink(evaluable=False), "NOT_REPRODUCED"),
    ],
)
def test_the_decision_table(final_record, ink_record, expected):
    assert an.verdict(gate(), final_record, ink_record)["verdict"] == expected
    reduced = an.verdict(gate("reduced"), final_record, ink_record)
    assert reduced["verdict"] == expected + "_WITH_REDUCED_FIT"


def test_a_failed_step_gives_does_not_run_and_no_other_verdict():
    for step in an.GATE_STEPS:
        result = an.verdict(gate(**{step: 1}), final(), ink(True))
        assert result == {
            "verdict": "DOES_NOT_RUN",
            "failed_steps": [step],
            "fit_config": "recipe",
        }
    # the records of a run that did not finish are not needed and not read
    assert an.verdict(gate(fit=137), None, None)["verdict"] == "DOES_NOT_RUN"


def test_partial_records_are_refused():
    partial = gate()
    del partial["steps"]["flatten"]
    with pytest.raises(ValueError, match="lacks steps"):
        an.verdict(partial, final(), ink())
    with pytest.raises(ValueError, match="fit_config"):
        an.verdict({"steps": gate()["steps"]}, final(), ink())
    with pytest.raises(ValueError, match="both required"):
        an.verdict(gate(), final(), None)
    with pytest.raises(ValueError, match="both required"):
        an.verdict(gate(), None, ink())
    one = final()
    del one["published"]["w048"]
    with pytest.raises(ValueError, match="both published"):
        an.verdict(gate(), one, ink())


def test_a_published_winding_with_no_eligible_candidate_fails_p1():
    record = final()
    record["published"]["w048"] = {"chosen": None, "chosen_score": None}
    result = an.verdict(gate(), record, ink(True))
    assert result["p1"] == {"w047": True, "w048": False}
    assert result["p2_consecutive"] is None
    assert result["verdict"] == "LETTERS_OFF_THE_PUBLISHED_WINDINGS"


# --- orientation ------------------------------------------------------------------------------------


def test_the_distance_record_says_which_way_the_normals_point():
    a, a_valid = cylinder(1000.0)
    b, b_valid = cylinder(1000.0, theta0=0.01)
    assert an.surface_distance(a, a_valid, b, b_valid)["normal_cosine_median"] > 0.99
    back = b[:, ::-1].copy()
    turned = an.surface_distance(a, a_valid, back, b_valid)
    assert turned["normal_cosine_median"] < -0.99
    assert turned["median"] == pytest.approx(
        0.0, abs=0.05
    )  # the distance does not care
    nothing = an.surface_distance(a, a_valid, b, np.zeros_like(b_valid))
    assert nothing["normal_cosine_median"] is None


def select_record(tmp_path, reverse=(False, False)):
    published, candidates = {}, []
    for k, (name, radius) in enumerate((("w047", 1000.0), ("w048", 1013.0))):
        xyz, valid = cylinder(radius)
        write_tifxyz(tmp_path / f"pub_{name}.tifxyz", xyz, valid)
        published[name] = str(tmp_path / f"pub_{name}.tifxyz")
        ours = xyz[:, ::-1].copy() if reverse[k] else xyz
        write_tifxyz(tmp_path / f"{name}.tifxyz", ours, valid)
        candidates.append(str(tmp_path / f"{name}.tifxyz"))
    return an.select(published, candidates)


def test_orientation_is_the_sign_shared_by_every_published_winding_it_lies_along(
    tmp_path, capsys
):
    record = select_record(tmp_path / "same")
    assert an.orientation(record, "w047.tifxyz") > 0.99
    assert an.orientation(record, "w048.tifxyz") > 0.99
    turned = select_record(tmp_path / "turned", reverse=(False, True))
    assert an.orientation(turned, "w047.tifxyz") > 0.99
    assert an.orientation(turned, "w048.tifxyz") < -0.99
    (tmp_path / "final.json").write_text(json.dumps(turned))
    assert an.main(["orientation", str(tmp_path / "final.json"), "w048.tifxyz"]) == 0
    assert capsys.readouterr().out.startswith("-")


def test_orientation_refuses_a_winding_with_no_single_answer(tmp_path):
    record = select_record(tmp_path)
    record["published"]["w048"]["scores"]["w047.tifxyz"]["normal_cosine_median"] = -0.9
    with pytest.raises(ValueError, match="no single orientation"):
        an.orientation(record, "w047.tifxyz")
    for entry in record["published"].values():
        entry["scores"]["w048.tifxyz"]["normal_cosine_median"] = None
    with pytest.raises(ValueError, match="no single orientation"):
        an.orientation(record, "w048.tifxyz")
    with pytest.raises(ValueError, match="no single orientation"):
        an.orientation(record, "w999.tifxyz")


# --- the gate record, from the files the run scripts write -------------------------------------------


def gate_dir(tmp_path, windings=("w047", "w048"), **exits):
    folder = tmp_path / "gate_recipe"
    folder.mkdir(parents=True)
    names = ["distance_field", "fit", "snap"]
    names += [f"{step}_{w}" for step in an.PER_WINDING_STEPS for w in windings]
    for name in names:
        if exits.get(name, 0) is None:
            continue
        record = {"exit": exits.get(name, 0), "seconds": 5}
        (folder / f"{name}.json").write_text(json.dumps(record))
    return folder


def test_the_gate_is_assembled_from_one_file_per_step_and_winding(tmp_path):
    record = an.assemble_gate(gate_dir(tmp_path), "recipe", ["w047", "w048"])
    assert set(record["steps"]) == set(an.GATE_STEPS)
    assert all(step["exit"] == 0 for step in record["steps"].values())
    assert set(record["steps"]["render"]["windings"]) == {"w047", "w048"}
    assert an.verdict(record, final(), ink(True))["verdict"] == "REPRODUCED"


def test_a_step_that_failed_for_one_winding_failed(tmp_path):
    folder = gate_dir(tmp_path, flatten_w048=137, ink_w047=-9)
    record = an.assemble_gate(folder, "recipe", ["w047", "w048"])
    assert record["steps"]["flatten"]["exit"] == 137
    assert record["steps"]["ink"]["exit"] == 9
    result = an.verdict(record, final(), ink(True))
    assert result["verdict"] == "DOES_NOT_RUN"
    assert result["failed_steps"] == ["flatten", "ink"]


def test_a_step_with_no_record_did_not_run(tmp_path):
    folder = gate_dir(tmp_path, render_w048=None, fit=None)
    record = an.assemble_gate(folder, "reduced", ["w047", "w048"])
    assert record["steps"]["fit"] == {"exit": 1, "not_run": True}
    assert record["steps"]["render"]["exit"] == 1
    assert record["steps"]["render"]["windings"]["w048"] == {"exit": 1, "not_run": True}
    assert record["steps"]["render"]["windings"]["w047"]["exit"] == 0
    assert an.verdict(record, None, None)["failed_steps"] == ["fit", "render"]


def test_a_fit_with_no_winding_along_the_published_ones_ran_and_did_not_reproduce(
    tmp_path,
):
    folder = gate_dir(tmp_path, windings=())
    out = tmp_path / "gate.json"
    argv = ["gate", str(out), "--dir", str(folder), "--fit-config", "recipe"]
    assert an.main([*argv, "--windings"]) == 0
    record = json.loads(out.read_text())
    assert record["windings"] == []
    for step in ("snap", "flatten", "render", "ink"):
        assert record["steps"][step] == {"exit": 0, "nothing_to_do": True}
    none_chosen = {
        "published": {
            "w047": {"chosen": None, "chosen_score": None},
            "w048": {"chosen": None, "chosen_score": None},
        }
    }
    result = an.verdict(record, none_chosen, {"evaluable": False, "p3": False})
    assert result["verdict"] == "NOT_REPRODUCED"
    # but a fit that failed is still a run that did not run
    (folder / "fit.json").write_text(json.dumps({"exit": 1}))
    assert an.verdict(an.assemble_gate(folder, "recipe", []), None, None)["verdict"] == "DOES_NOT_RUN"  # fmt: skip


def test_the_gate_refuses_records_it_cannot_read(tmp_path):
    folder = gate_dir(tmp_path)
    with pytest.raises(ValueError, match="fit_config"):
        an.assemble_gate(folder, "smoke", ["w047"])
    (folder / "snap.json").write_text(json.dumps({"exit": "0"}))
    with pytest.raises(ValueError, match="no integer exit code"):
        an.assemble_gate(folder, "recipe", ["w047"])


# --- the whole comparison, from files ---------------------------------------------------------------


def write_side(
    root: Path, name: str, xyz, valid, cell_ink, empty_ct=None, blind_ink=None
):
    """A mesh, its 66-layer render (only the 4x level the script reads) and four reading-side maps; with
    `blind_ink`, the four blind-side maps as well."""
    import cv2
    import zarr

    write_tifxyz(root / f"{name}.tifxyz", xyz, valid)
    h, w = cell_ink.shape
    render = zarr.open(str(root / f"{name}_66.zarr"), mode="w")
    ct = np.full((66, h, w), 90, dtype=np.uint8)
    if empty_ct is not None:
        ct[40][empty_ct] = 0
    render.create_dataset("2", data=ct, chunks=(66, h, w))
    maps = root / f"{name}_maps"
    maps.mkdir()
    rng = np.random.default_rng(len(name))
    sides = [("_reverse", cell_ink)] + (
        [("", blind_ink)] if blind_ink is not None else []
    )
    for tag, values in sides:
        low, high = values.min(), values.max()
        for model in an.MODELS:
            p = (values - low) / (high - low) * 0.5 + 0.25
            p = np.clip(p + 0.005 * rng.standard_normal(p.shape), 0.0, 1.0)
            pixels = np.kron(p, np.ones((an.LATTICE, an.LATTICE)))
            if model == "hecate":
                small = cv2.resize(
                    pixels,
                    (int(pixels.shape[1] * 0.9), int(pixels.shape[0] * 0.9)),
                    interpolation=cv2.INTER_AREA,
                )
                cv2.imwrite(
                    str(maps / f"{name}_66__hecate__L66zc33.50{tag}.png"),
                    np.round(small * 255).astype(np.uint8),
                )
            else:
                cv2.imwrite(
                    str(maps / f"{name}_66__{model}__L66s26{tag}.tif"),
                    np.clip(64 + 128 * pixels, 0, 255).astype(np.uint8),
                )
    return [root / f"{name}.tifxyz", maps, root / f"{name}_66.zarr"]


def scene(tmp_path, reverse_columns=False, other_ink=False, blind_is_reading=False):
    rows, cols = 16, 24
    world = field((rows * 5 + 40, cols * 5 + 40), 4)  # ink on a 4-voxel world lattice
    pub_xyz, pub_valid = plane(rows, cols)
    pub_ink = world[: rows * 5, : cols * 5]
    empty = np.zeros(pub_ink.shape, dtype=bool)
    empty[60:, :8] = True
    blind = pub_ink if blind_is_reading else field(pub_ink.shape, 6)
    pub = write_side(
        tmp_path, "pub", pub_xyz, pub_valid, pub_ink, empty_ct=empty, blind_ink=blind
    )
    # ours: the same plane one voxel off the sheet, moved by (3, 2) world cells, in two overlapping pieces
    ours = []
    for name, col_cells in (("w047", 0), ("w048", 50)):
        x0 = 1000.0 + 4 * (2 + col_cells)
        xyz, valid = plane(rows, 14, x0=x0, z0=500.0 + 12.0, y0=2001.0)
        source = field(world.shape, 8) if other_ink else world
        ink_cells = source[3 : 3 + rows * 5, 2 + col_cells : 2 + col_cells + 14 * 5]
        if reverse_columns:
            # The canvas is 14 nodes wide but the mesh spans 13 steps, so the mirror image of cell j
            # is cell 64 - j (a quarter cell off, one voxel); cells past the last node are not used.
            mirrored = np.zeros_like(ink_cells)
            mirrored[:, :65] = ink_cells[:, 64::-1]
            xyz, ink_cells = xyz[:, ::-1].copy(), mirrored
        ours.append(write_side(tmp_path, name, xyz, valid, ink_cells))
    boxes = {"letters": [{"id": 1, "box": [80.0, 60.0, 240.0, 200.0]}]}
    (tmp_path / "boxes.json").write_text(json.dumps(boxes))
    argv = [
        str(tmp_path / "out.json"),
        "--published-mesh", str(pub[0]),
        "--published-maps", str(pub[1]),
        "--published-render", str(pub[2]),
        "--letter-boxes", str(tmp_path / "boxes.json"),
    ]  # fmt: skip
    for triple in ours:
        argv += ["--ours", *map(str, triple)]
    return argv, empty


def test_transfer_maps_finds_the_same_ink_through_the_scroll_positions(tmp_path):
    argv, empty = scene(tmp_path)
    assert tm.main(argv) == 0
    result = json.loads((tmp_path / "out.json").read_text())
    assert result["evaluable"] and result["p3"] is True and result["r"] > 0.9
    assert result["ours_depth"] == 1 and result["registered_comparison"] is True
    assert abs(result["control_wrong_side"]) < 0.3
    assert result["letter_box_coverage"] == 1.0
    assert [o["normal_cosine_median"] for o in result["ours"]] == [1.0, 1.0]
    assert all(o["cells_given"] > 1000 for o in result["ours"])
    assert result["transfer_distance_voxels"]["p50"] == pytest.approx(1.0)
    assert result["letter_boxes"][0]["id"] == 1 and result["letter_boxes"][0]["r"] > 0.9
    # blocks with an empty CT layer on the published render take no part
    assert result["published_cells"] < 75 * 115 - int(empty[:75].sum()) + 1
    assert result["cells_accepted"] <= result["published_cells"]


def test_transfer_maps_reports_other_ink_as_no_agreement(tmp_path):
    argv, _ = scene(tmp_path, other_ink=True)
    assert tm.main(argv) == 0
    result = json.loads((tmp_path / "out.json").read_text())
    assert result["evaluable"] and result["p3"] is False and abs(result["r"]) < 0.3


def test_transfer_maps_reads_the_published_blind_side_for_the_wrong_side_control(
    tmp_path,
):
    """With blind-side files that hold the reading-side ink, the control equals r and P3 cannot hold."""
    argv, _ = scene(tmp_path, blind_is_reading=True)
    assert tm.main(argv) == 0
    result = json.loads((tmp_path / "out.json").read_text())
    assert result["r"] > 0.9 and result["control_wrong_side"] > 0.9
    assert result["p3"] is False


def test_transfer_maps_stops_when_the_normals_point_the_other_way(tmp_path):
    argv, _ = scene(tmp_path, reverse_columns=True)
    with pytest.raises(SystemExit, match="does not sample along the published normals"):
        tm.main(argv)
    assert not (tmp_path / "out.json").exists()


def as_flipped(argv):
    return ["--ours-flipped" if a == "--ours" else a for a in argv]


def test_a_flipped_render_is_accepted_only_for_a_winding_whose_normals_are_opposite(
    tmp_path,
):
    argv, _ = scene(tmp_path, reverse_columns=True)
    assert tm.main(as_flipped(argv)) == 0
    result = json.loads((tmp_path / "out.json").read_text())
    assert result["p3"] is True and result["r"] > 0.9
    assert [o["normal_cosine_median"] for o in result["ours"]] == [-1.0, -1.0]
    assert [o["render_flipped"] for o in result["ours"]] == [True, True]


def test_a_flipped_render_of_a_winding_whose_normals_agree_is_refused(tmp_path):
    argv, _ = scene(tmp_path / "same")
    with pytest.raises(SystemExit, match="does not sample along the published normals"):
        tm.main(as_flipped(argv))
    with pytest.raises(SystemExit):
        tm.main(argv[:9])  # no winding of ours at all


def test_the_map_names_are_the_depth_plus_one_reading_side_files():
    maps = Path("/m")
    assert tm.map_file(maps, "x_66", "hecate").name == "x_66__hecate__L66zc33.50_reverse.png"  # fmt: skip
    assert tm.map_file(maps, "x_66", "dnative").name == "x_66__dnative__L66s26_reverse.tif"  # fmt: skip
    assert (
        tm.map_file(maps, "x_66", "hecate", False).name
        == "x_66__hecate__L66zc33.50.png"
    )
    assert (
        tm.map_file(maps, "x_66", "dnative", False).name == "x_66__dnative__L66s26.tif"
    )
    assert tm.map_file(maps, "x_66", "hecate", depth=3).name == "x_66__hecate__L66zc35.50_reverse.png"  # fmt: skip
    assert tm.map_file(maps, "x_66", "dnative", depth=3).name == "x_66__dnative__L66s28_reverse.tif"  # fmt: skip


def test_a_comparison_at_another_depth_is_marked_as_not_the_registered_one(tmp_path):
    argv, _ = scene(tmp_path)
    for model in an.MODELS:
        for name in ("w047", "w048"):
            source = tm.map_file(tmp_path / f"{name}_maps", f"{name}_66", model)
            source.rename(tm.map_file(source.parent, f"{name}_66", model, depth=3))
    with pytest.raises(SystemExit, match="cannot read"):
        tm.main(argv)
    assert tm.main([*argv, "--ours-depth", "3"]) == 0
    result = json.loads((tmp_path / "out.json").read_text())
    assert result["ours_depth"] == 3 and result["registered_comparison"] is False
    assert result["r"] > 0.9


# --- the chunks the snap reads ----------------------------------------------------------------------

sc = load("snap_chunks")
s3_fetch = load("s3_fetch")
s3_plan = load("s3_plan")
NAME = "surface.zarr"
PREFIX = f"Scroll/predictions/{NAME}"


def test_needed_chunks_cover_everything_within_reach_of_a_node():
    shape, chunks = (1000, 1000, 1000), (192, 192, 192)
    middle = np.array([[100.0, 100.0, 100.0]])
    assert sc.needed_chunks(middle, shape, chunks, 16.0) == {(0, 0, 0)}
    near_a_face = np.array(
        [[180.0, 100.0, 100.0]]
    )  # 180 + 16 = 196 is in the next chunk along z
    assert sc.needed_chunks(near_a_face, shape, chunks, 16.0) == {(0, 0, 0), (1, 0, 0)}
    assert sc.needed_chunks(near_a_face, shape, chunks, 11.0) == {(0, 0, 0)}
    corner = np.array([[190.0, 190.0, 190.0]])
    assert len(sc.needed_chunks(corner, shape, chunks, 16.0)) == 8
    edge = np.array([[995.0, 5.0, 5.0]])  # nothing lies outside the array
    assert sc.needed_chunks(edge, shape, chunks, 16.0) == {(5, 0, 0)}
    with pytest.raises(ValueError, match="half a chunk"):
        sc.needed_chunks(middle, shape, chunks, 96.0)


def test_the_windings_file_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "windings.txt"
    path.write_text("# chosen by geometry\nw047\n\n  w048  \n")
    assert sc.read_windings(path) == ["w047", "w048"]


def test_listed_and_unlisted_chunks_are_told_apart():
    needed = {(0, 0, 0), (0, 0, 1)}
    present, absent = sc.classify(needed, {f"{PREFIX}/0/0/0/1": 77, "other": 1}, PREFIX)
    assert present == {f"{PREFIX}/0/0/0/1": 77}
    assert absent == [f"{PREFIX}/0/0/0/0"]


def snap_scene(tmp_path):
    """Two small windings in chunk (1,0,0) of a 192-chunked array. Their nodes stop at x = 180, so only
    the snap's reach of 16 voxels takes them into chunk (1,0,1); each has one node that does not exist,
    stored as -1, which would add chunk (0,0,0) if it were read as a position."""
    meshes = tmp_path / "meshes"
    for name, y0 in (("w047", 100.0), ("w048", 113.0)):
        xyz, valid = plane(4, 4, x0=120.0, y0=y0, z0=300.0)
        valid[0, 0] = False
        write_tifxyz(meshes / name, xyz, valid)
    (tmp_path / "windings.txt").write_text("w047\nw048\n")
    surf = tmp_path / "local" / NAME
    (surf / "0").mkdir(parents=True)
    meta = {"shape": [600, 600, 600], "chunks": [192, 192, 192], "dimension_separator": "/", "fill_value": 0}  # fmt: skip
    (surf / "0" / ".zarray").write_text(json.dumps(meta))
    manifest = tmp_path / "work" / "manifest.json"
    argv = [str(meshes), str(tmp_path / "windings.txt"), str(surf), PREFIX, str(manifest)]  # fmt: skip
    return argv, surf, manifest


def fake_bucket(monkeypatch, listed, fail=()):
    """Stand in for the bucket: `listed` is key -> bytes; keys in `fail` cannot be fetched."""
    calls = []

    def list_prefix(prefix):
        calls.append(prefix)
        return [(k, len(v)) for k, v in listed.items() if k.startswith(prefix)]

    def fetch(dest, strip, key, size):
        if key.endswith(".zarray"):
            return "kept", 0
        if key in fail:
            return "failed: boom", 0
        path = Path(s3_fetch.target(dest, strip, key))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(listed[key])
        return "got", len(listed[key])

    monkeypatch.setattr(s3_plan, "list_prefix", list_prefix)
    monkeypatch.setattr(s3_fetch, "fetch", fetch)
    return calls


def test_snap_chunks_fetches_what_is_listed_and_records_what_the_bucket_lacks(
    tmp_path, monkeypatch
):
    argv, surf, manifest_path = snap_scene(tmp_path)
    listed = {f"{PREFIX}/0/1/0/0": b"abc", f"{PREFIX}/0/1/1/1": b"not needed"}
    calls = fake_bucket(monkeypatch, listed)
    assert sc.main(argv) == 0
    assert calls == [f"{PREFIX}/0/1/"]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["needed"] == 2 and manifest["complete"] is True
    assert manifest["fetched"] == {f"{PREFIX}/0/1/0/0": 3}
    assert manifest["absent_in_bucket"] == [f"{PREFIX}/0/1/0/1"]
    assert (surf / "0/1/0/0").read_bytes() == b"abc"
    assert not (surf / "0/1/1/1").exists()
    # the check before the snap needs no network and passes on exactly this state
    monkeypatch.setattr(s3_plan, "list_prefix", None)
    monkeypatch.setattr(s3_fetch, "fetch", None)
    assert sc.main([*argv, "--offline"]) == 0


def test_a_chunk_that_could_not_be_fetched_fails_the_step(tmp_path, monkeypatch):
    argv, surf, manifest_path = snap_scene(tmp_path)
    key = f"{PREFIX}/0/1/0/0"
    fake_bucket(monkeypatch, {key: b"abc"}, fail={key})
    assert sc.main(argv) == 1
    assert json.loads(manifest_path.read_text())["complete"] is False
    assert sc.main([*argv, "--offline"]) == 1


def test_the_offline_check_catches_a_lost_or_cut_chunk_and_a_changed_winding_list(
    tmp_path, monkeypatch
):
    argv, surf, manifest_path = snap_scene(tmp_path)
    key = f"{PREFIX}/0/1/0/0"
    fake_bucket(monkeypatch, {key: b"abc"})
    assert sc.main(argv) == 0
    chunk = surf / "0/1/0/0"
    chunk.write_bytes(b"ab")
    assert sc.main([*argv, "--offline"]) == 1
    chunk.unlink()
    assert sc.main([*argv, "--offline"]) == 1
    chunk.write_bytes(b"abc")
    assert sc.main([*argv, "--offline"]) == 0
    # a winding that reaches a chunk the manifest never looked at: zeros there would be unexamined
    xyz, valid = plane(4, 4, x0=120.0, y0=300.0, z0=300.0)
    write_tifxyz(tmp_path / "meshes" / "w049", xyz, valid)
    (tmp_path / "windings.txt").write_text("w047\nw048\nw049\n")
    assert sc.main([*argv, "--offline"]) == 1


def test_snap_chunks_refuses_an_array_whose_missing_chunks_are_not_zeros(
    tmp_path, monkeypatch
):
    argv, surf, _ = snap_scene(tmp_path)
    fake_bucket(monkeypatch, {})
    meta = json.loads((surf / "0/.zarray").read_text())
    (surf / "0/.zarray").write_text(json.dumps({**meta, "fill_value": 255}))
    with pytest.raises(SystemExit, match="fill value of 0"):
        sc.main(argv)
    (surf / "0/.zarray").write_text(json.dumps(meta))
    with pytest.raises(SystemExit, match="same name"):
        sc.main([*argv[:3], "Scroll/predictions/other.zarr", argv[4]])
    xyz, valid = plane(4, 4)
    write_tifxyz(tmp_path / "meshes" / "w050", xyz, np.zeros_like(valid))
    (tmp_path / "windings.txt").write_text("w050\n")
    with pytest.raises(SystemExit, match="has no nodes"):
        sc.main(argv)


def test_the_run_scripts_parse():
    import subprocess

    scripts = sorted(STEP.glob("*.sh"))
    assert len(scripts) >= 9
    for script in scripts:
        subprocess.run(["bash", "-n", str(script)], check=True)
