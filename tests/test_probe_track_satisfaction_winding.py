"""Tests for the track-metric measurement.

This confirms someone else's finding, which is a direction that invites
carelessness: it is easy to build a harness that agrees because it cannot
disagree. The control is therefore the first thing pinned.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import probe_track_satisfaction_winding as mod  # noqa: E402
import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

ARTIFACT = os.path.join(_REPO, "reports", "track_satisfaction_winding.txt")


def test_a_half_winding_is_rejected():
    """The control. Without it a harness that never rejects anything would
    'confirm' the blindness while measuring nothing at all."""
    for cfg in (mod.REPORTING, mod.SPLICING):
        sat, tot, _ = mod.score(0.5, cfg)
        assert sat == 0, "the harness cannot produce a rejection"
        assert tot > 0


def test_whole_windings_are_not():
    """The finding itself, through villa's unmodified tracks.py."""
    for d in (1.0, 2.0, 23.0):
        sat, tot, _ = mod.score(d, mod.REPORTING)
        assert sat == tot, f"displacement {d} changed the satisfied count"


def test_the_undisplaced_track_is_fully_satisfied():
    """The reference must pass, or every comparison below it is vacuous."""
    sat, tot, _ = mod.score(0.0, mod.REPORTING)
    assert sat == tot > 0


def test_the_metric_computes_the_winding_it_ignores():
    """The sharpest part: mode_winding tracks the displacement exactly, so the
    number that would expose it is computed and returned, then never compared."""
    base = mod.score(0.0, mod.REPORTING)[2]
    for d in (1.0, 2.0, 23.0):
        assert mod.score(d, mod.REPORTING)[2] == base + int(d)


def test_the_chunked_entry_point_behaves_the_same():
    """satisfaction_metrics.py imports the chunked wrapper, so the finding has to
    hold there and not only in the inner function."""
    assert mod.score_chunked(0.5, mod.REPORTING)[0] == 0
    sat, tot = mod.score_chunked(1.0, mod.REPORTING)
    assert sat == tot


def test_the_artifact_credits_where_the_finding_came_from():
    """It is Bullo27's finding; we measured it. That has to stay visible."""
    text = open(ARTIFACT).read()
    assert "Bullo27" in text
    assert "algebra, not a" in text


def test_the_artifact_keeps_its_limits():
    """Synthetic, one geometry, no fit run."""
    text = open(ARTIFACT).read()
    assert "No fit was run" in text
