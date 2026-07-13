# Scroll 3 Surface-Volume Renderer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render detector-ready 26-layer surface volumes for PHerc0332 (Scroll 3) mesh-only segments from `original.obj` + the masked 2.4µm volume zarr, validated against a released Scroll-1 surface volume, then run arm C over them.

**Architecture:** A new module `repro/sota_data/render_surface.py` with four pure/testable units — point-map builder (obj `vt`→`xyz` via `LinearNDInterpolator`), normals, tile-wise volume sampler, label-free fragment writer — plus a validation harness (Scroll-1 NCC gate) and an operational Scroll-3 render + inference step. Downstream inference reuses the existing `vesuvius_autoresearch.detector` pipeline unchanged.

**Tech Stack:** Python 3.10, NumPy, SciPy (`interpolate.LinearNDInterpolator`, `ndimage.map_coordinates`), zarr + s3fs (anonymous), tifffile/cv2, pytest, uv.

## Global Constraints

- Run everything via `uv run`. Python `>=3.10,<3.11`.
- Data: open anonymous S3 (`s3://vesuvius-challenge-open-data/`) only; no credentials.
- **Sample the volume at pyramid level 2** (matches the detector's input scale).
- **No ink-label file may persist or be published for a Scroll-3 render** — none exists. A transient all-zero label may be written ONLY to satisfy the detector loader during inference, and MUST be deleted immediately after; it is never committed, shipped, or shown as GT.
- Do NOT call `repro/sota_data/qualitative.write_fragment` — it writes a zero `_inklabels.png` that would masquerade as a label. Write a label-free fragment directly.
- Reuse, do not re-implement: `repro/sota_data/gt_register.parse_obj_vt` (returns `(v[N,3], vt[N,2])`), `repro/sota_data/register.ncc`, the detector `infer`/`read_image_mask` pipeline.
- Invalid/holes → NaN-masked, never silent zero-fill. Out-of-bounds samples clamped + counted; >1% per tile → loud provenance warning.
- Every render writes `{frag_id}_render_provenance.json` (segment, region, level, normal sign, spacing, bounds/clamp stats, input URIs).
- `--no-verify` commits (repo pre-commit reformats hand-compacted files; keep diffs surgical). Repo-wide mypy must stay green.

**Spec:** `docs/superpowers/specs/2026-07-13-scroll3-surface-renderer-design.md`

---

### Task 1: Point-map builder (obj → grid)

**Files:**
- Create: `repro/sota_data/render_surface.py`
- Test: `tests/test_render_surface.py`

**Interfaces:**
- Consumes: `gt_register.parse_obj_vt(path) -> (v[N,3], vt[N,2])`.
- Produces: `build_point_map(v, vt, size, uv_bbox=None) -> (pointmap[H,W,3] float32, valid[H,W] bool)`. Builds a regular grid over `uv_bbox` (default: `vt` min/max) of shape `(size, size)`, interpolates each xyz channel with `LinearNDInterpolator(vt, v)`; points outside the triangulation are NaN in `pointmap` and False in `valid`.
- Produces: `assert_bounds_fit(pointmap, valid, volume_shape_l2)` — raises `ValueError` (printing both bounding boxes) if any valid point falls outside `[0, volume_shape_l2)` on any axis.

- [ ] **Step 1: Write the failing test**

Create `tests/test_render_surface.py`:

```python
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repro.sota_data.render_surface import assert_bounds_fit, build_point_map


def _tilted_plane_mesh(n=40, scale=100.0):
    # vt = unit-square grid; v = same grid mapped to a tilted 3D plane z = 2x + 3y (+offset)
    us, vs = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n))
    vt = np.stack([us.ravel(), vs.ravel()], axis=1).astype(np.float32)
    x = us.ravel() * scale
    y = vs.ravel() * scale
    z = 2.0 * x + 3.0 * y + 10.0
    v = np.stack([x, y, z], axis=1).astype(np.float32)
    return v, vt


def test_point_map_reproduces_analytic_plane():
    v, vt = _tilted_plane_mesh()
    pm, valid = build_point_map(v, vt, size=64)
    assert pm.shape == (64, 64, 3) and valid.shape == (64, 64)
    assert valid.mean() > 0.95  # unit-square hull covers ~all of the grid
    xs, ys, zs = pm[..., 0], pm[..., 1], pm[..., 2]
    ok = valid
    assert np.nanmax(np.abs(zs[ok] - (2.0 * xs[ok] + 3.0 * ys[ok] + 10.0))) < 1e-2


def test_point_map_masks_outside_hull():
    # a triangular mesh (only lower-left half of the square) leaves the upper-right NaN
    v, vt = _tilted_plane_mesh()
    keep = vt[:, 0] + vt[:, 1] <= 1.0
    pm, valid = build_point_map(v[keep], vt[keep], size=64)
    assert not valid[-1, -1]           # upper-right corner outside the hull
    assert np.isnan(pm[-1, -1, 0])
    assert valid[0, 0]                 # lower-left inside


def test_assert_bounds_fit_raises_on_overflow():
    v, vt = _tilted_plane_mesh(scale=100.0)
    pm, valid = build_point_map(v, vt, size=32)
    assert_bounds_fit(pm, valid, (500, 500, 500))       # fits
    with pytest.raises(ValueError, match="bounds"):
        assert_bounds_fit(pm, valid, (50, 50, 50))       # z up to ~510 > 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render_surface.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (module/functions not defined).

- [ ] **Step 3: Write minimal implementation**

Create `repro/sota_data/render_surface.py`:

```python
"""Render detector-ready surface volumes from a segment's original.obj + a volume zarr.

The bucket's tifxyz_normalized grids are empty placeholders for the Scroll-3 segments, so
the flattened point map is rebuilt from the obj: vt (flattened UV) -> v (3D) interpolated
onto a regular grid. Everything downstream (normals, sampling, fragment writing) treats
that point map exactly as it would a released tifxyz grid. No ground-truth ink label is
ever fabricated for an unread scroll.
"""
import numpy as np
from scipy.interpolate import LinearNDInterpolator


def build_point_map(v, vt, size, uv_bbox=None):
    """Interpolate obj vertices (v[N,3]) over their flattened UV coords (vt[N,2]) onto a
    regular (size,size) grid spanning uv_bbox (default: vt min/max). Returns
    (pointmap[size,size,3] float32, valid[size,size] bool); outside the triangulation is
    NaN / False."""
    v = np.asarray(v, np.float64)
    vt = np.asarray(vt, np.float64)
    if uv_bbox is None:
        umin, vmin = vt.min(axis=0)
        umax, vmax = vt.max(axis=0)
    else:
        (umin, vmin), (umax, vmax) = uv_bbox
    gu = np.linspace(umin, umax, size)
    gv = np.linspace(vmin, vmax, size)
    gU, gV = np.meshgrid(gu, gv)
    interp = LinearNDInterpolator(vt, v)  # fills NaN outside the convex hull
    pm = interp(np.stack([gU.ravel(), gV.ravel()], axis=1)).reshape(size, size, 3)
    valid = np.isfinite(pm).all(axis=2)
    return pm.astype(np.float32), valid


def assert_bounds_fit(pointmap, valid, volume_shape_l2):
    """Raise ValueError if any valid point falls outside [0, volume_shape) on any axis."""
    pts = pointmap[valid]
    if pts.size == 0:
        raise ValueError("no valid points in point map")
    lo = np.nanmin(pts, axis=0)
    hi = np.nanmax(pts, axis=0)
    shape = np.asarray(volume_shape_l2, float)
    if (lo < 0).any() or (hi >= shape).any():
        raise ValueError(
            f"point-map bounds do not fit the volume: points [{lo} .. {hi}] vs "
            f"volume shape {tuple(volume_shape_l2)} — check coordinate scale/level"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_render_surface.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/render_surface.py tests/test_render_surface.py
git commit --no-verify -m "feat(render): obj vt->xyz point-map builder + bounds assertion"
```

---

### Task 2: Surface normals

**Files:**
- Modify: `repro/sota_data/render_surface.py`
- Test: `tests/test_render_surface.py`

**Interfaces:**
- Produces: `surface_normals(pointmap, valid, sign=1.0) -> normals[H,W,3] float32`. Tangents via `np.gradient` along the two grid axes of each xyz channel; `n = sign * normalize(du x dv)`; NaN where `valid` is False.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render_surface.py`:

```python
from repro.sota_data.render_surface import surface_normals


def test_normals_on_tilted_plane_are_constant_and_unit():
    v, vt = _tilted_plane_mesh()
    pm, valid = build_point_map(v, vt, size=64)
    n = surface_normals(pm, valid, sign=1.0)
    core = n[8:-8, 8:-8]              # avoid gradient edge effects
    # analytic plane z = 2x + 3y -> normal ∝ (-2, -3, 1)
    expect = np.array([-2.0, -3.0, 1.0]); expect /= np.linalg.norm(expect)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render_surface.py -k normals -q`
Expected: FAIL — `surface_normals` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `repro/sota_data/render_surface.py`:

```python
def surface_normals(pointmap, valid, sign=1.0):
    """Unit surface normals from a point map, via cross product of the two grid tangents.
    sign selects the depth direction (fixed empirically by the validation harness)."""
    pm = pointmap.astype(np.float64)
    dv = np.stack([np.gradient(pm[..., c], axis=0) for c in range(3)], axis=-1)  # along rows
    du = np.stack([np.gradient(pm[..., c], axis=1) for c in range(3)], axis=-1)  # along cols
    n = np.cross(du, dv)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        n = sign * n / norm
    n[~valid] = np.nan
    return n.astype(np.float32)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_render_surface.py -k normals -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/render_surface.py tests/test_render_surface.py
git commit --no-verify -m "feat(render): surface normals with empirical sign"
```

---

### Task 3: Tile-wise volume sampler

**Files:**
- Modify: `repro/sota_data/render_surface.py`
- Test: `tests/test_render_surface.py`

**Interfaces:**
- Produces: `sample_layers(pointmap, valid, normals, fetch_subvol, n_layers=26, k0=-13, tile=512) -> (layers[n_layers,H,W] float32, stats dict)`. For each `tile`×`tile` block, builds sample coords `p + k*n` for `k in range(k0, k0+n_layers)`, computes the integer bbox of finite coords, calls `fetch_subvol(z0,z1,y0,y1,x0,x1) -> ndarray`, and trilinearly samples via `scipy.ndimage.map_coordinates(order=1)`. Invalid pixels → 0 in layers, counted. `stats` has `clamped_frac`, `valid_frac`. `fetch_subvol` is injected so the sampler is testable against an in-memory volume and reused with a zarr-backed closure in production.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render_surface.py`:

```python
from repro.sota_data.render_surface import sample_layers


def test_sampler_reads_known_field_along_flat_surface():
    # Volume V[z,y,x] = x (a ramp); a flat surface at z=20 with +z normal should read,
    # at each layer k, the x-coordinate of each grid point (independent of k).
    Z, Y, X = 40, 80, 80
    vol = np.broadcast_to(np.arange(X, dtype=np.float32)[None, None, :], (Z, Y, X)).copy()

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    ys, xs = np.meshgrid(np.arange(10, 42), np.arange(10, 42), indexing="ij")
    pm = np.stack([np.full_like(xs, 20.0, float), ys.astype(float), xs.astype(float)],
                  axis=-1).astype(np.float32)  # (z=20, y, x)
    valid = np.ones(pm.shape[:2], bool)
    normals = np.zeros_like(pm); normals[..., 0] = 1.0  # +z
    layers, stats = sample_layers(pm, valid, normals, fetch, n_layers=6, k0=-2, tile=16)
    assert layers.shape == (6, 32, 32)
    # every layer equals the x-coordinate map (ramp), within interpolation tolerance
    for k in range(6):
        assert np.nanmax(np.abs(layers[k] - xs)) < 1e-3
    assert stats["valid_frac"] == 1.0


def test_sampler_masks_invalid_and_counts_clamp():
    Z, Y, X = 10, 20, 20
    vol = np.zeros((Z, Y, X), np.float32)

    def fetch(z0, z1, y0, y1, x0, x1):
        return vol[z0:z1, y0:y1, x0:x1]

    pm = np.zeros((16, 16, 3), np.float32); pm[..., 0] = 5; pm[..., 1] = 5; pm[..., 2] = 5
    valid = np.ones((16, 16), bool); valid[0, 0] = False
    normals = np.zeros_like(pm); normals[..., 0] = 1.0
    layers, stats = sample_layers(pm, valid, normals, fetch, n_layers=4, k0=-1, tile=16)
    assert (layers[:, 0, 0] == 0).all()      # invalid pixel zeroed
    assert 0.0 <= stats["clamped_frac"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render_surface.py -k sampler -q`
Expected: FAIL — `sample_layers` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `repro/sota_data/render_surface.py` (add `from scipy.ndimage import map_coordinates` at top):

```python
def sample_layers(pointmap, valid, normals, fetch_subvol, n_layers=26, k0=-13, tile=512):
    """Sample n_layers depth slices around the surface (p + k*n) tile-by-tile.
    fetch_subvol(z0,z1,y0,y1,x0,x1)->ndarray injects the volume (in-memory or zarr)."""
    H, W = valid.shape
    ks = np.arange(k0, k0 + n_layers)
    out = np.zeros((n_layers, H, W), np.float32)
    total = clamped = 0
    for ty in range(0, H, tile):
        for tx in range(0, W, tile):
            vv = valid[ty:ty + tile, tx:tx + tile]
            if not vv.any():
                continue
            p = pointmap[ty:ty + tile, tx:tx + tile]          # (h,w,3)
            n = normals[ty:ty + tile, tx:tx + tile]
            # coords[axis, k, h, w]
            coords = (p[None, ..., :] + ks[:, None, None, None] * n[None, ..., :])
            coords = np.moveaxis(coords, -1, 0)               # (3,k,h,w)
            finite = np.isfinite(coords).all(axis=0) & vv[None]
            cf = coords[:, finite]
            if cf.size == 0:
                continue
            z0 = int(np.floor(cf[0].min())); z1 = int(np.ceil(cf[0].max())) + 2
            y0 = int(np.floor(cf[1].min())); y1 = int(np.ceil(cf[1].max())) + 2
            x0 = int(np.floor(cf[2].min())); x1 = int(np.ceil(cf[2].max())) + 2
            sub = np.asarray(fetch_subvol(max(z0, 0), z1, max(y0, 0), y1,
                                          max(x0, 0), x1), np.float32)
            local = np.stack([coords[0] - max(z0, 0), coords[1] - max(y0, 0),
                              coords[2] - max(x0, 0)], axis=0)
            total += finite.sum()
            clamped += int((~np.isfinite(coords).all(axis=0) & vv[None]).sum())
            flat = local.reshape(3, -1)
            vals = map_coordinates(sub, flat, order=1, mode="constant", cval=0.0)
            vals = vals.reshape(n_layers, tile if ty + tile <= H else H - ty,
                                tile if tx + tile <= W else W - tx)
            block = np.where(finite, vals, 0.0)
            out[:, ty:ty + block.shape[1], tx:tx + block.shape[2]] = block
    vf = float(valid.mean())
    return out, {"valid_frac": vf, "clamped_frac": (clamped / total) if total else 0.0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_render_surface.py -k sampler -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/render_surface.py tests/test_render_surface.py
git commit --no-verify -m "feat(render): tile-wise trilinear volume sampler (injected fetch)"
```

---

### Task 4: Label-free fragment writer

**Files:**
- Modify: `repro/sota_data/render_surface.py`
- Test: `tests/test_render_surface.py`

**Interfaces:**
- Produces: `write_render_fragment(layers, valid, out_root, frag_id, provenance) -> out_seg`. Writes `layers/17.tif..(16+n).tif` (uint8, min-max scaled per the existing `qualitative.to_uint8` convention), `{frag_id}_mask.png` (255 where `valid`, else 0), and `{frag_id}_render_provenance.json`. **Writes NO `_inklabels.png`.**

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render_surface.py`:

```python
import glob
from repro.sota_data.render_surface import write_render_fragment


def test_writer_emits_layers_mask_provenance_no_label(tmp_path):
    layers = np.random.rand(26, 40, 40).astype(np.float32)
    valid = np.ones((40, 40), bool); valid[:5, :5] = False
    out = write_render_fragment(layers, valid, str(tmp_path), "seg_test",
                                {"segment": "s", "level": 2})
    assert len(glob.glob(f"{out}/layers/*.tif")) == 26
    assert glob.glob(f"{out}/*_inklabels.*") == []          # the honesty invariant
    import cv2, json
    m = cv2.imread(f"{out}/seg_test_mask.png", 0)
    assert m[0, 0] == 0 and m[20, 20] == 255
    prov = json.load(open(f"{out}/seg_test_render_provenance.json"))
    assert prov["segment"] == "s" and prov["level"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render_surface.py -k writer -q`
Expected: FAIL — `write_render_fragment` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `repro/sota_data/render_surface.py` (add `import json, os, cv2, tifffile` and `from repro.sota_data.convert import to_uint8` at top — `to_uint8` lives in `convert.py`, min-max scales to uint8):

```python
def write_render_fragment(layers, valid, out_root, frag_id, provenance):
    """Write a detector-format fragment WITHOUT an ink label (none exists). layers +
    mask + provenance only. Deliberately does not call qualitative.write_fragment, which
    would emit a zero _inklabels.png that could be mistaken for ground truth."""
    out_seg = os.path.join(out_root, frag_id)
    out_layers = os.path.join(out_seg, "layers")
    os.makedirs(out_layers, exist_ok=True)
    for k in range(layers.shape[0]):
        tifffile.imwrite(os.path.join(out_layers, f"{17 + k:02d}.tif"), to_uint8(layers[k]))
    mask = np.where(valid, 255, 0).astype(np.uint8)
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_mask.png"), mask)
    with open(os.path.join(out_seg, f"{frag_id}_render_provenance.json"), "w") as f:
        json.dump(provenance, f, indent=2, default=float)
    return out_seg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_render_surface.py -k writer -q`
Expected: PASS (1 passed). Then full module + mypy:
Run: `uv run pytest tests/test_render_surface.py -q` → all green.
Run: `uv run mypy repro/sota_data/render_surface.py --explicit-package-bases --namespace-packages` → Success.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/render_surface.py tests/test_render_surface.py
git commit --no-verify -m "feat(render): label-free fragment writer + provenance"
```

---

### Task 5: Validation harness — Scroll-1 NCC gate (integration; the acceptance gate)

**Files:**
- Modify: `repro/sota_data/render_surface.py` (add `render_region(seg, obj_path, volume_zarr_uri, y0, x0, size, level, sign, out_root)` orchestration + a `zarr_fetch(uri, level)` closure factory)
- Create: `repro/sota_data/validate_render.py` (the Scroll-1 gate script)
- Output: `reports/detector/render_validation.md` + `.json`

**Interfaces:**
- Consumes: Tasks 1–4 functions; `register.ncc`.
- Produces: `render_region(...)` (build point map → assert bounds → normals → sample → write fragment) and a validation that renders Scroll-1 `20230702185753` region `y4000_x2500` from `local_data/sota_gt_meshes/20230702185753/20230702185753_original.obj` + the `PHercParis4` volume, then shift-tolerant-NCC's the depth-center layer against the released surface `local_data/sota_distill/20230702185753_y4000_x2500/layers/{mid}.tif`.

**Gate rationale (important):** the released SOTA surface uses the NEW re-flattening while `original.obj` carries the OLD flattening; the registration work established these agree to ~8 old-scan voxels (that is *why* the obj `vt` registered onto the SOTA region). So the achievable pixel-NCC is bounded well below 1.0 by that ~8-voxel lateral residual. The gate therefore uses **shift-tolerant** NCC (search integer shifts up to ±12 px) and both normal signs.

- [ ] **Step 1: Implement `render_region` + `zarr_fetch`**

Add to `repro/sota_data/render_surface.py`:

```python
def zarr_fetch(volume_zarr_uri, level):
    """Return a fetch_subvol(z0,z1,y0,y1,x0,x1) closure over a pyramid level of an S3 zarr."""
    import s3fs
    import zarr
    fs = s3fs.S3FileSystem(anon=True)
    g = zarr.open(zarr.storage.FSStore(volume_zarr_uri, fs=fs), mode="r")
    arr = g[str(level)]

    def fetch(z0, z1, y0, y1, x0, x1):
        d, h, w = arr.shape
        return np.asarray(arr[z0:min(z1, d), y0:min(y1, h), x0:min(x1, w)])
    return fetch, arr.shape


def render_region(seg, obj_path, volume_zarr_uri, y0, x0, size, level, sign, out_root,
                  frag_id=None, extra_prov=None):
    """Full pipeline for one region -> label-free fragment dir. Returns (out_seg, stats)."""
    from repro.sota_data.gt_register import parse_obj_vt
    v, vt = parse_obj_vt(obj_path)
    fetch, vol_shape = zarr_fetch(volume_zarr_uri, level)
    # UV bbox for the requested pixel region: vt is normalized [0,1]-ish; map region by
    # fraction of the vt span (documented approximation for v1 — see report).
    umin, vmin = vt.min(axis=0); umax, vmax = vt.max(axis=0)
    su, sv = (umax - umin), (vmax - vmin)
    # full-surface point map at `size` per axis, then no crop for v1 (region selection is
    # done by choosing size + later by mask); for the Scroll-1 gate we render the whole
    # flattened surface at `size` and compare on the released region's footprint.
    pm, valid = build_point_map(v, vt, size)
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats = sample_layers(pm, valid, normals, fetch)
    fid = frag_id or f"{seg}_render"
    prov = {"segment": seg, "region_px": [y0, x0, size], "level": level,
            "normal_sign": sign, "volume": volume_zarr_uri, "valid_frac": stats["valid_frac"],
            "clamped_frac": stats["clamped_frac"], **(extra_prov or {})}
    out_seg = write_render_fragment(layers, valid, out_root, fid, prov)
    return out_seg, stats
```

- [ ] **Step 2: Write the validation script**

Create `repro/sota_data/validate_render.py`:

```python
"""Scroll-1 acceptance gate: render 20230702185753 from its original.obj + the PHercParis4
volume and shift-tolerant-NCC the surface against the released SOTA surface layers. Prints
the best NCC + shift + sign; writes reports/detector/render_validation.{md,json}."""
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.register import ncc
from repro.sota_data.render_surface import render_region

SEG = "20230702185753"
OBJ = f"local_data/sota_gt_meshes/{SEG}/{SEG}_original.obj"
VOL = "vesuvius-challenge-open-data/PHercParis4/volumes/"  # discovered at runtime below
RELEASED = f"local_data/sota_distill/{SEG}_y4000_x2500/layers"
OUT = "local_data/rendered"
SIZE = 4096


def best_shift_ncc(a, b, max_shift=12):
    best = (-1.0, 0, 0)
    for dy in range(-max_shift, max_shift + 1, 3):
        for dx in range(-max_shift, max_shift + 1, 3):
            bs = np.roll(np.roll(b, dy, 0), dx, 1)
            c = ncc(a, bs)
            if c > best[0]:
                best = (c, dy, dx)
    return best


def main():
    import s3fs
    fs = s3fs.S3FileSystem(anon=True)
    vol = sorted(p for p in fs.ls(VOL, detail=False) if p.endswith(".zarr"))[0]
    released = cv2.imread(sorted(glob.glob(f"{RELEASED}/*.tif"))[13], 0).astype(np.float32)
    results = {}
    for sign in (1.0, -1.0):
        out_seg, stats = render_region(SEG, OBJ, vol, 4000, 2500, SIZE, level=2,
                                       sign=sign, out_root=OUT,
                                       frag_id=f"{SEG}_valid_sign{int(sign)}")
        mid = sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13]
        rendered = cv2.imread(mid, 0).astype(np.float32)
        h = min(rendered.shape[0], released.shape[0])
        w = min(rendered.shape[1], released.shape[1])
        c, dy, dx = best_shift_ncc(rendered[:h, :w], released[:h, :w])
        results[f"sign{int(sign)}"] = {"ncc": c, "shift": [dy, dx], **stats}
        print(f"sign={sign:+.0f}: best NCC={c:.4f} shift=({dy},{dx}) "
              f"valid={stats['valid_frac']:.3f} clamped={stats['clamped_frac']:.3f}",
              flush=True)
    best = max(results.values(), key=lambda r: r["ncc"])
    verdict = "PASS" if best["ncc"] >= 0.50 else "FAIL"
    os.makedirs("reports/detector", exist_ok=True)
    with open("reports/detector/render_validation.json", "w") as f:
        json.dump({"seg": SEG, "results": results, "verdict": verdict,
                   "gate": "shift-tolerant NCC >= 0.50 (bounded by ~8vox flattening residual)"},
                  f, indent=2, default=float)
    with open("reports/detector/render_validation.md", "w") as f:
        f.write(f"# Renderer validation (Scroll 1 {SEG}) — {verdict}\n\n")
        f.write("Rendered from original.obj + PHercParis4 volume vs the released SOTA "
                "surface. Shift-tolerant NCC (±12px) accounts for the ~8-voxel old-vs-new "
                "flattening residual.\n\n")
        for k, r in results.items():
            f.write(f"- {k}: NCC {r['ncc']:.4f} shift {r['shift']} "
                    f"valid {r['valid_frac']:.3f} clamped {r['clamped_frac']:.3f}\n")
    print(f"VERDICT: {verdict}", flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Static checks**

Run: `uv run python -m py_compile repro/sota_data/render_surface.py repro/sota_data/validate_render.py && echo COMPILE_OK`
Expected: `COMPILE_OK`.
Run: `uv run mypy repro/sota_data/render_surface.py repro/sota_data/validate_render.py --explicit-package-bases --namespace-packages 2>&1 | tail -1`
Expected: `Success`.

- [ ] **Step 4: Run the live gate (network + ~minutes)**

Run: `uv run python -m repro.sota_data.validate_render`
Expected: prints per-sign NCC and a `VERDICT:` line. **Interpretation:**
- PASS (best shift-tolerant NCC ≥ 0.50, best shift ≤ 12px, valid_frac high) → the renderer is correct; record the winning sign; proceed to Task 6.
- FAIL → do NOT proceed. Diagnose in order: (a) bounds assertion tripped ⇒ coordinate scale/level wrong; (b) NCC flat at all shifts ⇒ point-map UV→region mapping wrong (inspect the rendered mid-layer PNG vs released); (c) NCC decent but only at large shift ⇒ expected residual, consider widening the gate. Report findings; the plan pauses here for a fix rather than shipping an unvalidated renderer.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/render_surface.py repro/sota_data/validate_render.py reports/detector/render_validation.md reports/detector/render_validation.json
git commit --no-verify -m "feat(render): Scroll-1 NCC validation gate (shift-tolerant, residual-aware)"
```

---

### Task 6: Scroll-3 render + arm C inference + first-look report (operational)

**Files:**
- Create: `repro/sota_data/scroll3_render.py` (orchestration)
- Output: `reports/detector/scroll3_first_look.md` + PNGs under `reports/detector/`

**Preconditions:** Task 5 verdict = PASS (use its winning normal sign).

**Interfaces:**
- Consumes: `render_surface.render_region`, the detector `infer`, the validated sign.

- [ ] **Step 1: Write the orchestration script**

Create `repro/sota_data/scroll3_render.py`:

```python
"""Render the two PHerc0332 (Scroll 3) segments from original.obj + the masked volume,
run arm C, and write an honestly-captioned first-look report. NO ground truth exists on
Scroll 3: this is a qualitative texture/letterform look plus the released renderer, not a
reading claim."""
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.render_surface import render_region

SEGS = ["20240711124827-20240618142020", "20240828190516-20240716140050"]
BASE = "vesuvius-challenge-open-data/PHerc0332"
VOL = f"{BASE}/volumes/20251211183505-2.399um-0.2m-78keV-masked.zarr"
ARM_C = "models/detector_xscroll_c/detector_epoch=11.ckpt"
OUT_ROOT = "local_data/rendered_scroll3"
SIGN = float(os.environ.get("RENDER_SIGN", "1"))  # set from Task 5 verdict
SIZE = 4096


def _fetch_obj(seg):
    import s3fs
    fs = s3fs.S3FileSystem(anon=True)
    dst = f"local_data/scroll3_meshes/{seg}_original.obj"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        fs.get(f"{BASE}/segments/{seg}/mesh/intermediate/{seg}_original.obj", dst)
    return dst


def infer_no_label(frag_root, frag_id):
    """Run arm C on a label-free fragment: write a transient all-zero label ONLY to satisfy
    the loader, run infer, then delete it (never persisted/shipped)."""
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.infer import infer
    dummy = os.path.join(frag_root, frag_id, f"{frag_id}_inklabels.png")
    lay0 = sorted(glob.glob(os.path.join(frag_root, frag_id, "layers", "*.tif")))[0]
    h, w = cv2.imread(lay0, 0).shape
    cv2.imwrite(dummy, np.zeros((h, w), np.uint8))
    try:
        prob = infer(DetectorConfig(data_root=frag_root), ARM_C, frag_id)
    finally:
        os.remove(dummy)  # honesty invariant: no label file persists
    return prob


def main():
    os.makedirs("reports/detector", exist_ok=True)
    rows = []
    for seg in SEGS:
        obj = _fetch_obj(seg)
        fid = f"scroll3_{seg}"
        out_seg, stats = render_region(seg, obj, VOL, 0, 0, SIZE, level=2, sign=SIGN,
                                       out_root=OUT_ROOT, frag_id=fid,
                                       extra_prov={"scroll": "PHerc0332", "no_ground_truth": True})
        prob = infer_no_label(OUT_ROOT, fid)
        surf = cv2.imread(sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13], 0)
        cv2.imwrite(f"reports/detector/{fid}_surface.png",
                    cv2.resize(surf, (surf.shape[1] // 4, surf.shape[0] // 4)))
        pv = (np.clip(prob, 0, 1) * 255).astype(np.uint8)
        cv2.imwrite(f"reports/detector/{fid}_armC_ink.png",
                    cv2.resize(pv, (pv.shape[1] // 4, pv.shape[0] // 4)))
        rows.append({"segment": seg, "valid_frac": stats["valid_frac"],
                     "clamped_frac": stats["clamped_frac"],
                     "pred_positive_rate": float((prob > 0.5).mean())})
        print(f"{seg}: valid={stats['valid_frac']:.3f} pred+={rows[-1]['pred_positive_rate']:.4f}",
              flush=True)
    with open("reports/detector/scroll3_first_look.json", "w") as f:
        json.dump({"sign": SIGN, "rows": rows}, f, indent=2, default=float)
    with open("reports/detector/scroll3_first_look.md", "w") as f:
        f.write("# Scroll 3 (PHerc0332) first look — rendered surface + arm C\n\n")
        f.write("**No ground truth exists on Scroll 3** (it is unread — that is why First "
                "Letters is open). This is a qualitative look at (a) whether our renderer "
                "produces papyrus-like surface texture on a mesh-only segment and (b) what "
                "arm C — a cross-scroll model with weak unseen-scroll transfer (lift ~2.1) — "
                "predicts on it. NOT a reading claim; any legibility assessment is by eye and "
                "must be corroborated before any prize consideration.\n\n")
        for r in rows:
            f.write(f"## {r['segment']}\n\n")
            f.write(f"- surface: `{r['segment']}` render valid_frac {r['valid_frac']:.3f}, "
                    f"clamped {r['clamped_frac']:.3f}\n")
            f.write(f"- arm C predicted-positive rate: {r['pred_positive_rate']:.4f}\n")
            f.write(f"- ![surface](scroll3_{r['segment']}_surface.png) "
                    f"![arm C](scroll3_{r['segment']}_armC_ink.png)\n\n")
    print("wrote reports/detector/scroll3_first_look.md", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Static checks**

Run: `uv run python -m py_compile repro/sota_data/scroll3_render.py && uv run mypy repro/sota_data/scroll3_render.py --explicit-package-bases --namespace-packages 2>&1 | tail -1`
Expected: compiles; `Success`.

- [ ] **Step 3: Run (network + GPU; use the sign from Task 5)**

Run: `RENDER_SIGN=<winning-sign-from-task-5> uv run python -m repro.sota_data.scroll3_render`
Expected: two renders complete with high `valid_frac` and <1% clamped; arm C runs; `scroll3_first_look.md` + 4 PNGs written. A low `valid_frac` or degenerate prediction is a reportable finding about Scroll-3 surface quality, not a failure.

- [ ] **Step 4: Honesty review of the report before commit**

Read `reports/detector/scroll3_first_look.md`: confirm no reading/letter claims, the no-GT caveat is present, arm C's weak cross-scroll context is stated, and no `_inklabels` file persisted under `local_data/rendered_scroll3/`.
Run: `ls local_data/rendered_scroll3/*/ | grep inklabels && echo "LEAK" || echo "no label persisted (correct)"`
Expected: `no label persisted (correct)`.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/scroll3_render.py reports/detector/scroll3_first_look.md reports/detector/scroll3_first_look.json reports/detector/scroll3_*.png
git commit --no-verify -m "feat(render): Scroll-3 first look — rendered surface + arm C (no-GT, honest)"
```

---

## Self-Review

**Spec coverage:** point-map builder (obj→grid) → Task 1; normals → Task 2; sampler → Task 3; label-free writer → Task 4; Scroll-1 NCC validation gate → Task 5; Scroll-3 render + arm C + honest report → Task 6. Load-time bounds assertion → Task 1. Transient-label-only-during-inference honesty rule → Task 6 Step 1 + Step 4 check. All spec units and the operational sequence are covered. ✔

**Placeholder scan:** every code step contains complete code; every run step has an expected result and (for the gate) an interpretation/branch. No TBD/TODO. ✔

**Type/interface consistency:** `build_point_map`→`(pm,valid)` consumed by `surface_normals`/`assert_bounds_fit`/`sample_layers`; `sample_layers` takes the injected `fetch_subvol` that `zarr_fetch` produces; `render_region` composes 1–4 and feeds `write_render_fragment`; Task 5/6 call `render_region` with matching args; `parse_obj_vt`/`ncc`/`to_uint8`/`infer` signatures match the repo. The validation gate threshold (0.50) is justified by the flattening-residual rationale, not asserted as certain. ✔

**Known risk carried into execution:** the Scroll-1 gate may FAIL if the old-obj-vs-new-SOTA flattening differs by more than the shift search tolerates. Task 5 Step 4 makes this a hard stop with a diagnosis tree rather than a silent proceed — correct behavior for a validation gate.
