import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.register import (correspondence_field, fit_affine_orb,
                                      fit_similarity, ncc, read_tifxyz, warp_via_field)


def _surface(h=80, w=120):
    """A smooth synthetic surface patch: xyz grid with gentle curvature."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    zz = 5.0 * np.sin(xx / 25.0) + 3.0 * np.cos(yy / 18.0)
    return np.stack([xx * 2.0, yy * 2.0, zz], axis=-1)  # (h, w, 3)


def _apply_sim(xyz, s, R, t):
    return (s * xyz.reshape(-1, 3) @ R.T + t).reshape(xyz.shape)


def _rot(deg_z):
    a = np.deg2rad(deg_z)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0],
                     [0, 0, 1]], np.float32)


def test_read_tifxyz_both_layouts(tmp_path):
    xyz = _surface(16, 24)
    p1 = str(tmp_path / "hw3.tifxyz")
    tifffile.imwrite(p1, xyz)                      # (H, W, 3)
    p2 = str(tmp_path / "planes.tifxyz")
    tifffile.imwrite(p2, xyz.transpose(2, 0, 1))   # (3, H, W)
    for p in (p1, p2):
        out = read_tifxyz(p)
        assert out.shape == (16, 24, 3)
        assert np.allclose(out, xyz, atol=1e-4)


def test_read_tifxyz_bad_shape_raises(tmp_path):
    p = str(tmp_path / "bad.tifxyz")
    tifffile.imwrite(p, np.zeros((16, 24), np.float32))
    with pytest.raises(ValueError, match="tifxyz"):
        read_tifxyz(p)


def test_fit_similarity_recovers_known_transform():
    xyz = _surface()
    s_true, R_true, t_true = 3.3, _rot(30), np.array([100., -40., 7.], np.float32)
    dst = _apply_sim(xyz, s_true, R_true, t_true)
    src_pts = xyz.reshape(-1, 3)
    dst_pts = dst.reshape(-1, 3)
    s, R, t, med = fit_similarity(src_pts, dst_pts, seed=0)
    assert abs(s - s_true) / s_true < 0.02
    assert med < 0.5  # dst units
    # transformed src lands on dst
    moved = s * src_pts @ R.T + t
    assert float(np.median(np.linalg.norm(moved - dst_pts, axis=1))) < 0.5


def test_correspondence_and_warp_roundtrip():
    old_xyz = _surface()
    s_true, R_true, t_true = 2.0, _rot(-20), np.array([-15., 30., 2.], np.float32)
    new_xyz = _apply_sim(old_xyz, 1.0 / s_true,
                         R_true.T, -(1.0 / s_true) * (R_true.T @ t_true))
    # new = inverse-sim of old, so old = sim(new); fit new->old
    s, R, t, _ = fit_similarity(new_xyz.reshape(-1, 3), old_xyz.reshape(-1, 3), seed=0)
    field, res = correspondence_field(new_xyz, s, R, t, old_xyz, stride=2)
    assert float(np.nanmedian(res)) < 1.0
    # a label painted on the old grid round-trips onto the new grid at the same
    # spatial pattern (here grids are aligned index-wise by construction)
    old_label = np.zeros(old_xyz.shape[:2], np.uint8)
    old_label[20:40, 30:60] = 255
    warped = warp_via_field(old_label, field, old_label.shape,
                            interpolation=cv2.INTER_NEAREST)
    inter = np.logical_and(warped > 127, old_label > 127).sum()
    union = np.logical_or(warped > 127, old_label > 127).sum()
    assert inter / union > 0.9  # IoU of the recovered block


def test_ncc_extremes():
    rng = np.random.default_rng(0)
    a = rng.random((64, 64)).astype(np.float32)
    assert ncc(a, a) > 0.999
    assert abs(ncc(a, rng.random((64, 64)).astype(np.float32))) < 0.2


def test_fit_affine_orb_recovers_shift():
    rng = np.random.default_rng(1)
    img = (rng.random((256, 256)) * 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (5, 5), 0)
    M_true = np.float32([[1, 0, 17], [0, 1, -9]])
    moved = cv2.warpAffine(img, M_true, (256, 256))
    M, inl = fit_affine_orb(img, moved)
    assert inl >= 25
    assert abs(M[0, 2] - 17) < 2 and abs(M[1, 2] + 9) < 2


def test_read_tifxyz_directory_layout(tmp_path):
    # Real bucket format discovered at probe time: a .tifxyz is a DIRECTORY containing
    # meta.json + x.tif + y.tif + z.tif planes.
    xyz = _surface(16, 24)
    d = tmp_path / "seg.tifxyz"
    d.mkdir()
    for i, name in enumerate(["x.tif", "y.tif", "z.tif"]):
        tifffile.imwrite(str(d / name), xyz[..., i])
    (d / "meta.json").write_text("{}")
    out = read_tifxyz(str(d))
    assert out.shape == (16, 24, 3)
    assert np.allclose(out, xyz, atol=1e-4)


def test_valid_masks_drop_minus_one_markers():
    # Real bucket meshes mark invalid pixels as (-1,-1,-1), not zeros.
    from repro.sota_data.register import _valid_points
    xyz = _surface(8, 8)
    xyz[0, 0] = (-1, -1, -1)
    xyz[1, 1] = (0, 0, 0)
    pts = _valid_points(xyz)
    assert len(pts) == 62  # both markers dropped
