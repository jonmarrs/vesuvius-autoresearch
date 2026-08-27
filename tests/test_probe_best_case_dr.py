"""Tests for the best-case-dr probe.

Its first version reported a statistic that was an artifact of tie-breaking, and
its verdict lands within noise of the pre-registered threshold. Both facts have
to stay visible, so they are pinned here.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_best_case_dr as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")
ARTIFACT = os.path.join(_REPO, "reports", "best_case_dr.txt")


def test_the_physical_range_is_the_measured_one():
    """The sweep that carries the verdict must cover the spacings real shards
    actually show, 11.32 to 16.74, and not more."""
    assert min(mod.PHYSICAL_DR) <= 11.32
    assert max(mod.PHYSICAL_DR) >= 16.74
    assert max(mod.PHYSICAL_DR) < 20.0


@needs_data
def test_satisfaction_is_not_maximised_by_shrinking_dr():
    """The degeneracy that would make 'best-case dr' meaningless. If the score rose
    monotonically as dr fell, any window would be satisfiable at a small enough
    spacing and the question would answer itself."""
    from probe_real_patch_satisfaction import real_windows
    from probe_spiral_satisfaction_splicing_and_seam import REPORTING, score_with
    from probe_spiral_satisfaction_winding import IdentityTransform

    windows = real_windows((2, 4), n_windows=20)
    tiny = np.median(
        [score_with(p, 0.5, REPORTING, IdentityTransform()) for _, p in windows]
    )
    mid = np.median(
        [score_with(p, 12.81, REPORTING, IdentityTransform()) for _, p in windows]
    )
    assert tiny <= mid


@needs_data
def test_ties_are_reported_not_broken_silently():
    """The defect in the first version: with three quads many dr values tie, and
    keeping the first maximum reports the sweep's starting end as if it were a
    fitted value."""
    from probe_real_patch_satisfaction import real_windows

    windows = real_windows((2, 4), n_windows=10)
    total = int(windows[0][1].valid_quad_mask.sum().item())
    _, _, tied = mod.satisfied_over(windows[0][1], mod.DR_SWEEP, total)
    assert len(tied) > 1, "no ties here; the guard would be untested"
    text = open(ARTIFACT).read()
    assert "share of the dr sweep tied at that best" in text
    assert "why 'the winning dr' is not reported" in text


def test_the_marginal_verdict_is_labelled_as_noise():
    """48.3% against a 50% threshold on n=60 cannot be distinguished from it. The
    artifact must say so rather than reporting a clean fail."""
    text = open(ARTIFACT).read()
    assert "inside the noise" in text
    assert "is not evidence that it is below" in text


def test_the_artifact_leads_with_what_is_not_marginal():
    """The doubling from 21.7% to 48.3% is the finding; the threshold comparison is
    not."""
    text = open(ARTIFACT).read()
    assert "What is NOT marginal" in text
    assert "more than double" in text
