"""Column boxes must transfer by 3D correspondence, not by re-reading ink.

The column metric asks whether a prediction carries more signal inside text columns than in
gutters. If the boxes were derived from an ink-detection output, the target would measure
agreement with that output -- the agreement-with-teacher circularity this project already
corrected. So columns move between flattenings through the shared 3D scan, and their
identities stay anchored to the papyrological reading.
"""

import pathlib
import sys

import numpy as np
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from transfer_columns_to_flattening import bridge_points, transfer_columns  # noqa: E402


def _grid(h, w, x0=0.0, y0=0.0):
    """A synthetic flattening: grid cell (r, c) holds a known 3D point."""
    rr, cc = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    xs = (cc + x0).astype(np.float32)
    ys = (rr + y0).astype(np.float32)
    zs = np.zeros_like(xs)
    return np.stack([xs, ys, zs], axis=-1)


def test_identity_flattening_maps_every_point_to_itself():
    src = _grid(20, 30)
    pts = np.array([[3, 4], [10, 25], [19, 0]])
    dst_yx, resid = bridge_points(src, src, pts)
    assert np.array_equal(dst_yx, pts)
    assert np.allclose(resid, 0.0)


def test_a_shifted_flattening_recovers_the_shift():
    """The destination grid holds the same 3D points offset by 5 columns."""
    src = _grid(20, 30)
    dst = _grid(20, 30, x0=-5.0)
    pts = np.array([[3, 10], [7, 20]])
    dst_yx, resid = bridge_points(src, dst, pts)
    assert np.array_equal(dst_yx[:, 1], pts[:, 1] + 5)
    assert np.allclose(resid, 0.0)


def test_transfer_reports_columns_that_fall_outside_the_destination():
    """A destination whose valid material is an ISLAND inside a wider grid -- not a
    destination that is simply narrower than the source -- must not let a column with no
    real correspondence pass as `fully_inside`.

    A grid narrower than the source (the original form of this test) trips `fully_inside`'s
    strict-interior check by accident: an out-of-range column pins to the grid's own edge,
    and the edge check catches it for the wrong reason. Real data does not look like that --
    w011's valid material sits at grid columns 5-661 inside a 736-wide grid, so all 22
    columns in the real transfer landed strictly interior to the GRID while several had no
    real correspondence in the MATERIAL at all (reports/detector/w011_column_transfer.md).
    This fixture models that shape: dst is a wide grid whose valid material is a narrow
    island, so an out-of-range column maps to the island's edge -- strictly interior to the
    grid, not to the material -- and `fully_inside` alone cannot see the problem. The
    residual flag can.
    """
    src = _grid(40, 100)
    dst = _grid(40, 200)
    dst[:, 50:, :] = -1.0  # valid material occupies x in [0, 50) only; rest is unset
    columns = [
        {"col": 1, "gx0": 5, "gx1": 20, "text_band": [5, 35], "cross_strip": False},
        {"col": 2, "gx0": 70, "gx1": 90, "text_band": [5, 35], "cross_strip": False},
    ]
    mapped, stats = transfer_columns(src, dst, columns)
    by_col = {m["col"]: m for m in mapped}

    assert by_col[1]["fully_inside"] is True
    assert by_col[1]["residual_suspect"] is False

    # Column 2's material isn't in the destination at all, but every mapped point still
    # lands strictly inside the 200-wide grid, pinned to the island's edge (x=49) rather
    # than the grid's edge (x=199) -- so fully_inside is (wrongly) True here too.
    assert by_col[2]["fully_inside"] is True
    assert by_col[2]["residual_suspect"] is True
    assert stats["n_fully_inside"] == 2
    assert stats["n_residual_suspect"] == 1


def test_a_pure_offset_residual_is_flagged_even_when_fully_inside():
    """The regression case for the failure `fully_inside` cannot see: a rigid offset in one
    axis still resolves to the correct grid cell in the other two (nearest-neighbour cancels
    the constant term), so the mapped envelope looks clean and strictly interior. Only the
    residual reveals that the 'correspondence' is 1000 scan units away -- clearly not a
    genuine match by this project's own standard (register_run.py treats ~7.95 voxels as
    genuine; reports/detector/w011_column_transfer.md found nothing under ~185)."""
    src = _grid(20, 30)
    dst = src.copy()
    dst[..., 2] += 1000.0  # every destination point shifted by the same amount in z
    columns = [
        {"col": 1, "gx0": 2, "gx1": 25, "text_band": [0, 19], "cross_strip": False}
    ]

    mapped, _ = transfer_columns(src, dst, columns)

    assert mapped[0]["fully_inside"] is True
    assert mapped[0]["median_residual"] == pytest.approx(1000.0, abs=1e-3)
    assert mapped[0]["residual_suspect"] is True


def test_cross_strip_flag_is_carried_not_dropped():
    src = _grid(40, 100)
    columns = [
        {"col": 9, "gx0": 5, "gx1": 20, "text_band": [5, 35], "cross_strip": True},
    ]
    mapped, _ = transfer_columns(src, src, columns)
    assert mapped[0]["cross_strip"] is True


def test_invalid_source_cells_are_excluded_rather_than_bridged():
    """tifxyz marks invalid cells; bridging them would invent correspondence."""
    src = _grid(20, 30)
    src[5:10, :, :] = -1.0  # the released invalid marker
    columns = [
        {"col": 1, "gx0": 2, "gx1": 25, "text_band": [0, 19], "cross_strip": False}
    ]
    mapped, _ = transfer_columns(src, src, columns)
    # box is 20 rows x 24 cols = 480 cells; rows 5:10 (5 rows) are invalid across the full
    # 24-col width the box covers, so exactly 480 - 5*24 = 360 cells remain. An exact bound
    # (not a loose `< 480`) so an exclusion bug that drops only some of the 5 invalid rows
    # -- e.g. 456, one row's worth short -- does not slip through.
    assert mapped[0]["n_mapped"] == 360


def test_a_column_with_no_valid_cells_is_reported_not_crashed():
    src = _grid(20, 30)
    src[:, :, :] = -1.0
    columns = [
        {"col": 1, "gx0": 2, "gx1": 25, "text_band": [0, 19], "cross_strip": False}
    ]
    mapped, stats = transfer_columns(src, src, columns)
    assert mapped[0]["n_mapped"] == 0
    assert mapped[0]["fully_inside"] is False
    assert stats["n_fully_inside"] == 0
