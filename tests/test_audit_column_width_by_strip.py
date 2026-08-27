"""Tests for the per-strip width audit.

This one contradicts a claim in our own registration report, so the tests guard
against the ways a false accusation could be manufactured: letting the flagged
columns drive it, mislabelling which strip a column belongs to, or reporting a
step that a permutation test would call chance.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import audit_column_width_by_strip as mod  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_target = pytest.mark.skipif(
    not os.path.isdir(mod.TARGET), reason="scrollgt column target not present"
)
ARTIFACT = os.path.join(_REPO, "reports", "column_width_by_strip.txt")


@needs_target
def test_the_flagged_columns_are_excluded():
    """Cols 9 and 16 span strip crops with +/-250 grid px of slack, and col 1 sits
    at the grid edge. Letting the three most suspect measurements decide a verdict
    about measurement error would be circular."""
    rows, _ = mod.load()
    assert {r["col"] for r in rows}.isdisjoint({1, 9, 16})
    assert len(rows) == 19


@needs_target
def test_strip_assignment_matches_the_published_tiling():
    """The registration report says the strips tile 1-8 / 9-16 / 17-22. Getting a
    boundary wrong would invent a step or hide one."""
    assert mod.strip_of(8) == 1
    assert mod.strip_of(10) == 2
    assert mod.strip_of(15) == 2
    assert mod.strip_of(17) == 3
    assert mod.strip_of(22) == 3


@needs_target
def test_within_strip_spread_is_small_against_the_between_strip_step():
    """What makes it a step rather than noise: each strip is internally tight."""
    rows, _ = mod.load()
    w = np.array([r["width_mm"] for r in rows])
    col = np.array([r["col"] for r in rows])
    strip = np.array([mod.strip_of(c) for c in col])
    within = max(w[strip == s].std() for s in (1, 2, 3))
    between = w[strip == 3].mean() - w[strip == 1].mean()
    assert between > 4 * within, (
        f"between-strip step {between:.1f} mm is not large against "
        f"within-strip spread {within:.1f} mm"
    )


@needs_target
def test_the_step_model_beats_the_trend_model():
    """A physical drift along the roll predicts a trend. If the trend fitted at
    least as well, the finding would not stand."""
    rows, _ = mod.load()
    w = np.array([r["width_mm"] for r in rows])
    col = np.array([r["col"] for r in rows])
    strip = np.array([mod.strip_of(c) for c in col])
    step = np.zeros_like(w)
    for s in (1, 2, 3):
        step[strip == s] = w[strip == s].mean()
    lin = np.polyval(np.polyfit(col, w, 1), col)
    assert float(((w - step) ** 2).sum()) < float(((w - lin) ** 2).sum())


def test_the_artifact_reports_a_permutation_p_value():
    """A step you can see by eye still needs a null. The artifact must carry one."""
    text = open(ARTIFACT).read()
    assert "permutation test" in text
    assert "p = 0.0000" in text


def test_the_artifact_does_not_overturn_the_area_audit():
    """The two results coexist: compensating per-strip errors preserve total length
    and barely move total area, so the global check remains valid."""
    text = open(ARTIFACT).read()
    assert "does not overturn the area audit" in text


def test_the_artifact_keeps_its_own_limits():
    """It detects a discrepancy BETWEEN strips, not an absolute error common to
    all three, and cannot rule out a coincidence at the crop boundary."""
    text = open(ARTIFACT).read()
    assert "not an absolute error common to all three" in text
