"""Tests for the radius/winding calibration.

The monotonicity verdict is the load-bearing part: `check_patch_spatial_balance`
reports an inner-to-outer band table, and that table is only readable as
inner-to-outer if radius actually orders windings. So `is_monotone` must be able
to return False, and the script must say what a False means.
"""

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import calibrate_radius_to_winding as mod  # noqa: E402


def test_monotone_accepts_a_rising_sequence():
    assert mod.is_monotone([100.0, 200.0, 300.0])


def test_monotone_accepts_a_plateau():
    """Equal medians are not a violation; the claim is non-decreasing."""
    assert mod.is_monotone([100.0, 100.0, 200.0])


def test_monotone_rejects_a_dip():
    assert not mod.is_monotone([100.0, 300.0, 250.0])


def test_monotone_rejects_a_dip_at_the_end():
    assert not mod.is_monotone([100.0, 200.0, 300.0, 299.0])


def test_a_single_value_is_trivially_monotone():
    assert mod.is_monotone([42.0])
    assert mod.is_monotone([])


def test_the_sampled_windings_span_inner_to_outer():
    """A calibration that only sampled outer windings could not detect a
    non-monotone proxy, which is the failure it exists to catch."""
    assert min(mod.SAMPLE) <= 10
    assert max(mod.SAMPLE) >= 129
    assert len(mod.SAMPLE) >= 8
