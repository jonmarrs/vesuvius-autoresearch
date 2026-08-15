"""The published tool and the implementation we actually run must agree.

`tools/placement_check/` is a subtree of https://github.com/jonmarrs/placement-check, the
standalone tool. `repro/sota_data/register.py::placement_peak` is what actually gates our
registration. They are separate implementations on purpose: the published one is numpy-only
so it is trivial to adopt, ours uses the OpenCV already in this environment.

Two implementations of the same check is exactly the shape of the bug that started all of
this, where a hardcoded constant existed in two modules and only one got fixed. The
difference here is that these are allowed to differ in code, so a source-level comparison
would be wrong. What must not differ is the ANSWER, so that is what this compares.

If it fails, the tool we advertise is not the tool we run, and one of them is lying.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tools", "placement_check"
    ),
)

from repro.sota_data.register import placement_peak as ours  # noqa: E402

try:
    from placement_check import placement_offset as published  # noqa: E402
except ImportError:  # pragma: no cover
    published = None

requires_tool = pytest.mark.skipif(
    published is None, reason="tools/placement_check absent"
)


def speckle(h=520, w=520, n=90, seed=0):
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w), np.uint8)
    for _ in range(n):
        y, x = rng.integers(70, h - 90), rng.integers(70, w - 90)
        img[y : y + 18, x : x + 7] = 255
    return img


@requires_tool
@pytest.mark.parametrize("shift", [(0, 0), (11, -19), (-7, 23), (25, 14)])
def test_both_implementations_find_the_same_peak(shift):
    a = speckle(seed=abs(shift[0]) + 1)
    b = np.roll(np.roll(a, shift[0], 0), shift[1], 1)
    oy, ox, _, _ = ours(a, b, max_shift=48)
    r = published(a, b, max_shift=48)
    assert (oy, ox) == (r.dy, r.dx) == shift, (
        f"published tool says {(r.dy, r.dx)}, ours says {(oy, ox)}, truth is {shift}"
    )


@requires_tool
def test_both_agree_on_a_noisy_reference():
    """Agreement on clean synthetic data is easy; the real case is a mediocre reference."""
    a = speckle(seed=7)
    b = np.roll(a, 13, 1).copy()
    rng = np.random.default_rng(8)
    flip = rng.random(b.shape) < 0.2
    b[flip] = np.where(b[flip] > 0, 0, 255)
    oy, ox, _, _ = ours(a, b, max_shift=48)
    r = published(a, b, max_shift=48)
    assert (oy, ox) == (r.dy, r.dx)


@requires_tool
def test_both_refuse_an_empty_mask():
    """The degenerate-input guard is the point of the tool; both must keep it."""
    a = speckle()
    for impl in (
        lambda: ours(np.zeros_like(a), a),
        lambda: published(np.zeros_like(a), a),
    ):
        with pytest.raises(ValueError):
            impl()
