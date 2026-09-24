"""Half-pixel IMAGE re-sample: builder and rule, tested before the arm existed."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_scorer_subpixel import HI, LO, verdict  # noqa: E402
from build_subpixel_image_arm import half_pixel_shift_x  # noqa: E402


def test_a_constant_image_is_unchanged():
    s = np.full((7, 50), 123, np.uint8)
    out = half_pixel_shift_x(s)
    assert out.dtype == np.uint8 and out.shape == s.shape
    assert (out == 123).all()


def test_a_ramp_moves_by_exactly_half_a_pixel():
    s = np.tile((2 * np.arange(100)).astype(np.uint8), (3, 1))  # 0, 2, 4, ...
    out = half_pixel_shift_x(s)
    assert (out[:, :-1] == s[:, :-1] + 1).all()  # value at k + 0.5
    assert (out[:, -1] == s[:, -1]).all()  # last column has no right neighbour: kept


def test_verdict_bands():
    assert (LO, HI) == (0.02, 0.06)
    assert verdict(0.08)[0] == "SCORER AMPLIFIES"
    assert verdict(0.04)[0] == "BOTH"
    assert verdict(0.01)[0] == "RENDER-SIDE"
