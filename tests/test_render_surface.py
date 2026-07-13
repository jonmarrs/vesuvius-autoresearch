import glob
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repro.sota_data.render_surface import (
    assert_bounds_fit,
    build_point_map,
    sample_layers,
    surface_normals,
    write_render_fragment,
)


def _tilted_plane_mesh(n=40, scale=100.0):
    # vt = unit-square grid; v = same grid mapped to a tilted 3D plane z = 2x + 3y (+offset)
    us, vs = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n))
    vt = np.stack([us.ravel(), vs.ravel()], axis=1).astype(np.float32)
    x = us.ravel() * scale
    y = vs.ravel() * scale
    z = 2.0 * x + 3.0 * y + 10.0
    v = np.stack([x, y, z], axis=1).astype(np.float32)
    return v, vt


# ---- Task 1: point-map builder ----

def test_point_map_reproduces_analytic_plane():
    v, vt = _tilted_plane_mesh()
    pm, valid = build_point_map(v, vt, size=64)
    assert pm.shape == (64, 64, 3) and valid.shape == (64, 64)
    assert valid.mean() > 0.95
    xs, ys, zs = pm[..., 0], pm[..., 1], pm[..., 2]
    ok = valid
    assert np.nanmax(np.abs(zs[ok] - (2.0 * xs[ok] + 3.0 * ys[ok] + 10.0))) < 1e-2


def test_point_map_masks_outside_hull():
    v, vt = _tilted_plane_mesh()
    keep = vt[:, 0] + vt[:, 1] <= 1.0
    pm, valid = build_point_map(v[keep], vt[keep], size=64)
    assert not valid[-1, -1]
    assert np.isnan(pm[-1, -1, 0])
    assert valid[0, 0]


def test_assert_bounds_fit_raises_on_overflow():
    v, vt = _tilted_plane_mesh(scale=100.0)
    pm, valid = build_point_map(v, vt, size=32)
    # z = 2x + 3y + 10 reaches ~510 at x=y=100, so a fitting volume must exceed that
    assert_bounds_fit(pm, valid, (600, 600, 600))
    with pytest.raises(ValueError, match="bounds"):
        assert_bounds_fit(pm, valid, (50, 50, 50))


# ---- tifxyz -> sampler-ready point map ----

def test_pointmap_from_tifxyz_reorders_scales_and_masks():
    from repro.sota_data.render_surface import pointmap_from_tifxyz
    xyz = np.zeros((3, 3, 3), np.float32)
    xyz[0, 0] = [400.0, 800.0, 1200.0]   # (x,y,z) at level 0
    xyz[1, 1] = [-1.0, -1.0, -1.0]        # invalid sentinel
    # everything else stays (0,0,0) -> also invalid
    pm, valid = pointmap_from_tifxyz(xyz, level_div=4)
    assert valid[0, 0] and not valid[1, 1] and not valid[2, 2]
    # reordered to (z,y,x) and /4: (1200,800,400)/4 = (300,200,100)
    assert np.allclose(pm[0, 0], [300.0, 200.0, 100.0])
    assert np.isnan(pm[1, 1]).all()


# ---- Task 2: normals ----

def test_normals_on_tilted_plane_are_constant_and_unit():
    v, vt = _tilted_plane_mesh()
    pm, valid = build_point_map(v, vt, size=64)
    n = surface_normals(pm, valid, sign=1.0)
    core = n[8:-8, 8:-8]
    expect = np.array([-2.0, -3.0, 1.0])
    expect /= np.linalg.norm(expect)
    mean = np.nanmean(core.reshape(-1, 3), axis=0)
    assert np.linalg.norm(np.abs(mean) - np.abs(expect)) < 0.02
    norms = np.linalg.norm(core.reshape(-1, 3), axis=1)
    assert np.nanmax(np.abs(norms - 1.0)) < 1e-3


def test_normal_sign_flips_direction():
    v, vt = _tilted_plane_mesh()
    pm, valid = build_point_map(v, vt, size=64)
    a = surface_normals(pm, valid, sign=1.0)[32, 32]
    b = surface_normals(pm, valid, sign=-1.0)[32, 32]
    assert np.allclose(a, -b, atol=1e-5)


# ---- Task 3: sampler ----

def test_sampler_reads_known_field_along_flat_surface():
    Z, Y, X = 40, 80, 80
    vol = np.broadcast_to(np.arange(X, dtype=np.float32)[None, None, :], (Z, Y, X)).copy()

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    ys, xs = np.meshgrid(np.arange(10, 42), np.arange(10, 42), indexing="ij")
    pm = np.stack([np.full_like(xs, 20.0, float), ys.astype(float), xs.astype(float)],
                  axis=-1).astype(np.float32)
    valid = np.ones(pm.shape[:2], bool)
    normals = np.zeros_like(pm)
    normals[..., 0] = 1.0
    layers, stats = sample_layers(pm, valid, normals, fetch, n_layers=6, k0=-2, tile=16)
    assert layers.shape == (6, 32, 32)
    for k in range(6):
        assert np.nanmax(np.abs(layers[k] - xs)) < 1e-3
    assert stats["valid_frac"] == 1.0


def test_sampler_masks_invalid_and_counts_clamp():
    Z, Y, X = 10, 20, 20
    vol = np.zeros((Z, Y, X), np.float32)

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    pm = np.zeros((16, 16, 3), np.float32)
    pm[..., 0] = 5
    pm[..., 1] = 5
    pm[..., 2] = 5
    valid = np.ones((16, 16), bool)
    valid[0, 0] = False
    normals = np.zeros_like(pm)
    normals[..., 0] = 1.0
    layers, stats = sample_layers(pm, valid, normals, fetch, n_layers=4, k0=-1, tile=16)
    assert (layers[:, 0, 0] == 0).all()
    assert 0.0 <= stats["clamped_frac"] <= 1.0


# ---- Task 4: writer ----

def test_writer_emits_layers_mask_provenance_no_label(tmp_path):
    layers = np.random.rand(26, 40, 40).astype(np.float32)
    valid = np.ones((40, 40), bool)
    valid[:5, :5] = False
    out = write_render_fragment(layers, valid, str(tmp_path), "seg_test",
                                {"segment": "s", "level": 2})
    assert len(glob.glob(f"{out}/layers/*.tif")) == 26
    assert glob.glob(f"{out}/*_inklabels.*") == []
    import json

    import cv2
    m = cv2.imread(f"{out}/seg_test_mask.png", 0)
    assert m[0, 0] == 0 and m[20, 20] == 255
    prov = json.load(open(f"{out}/seg_test_render_provenance.json"))
    assert prov["segment"] == "s" and prov["level"] == 2
