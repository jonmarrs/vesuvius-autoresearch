"""Tests for placement-check, including proof that it can fail."""

import numpy as np
import pytest
from placement_check import PlacementResult, placement_offset


def speckle(h=600, w=600, n=100, seed=0):
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w), np.uint8)
    for _ in range(n):
        y, x = rng.integers(70, h - 90), rng.integers(70, w - 90)
        img[y : y + 20, x : x + 8] = 255
    return img


def test_identical_inputs_have_zero_offset():
    a = speckle()
    r = placement_offset(a, a, max_shift=48)
    assert (r.dy, r.dx) == (0, 0) and r.offset == 0.0
    assert r.dice_at_zero == pytest.approx(1.0)


@pytest.mark.parametrize("shift", [(13, -21), (-9, 17), (0, 25), (31, 0)])
def test_known_shift_is_recovered_exactly(shift):
    """The whole point. If this cannot recover a shift it is decoration."""
    a = speckle(seed=1)
    b = np.roll(np.roll(a, shift[0], 0), shift[1], 1)
    r = placement_offset(a, b, max_shift=64)
    assert (r.dy, r.dx) == shift
    assert r.dice_at_peak > r.dice_at_zero


def test_bool_input_is_not_silently_emptied():
    """`bool > 127` is all-False, which used to score a PERFECT zero offset."""
    a = speckle() > 127
    r = placement_offset(a, np.roll(a, 11, 0), max_shift=48)
    assert (r.dy, r.dx) == (11, 0)


def test_empty_input_raises_rather_than_passing():
    a = speckle()
    with pytest.raises(ValueError, match="empty after binarisation"):
        placement_offset(np.zeros_like(a), a, max_shift=32)


def test_peak_at_the_search_boundary_raises():
    """An under-reported offset must not be returned as if it were the answer."""
    a = speckle(seed=2)
    b = np.roll(a, 60, 0)
    with pytest.raises(ValueError, match="search boundary"):
        placement_offset(a, b, max_shift=20)


def test_shape_mismatch_is_named():
    with pytest.raises(ValueError, match="shape mismatch"):
        placement_offset(speckle(), speckle(h=500, w=600))


def test_non_2d_input_is_rejected():
    with pytest.raises(ValueError, match="must be 2-D"):
        placement_offset(
            np.ones((4, 4, 3), np.uint8) * 255, np.ones((4, 4, 3), np.uint8)
        )


def test_passed_uses_the_caller_threshold():
    r = PlacementResult(dy=3, dx=4, offset=5.0, dice_at_zero=0.5, dice_at_peak=0.6)
    assert r.passed(8) and not r.passed(4)


def test_a_weak_reference_still_locates_the_peak():
    """A noisy reference should widen the peak, not move it."""
    a = speckle(seed=3)
    b = np.roll(a, 15, 1).copy()
    rng = np.random.default_rng(4)
    flip = rng.random(b.shape) < 0.25  # corrupt a quarter of the reference
    b[flip] = np.where(b[flip] > 0, 0, 255)
    r = placement_offset(a, b, max_shift=48)
    assert r.dx == 15 and r.dy == 0
