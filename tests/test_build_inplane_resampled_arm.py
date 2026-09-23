"""Re-sampling one sheet in-plane WITHOUT moving it: the builder's contract.

The study needs a surface that is the same sheet, laid out on the same grid,
sampled at different points. Bilinear interpolation at cell centres puts points
inside a curved sheet (~0.9 vx, measured), which the offset sweep shows already
costs ink, so the builder uses Catmull-Rom along one axis and these tests pin
that it stays on the sheet.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_inplane_resampled_arm import resample_u  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_measure_flatten_normal_offset import cylinder  # noqa: E402


def test_zero_shift_is_the_input():
    P, m = cylinder()
    Q, mq = resample_u(P, m, 0.0)
    assert np.array_equal(Q[mq], P[mq])
    assert mq[:, 1:-2].all()


def test_a_straight_line_is_reproduced_exactly():
    rows, cols = 5, 12
    u = np.arange(cols, dtype=float)
    P = np.stack(np.broadcast_arrays(3.0 * u, 2.0 * u + 1, 0.5 * u + 7), -1)
    P = np.broadcast_to(P, (rows, cols, 3)).copy()
    m = np.ones((rows, cols), bool)
    Q, mq = resample_u(P, m, 0.5)
    expect = np.stack([3.0 * (u + 0.5), 2.0 * (u + 0.5) + 1, 0.5 * (u + 0.5) + 7], -1)
    assert np.allclose(Q[:, 1:-2], expect[1:-2][None], atol=1e-9)


def test_half_cell_stays_on_a_curved_sheet():
    """Radius 1000 vx, 20 vx grid: the resampled points must sit on the cylinder
    to well under 0.01 vx (bilinear would be ~0.05 here, 0.9 on real data)."""
    P, m = cylinder(cols=100)  # 2 rad of arc: no arctan2 wrap in the check below
    Q, mq = resample_u(P, m, 0.5)
    r = np.hypot(Q[..., 0], Q[..., 1])[mq]
    assert np.abs(r - 1000.0).max() < 0.01
    # and it really moved: half a 20 vx cell along the sheet
    s0 = np.arctan2(P[..., 1], P[..., 0])[mq] * 1000.0
    s1 = np.arctan2(Q[..., 1], Q[..., 0])[mq] * 1000.0
    assert np.allclose(s1 - s0, 10.0, atol=1e-3)


def test_an_invalid_neighbour_invalidates_the_cell():
    P, m = cylinder()
    m = m.copy()
    m[3, 10] = False
    Q, mq = resample_u(P, m, 0.5)
    # cells whose 4-point stencil (j-1..j+2) touches column 10 in row 3
    assert not mq[3, 8:12].any()
    assert mq[3, 7] and mq[3, 12]
    assert (Q[~mq] == 0).all()
