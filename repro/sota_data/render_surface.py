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
    zyx = xyz[..., ::-1] / float(level_div)  # (x,y,z) -> (z,y,x), scaled to the level
    pm = zyx.astype(np.float32)
    pm[~valid] = np.nan
    return pm, valid


def read_tifxyz(path):
    """Read a tifxyz geometry dir (x.tif / y.tif / z.tif) into an (H,W,3) float32 grid in
    (x,y,z) channel order. `path` may be a local dir or an S3 key/url (anonymous)."""
    if path.startswith("s3://") or path.startswith("vesuvius-challenge"):
        import io

        import s3fs

        fs = s3fs.S3FileSystem(anon=True)
        key = path.replace("s3://", "")
        planes = [tifffile.imread(io.BytesIO(fs.cat(f"{key}/{c}.tif"))) for c in "xyz"]
    else:
        planes = [tifffile.imread(os.path.join(path, f"{c}.tif")) for c in "xyz"]
    return np.stack(planes, axis=-1).astype(np.float32)


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


def sample_layers(
    pointmap,
    valid,
    normals,
    fetch_subvol,
    n_layers=26,
    k0=-13,
    tile=32,
    max_bbox_voxels=6e8,
    group=8,
    group_max_voxels=8e8,
    workers=None,
):
    """Sample n_layers depth slices around the surface (p + k*n).

    Tiles (`tile` px, small enough to be ~locally planar on the wrapped scroll) are the
    correctness unit: each tile's 3D bbox is guarded by `max_bbox_voxels` (raise, don't
    OOM). For THROUGHPUT, tiles are grouped into `group`x`group` super-tiles fetched with
    ONE fetch_subvol call each — a zarr/S3 store parallelizes the chunk reads inside a
    single big slice request, whereas many small requests serialize on the client
    (measured: 61M-voxel fetch 1.7s vs 0.15-0.33s per tiny tile x ~1000 tiles). If a
    group's union bbox exceeds `group_max_voxels` (too oblique/curved), its tiles fall
    back to individual fetches. `workers` is accepted for backward compatibility and
    ignored (cross-request threading measured slower — it serializes on the s3fs sync
    bridge)."""
    H, W = valid.shape
    ks = np.arange(k0, k0 + n_layers)
    out = np.zeros((n_layers, H, W), np.float32)
    total = clamped = 0

    def _tile_geometry(ty, tx):
        """coords/finite/bbox for one tile, or None if nothing to sample. Applies the
        per-tile planarity guard."""
        vv = valid[ty : ty + tile, tx : tx + tile]
        if not vv.any():
            return None
        p = pointmap[ty : ty + tile, tx : tx + tile]
        n = normals[ty : ty + tile, tx : tx + tile]
        coords = p[None, ..., :] + ks[:, None, None, None] * n[None, ..., :]
        coords = np.moveaxis(coords, -1, 0)  # (3,k,h,w)
        finite = np.isfinite(coords).all(axis=0) & vv[None]
        cf = coords[:, finite]
        if cf.size == 0:
            return None
        z0 = int(np.floor(cf[0].min()))
        z1 = int(np.ceil(cf[0].max())) + 2
        y0 = int(np.floor(cf[1].min()))
        y1 = int(np.ceil(cf[1].max())) + 2
        x0 = int(np.floor(cf[2].min()))
        x1 = int(np.ceil(cf[2].max())) + 2
        bbox_vox = (z1 - max(z0, 0)) * (y1 - max(y0, 0)) * (x1 - max(x0, 0))
        if bbox_vox > max_bbox_voxels:
            raise ValueError(
                f"tile ({ty},{tx}) 3D bbox is {bbox_vox:.2e} voxels "
                f"(z {z1 - z0}, y {y1 - y0}, x {x1 - x0}) > cap {max_bbox_voxels:.0e}: "
                "the surface patch is too large/oblique — use a smaller `tile`"
            )
        n_clamped = int((~np.isfinite(coords).all(axis=0) & vv[None]).sum())
        return (
            coords,
            finite,
            (max(z0, 0), z1, max(y0, 0), y1, max(x0, 0), x1),
            n_clamped,
        )

    def _sample_into(ty, tx, coords, finite, sub, off):
        vals = map_coordinates(
            np.asarray(sub, np.float32),
            np.stack(
                [coords[0] - off[0], coords[1] - off[1], coords[2] - off[2]], axis=0
            ).reshape(3, -1),
            order=1,
            mode="constant",
            cval=0.0,
        ).reshape(n_layers, min(tile, H - ty), min(tile, W - tx))
        out[:, ty : ty + vals.shape[1], tx : tx + vals.shape[2]] = np.where(
            finite, vals, 0.0
        )

    gpx = max(1, group) * tile
    for gy in range(0, H, gpx):
        for gx in range(0, W, gpx):
            members = []
            for ty in range(gy, min(gy + gpx, H), tile):
                for tx in range(gx, min(gx + gpx, W), tile):
                    geo = _tile_geometry(ty, tx)
                    if geo is None:
                        continue
                    coords, finite, bbox, n_clamped = geo
                    members.append((ty, tx, coords, finite, bbox))
                    total += int(finite.sum())
                    clamped += n_clamped
            if not members:
                continue
            if hasattr(fetch_subvol, "warm"):
                # chunk-cached fetcher: prefetch exactly the (deduped) chunks the
                # members touch, concurrently; per-tile reads then hit RAM. This is
                # the fast path for a wrapped sheet, whose union BBOX is mostly empty
                # space (measured: 2.7-6.6 GVox unions for 256px groups).
                fetch_subvol.warm([m[4] for m in members])
                for ty, tx, coords, finite, bbox in members:
                    sub = fetch_subvol(
                        bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]
                    )
                    _sample_into(
                        ty, tx, coords, finite, sub, (bbox[0], bbox[2], bbox[4])
                    )
                continue
            uz0 = min(m[4][0] for m in members)
            uz1 = max(m[4][1] for m in members)
            uy0 = min(m[4][2] for m in members)
            uy1 = max(m[4][3] for m in members)
            ux0 = min(m[4][4] for m in members)
            ux1 = max(m[4][5] for m in members)
            union_vox = (uz1 - uz0) * (uy1 - uy0) * (ux1 - ux0)
            if union_vox <= group_max_voxels:
                sub = fetch_subvol(uz0, uz1, uy0, uy1, ux0, ux1)
                for ty, tx, coords, finite, _ in members:
                    _sample_into(ty, tx, coords, finite, sub, (uz0, uy0, ux0))
            else:
                # group too curved for one prefetch — per-tile fetches (correct, slower)
                for ty, tx, coords, finite, bbox in members:
                    sub = fetch_subvol(
                        bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]
                    )
                    _sample_into(
                        ty, tx, coords, finite, sub, (bbox[0], bbox[2], bbox[4])
                    )
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
        tifffile.imwrite(
            os.path.join(out_layers, f"{17 + k:02d}.tif"), to_uint8(layers[k])
        )
    mask = np.where(valid, 255, 0).astype(np.uint8)
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_mask.png"), mask)
    with open(os.path.join(out_seg, f"{frag_id}_render_provenance.json"), "w") as f:
        json.dump(provenance, f, indent=2, default=float)
    return out_seg


def surface_structure(layer, mask):
    """Papyrus-texture score for a rendered surface layer: high-pass std over valid pixels.
    Real papyrus fibers give a high value; a wrong coordinate scale / empty render is flat.
    Used to infer the obj level-scale teacher-free on scrolls without ground truth."""
    import cv2

    img = np.asarray(layer, np.float32)
    hp = img - cv2.GaussianBlur(img, (0, 0), 6)
    m = np.asarray(mask, bool) & (img > 0)
    return float(hp[m].std()) if m.any() else 0.0


class ChunkCachedZarrFetch:
    """fetch_subvol over an S3 zarr level that serves bbox reads from a chunk cache.

    Why: a wrapped papyrus sheet's bounding boxes are mostly empty space, so dense
    `arr[z0:z1, ...]` reads either explode (billions of voxels for a modest surface
    patch) or degenerate into ~1000 serial tiny reads (s3fs serializes separate calls).
    The surface only *touches* a bounded set of 128^3 chunks; `warm()` fetches exactly
    that set — deduplicated across neighboring tiles — in ONE `fs.cat(keys)` call
    (s3fs's genuinely concurrent path), and `__call__` assembles bboxes from the cache.

    Zarr v2 format is decoded directly from `.zarray` metadata (chunk shape, dtype,
    compressor via numcodecs, C order, key separator) — the stable on-disk spec.
    Missing chunk keys mean fill_value (uninitialized chunks), served as zeros.
    """

    def __init__(self, volume_zarr_uri, level):
        import json as _json

        import s3fs

        self.fs = s3fs.S3FileSystem(anon=True)
        self.root = volume_zarr_uri.rstrip("/")
        meta = _json.loads(self.fs.cat(f"{self.root}/{level}/.zarray").decode())
        self.level = level
        self.shape = tuple(meta["shape"])
        self.chunks = tuple(meta["chunks"])
        self.dtype = np.dtype(meta["dtype"])
        self.fill_value = meta.get("fill_value") or 0
        self.sep = meta.get("dimension_separator", ".")
        self.order = meta.get("order", "C")
        comp = meta.get("compressor")
        if comp is not None:
            import numcodecs

            self.codec = numcodecs.get_codec(comp)
        else:
            self.codec = None
        if meta.get("filters"):
            raise ValueError(
                f"zarr filters not supported by this reader: {meta['filters']}"
            )
        self.cache: dict = {}

    def _key(self, cz, cy, cx):
        return f"{self.root}/{self.level}/{cz}{self.sep}{cy}{self.sep}{cx}"

    def _decode(self, raw):
        buf = self.codec.decode(raw) if self.codec is not None else raw
        return np.frombuffer(buf, dtype=self.dtype).reshape(
            self.chunks, order=self.order
        )

    def _chunk_ids_for_bbox(self, z0, z1, y0, y1, x0, x1):
        cz0, cz1 = z0 // self.chunks[0], (max(z1 - 1, z0)) // self.chunks[0]
        cy0, cy1 = y0 // self.chunks[1], (max(y1 - 1, y0)) // self.chunks[1]
        cx0, cx1 = x0 // self.chunks[2], (max(x1 - 1, x0)) // self.chunks[2]
        return [
            (cz, cy, cx)
            for cz in range(cz0, cz1 + 1)
            for cy in range(cy0, cy1 + 1)
            for cx in range(cx0, cx1 + 1)
        ]

    def warm(self, bboxes, batch=768):
        """Fetch (concurrently) the deduped chunk set covering `bboxes`; replaces the
        cache (per-group memory bound)."""
        ids = set()
        for z0, z1, y0, y1, x0, x1 in bboxes:
            ids.update(
                self._chunk_ids_for_bbox(
                    max(z0, 0),
                    min(z1, self.shape[0]),
                    max(y0, 0),
                    min(y1, self.shape[1]),
                    max(x0, 0),
                    min(x1, self.shape[2]),
                )
            )
        self.cache = {}
        todo = sorted(ids)
        for i in range(0, len(todo), batch):
            keys = [self._key(*cid) for cid in todo[i : i + batch]]
            got = self.fs.cat(keys, on_error="omit")  # concurrent; missing = fill_value
            for cid, key in zip(todo[i : i + batch], keys, strict=False):
                raw = got.get(key)
                self.cache[cid] = self._decode(raw) if raw is not None else None
        return len(todo)

    def __call__(self, z0, z1, y0, y1, x0, x1):
        z1 = min(z1, self.shape[0])
        y1 = min(y1, self.shape[1])
        x1 = min(x1, self.shape[2])
        out = np.full((z1 - z0, y1 - y0, x1 - x0), self.fill_value, self.dtype)
        for cid in self._chunk_ids_for_bbox(z0, z1, y0, y1, x0, x1):
            chunk = self.cache.get(cid, "MISS")
            if chunk is None:
                continue  # uninitialized chunk -> fill_value already in out
            if isinstance(chunk, str):  # not warmed: fetch this one chunk now
                raw = self.fs.cat(self._key(*cid), on_error="return")
                chunk = self._decode(raw) if isinstance(raw, bytes) else None
                self.cache[cid] = chunk
                if chunk is None:
                    continue
            bz0, by0, bx0 = (
                cid[0] * self.chunks[0],
                cid[1] * self.chunks[1],
                cid[2] * self.chunks[2],
            )
            sz0, sz1 = max(z0, bz0), min(z1, bz0 + self.chunks[0])
            sy0, sy1 = max(y0, by0), min(y1, by0 + self.chunks[1])
            sx0, sx1 = max(x0, bx0), min(x1, bx0 + self.chunks[2])
            out[sz0 - z0 : sz1 - z0, sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = chunk[
                sz0 - bz0 : sz1 - bz0, sy0 - by0 : sy1 - by0, sx0 - bx0 : sx1 - bx0
            ]
        return out


def zarr_fetch(volume_zarr_uri, level):
    """Return a chunk-cached fetch_subvol(z0,z1,y0,y1,x0,x1) over a pyramid level of an
    S3 zarr, plus the level's shape. The returned object also exposes .warm(bboxes) for
    grouped concurrent prefetch (used by sample_layers)."""
    fetch = ChunkCachedZarrFetch(volume_zarr_uri, level)
    return fetch, fetch.shape


def render_region(
    seg,
    obj_path,
    volume_zarr_uri,
    y0,
    x0,
    size,
    level,
    sign,
    out_root,
    frag_id=None,
    extra_prov=None,
    obj_level_div=None,
):
    """Full pipeline for one region -> label-free fragment dir. Returns (out_seg, stats).

    The obj `v` is (x,y,z); the sampler needs (z,y,x) at the sampled pyramid `level`. We
    reorder and divide by `obj_level_div` (default 2**level, i.e. obj coords assumed to be
    level-0 voxels). This convention was validated on Scroll 1 via the tifxyz path
    (reports/detector/render_validation.md); on scrolls without ground truth it is
    inferred (see scroll3_render's coherence check)."""
    from repro.sota_data.gt_register import parse_obj_vt

    v, vt = parse_obj_vt(obj_path)
    fetch, vol_shape = zarr_fetch(volume_zarr_uri, level)
    pm_xyz, valid = build_point_map(v, vt, size)
    div = float(obj_level_div if obj_level_div is not None else 2**level)
    pm = pm_xyz[..., ::-1] / div  # (x,y,z) -> (z,y,x), scaled to the level
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats = sample_layers(pm, valid, normals, fetch, tile=32)
    fid = frag_id or f"{seg}_render"
    prov = {
        "segment": seg,
        "region_px": [y0, x0, size if isinstance(size, int) else list(size)],
        "level": level,
        "normal_sign": sign,
        "volume": volume_zarr_uri,
        "valid_frac": stats["valid_frac"],
        "clamped_frac": stats["clamped_frac"],
        **(extra_prov or {}),
    }
    out_seg = write_render_fragment(layers, valid, out_root, fid, prov)
    return out_seg, stats


def render_region_tifxyz(
    seg,
    tifxyz_path,
    volume_zarr_uri,
    y0,
    x0,
    size,
    level,
    sign,
    out_root,
    frag_id=None,
    extra_prov=None,
):
    """Render from a released tifxyz geometry grid — the format most bucket segments ship.

    Unlike the obj path there is no coordinate-scale ambiguity: tifxyz values are level-0
    voxel coords by bucket convention (validated on Scroll 1,
    reports/detector/render_validation.md), so the level divisor is always 2**level.
    (y0, x0, size) select a region in tifxyz GRID pixels; size is an int (square) or an
    (h, w) pair; size=0 renders the whole grid."""
    xyz = read_tifxyz(tifxyz_path)
    if size:
        h, w = (size, size) if isinstance(size, int) else size
        xyz = xyz[y0 : y0 + h, x0 : x0 + w]
    if xyz.size == 0:
        raise ValueError(f"region ({y0},{x0},{size}) is outside the tifxyz grid")
    pm, valid = pointmap_from_tifxyz(xyz, level_div=2**level)
    fetch, vol_shape = zarr_fetch(volume_zarr_uri, level)
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats = sample_layers(pm, valid, normals, fetch, tile=32)
    fid = frag_id or f"{seg}_render"
    prov = {
        "segment": seg,
        "geometry": "tifxyz",
        "tifxyz": tifxyz_path,
        "region_px": [y0, x0, size if isinstance(size, int) else list(size)],
        "level": level,
        "normal_sign": sign,
        "volume": volume_zarr_uri,
        "valid_frac": stats["valid_frac"],
        "clamped_frac": stats["clamped_frac"],
        **(extra_prov or {}),
    }
    out_seg = write_render_fragment(layers, valid, out_root, fid, prov)
    return out_seg, stats
