"""Tests for the proposed fix.

This is the one artifact in the series that claims something WORKS rather than
that something is broken, so the tests are aimed at the ways a working detector
can be fake: one that fires on everything, one that fires on nothing, and one
that disagrees with the metric it is supposed to be checking.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import winding_disagreement_check as mod  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

ARTIFACT = os.path.join(_REPO, "reports", "winding_disagreement_check.txt")
DR = 12.81


def _patch(winding, scatter=0.0, seed=0, n=64):
    rng = np.random.default_rng(seed)
    thetas = np.linspace(0.30, 1.30, n)
    radii = winding * DR + thetas / (2 * np.pi) * DR
    if scatter:
        radii = radii + rng.normal(0.0, scatter, size=radii.shape)
    return radii, thetas


def test_it_agrees_when_the_patch_is_where_it_belongs():
    """A detector that fires on everything is useless."""
    for w in (3, 5, 12):
        radii, thetas = _patch(w)
        assert mod.disagreement(radii, thetas, DR, w) == 0


def test_it_fires_by_exactly_the_number_of_windings_displaced():
    """And reports the magnitude, not just a boolean, since a fit that is one wrap
    out is a different problem from one that is twenty out."""
    for offset in (1, 2, 5, 23):
        radii, thetas = _patch(5 + offset)
        assert mod.disagreement(radii, thetas, DR, 5) == offset


def test_it_does_not_fire_on_noise_alone():
    """The failure that would make it unusable in practice: a patch in the right
    place with realistic scatter must not be reported as misplaced."""
    for seed in range(8):
        radii, thetas = _patch(5, scatter=2.0, seed=seed)
        assert mod.disagreement(radii, thetas, DR, 5) == 0


def test_it_reproduces_villa_arithmetic_rather_than_rounding():
    """The detector must snap the way the metric snaps. Swept over the range a real
    patch can occupy, villa's form and round() agree everywhere EXCEPT at exact
    half-winding ties, and there villa's outcome is set by floating-point residue
    rather than by a rule -- it is not simply 'rounds up', which an earlier version
    of this docstring claimed. Using round() would invent disagreements at the
    boundary, which is precisely what this tool exists to distinguish."""
    disagreements = []
    for w in range(0, 60):
        for frac in np.linspace(-0.5, 0.5, 401):
            med = (w + frac) * DR
            villa = int(round(float(mod.snapped_target(med, DR)) / DR))
            plain = int(round(med / DR))
            if villa != plain:
                disagreements.append(frac)
    assert disagreements, "no disagreement found; the distinction would be moot"
    assert all(abs(abs(f) - 0.5) < 1e-9 for f in disagreements), (
        "villa and round() differ somewhere other than an exact tie"
    )


def test_the_shifted_radius_is_flat_along_a_winding():
    """The premise that makes a median meaningful: a point's shifted radius does not
    depend on where it sits around the turn."""
    radii, thetas = _patch(7)
    sr = mod.shifted_radius(radii, thetas, DR)
    assert float(np.ptp(sr)) < 1e-9
    assert float(np.median(sr)) == pytest.approx(7 * DR)


def test_the_artifact_scores_with_villa_rather_than_asserting():
    """The demonstration's left-hand column must come from villa's own function. An
    earlier version asserted 'every row scores identically' in prose."""
    text = open(ARTIFACT).read()
    assert "scored by its own unmodified function, not asserted" in text
    assert "IDENTICAL (spread 0.00e+00)" in text


def test_the_artifact_keeps_the_end_to_end_limit():
    """It has never been run against a real annotated patch, because none is
    published. If that caveat goes, the demonstration overclaims."""
    text = open(ARTIFACT).read()
    assert "cannot be validated end to end" in text
    assert "no fitted spiral checkpoint is" in text
