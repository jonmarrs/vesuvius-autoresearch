"""Tests for the real-geometry satisfaction probe.

This probe carries the report's first real-data leg, so the tests are aimed at
the two ways it could be hollow: a displacement that does not actually move the
patch, and a construction whose score cannot change at all, which would make a
zero delta at one winding mean nothing.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np  # noqa: E402
import probe_real_patch_satisfaction as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_real_patch_scatter import patch_dirs  # noqa: E402
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    score_with,
)
from probe_spiral_satisfaction_winding import IdentityTransform, displace  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

needs_data = pytest.mark.skipif(not patch_dirs(), reason="real patch data absent")
ARTIFACT = os.path.join(_REPO, "reports", "real_patch_satisfaction.txt")


@needs_data
def test_the_displacement_actually_moves_the_patch():
    """The premise. If `displace` were a no-op on real coordinates, a zero delta
    would be arithmetic rather than a finding."""
    windows = mod.real_windows((2, 4), n_windows=6)
    _, patch = windows[0]
    before = np.sqrt(patch.zyxs[..., 1].numpy() ** 2 + patch.zyxs[..., 2].numpy() ** 2)
    moved = displace(patch, 12.81, n_windings=1.0)
    after = np.sqrt(moved.zyxs[..., 1].numpy() ** 2 + moved.zyxs[..., 2].numpy() ** 2)
    assert float(np.median(after - before)) == pytest.approx(12.81, abs=1e-3)


@needs_data
def test_a_half_winding_does_move_the_score():
    """The control that gives the whole-winding zero its meaning. Checked on the
    pooled set, not one window: the first real window I looked at happened to be
    one of the ~52% a half winding does not move, which alone would have argued
    the opposite."""
    windows = mod.real_windows((12, 16), n_windows=36)
    changed = 0
    for _, patch in windows:
        a = score_with(patch, mod.REAL_DR, REPORTING, IdentityTransform())
        b = score_with(
            displace(patch, mod.REAL_DR, n_windings=0.5),
            mod.REAL_DR,
            REPORTING,
            IdentityTransform(),
        )
        changed += abs(b - a) > 1e-9
    assert changed / len(windows) > 0.5, "the control cannot move the score"


@needs_data
def test_a_whole_winding_does_not():
    """The finding itself, on real traced geometry rather than a synthetic patch."""
    windows = mod.real_windows((12, 16), n_windows=36)
    for _, patch in windows:
        a = score_with(patch, mod.REAL_DR, REPORTING, IdentityTransform())
        b = score_with(
            displace(patch, mod.REAL_DR, n_windings=1.0),
            mod.REAL_DR,
            REPORTING,
            IdentityTransform(),
        )
        assert abs(b - a) < 1e-9


def test_the_control_rows_are_labelled_in_the_artifact():
    """A reader must be able to see which rows are the control without knowing to
    ask, or the zeros look like the whole story."""
    text = open(ARTIFACT).read()
    assert text.count("<- control") >= 2
    assert (
        "could not move the score and the zeros at 1.0 and 2.0 would mean nothing"
        in text
    )


def test_the_artifact_reports_the_scale_tension():
    """The half of this probe that cannot be resolved: real data matches the
    synthetic patch's extent or its quad count, never both."""
    text = open(ARTIFACT).read()
    assert "extent-matched" in text and "quad-matched" in text
    assert "never both" in text


def test_the_artifact_carries_the_unfavourable_verdict():
    """The pre-registered rule failed, and the report has to say so rather than
    leading with the real-data confirmation."""
    text = open(ARTIFACT).read()
    assert "below the pre-registered" in text
    assert "must carry that qualification" in text
