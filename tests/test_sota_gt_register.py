import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.gt_register import (parse_obj_vt, register_label_to_region)


def test_parse_obj_vt_positional(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nvt 10 20\nv 4 5 6\nvt 30 40\nf 1/1 2/2\n")
    v, vt = parse_obj_vt(p)
    assert v.shape == (2, 3) and vt.shape == (2, 2)
    assert np.allclose(v[1], [4, 5, 6]) and np.allclose(vt[0], [10, 20])


def test_parse_obj_vt_mismatch_raises(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nv 4 5 6\nvt 10 20\n")
    with pytest.raises(ValueError, match="mismatch"):
        parse_obj_vt(p)


def test_register_label_to_region_recovers_block():
    # synthetic: region grid maps 1:1 to obj vertices; label is a block.
    h = w = 40
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    region_xyz = np.stack([xx, yy, np.zeros_like(xx)], axis=-1)  # (h,w,3)
    obj_v = region_xyz.reshape(-1, 3)                             # vertices = region pts
    H = W = 40
    # vt with row=H-v,col=u convention: choose vt so that vertex at (r,c) -> label (r,c)
    # label pixel (row,col) = (H - vt_v, vt_u). Want that to equal (r,c) for grid pixel r,c
    # so vt_u = c, vt_v = H - r.
    vt = np.stack([xx.reshape(-1), (H - yy).reshape(-1)], axis=1)  # (u, v)
    old_label = np.zeros((H, W), np.uint8)
    old_label[10:25, 12:30] = 255
    reg, residual, period = register_label_to_region(region_xyz, obj_v, vt, old_label, size=40)
    assert residual < 1e-3
    inter = np.logical_and(reg > 127, old_label > 127).sum()
    union = np.logical_or(reg > 127, old_label > 127).sum()
    assert inter / union > 0.9
    assert 0.0 <= period <= 1.0
