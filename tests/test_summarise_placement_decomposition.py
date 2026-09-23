"""The pair classifier behind the fit-vs-layout placement split."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarise_placement_decomposition import category  # noqa: E402


def test_same_seed_across_flatten_modes_is_layout_only():
    assert category("outer_curbase_s4", "detfit_s4").endswith("(layout only)")


def test_different_seeds_are_fit_pairs_in_every_mode():
    assert (
        category("outer_curbase_s4", "outer_curbase_s5")
        == "different fits, both stock flatten"
    )
    assert (
        category("detfit_s4", "detfit_s9")
        == "different fits, both deterministic flatten"
    )
    assert (
        category("detfit_s4", "outer_curbase_s5")
        == "different fits, deterministic vs stock"
    )


def test_named_pairs_and_unrelated_pairs():
    assert (
        category("radial_work_rad0", "flat_study_probe") == "control: identical strips"
    )
    assert category("radial_work_rad0b", "radial_work_rad0").startswith("same meshes")
    assert category("radial_work_rad0", "detfit_s4") is None
