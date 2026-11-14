"""Finding 113's rules as code: the choice of windings, the stacked check, the tiles and the mark table."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/eligible_band"
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-14_first_letters_0211_ink_read.md"
).read_text()


def _load(name):
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", HERE / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cw, st, sm, bt = (
    _load(n) for n in ("choose_windings", "stacked_check", "score_marks", "blind_tiles")
)


def test_one_winding_is_chosen_from_each_quarter_of_those_at_the_minimum():
    windings = {f"w{i:03d}": {"excess": 0.05 + 0.01 * (i % 7)} for i in range(10, 50)}
    windings["w050"] = None
    good = [n for n, w in windings.items() if w and w["excess"] >= 0.07]
    chosen = cw.choose(windings)
    assert len(chosen) == 4 and chosen == sorted(chosen)
    size = -(-len(good) // 4)
    for k, name in enumerate(chosen):
        group = good[k * size : (k + 1) * size]
        assert name in group
        assert windings[name]["excess"] == max(windings[n]["excess"] for n in group)
    assert cw.choose({"w010": {"excess": 0.01}}) == []


def test_neighbours_are_snapped_with_the_chosen_where_the_fit_wrote_them():
    windings = {f"w{i:03d}": {"excess": 0.1} for i in range(10, 20)}
    assert cw.with_neighbours(["w010", "w015"], windings) == [
        "w010",
        "w011",
        "w014",
        "w015",
        "w016",
    ]


def test_of_two_chosen_windings_stacked_on_each_other_the_lower_excess_one_is_dropped():
    assert st.is_stacked(0.30) and not st.is_stacked(0.299)
    excess = {"w020": 0.2, "w021": 0.1, "w040": 0.3}
    chosen = ["w020", "w021", "w040"]
    assert st.keep(chosen, {"w020": ["w021"]}, excess) == ["w020", "w040"]
    assert st.keep(chosen, {"w021": ["w020"], "w020": ["w021"]}, excess) == [
        "w020",
        "w040",
    ]
    assert st.keep(chosen, {"w040": ["w039"]}, excess) == chosen


def _counts(strips, marked, letters=0):
    return {"strips": strips, "marked": marked, "letters": letters}


def test_the_mark_table_is_the_registered_one():
    good = {"reading": _counts(12, 9), "other": _counts(12, 3)}
    target = lambda r, o: {"reading": r, "other": o}  # noqa: E731
    assert (
        sm.verdict(target(_counts(32, 20, 3), _counts(32, 5, 2)), good)["verdict"]
        == "LETTER_CANDIDATES"
    )
    assert (
        sm.verdict(target(_counts(32, 20, 3), _counts(32, 5, 3)), good)["verdict"]
        == "STROKES"
    )
    assert (
        sm.verdict(target(_counts(32, 20, 2), _counts(32, 5)), good)["verdict"]
        == "STROKES"
    )
    assert (
        sm.verdict(target(_counts(32, 8), _counts(32, 5)), good)["verdict"]
        == "NOTHING_SEEN"
    )
    lost = sm.verdict(target(_counts(32, 5), _counts(32, 20)), good)
    assert lost["verdict"] == "NOTHING_SEEN" and lost["other_side_wins"]
    for anchors in (
        {"reading": _counts(12, 8), "other": _counts(12, 0)},
        {"reading": _counts(12, 12), "other": _counts(12, 4)},
    ):
        assert (
            sm.verdict(target(_counts(32, 20, 5), _counts(32, 0)), anchors)["verdict"]
            == "READER_NOT_CALIBRATED"
        )


def test_fisher_matches_a_table_worked_by_hand():
    # 3 of 3 against 0 of 3: one arrangement in C(6, 3) = 20
    assert sm.fisher_one_sided(3, 0, 0, 3) == 1 / 20
    assert sm.fisher_one_sided(0, 3, 3, 0) == 1.0
    assert abs(sm.fisher_one_sided(2, 1, 1, 2) - 10 / 20) < 1e-12


def test_tiles_need_ct_and_do_not_overlap():
    ok = np.ones((200, 300), bool)
    ok[:96, 96:192] = False
    origins = bt.tile_origins(ok)
    assert (0, 96) not in origins and (0, 0) in origins and (96, 96) in origins
    assert all(r % 96 == 0 and c % 96 == 0 for r, c in origins) and len(origins) == 5


def test_four_tiles_by_score_and_four_at_random_from_the_rest():
    scores = {(0, 96 * i): float(i) for i in range(20)}
    picked = bt.pick(scores, np.random.default_rng(0))
    top = {o for o, how in picked.items() if how == "top"}
    assert top == {(0, 96 * i) for i in (16, 17, 18, 19)}
    assert sum(how == "random" for how in picked.values()) == 4 and len(picked) == 8
    assert bt.pick(scores, np.random.default_rng(0)) == picked


def test_the_tile_score_treats_the_sides_alike():
    rng = np.random.default_rng(1)
    ok = np.ones((96, 192), bool)
    loud, quiet = rng.normal(0, 3, ok.shape), rng.normal(0, 1, ok.shape)
    one = bt.tile_scores({"reading": [loud], "other": [quiet]}, ok, [(0, 0)])
    two = bt.tile_scores({"reading": [quiet], "other": [loud]}, ok, [(0, 0)])
    assert one == two


def test_anchors_are_tiles_with_labelled_ink():
    ok = np.ones((96, 480), bool)
    scored = np.zeros_like(ok)
    scored[:, :240] = True
    ink = np.zeros_like(ok)
    ink[:, :96] = True
    origins = bt.anchor_origins(ok, scored, ink, np.random.default_rng(0))
    assert origins and all(c <= 48 for _, c in origins)


def test_a_strip_is_dark_where_the_ensemble_is_high_and_numbers_are_a_permutation():
    low, high = np.zeros((4, 4)), np.ones((4, 4))
    image = bt.strip([low, high], 0.0, 1.0)
    assert image.shape == (4, 4 + bt.GAP + 4)
    assert image[0, 0] == 255 and image[0, -1] == 0 and image[0, 4] == 255
    numbers = bt.shuffled_numbers(10, np.random.default_rng(0))
    assert sorted(numbers) == [f"{i:03d}" for i in range(1, 11)] and numbers != sorted(
        numbers
    )


def test_the_constants_are_the_registrations():
    assert "excess at 0.07 or above" in REGISTRATION and cw.MINIMUM == 0.07
    assert "four groups of equal size" in REGISTRATION and cw.GROUPS == 4
    assert "at least 30% of its\n   nodes lie within 2 voxels" in REGISTRATION
    assert st.STACKED_SHARE == 0.30 and st.WITHIN == "2"
    assert "tiles of 96 lattice cells" in REGISTRATION and bt.TILE == 96
    assert "at least 90% of their cells" in REGISTRATION and bt.CT_MIN == 0.90
    assert (
        "the four with\n     the highest score and four drawn at random from the rest (seed 113)"
        in REGISTRATION
    )
    assert (bt.TOP, bt.RANDOM, bt.SEED, bt.ANCHORS) == (4, 4, 113, 12)
    assert (
        "at least 10% of their scored cells ink" in REGISTRATION
        and bt.ANCHOR_INK_MIN == 0.10
    )
    assert "at least 70% of the anchors' reading-side strips" in REGISTRATION
    assert (sm.ANCHOR_READING_MIN, sm.ANCHOR_OTHER_MAX) == (0.70, 0.30)
    assert "at least three PHerc. 0211 reading-side strips are marked 2" in REGISTRATION
    assert (
        sm.LETTER_STRIPS_MIN == 3
        and "p below 0.05" in REGISTRATION
        and sm.P_MAX == 0.05
    )
    assert "The reading side is `_reverse`" in REGISTRATION and bt.SIDES == {
        "reading": True,
        "other": False,
    }
