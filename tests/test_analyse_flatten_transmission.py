"""The transmission rule, tested before either flatten ran.

T is measured against a self-calibrated reference: the SAME radial shift applied
directly to the reference flat surface. So T = 1 means "the flatten passed the
mesh offset through untouched", with no assumed angle between the radial
direction and the surface normal.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_flatten_transmission import (  # noqa: E402
    radial_shift,
    transmission,
    verdict,
)
from test_measure_flatten_normal_offset import cylinder  # noqa: E402

AXIS = (0.0, 0.0)


def test_radial_shift_moves_points_exactly():
    P, m = cylinder()
    Q = radial_shift(P, m, AXIS, 4.0)
    r0 = np.hypot(P[..., 0], P[..., 1])
    r1 = np.hypot(Q[..., 0], Q[..., 1])
    assert np.allclose(r1 - r0, 4.0)
    assert np.array_equal(P[..., 2], Q[..., 2])


def test_full_transmission_reads_one():
    P, m = cylinder()
    t = transmission(
        P,
        m,
        radial_shift(P, m, AXIS, -4.0),
        m,
        radial_shift(P, m, AXIS, 4.0),
        m,
        AXIS,
        4.0,
    )
    assert abs(t["T_in"] - 1) < 0.02 and abs(t["T_out"] - 1) < 0.02, t


def test_an_absorbed_offset_reads_zero_even_when_resampled():
    """The flatten re-parametrises; an absorbed offset lands on the reference
    sheet on a different grid. That must read T ~ 0, not the grid offset."""
    P, m = cylinder()
    Rs, _ = cylinder(du=7.0, dv=7.0)
    t = transmission(P, m, Rs, m, Rs, m, AXIS, 4.0)
    assert abs(t["T_in"]) < 0.1 and abs(t["T_out"]) < 0.1, t


def test_half_transmission_reads_half():
    P, m = cylinder()
    t = transmission(
        P,
        m,
        radial_shift(P, m, AXIS, -2.0),
        m,
        radial_shift(P, m, AXIS, 2.0),
        m,
        AXIS,
        4.0,
    )
    assert abs(t["T_in"] - 0.5) < 0.05 and abs(t["T_out"] - 0.5) < 0.05, t


def test_verdict_bands():
    assert verdict(0.95, 1.02)[0] == "TRANSMITS"
    assert verdict(0.05, -0.1)[0] == "ABSORBED"
    assert verdict(0.5, 0.6)[0] == "PARTIAL"
    assert verdict(0.9, 0.1)[0] == "ASYMMETRIC"
