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
    """A destination covering only part of the source must not silently clip a column."""
    src = _grid(40, 100)
    dst = _grid(40, 50)  # covers source x in [0, 50) only
    columns = [
        {"col": 1, "gx0": 5, "gx1": 20, "text_band": [5, 35], "cross_strip": False},
        {"col": 2, "gx0": 70, "gx1": 90, "text_band": [5, 35], "cross_strip": False},
    ]
    mapped, stats = transfer_columns(src, dst, columns)
    inside = {m["col"]: m["fully_inside"] for m in mapped}
    assert inside[1] is True
    assert inside[2] is False
    assert stats["n_fully_inside"] == 1


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
    assert mapped[0]["n_mapped"] > 0
    assert mapped[0]["n_mapped"] < 20 * 24  # the invalid band did not contribute


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
