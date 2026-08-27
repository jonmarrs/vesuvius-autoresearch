"""Tests for the real-residual exceedance probe, whose result is VOID by its own gate.

The probe reports a number it then refuses to interpret, so the tests here are
about the refusal holding: the gate must be checked before the verdict, the
ladder comparison must be a like-for-like superset, and the narrative ratio must
be computed from the same variables the table prints.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import probe_real_residual_exceedance as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")
ARTIFACT = os.path.join(_REPO, "reports", "real_residual_exceedance.txt")


def test_the_long_ladder_is_a_strict_superset():
    """The comparison that establishes amplitude-insensitivity is only valid if the
    longer ladder contains the shorter one. A first version was longer and also
    coarser, and reported MORE rays without an onset on the longer ladder -- an
    impossibility, and one that would have been published as 'extending the ladder
    changes nothing' if the numbers had happened to agree."""
    assert set(mod.RMS_LEVELS).issubset(set(mod.LADDER_LONG))
    assert max(mod.LADDER_LONG) > 30 * max(mod.RMS_LEVELS) / 32


def test_the_gate_threshold_is_the_pre_registered_one():
    """A validity gate that can be relaxed after seeing the answer is not a gate."""
    assert mod.VOID_IF_NO_ONSET_ABOVE == 0.25
    assert mod.BAND == (0.5, 2.0)
    assert mod.E_GAUSS == 23.59


def test_the_artifact_refuses_a_verdict():
    """The gate fired, so the exceedance the probe computed must carry no reading.
    It happens to land inside the pre-registered band, which is exactly when an
    unreported gate failure would be most tempting and most wrong."""
    text = open(ARTIFACT).read()
    assert "VOID" in text
    assert "No verdict: the validity gate above failed." in text


def test_the_artifact_does_not_claim_a_replacement_figure():
    """The finding is a direction, not a number, and must not drift into one."""
    text = open(ARTIFACT).read()
    assert "direction, not a replacement figure" in text


def test_the_narrative_ratio_matches_the_table():
    """Drift guard on the one derived number in the prose. It was hand-typed as
    'roughly eight times' from an earlier, coarser run and was wrong by 3x once the
    ladders were made comparable."""
    import re

    text = open(ARTIFACT).read()
    stated = re.search(r"([\d.]+)x as many rays \((\d+)% against (\d+)%\)", text)
    assert stated, "the ratio sentence changed shape; re-check it by hand"
    ratio, gauss, real = (
        float(stated.group(1)),
        int(stated.group(2)),
        int(stated.group(3)),
    )
    assert abs(ratio - gauss / max(real, 1)) < 0.15


def test_the_field_generator_holds_the_donor_fixed():
    """Amplitude must be the only thing varying along a ladder whose first crossing
    is read as an onset. An earlier version drew a new donor per call, so the scan
    was over donor x amplitude jointly."""
    import inspect

    src = inspect.getsource(mod.make_field_fn)
    assert "jitter" not in src
    assert "def make_field_fn(donor)" in src


@needs_data
def test_a_fixed_donor_gives_a_reproducible_field():
    """The consequence of the fix, measured rather than asserted from the source."""
    import numpy as np

    bank = mod.residual_bank()
    fn = mod.make_field_fn(bank[0][1])
    a = fn((24, 32), 1.0, 1.0, np.random.default_rng(5))
    b = fn((24, 32), 1.0, 1.0, np.random.default_rng(5))
    np.testing.assert_allclose(a, b)
