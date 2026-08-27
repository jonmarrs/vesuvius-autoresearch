"""Tests for the cross-estimator consistency check.

This probe returns a result that FAVOURS a figure I already published, which is
the direction that earns the most scepticism in this series. So the tests here
are aimed at the ways a favourable answer could be manufactured: a band widened
after the fact, two estimators that are not actually different, a correction
that secretly shares information between them, and a decision rule that cannot
return the unfavourable verdict.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_cross_estimator_consistency as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")

ARTIFACT = os.path.join(_REPO, "reports", "cross_estimator_consistency.txt")


def test_the_band_is_the_one_that_was_pre_registered():
    """A pre-registered rule is only worth anything if it cannot be edited after
    the result is known. The commit message fixes it at [0.80, 1.25]; if this
    ever fails, the band moved and the preregistration is void."""
    assert mod.BAND == (0.80, 1.25)


def test_the_two_estimators_are_actually_different():
    """The premise. If the plane and quadratic fits were near-identical, their
    agreement after correction would be trivially guaranteed and the probe would
    be measuring nothing."""
    assert mod.ORDERS == {"plane": 1, "quadratic": 2}


@needs_data
def test_the_attenuations_differ_by_a_large_factor():
    """The same premise, measured rather than assumed: the correction being
    applied to each estimator must be substantially different, or agreement
    afterwards is not evidence about the correction."""
    old_rms, old_n = mod.INJECT_RMS, mod.N_SAMPLES
    mod.INJECT_RMS, mod.N_SAMPLES = [1.0], 20
    try:
        _, k_plane = mod.refit(1, 1.45, 1.05, seed=1)
        _, k_quad = mod.refit(2, 1.45, 1.05, seed=1)
    finally:
        mod.INJECT_RMS, mod.N_SAMPLES = old_rms, old_n
    assert k_plane > 2 * k_quad


@needs_data
def test_the_floors_differ_by_an_order_of_magnitude():
    """Second half of the same premise. A shared floor would make the two
    corrections more alike than they look."""
    old_rms, old_n = mod.INJECT_RMS, mod.N_SAMPLES
    mod.INJECT_RMS, mod.N_SAMPLES = [1.0], 20
    try:
        floor_plane, _ = mod.refit(1, 1.45, 1.05, seed=1)
        floor_quad, _ = mod.refit(2, 1.45, 1.05, seed=1)
    finally:
        mod.INJECT_RMS, mod.N_SAMPLES = old_rms, old_n
    assert floor_plane > 10 * floor_quad


def test_the_correction_shares_nothing_between_estimators():
    """Independence guard. `corrected` must be a function of one estimator's own
    reported value, floor and k. If it could see the other estimator, agreement
    would be built in rather than measured."""
    import inspect

    src = inspect.getsource(mod.corrected)
    for forbidden in ("plane", "quadratic", "ORDERS", "ratio"):
        assert forbidden not in src
    assert mod.corrected(2.0, 0.0, 1.0) == pytest.approx(2.0)
    assert mod.corrected(2.0, 0.0, 0.5) == pytest.approx(4.0)


def test_the_rule_can_return_the_unfavourable_verdict():
    """The rule must be able to fail, and on this data it does: the published
    isotropic surrogate is rejected by it. A criterion that passed every arm
    would be decoration."""
    text = open(ARTIFACT).read()
    iso = text[text.index("isotropic 0.561") : text.index("anisotropic 1.45")]
    assert "FAILS the pre-registered band" in iso


def test_the_artifact_reports_a_pass_only_for_the_admissible_surrogate():
    """The discriminating result, pinned. Two independent criteria now select the
    same surrogate: the lag-1 admissibility test used earlier, and this one,
    which knows nothing about lag-1."""
    text = open(ARTIFACT).read()
    aniso = text[text.index("anisotropic 1.45") :]
    assert "PASSES the pre-registered band" in aniso


def test_the_supplementary_p95_is_labelled_as_not_pre_registered():
    """The p95 ratio was added after seeing the p50 result. That is legitimate
    only while it is labelled, so this pins the label, not the number."""
    text = open(ARTIFACT).read()
    assert text.count("not pre-registered") >= 2


def test_the_reported_ratio_matches_the_corrected_columns():
    """Drift guard against the failure mode this project keeps repeating: a
    number in prose that no longer matches the table above it. R must equal the
    quotient of the two corrected medians actually printed."""
    import re

    text = open(ARTIFACT).read()
    checked = 0
    for block in text.split("=== ")[1:]:
        values = {}
        for line in block.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 7 and cells[0] in ("plane", "quadratic"):
                values[cells[0]] = float(cells[4])  # the corrected p50 column
        ratio = re.search(r"corrected\(quadratic\) = ([\d.]+)", block)
        if len(values) != 2 or not ratio:
            continue
        expected = values["plane"] / values["quadratic"]
        assert float(ratio.group(1)) == pytest.approx(expected, rel=0.02)
        checked += 1
    assert checked == 2, "both surrogate blocks must be checked"


def test_agreement_is_not_claimed_as_proof():
    """The probe's own stated limit must survive in the artifact: two estimators
    sharing a wrong assumption would agree and both be wrong."""
    text = open(ARTIFACT).read()
    assert "necessary" in text and "not sufficient" in text


@needs_data
def test_real_reported_uses_no_surrogate():
    """What the estimator returns on real patches must not depend on which field
    would have been injected, or the comparison is the model checking itself."""
    import inspect

    src = inspect.getsource(mod.real_reported)
    for forbidden in (
        "anisotropic_field",
        "sigma_col",
        "sigma_row",
        "smooth_reference",
    ):
        assert forbidden not in src


@needs_data
def test_the_two_estimators_disagree_before_correction():
    """Without this, the whole probe could be trivial: if the raw numbers already
    matched, no correction would be under test."""
    old_n = mod.N_SAMPLES
    mod.N_SAMPLES = 30
    try:
        plane = mod.real_reported(1, seed=2)
        quad = mod.real_reported(2, seed=2)
    finally:
        mod.N_SAMPLES = old_n
    assert float(np.median(plane)) > 2 * float(np.median(quad))
