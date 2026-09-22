"""The normal-offset metric must separate MOVING a surface from RE-SAMPLING it.

Nearest-neighbour distance cannot: two samplings of one sheet on grids offset
in-plane read as far apart as the grid spacing allows. That is how two stock
flattens of identical meshes came to be reported as "7 vx apart" while lying on
the same sheet (reports/the_flatten_moves_the_grid_not_the_surface.md).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from measure_flatten_normal_offset import normal_offset  # noqa: E402

R, STEP = 1000.0, 20.0  # a gently curved sheet on a 20 vx grid, like the flat tifxyz


def cylinder(radius=R, du=0.0, dv=0.0, rows=60, cols=200):
    """Grid (rows, cols, 3) on a cylinder about the z axis, spacing STEP along the
    sheet, optionally offset in-plane by (du, dv) voxels."""
    s = (np.arange(cols) * STEP + du)[None, :]
    z = (np.arange(rows) * STEP + dv)[:, None] + 0 * s
    theta = s / radius
    x = radius * np.cos(theta) + 0 * z
    y = radius * np.sin(theta) + 0 * z
    P = np.stack([x, y, z], -1)
    return P, np.ones(P.shape[:2], bool)


def test_identical_surfaces_read_zero():
    P, m = cylinder()
    r = normal_offset(P, m, P, m)
    assert r["nn_p50"] < 1e-9 and r["normal_abs_p50"] < 1e-9


def test_a_normal_shift_is_read_as_that_shift():
    PA, m = cylinder()
    PB, _ = cylinder(radius=R + 4.0)
    r = normal_offset(PA, m, PB, m)
    assert abs(r["normal_abs_p50"] - 4.0) < 0.1, r
    assert abs(abs(r["normal_signed_median"]) - 4.0) < 0.1, r


def test_an_in_plane_resample_of_one_sheet_is_not_a_displacement():
    """The case nearest-neighbour distance gets wrong: same sheet, grid offset
    by (7, 7) vx in-plane. NN reads ~9.9 vx; the normal component must be ~0."""
    PA, m = cylinder()
    PB, _ = cylinder(du=7.0, dv=7.0)
    r = normal_offset(PA, m, PB, m)
    assert r["nn_p50"] > 8.0, r
    assert r["normal_abs_p50"] < 0.2, r
    assert r["in_plane_p50"] > 8.0, r


def test_outward_sign_does_not_depend_on_grid_orientation():
    """The grid normal's sign is arbitrary (it flips with column order), so a
    displacement must be read along the OUTWARD normal about an axis for 'in'
    and 'out' to be comparable across surfaces."""
    PA, m = cylinder()
    for flip in (False, True):
        A = PA[:, ::-1] if flip else PA
        out = normal_offset(A, m, cylinder(radius=R + 4.0)[0], m, axis=(0.0, 0.0))
        inn = normal_offset(A, m, cylinder(radius=R - 4.0)[0], m, axis=(0.0, 0.0))
        assert abs(out["normal_outward_median"] - 4.0) < 0.1, (flip, out)
        assert abs(inn["normal_outward_median"] + 4.0) < 0.1, (flip, inn)
