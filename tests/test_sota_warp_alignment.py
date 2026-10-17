"""The registration warp puts each region pixel where the tifxyz convention says it is.

Until 2026-10-17 the crop was rounded to whole mesh cells and the field stretched over it
pixel-centre to pixel-centre, which placed an identity registration 1.8-13.8 px off at the
7.91 um mesh's 16.3 level-2 px per cell."""

import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.register import (
    WARP_ALIGNMENT,
    region_in_mesh,
    sample_field,
    stride_coords,
    warp_provenance,
    warp_via_field,
)

LEVEL0 = (50600, 36400)  # 20230702185753


def _ramps(h, w):
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    return rows, cols


@pytest.mark.parametrize(
    "mesh_shape",
    [(776, 559), (2530, 1820)],  # the 7.91 um mesh (16.3 px a cell); the 2.4 um (5.0)
)
@pytest.mark.parametrize("y0, x0", [(4000, 2500), (4013, 2507), (0, 0)])
def test_an_identity_registration_lands_on_its_own_pixels(mesh_shape, y0, x0):
    """Each mesh vertex maps to the level-2 pixel it sits on; the warp must give back the
    region's own coordinates, to within cv2.remap's 1/32 px."""
    size, pad = 512, 32
    mh, mw = mesh_shape
    sy, sx = mh / (LEVEL0[0] / 4), mw / (LEVEL0[1] / 4)
    r, c = np.mgrid[0:mh, 0:mw].astype(np.float64)
    # the field's values index an image whose (pad, pad) is the region's first pixel
    field = np.stack([r / sy - (y0 - pad), c / sx - (x0 - pad)], -1).astype(np.float32)
    crop, coords = region_in_mesh(field, LEVEL0, (y0, x0, size))
    row_img, col_img = _ramps(size + 2 * pad, size + 2 * pad)
    got_r = warp_via_field(row_img, crop, (size, size), coords=coords)
    got_c = warp_via_field(col_img, crop, (size, size), coords=coords)
    want_r, want_c = _ramps(size, size)
    assert (got_r > 0).all() and (got_c > 0).all()  # every pixel valid (0 = invalid)
    assert np.abs(got_r - (want_r + pad)).max() < 0.05
    assert np.abs(got_c - (want_c + pad)).max() < 0.05


@pytest.mark.parametrize("stride, h, w", [(2, 64, 48), (8, 61, 45)])
def test_a_stride_field_is_read_from_its_first_pixel(stride, h, w):
    """Field vertex j sits on output pixel j * stride, as `correspondence_field` computes
    it. cv2.resize put it (stride - 1) / 2 px off, and spread the vertices over the
    whole output when h was not a multiple of the stride."""
    r, c = np.mgrid[0:h:stride, 0:w:stride].astype(np.float32)
    row, col, bad = sample_field(
        np.stack([r, c], -1), (h, w), coords=stride_coords((h, w), stride)
    )
    want_r, want_c = _ramps(h, w)
    last_r, last_c = (len(r) - 1) * stride, (r.shape[1] - 1) * stride
    assert not bad[: last_r + 1, : last_c + 1].any()
    assert (
        bad[last_r + 1 :].all() and bad[:, last_c + 1 :].all()
    )  # past the last vertex
    ok = ~bad
    assert np.abs(row - want_r)[ok].max() < 1e-4
    assert np.abs(col - want_c)[ok].max() < 1e-4


def test_an_invalid_vertex_spoils_only_the_pixels_it_weighs_on():
    field = np.ones((3, 3, 2), np.float32)
    field[1, 2] = np.nan
    on_vertex = (np.array([1.0]), np.array([1.0]))  # (1, 2) has zero weight here
    _, _, bad = sample_field(field, (1, 1), coords=on_vertex)
    assert not bad.any()
    between = (np.array([1.0]), np.array([1.5]))
    _, _, bad = sample_field(field, (1, 1), coords=between)
    assert bad.all()


def test_a_region_past_the_mesh_edge_is_zeroed_not_extended():
    """A 10-row mesh at 10 level-2 px a cell ends at row 90: the region's later rows have no
    vertex to sample and must come back invalid, not the edge row repeated."""
    mesh = np.ones((10, 10, 2), np.float32)  # every vertex reads pixel (1, 1)
    level0 = (400, 400)  # 100 level-2 rows over 10 vertex rows
    crop, coords = region_in_mesh(mesh, level0, (88, 0, 8))
    out = warp_via_field(np.full((3, 3), 255, np.uint8), crop, (8, 8), coords=coords)
    assert (out[:3] == 255).all()  # rows 88-90 lie on or before the last vertex
    assert (out[3:] == 0).all()


def test_the_old_crop_and_stretch_was_several_pixels_off():
    """The replaced warp, on the identity registration above: what the fix removes."""
    mh, size, y0 = 776, 4096, 4000
    sy = mh / (LEVEL0[0] / 4)
    rows = (np.arange(mh, dtype=np.float32) / sy)[:, None]  # each vertex's level-2 row
    ys, ye = int(round(y0 * sy)), int(round((y0 + size) * sy))
    old = cv2.resize(rows[ys:ye], (1, size), interpolation=cv2.INTER_LINEAR)[:, 0]
    error = old - (y0 + np.arange(size))
    assert np.abs(error).min() > 1.5 and np.abs(error).max() > 13
    crop, coords = region_in_mesh(rows, LEVEL0, (y0, 0, size))
    new, _, bad = sample_field(
        np.repeat(crop[:, :, None], 2, 2), (size, 1), coords=(coords[0], np.zeros(1))
    )
    assert not bad.any()
    assert np.abs(new[:, 0] - (y0 + np.arange(size))).max() < 1e-3


def test_a_label_says_which_warp_made_it(tmp_path):
    """The probes read labels written here (stats beside them) and ScrollGT's (none)."""
    import json

    label = tmp_path / "registered_label_l2region.png"
    label.touch()
    assert "carries no warp record" in warp_provenance(str(label))
    stats = tmp_path / "registration_stats.json"
    stats.write_text(json.dumps({"method": "obj-exact"}))
    assert "registered by the warp before 2026-10-17" in warp_provenance(str(label))
    stats.write_text(json.dumps({"warp_alignment": WARP_ALIGNMENT}))
    assert warp_provenance(str(label)) is None
