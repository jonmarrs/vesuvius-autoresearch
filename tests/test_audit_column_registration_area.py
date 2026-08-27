"""Tests for the external area audit of the column registration.

The audit corroborates a registration we publish, so the tests pin the things
that would make a corroboration hollow: a unit conversion that quietly cancels,
a comparison against a number that is not actually external, and the claim that
area constrains scale tightly.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import audit_column_registration_area as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_target = pytest.mark.skipif(
    not os.path.isdir(mod.TARGET), reason="scrollgt column target not present"
)
ARTIFACT = os.path.join(_REPO, "reports", "column_registration_area.txt")


@needs_target
def test_the_grid_pixel_size_comes_from_the_scan_not_the_fit():
    """The whole point of the audit. 2.399 um is in the volume's own name and the
    0.05 is the grid scale; neither was fitted, so the conversion is external."""
    meta, _, _, _ = mod.load()
    assert float(meta["geometry"]["scale"]) == 0.05
    assert mod.um_per_grid_px(meta) == pytest.approx(47.98, abs=0.01)


@needs_target
def test_the_column_count_matches_the_publication():
    """A count that disagreed would sink the area comparison before it started."""
    _, cols, _, _ = mod.load()
    assert len(cols["columns"]) == mod.PUBLISHED_COLUMNS


@needs_target
def test_the_area_lands_near_the_published_figure():
    """The result. Loose bound rather than the measured 1.01x, so this fails on a
    real regression rather than on resampling noise."""
    meta, cols, valid, _ = mod.load()
    a = mod.areas(meta, cols, valid)
    ratio = a["in_columns_cm2"] / mod.PUBLISHED_CM2
    assert 0.9 < ratio < 1.1, f"area ratio {ratio:.2f} has moved"


@needs_target
def test_the_column_area_is_a_subset_of_the_grid_area():
    """Sanity on the sum: the columns cannot enclose more valid papyrus than the
    grid contains, and should not enclose all of it either."""
    meta, cols, valid, _ = mod.load()
    a = mod.areas(meta, cols, valid)
    assert a["in_columns_cm2"] < a["whole_grid_cm2"]
    assert a["in_columns_cm2"] > 0.5 * a["whole_grid_cm2"]


def test_the_artifact_states_the_constraint_is_quadratic():
    """Why 1% agreement is evidence rather than coincidence."""
    text = open(ARTIFACT).read()
    assert "quadratic in the scale" in text


def test_the_artifact_admits_it_was_not_pre_registered():
    """It was computed to see whether the numbers were plausible. Saying so is the
    difference between a check and a threshold chosen after the answer."""
    text = open(ARTIFACT).read()
    assert "not pre-registered" in text


def test_the_artifact_disclaims_per_column_accuracy():
    """An area agreement is compatible with individual edges off in compensating
    directions, and two columns are already flagged as spanning strip-crop gaps."""
    text = open(ARTIFACT).read()
    assert "does not establish: per-column boundary accuracy" in text.lower()
