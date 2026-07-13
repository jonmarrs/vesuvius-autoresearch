"""Render detector-ready surface volumes from a segment's original.obj + a volume zarr.

The bucket's tifxyz_normalized grids are empty placeholders for the Scroll-3 segments, so
the flattened point map is rebuilt from the obj: vt (flattened UV) -> v (3D) interpolated
onto a regular grid. Everything downstream (normals, sampling, fragment writing) treats
that point map exactly as it would a released tifxyz grid. No ground-truth ink label is
ever fabricated for an unread scroll.
"""
import json
import os

import cv2
import numpy as np
import tifffile
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import map_coordinates

from repro.sota_data.convert import to_uint8


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


def pointmap_from_tifxyz(xyz, level_div=4):
    """Convert a read_tifxyz grid (H,W,3 in (x,y,z), level-0 voxel coords, with -1/0
    invalid sentinels) into a sampler-ready point map: reordered to (z,y,x) volume-index
    convention and divided by level_div (4 = level-0 -> level-2). Returns
    (pointmap[H,W,3] float32, valid[H,W] bool)."""
    xyz = np.asarray(xyz, np.float64)
    valid = ~((np.abs(xyz + 1) < 1e-6).all(axis=2) | (np.abs(xyz) < 1e-9).all(axis=2))
    valid &= np.isfinite(xyz).all(axis=2)
    zyx = xyz[..., ::-1] / float(level_div)   # (x,y,z) -> (z,y,x), scaled to the level
    pm = zyx.astype(np.float32)
    pm[~valid] = np.nan
    return pm, valid


def surface_normals(pointmap, valid, sign=1.0):
    """Unit surface normals from a point map, via cross product of the two grid tangents.
    sign selects the depth direction (fixed empirically by the validation harness)."""
    pm = pointmap.astype(np.float64)
    dv = np.stack([np.gradient(pm[..., c], axis=0) for c in range(3)], axis=-1)  # rows
    du = np.stack([np.gradient(pm[..., c], axis=1) for c in range(3)], axis=-1)  # cols
    n = np.cross(du, dv)
    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        n = sign * n / norm
    n[~valid] = np.nan
    return n.astype(np.float32)


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
            p = pointmap[ty:ty + tile, tx:tx + tile]
            n = normals[ty:ty + tile, tx:tx + tile]
            coords = (p[None, ..., :] + ks[:, None, None, None] * n[None, ..., :])
            coords = np.moveaxis(coords, -1, 0)               # (3,k,h,w)
            finite = np.isfinite(coords).all(axis=0) & vv[None]
            cf = coords[:, finite]
            if cf.size == 0:
                continue
            z0 = int(np.floor(cf[0].min()))
            z1 = int(np.ceil(cf[0].max())) + 2
            y0 = int(np.floor(cf[1].min()))
            y1 = int(np.ceil(cf[1].max())) + 2
            x0 = int(np.floor(cf[2].min()))
            x1 = int(np.ceil(cf[2].max())) + 2
            sub = np.asarray(fetch_subvol(max(z0, 0), z1, max(y0, 0), y1,
                                          max(x0, 0), x1), np.float32)
            local = np.stack([coords[0] - max(z0, 0), coords[1] - max(y0, 0),
                              coords[2] - max(x0, 0)], axis=0)
            total += int(finite.sum())
            clamped += int((~np.isfinite(coords).all(axis=0) & vv[None]).sum())
            bh = min(tile, H - ty)
            bw = min(tile, W - tx)
            vals = map_coordinates(sub, local.reshape(3, -1), order=1,
                                   mode="constant", cval=0.0).reshape(n_layers, bh, bw)
            out[:, ty:ty + bh, tx:tx + bw] = np.where(finite, vals, 0.0)
    vf = float(valid.mean())
    return out, {"valid_frac": vf, "clamped_frac": (clamped / total) if total else 0.0}


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


def zarr_fetch(volume_zarr_uri, level):
    """Return a fetch_subvol(z0,z1,y0,y1,x0,x1) closure over a pyramid level of an S3 zarr,
    plus the level's shape."""
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
    pm, valid = build_point_map(v, vt, size)
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats = sample_layers(pm, valid, normals, fetch)
    fid = frag_id or f"{seg}_render"
    prov = {"segment": seg, "region_px": [y0, x0, size], "level": level,
            "normal_sign": sign, "volume": volume_zarr_uri,
            "valid_frac": stats["valid_frac"], "clamped_frac": stats["clamped_frac"],
            **(extra_prov or {})}
    out_seg = write_render_fragment(layers, valid, out_root, fid, prov)
    return out_seg, stats
