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
    xyz[0, 0] = [400.0, 800.0, 1200.0]  # (x,y,z) at level 0
    xyz[1, 1] = [-1.0, -1.0, -1.0]  # invalid sentinel
    # everything else stays (0,0,0) -> also invalid
    pm, valid = pointmap_from_tifxyz(xyz, level_div=4)
    assert valid[0, 0] and not valid[1, 1] and not valid[2, 2]
    # reordered to (z,y,x) and /4: (1200,800,400)/4 = (300,200,100)
    assert np.allclose(pm[0, 0], [300.0, 200.0, 100.0])
    assert np.isnan(pm[1, 1]).all()


def test_surface_structure_high_on_texture_zero_on_flat():
    from repro.sota_data.render_surface import surface_structure

    rng = np.random.default_rng(0)
    mask = np.ones((64, 64), bool)
    textured = rng.integers(40, 200, (64, 64)).astype(np.float32)  # fiber-like noise
    flat = np.full((64, 64), 100.0, np.float32)
    assert surface_structure(textured, mask) > 5.0
    assert surface_structure(flat, mask) < 1e-6
    # empty (all-zero) render -> no valid pixels -> 0
    assert surface_structure(np.zeros((64, 64), np.float32), mask) == 0.0


def test_cli_wires_args_and_infers_when_auto(monkeypatch, tmp_path):
    # Mock the (network/GPU-bound) render_region so we test only the CLI's wiring.
    import repro.sota_data.render_cli as cli

    calls = []

    def fake_render_region(
        seg,
        obj,
        vol,
        y0,
        x0,
        size,
        level,
        sign,
        out_root,
        frag_id=None,
        obj_level_div=None,
        extra_prov=None,
    ):
        calls.append(
            {
                "seg": seg,
                "y0": y0,
                "x0": x0,
                "size": size,
                "level": level,
                "sign": sign,
                "div": obj_level_div,
                "fid": frag_id,
            }
        )
        d = tmp_path / (frag_id or seg)
        (d / "layers").mkdir(parents=True, exist_ok=True)
        import numpy as np
        import tifffile

        for k in range(26):
            tifffile.imwrite(
                str(d / "layers" / f"{17 + k:02d}.tif"), np.full((8, 8), 100, np.uint8)
            )
        import cv2

        cv2.imwrite(
            str(d / f"{frag_id or seg}_mask.png"), np.full((8, 8), 255, np.uint8)
        )
        return str(d), {"valid_frac": 1.0, "clamped_frac": 0.0}

    monkeypatch.setattr(cli, "render_region", fake_render_region)
    obj = tmp_path / "20240711_original.obj"
    obj.write_text("v 0 0 0\nvt 0 0\n")
    rc = cli.main(
        [
            "--obj",
            str(obj),
            "--volume",
            "vesuvius-challenge-open-data/x.zarr",
            "--out",
            str(tmp_path),
            "--region",
            "100",
            "200",
            "1024",
            "--level",
            "2",
            "--scale",
            "2",
        ]
    )
    assert rc == 0
    final = calls[-1]
    assert final["y0"] == 100 and final["x0"] == 200 and final["size"] == 1024
    assert final["div"] == 2.0 and final["seg"] == "20240711"  # obj basename -> frag id


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
    vol = np.broadcast_to(
        np.arange(X, dtype=np.float32)[None, None, :], (Z, Y, X)
    ).copy()

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    ys, xs = np.meshgrid(np.arange(10, 42), np.arange(10, 42), indexing="ij")
    pm = np.stack(
        [np.full_like(xs, 20.0, float), ys.astype(float), xs.astype(float)], axis=-1
    ).astype(np.float32)
    valid = np.ones(pm.shape[:2], bool)
    normals = np.zeros_like(pm)
    normals[..., 0] = 1.0
    layers, stats = sample_layers(pm, valid, normals, fetch, n_layers=6, k0=-2, tile=16)
    assert layers.shape == (6, 32, 32)
    for k in range(6):
        assert np.nanmax(np.abs(layers[k] - xs)) < 1e-3
    assert stats["valid_frac"] == 1.0


def test_sampler_grouped_prefetch_matches_per_tile():
    # Super-tile prefetching is a pure throughput optimization: results must be
    # bit-identical whether tiles are fetched individually (group=1 / tiny cap forcing
    # the fallback) or via one grouped fetch.
    Z, Y, X = 30, 96, 96
    rng = np.random.default_rng(1)
    vol = rng.random((Z, Y, X)).astype(np.float32)
    fetches = []

    def fetch(z0, z1, y0, y1, x0, x1):
        fetches.append((z1 - z0) * (y1 - y0) * (x1 - x0))
        return vol[z0:z1, y0:y1, x0:x1]

    ys, xs = np.meshgrid(np.arange(10, 74), np.arange(10, 74), indexing="ij")
    pm = np.stack(
        [np.full_like(xs, 15.0, float), ys.astype(float), xs.astype(float)], axis=-1
    ).astype(np.float32)
    valid = np.ones(pm.shape[:2], bool)
    normals = np.zeros_like(pm)
    normals[..., 0] = 1.0
    grouped, s1 = sample_layers(
        pm, valid, normals, fetch, n_layers=5, k0=-2, tile=16, group=8
    )
    n_grouped_fetches = len(fetches)
    fetches.clear()
    pertile, s2 = sample_layers(
        pm,
        valid,
        normals,
        fetch,
        n_layers=5,
        k0=-2,
        tile=16,
        group=8,
        group_max_voxels=1,
    )  # force per-tile fallback
    n_pertile_fetches = len(fetches)
    assert np.array_equal(grouped, pertile)
    assert s1 == s2
    assert (
        n_grouped_fetches < n_pertile_fetches
    )  # grouping actually reduced round-trips


def test_sampler_warm_capable_fetcher_matches_plain():
    # A warm()-capable fetcher (chunk-cached path) must produce identical output to a
    # plain callable, and warm() must be invoked with the member tile bboxes.
    Z, Y, X = 30, 96, 96
    rng = np.random.default_rng(2)
    vol = rng.random((Z, Y, X)).astype(np.float32)

    def plain(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    class Warmable:
        def __init__(self):
            self.warm_calls = 0

        def warm(self, bboxes):
            self.warm_calls += 1
            assert all(len(b) == 6 for b in bboxes)

        def __call__(self, z0, z1, y0, y1, x0, x1):
            return vol[z0:z1, y0:y1, x0:x1]

    ys, xs = np.meshgrid(np.arange(10, 74), np.arange(10, 74), indexing="ij")
    pm = np.stack(
        [np.full_like(xs, 15.0, float), ys.astype(float), xs.astype(float)], axis=-1
    ).astype(np.float32)
    valid = np.ones(pm.shape[:2], bool)
    normals = np.zeros_like(pm)
    normals[..., 0] = 1.0
    a, s1 = sample_layers(
        pm, valid, normals, plain, n_layers=5, k0=-2, tile=16, group=4
    )
    w = Warmable()
    b, s2 = sample_layers(pm, valid, normals, w, n_layers=5, k0=-2, tile=16, group=4)
    assert np.array_equal(a, b) and s1 == s2
    assert w.warm_calls >= 1


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
    out = write_render_fragment(
        layers, valid, str(tmp_path), "seg_test", {"segment": "s", "level": 2}
    )
    assert len(glob.glob(f"{out}/layers/*.tif")) == 26
    assert glob.glob(f"{out}/*_inklabels.*") == []
    import json

    import cv2

    m = cv2.imread(f"{out}/seg_test_mask.png", 0)
    assert m[0, 0] == 0 and m[20, 20] == 255
    prov = json.load(open(f"{out}/seg_test_render_provenance.json"))
    assert prov["segment"] == "s" and prov["level"] == 2


# ---- tifxyz input path (released geometry grids, e.g. PHerc1667) ----


def _write_tifxyz_dir(tmp_path, xyz):
    import tifffile

    d = tmp_path / "seg-on-scan-2.4um.tifxyz"
    d.mkdir()
    for c, name in enumerate("xyz"):
        tifffile.imwrite(str(d / f"{name}.tif"), xyz[..., c])
    return str(d)


def test_read_tifxyz_stacks_planes_in_xyz_order(tmp_path):
    from repro.sota_data.render_surface import read_tifxyz

    xyz = np.zeros((6, 5, 3), np.float32)
    xyz[..., 0] = 11.0  # x
    xyz[..., 1] = 22.0  # y
    xyz[..., 2] = 33.0  # z
    d = _write_tifxyz_dir(tmp_path, xyz)
    got = read_tifxyz(d)
    assert got.shape == (6, 5, 3)
    assert got[0, 0, 0] == 11.0 and got[0, 0, 1] == 22.0 and got[0, 0, 2] == 33.0


def test_render_region_tifxyz_slices_scales_and_writes_labelfree(tmp_path, monkeypatch):
    import repro.sota_data.render_surface as rs

    # flat surface: 48x48 grid at z=40 (level-0 voxel coords), x/y = 4*grid index + 40
    n = 48
    ys, xs = np.meshgrid(
        np.arange(n, dtype=np.float32), np.arange(n, dtype=np.float32), indexing="ij"
    )
    xyz = np.stack([4.0 * xs + 40.0, 4.0 * ys + 40.0, np.full_like(xs, 40.0)], axis=-1)
    xyz[0, 0] = -1.0  # invalid sentinel survives into the mask
    d = _write_tifxyz_dir(tmp_path, xyz)

    # level-1 volume holding a linear field in x, values in [0,255]
    Z, Y, X = 40, 120, 120
    vol = np.broadcast_to(
        np.arange(X, dtype=np.float32)[None, None, :], (Z, Y, X)
    ).copy()
    fetches = []

    def fake_zarr_fetch(uri, level):
        def fetch(z0, z1, y0, y1, x0, x1):
            fetches.append((z0, z1, y0, y1, x0, x1))
            return vol[z0:z1, y0:y1, x0:x1]

        return fetch, (Z, Y, X)

    monkeypatch.setattr(rs, "zarr_fetch", fake_zarr_fetch)

    out_seg, stats = rs.render_region_tifxyz(
        "segX",
        d,
        "bucket/vol.zarr",
        y0=8,
        x0=8,
        size=32,
        level=1,
        sign=1.0,
        out_root=str(tmp_path / "out"),
        frag_id="segX_r0",
    )
    # 26 layers + mask + provenance, and NO fabricated ink label
    assert len(glob.glob(f"{out_seg}/layers/*.tif")) == 26
    assert glob.glob(f"{out_seg}/*_inklabels.*") == []
    import json

    prov = json.load(open(f"{out_seg}/segX_r0_render_provenance.json"))
    assert prov["geometry"] == "tifxyz" and prov["region_px"] == [8, 8, 32]
    assert prov["level"] == 1 and prov["segment"] == "segX"
    # level-0 coords / 2**level: grid px (8..39) -> x = (4*g+40)/2 in [36..98] at level 1
    assert stats["valid_frac"] == 1.0  # the sentinel px was sliced away by the region
    zs = [f[0] for f in fetches]
    xsl = [f[4] for f in fetches]
    # depth: surface z=40/2=20 at level 1, k=-13..12 + interp pad -> z in [7, 35)
    assert fetches and min(zs) >= 6 and max(f[1] for f in fetches) <= 36
    assert min(xsl) >= 30 and max(f[5] for f in fetches) <= 105
    # center layer reads the linear-x field at level-1 coords
    import tifffile

    mids = sorted(glob.glob(f"{out_seg}/layers/*.tif"))
    mid = tifffile.imread(mids[13]).astype(np.float32)
    expect = (4.0 * (np.arange(8, 40, dtype=np.float32)) + 40.0) / 2.0
    assert np.abs(mid[16] - expect).max() < 1.0


def test_cli_tifxyz_mode_wires_args_no_scale_probe(monkeypatch, tmp_path):
    import repro.sota_data.render_cli as cli

    calls = []

    def fake_rrt(
        seg,
        tifxyz,
        vol,
        y0,
        x0,
        size,
        level,
        sign,
        out_root,
        frag_id=None,
        extra_prov=None,
    ):
        calls.append(
            {
                "seg": seg,
                "tifxyz": tifxyz,
                "y0": y0,
                "x0": x0,
                "size": size,
                "level": level,
                "sign": sign,
                "fid": frag_id,
            }
        )
        return str(tmp_path / "o"), {"valid_frac": 1.0, "clamped_frac": 0.0}

    def boom(*a, **k):
        raise AssertionError("scale probe must not run for tifxyz input")

    monkeypatch.setattr(cli, "render_region_tifxyz", fake_rrt)
    monkeypatch.setattr(cli, "infer_scale", boom)
    rc = cli.main(
        [
            "--tifxyz",
            "bucket/seg/mesh/seg-on-scan.tifxyz",
            "--volume",
            "bucket/vol.zarr",
            "--out",
            str(tmp_path),
            "--region",
            "5",
            "6",
            "512",
            "--level",
            "1",
        ]
    )
    assert rc == 0
    c = calls[-1]
    assert c["y0"] == 5 and c["x0"] == 6 and c["size"] == 512 and c["level"] == 1
    assert c["seg"] == "seg-on-scan"  # frag id from tifxyz dirname
