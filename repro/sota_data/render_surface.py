"""Render detector-ready surface volumes from a segment's original.obj + a volume zarr.

The bucket's tifxyz_normalized grids are empty placeholders for the Scroll-3 segments, so
the flattened point map is rebuilt from the obj: vt (flattened UV) -> v (3D) interpolated
onto a regular grid. Everything downstream (normals, sampling, fragment writing) treats
that point map exactly as it would a released tifxyz grid. No ground-truth ink label is
ever fabricated for an unread scroll.
"""

import json
import math
import os

import numpy as np
import tifffile
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import map_coordinates

from repro.sota_data.fragment import write_fragment_artifact


def grid_shape(size):
    """Normalize an integer or (height, width) pair; normals need two pixels per axis."""
    try:
        shape = (size, size) if isinstance(size, (int, np.integer)) else tuple(size)
    except TypeError as exc:
        raise ValueError("grid size must be an integer or (height, width)") from exc
    if len(shape) != 2 or any(
        not isinstance(n, (int, np.integer)) or n < 2 for n in shape
    ):
        raise ValueError("grid size must be an integer or (height, width), each >= 2")
    return tuple(int(n) for n in shape)


def validate_region(y0, x0, size, full_shape):
    h, w = grid_shape(size)
    if any(not isinstance(n, (int, np.integer)) or n < 0 for n in (y0, x0)):
        raise ValueError("region origins must be nonnegative integers")
    if y0 + h > full_shape[0] or x0 + w > full_shape[1]:
        raise ValueError(f"region ({y0},{x0},{h},{w}) exceeds grid {tuple(full_shape)}")
    return h, w


def validate_level_sign(level, sign):
    if not isinstance(level, (int, np.integer)) or not 0 <= level <= 30:
        raise ValueError("level must be an integer in [0,30]")
    if sign not in (-1, 1):
        raise ValueError("normal sign must be -1 or +1")


def _pointmap_inputs(pointmap, valid):
    pm = np.asarray(pointmap, np.float64)
    valid = np.asarray(valid)
    if (
        pm.ndim != 3
        or pm.shape[-1] != 3
        or valid.shape != pm.shape[:2]
        or valid.dtype != np.bool_
    ):
        raise ValueError("point map must be (H,W,3) with an aligned boolean valid mask")
    if min(valid.shape) < 2:
        raise ValueError("point map grid must have at least two pixels per axis")
    if not np.isfinite(pm[valid]).all():
        raise ValueError("valid point-map coordinates must be finite")
    return pm, valid


def build_point_map(v, vt, size, uv_bbox=None, *, origin=(0, 0), grid_size=None):
    """Interpolate obj vertices (v[N,3]) over their flattened UV coords (vt[N,2]) onto a
    regular grid spanning uv_bbox (default: vt min/max). `grid_size` fixes the full UV
    grid resolution; `origin` and `size` select a crop without allocating the full map.
    Without grid_size, size is the full grid and origin must be zero. Interpolation uses
    the UV convex hull; it does not reconstruct mesh holes or overlapping UV islands.
    """
    v = np.asarray(v, np.float64)
    vt = np.asarray(vt, np.float64)
    if v.ndim != 2 or v.shape[1:] != (3,) or vt.shape != (len(v), 2) or len(v) < 3:
        raise ValueError("vertices must be paired arrays (N,3)/(N,2), with N >= 3")
    if not np.isfinite(v).all() or not np.isfinite(vt).all():
        raise ValueError("OBJ vertex/UV coordinates must be finite")
    unique_uv, first, inverse = np.unique(
        vt, axis=0, return_index=True, return_inverse=True
    )
    if not np.allclose(v, v[first][inverse], rtol=0, atol=1e-6):
        raise ValueError("overlapping OBJ UV coordinates map to different 3D points")
    v, vt = v[first], unique_uv
    h, w = grid_shape(size)
    full_shape = grid_shape(grid_size if grid_size is not None else size)
    y0, x0 = origin
    validate_region(y0, x0, size, full_shape)
    if uv_bbox is None:
        umin, vmin = vt.min(axis=0)
        umax, vmax = vt.max(axis=0)
    else:
        (umin, vmin), (umax, vmax) = uv_bbox
    if not np.isfinite([umin, vmin, umax, vmax]).all() or umax <= umin or vmax <= vmin:
        raise ValueError("UV bounds must be finite and span both axes")
    gu = np.linspace(umin, umax, full_shape[1])[x0 : x0 + w]
    gv = np.linspace(vmin, vmax, full_shape[0])[y0 : y0 + h]
    gU, gV = np.meshgrid(gu, gv)
    interp = LinearNDInterpolator(vt, v)  # fills NaN outside the convex hull
    pm = interp(np.stack([gU.ravel(), gV.ravel()], axis=1)).reshape(h, w, 3)
    # Barycentric interpolation stays within the vertex coordinate ranges, but
    # roundoff can put an exact zero boundary just below zero (e.g. -5e-18).
    # Preserve actual negative vertices while removing that numerical overshoot.
    np.clip(pm, v.min(axis=0), v.max(axis=0), out=pm)
    valid = np.isfinite(pm).all(axis=2)
    return pm.astype(np.float32), valid


def assert_bounds_fit(pointmap, valid, volume_shape_l2):
    """Raise ValueError if any valid point falls outside [0, volume_shape) on any axis."""
    pointmap, valid = _pointmap_inputs(pointmap, valid)
    pts = pointmap[valid]
    if pts.size == 0:
        raise ValueError("no valid points in point map")
    lo = np.nanmin(pts, axis=0)
    hi = np.nanmax(pts, axis=0)
    shape = np.asarray(volume_shape_l2, float)
    if shape.shape != (3,) or not np.isfinite(shape).all() or (shape <= 0).any():
        raise ValueError("volume shape must have three positive finite dimensions")
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
    if xyz.ndim != 3 or xyz.shape[-1] != 3 or min(xyz.shape[:2]) < 2:
        raise ValueError("tifxyz grid must have shape (H,W,3), with H,W >= 2")
    if not np.isfinite(level_div) or level_div <= 0:
        raise ValueError("coordinate divisor must be positive and finite")
    valid = ~((np.abs(xyz + 1) < 1e-6).all(axis=2) | (np.abs(xyz) < 1e-9).all(axis=2))
    valid &= np.isfinite(xyz).all(axis=2)
    zyx = xyz[..., ::-1] / float(level_div)  # (x,y,z) -> (z,y,x), scaled to the level
    pm = zyx.astype(np.float32)
    pm[~valid] = np.nan
    return pm, valid


def read_tifxyz(path):
    """Read a tifxyz geometry dir (x.tif / y.tif / z.tif) into an (H,W,3) float32 grid in
    (x,y,z) channel order. `path` may be a local dir or an S3 key/url (anonymous)."""
    path = os.fspath(path)
    if path.startswith("s3://") or path.startswith("vesuvius-challenge"):
        import io

        import s3fs

        fs = s3fs.S3FileSystem(anon=True)
        key = path.replace("s3://", "")
        planes = [tifffile.imread(io.BytesIO(fs.cat(f"{key}/{c}.tif"))) for c in "xyz"]
    else:
        planes = [tifffile.imread(os.path.join(path, f"{c}.tif")) for c in "xyz"]
    if any(p.ndim != 2 or p.shape != planes[0].shape for p in planes):
        raise ValueError("tifxyz planes must be aligned 2D grayscale grids")
    return np.stack(planes, axis=-1).astype(np.float32)


def surface_normals(pointmap, valid, sign=1.0):
    """Unit surface normals from a point map, via cross product of the two grid tangents.
    sign selects the depth direction (fixed empirically by the validation harness)."""
    pm, valid = _pointmap_inputs(pointmap, valid)
    if sign not in (-1, 1):
        raise ValueError("normal sign must be -1 or +1")
    pm = pm.copy()
    pm[~valid] = np.nan
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
    volume_shape=None,
    return_valid=False,
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
    bridge). `volume_shape` clips reads to known source bounds. Without it, coverage is
    checked against the fetched array (upper-clipped slices are supported). valid_frac
    measures pixels supported at *every* depth; clamped_frac counts unsupported depth
    samples among geometry-valid pixels, including nonfinite normals. `return_valid`
    also returns the full-depth boolean mask. uint16 intensities are scaled by /256 to
    detector byte units before interpolation; floats retain their source units.
    """
    pointmap, valid = _pointmap_inputs(pointmap, valid)
    normals = np.asarray(normals)
    if normals.shape != pointmap.shape:
        raise ValueError("normal grid must match the point map")
    finite_normals = valid & np.isfinite(normals).all(axis=-1)
    if not np.allclose(
        np.linalg.norm(normals[finite_normals], axis=-1), 1, rtol=0, atol=1e-4
    ):
        raise ValueError("finite normals must be unit vectors")
    for name, value in (("n_layers", n_layers), ("tile", tile), ("group", group)):
        if not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not isinstance(k0, (int, np.integer)):
        raise ValueError("k0 must be an integer")
    for cap in (max_bbox_voxels, group_max_voxels):
        if not np.isfinite(cap) or cap <= 0:
            raise ValueError("voxel caps must be positive and finite")
    volume_shape = (
        volume_shape
        if volume_shape is not None
        else getattr(fetch_subvol, "shape", None)
    )
    if volume_shape is not None:
        volume_shape = np.asarray(volume_shape)
        if (
            volume_shape.shape != (3,)
            or not np.issubdtype(volume_shape.dtype, np.integer)
            or (volume_shape <= 0).any()
        ):
            raise ValueError("volume shape must have three positive integer dimensions")
    H, W = valid.shape
    ks = np.arange(k0, k0 + n_layers)
    out = np.zeros((n_layers, H, W), np.float32)
    total = n_layers * int(valid.sum())
    covered_count = 0
    supported = np.zeros((H, W), bool)

    def _fetch_bbox(z0, z1, y0, y1, x0, x1):
        sub = np.asarray(fetch_subvol(z0, z1, y0, y1, x0, x1))
        expected = (z1 - z0, y1 - y0, x1 - x0)
        if sub.ndim != 3 or (volume_shape is not None and sub.shape != expected):
            raise ValueError(
                f"fetched shape {sub.shape} does not match requested {expected}"
            )
        if any(a > b for a, b in zip(sub.shape, expected, strict=False)):
            raise ValueError("fetched array exceeds requested bounds")
        if min(sub.shape) == 0:
            raise ValueError("fetched volume must be a nonempty 3D array")
        if not (
            sub.dtype.kind == "u" and sub.dtype.itemsize in (1, 2)
        ) and not np.issubdtype(sub.dtype, np.floating):
            raise ValueError(f"unsupported volume dtype: {sub.dtype}")
        if np.issubdtype(sub.dtype, np.floating):
            if not np.isfinite(sub).all():
                raise ValueError("fetched volume must be finite")
            if sub.min() < 0 or sub.max() > 255:
                raise ValueError(
                    "floating volume intensities must be in byte range [0,255]"
                )
        pixels = sub.astype(np.float32, copy=False)
        if sub.dtype.kind == "u" and sub.dtype.itemsize == 2:
            pixels /= 256
        return pixels

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
        finite &= (coords >= 0).all(axis=0)
        if volume_shape is not None:
            finite &= (coords <= (volume_shape - 1)[:, None, None, None]).all(axis=0)
        cf = coords[:, finite]
        if cf.size == 0:
            return None
        z0 = int(np.floor(cf[0].min()))
        z1 = int(np.ceil(cf[0].max())) + 2
        y0 = int(np.floor(cf[1].min()))
        y1 = int(np.ceil(cf[1].max())) + 2
        x0 = int(np.floor(cf[2].min()))
        x1 = int(np.ceil(cf[2].max())) + 2
        if volume_shape is not None:
            z1, y1, x1 = (
                min(z1, volume_shape[0]),
                min(y1, volume_shape[1]),
                min(x1, volume_shape[2]),
            )
        bbox_vox = (z1 - z0) * (y1 - y0) * (x1 - x0)
        if bbox_vox > max_bbox_voxels:
            raise ValueError(
                f"tile ({ty},{tx}) 3D bbox is {bbox_vox:.2e} voxels "
                f"(z {z1 - z0}, y {y1 - y0}, x {x1 - x0}) > cap {max_bbox_voxels:.0e}: "
                "the surface patch is too large/oblique — use a smaller `tile`"
            )
        return (
            coords,
            finite,
            (max(z0, 0), z1, max(y0, 0), y1, max(x0, 0), x1),
        )

    def _sample_into(ty, tx, coords, finite, sub, off):
        nonlocal covered_count
        local = coords - np.asarray(off)[:, None, None, None]
        covered = (
            finite
            & (local >= 0).all(axis=0)
            & (local <= (np.asarray(sub.shape) - 1)[:, None, None, None]).all(axis=0)
        )
        covered_count += int(covered.sum())
        supported[ty : ty + covered.shape[1], tx : tx + covered.shape[2]] = covered.all(
            axis=0
        )
        vals = map_coordinates(
            sub,
            np.where(covered[None], local, 0).reshape(3, -1),
            order=1,
            mode="constant",
            cval=0.0,
        ).reshape(n_layers, min(tile, H - ty), min(tile, W - tx))
        out[:, ty : ty + vals.shape[1], tx : tx + vals.shape[2]] = np.where(
            covered, vals, 0.0
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
                    coords, finite, bbox = geo
                    members.append((ty, tx, coords, finite, bbox))
            if not members:
                continue
            if hasattr(fetch_subvol, "warm"):
                # chunk-cached fetcher: prefetch exactly the (deduped) chunks the
                # members touch, concurrently; per-tile reads then hit RAM. This is
                # the fast path for a wrapped sheet, whose union BBOX is mostly empty
                # space (measured: 2.7-6.6 GVox unions for 256px groups).
                fetch_subvol.warm([m[4] for m in members])
                for ty, tx, coords, finite, bbox in members:
                    sub = _fetch_bbox(
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
                sub = _fetch_bbox(uz0, uz1, uy0, uy1, ux0, ux1)
                for ty, tx, coords, finite, _ in members:
                    _sample_into(ty, tx, coords, finite, sub, (uz0, uy0, ux0))
            else:
                # group too curved for one prefetch — per-tile fetches (correct, slower)
                for ty, tx, coords, finite, bbox in members:
                    sub = _fetch_bbox(
                        bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]
                    )
                    _sample_into(
                        ty, tx, coords, finite, sub, (bbox[0], bbox[2], bbox[4])
                    )
    stats = {
        "geometry_valid_frac": float(valid.mean()),
        "valid_frac": float(supported.mean()),
        "clamped_frac": (1 - covered_count / total) if total else 0.0,
    }
    return (out, stats, supported) if return_valid else (out, stats)


def write_render_fragment(layers, valid, out_root, frag_id, provenance):
    """Write a detector-format fragment WITHOUT an ink label (none exists). layers +
    mask + provenance only. Existing fragments are refused and publication is staged.
    """
    return write_fragment_artifact(
        layers, valid, out_root, frag_id, provenance=provenance
    )


def surface_structure(layer, mask):
    """Papyrus-texture score for a rendered surface layer: high-pass std over valid pixels.
    Real papyrus fibers give a high value; a wrong coordinate scale / empty render is flat.
    Used to infer the obj level-scale teacher-free on scrolls without ground truth."""
    import cv2

    img = np.asarray(layer, np.float32)
    if (
        img.ndim != 2
        or np.asarray(mask).shape != img.shape
        or not np.isfinite(img).all()
    ):
        raise ValueError("structure score requires a finite 2D layer and aligned mask")
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
    Missing chunk keys mean the declared fill_value (uninitialized chunks). Read errors
    propagate. Decoded cache storage and each dense bbox have a configurable byte cap;
    the default is 512 MiB for each, not a cap on total process memory.
    """

    def __init__(self, volume_zarr_uri, level, max_cache_bytes=512 * 1024**2):
        import s3fs

        self.fs = s3fs.S3FileSystem(anon=True)
        validate_level_sign(level, 1)
        self.root = os.fspath(volume_zarr_uri).removeprefix("s3://").rstrip("/")
        meta = json.loads(self.fs.cat(f"{self.root}/{level}/.zarray").decode())
        self.level = level
        if meta.get("zarr_format") != 2:
            raise ValueError("chunk reader requires Zarr v2 metadata")
        self.shape = tuple(meta["shape"])
        self.chunks = tuple(meta["chunks"])
        if any(
            len(values) != 3 or any(type(n) is not int or n < 1 for n in values)
            for values in (self.shape, self.chunks)
        ):
            raise ValueError(
                "Zarr shape/chunks must have three positive integer dimensions"
            )
        self.dtype = np.dtype(meta["dtype"])
        if not (
            self.dtype.kind == "u" and self.dtype.itemsize in (1, 2)
        ) and not np.issubdtype(self.dtype, np.floating):
            raise ValueError(f"unsupported volume dtype: {self.dtype}")
        if not isinstance(max_cache_bytes, int) or max_cache_bytes < 1:
            raise ValueError("max_cache_bytes must be a positive integer")
        self.max_cache_bytes = max_cache_bytes
        self.chunk_bytes = math.prod(self.chunks) * self.dtype.itemsize
        if self.chunk_bytes > max_cache_bytes:
            raise MemoryError("one Zarr chunk exceeds the cache byte budget")
        # Tiny chunks otherwise allow millions of Python index/cache objects while
        # their voxel payload still fits the byte cap. Bound those allocations too.
        self.max_chunks = min(
            65536, max(1, max_cache_bytes // max(self.chunk_bytes, 256))
        )
        self.fill_value = meta.get("fill_value") or 0
        self.sep = meta.get("dimension_separator", ".")
        self.order = meta.get("order", "C")
        if self.sep not in (".", "/") or self.order not in ("C", "F"):
            raise ValueError("invalid Zarr dimension separator/order")
        try:
            fill = float(self.fill_value)
            if not np.isfinite(fill):
                raise ValueError("Zarr fill value must be finite")
            if np.issubdtype(self.dtype, np.integer):
                limits = np.iinfo(self.dtype)
                if fill != int(fill) or not limits.min <= fill <= limits.max:
                    raise ValueError("Zarr fill value is outside the dtype range")
            self.fill_value = self.dtype.type(fill)
            if not np.isfinite(self.fill_value):
                raise ValueError("Zarr fill value is outside the dtype range")
        except (TypeError, OverflowError) as exc:
            raise ValueError("invalid Zarr fill value") from exc
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

    def _read_chunk_result(self, key, raw):
        if isinstance(raw, FileNotFoundError):
            return None  # Zarr's genuinely absent chunk means the declared fill value.
        if isinstance(raw, Exception):
            raise OSError(f"failed to read Zarr chunk {key}: {raw}") from raw
        if not isinstance(raw, (bytes, bytearray, memoryview)):
            raise OSError(
                f"invalid read result for Zarr chunk {key}: {type(raw).__name__}"
            )
        try:
            return self._decode(raw)
        except Exception as exc:
            raise ValueError(f"invalid Zarr chunk {key}: {exc}") from exc

    def _clip_bbox(self, bbox):
        if len(bbox) != 6 or any(not isinstance(n, (int, np.integer)) for n in bbox):
            raise ValueError("volume bbox must contain six integer bounds")
        result = []
        for axis, (lo, hi) in enumerate(zip(bbox[::2], bbox[1::2], strict=False)):
            if hi < lo:
                raise ValueError("volume bbox end precedes start")
            result.extend(
                (max(0, min(lo, self.shape[axis])), max(0, min(hi, self.shape[axis])))
            )
        return tuple(result)

    def _chunk_ids_for_bbox(self, z0, z1, y0, y1, x0, x1):
        if z1 <= z0 or y1 <= y0 or x1 <= x0:
            return []
        cz0, cz1 = z0 // self.chunks[0], (max(z1 - 1, z0)) // self.chunks[0]
        cy0, cy1 = y0 // self.chunks[1], (max(y1 - 1, y0)) // self.chunks[1]
        cx0, cx1 = x0 // self.chunks[2], (max(x1 - 1, x0)) // self.chunks[2]
        count = (cz1 - cz0 + 1) * (cy1 - cy0 + 1) * (cx1 - cx0 + 1)
        if count > self.max_chunks:
            raise MemoryError(
                "volume bbox exceeds chunk count budget; use smaller tiles"
            )
        if count * self.chunk_bytes > self.max_cache_bytes:
            raise MemoryError(
                "volume bbox exceeds chunk byte budget; use smaller tiles"
            )
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
        if not isinstance(batch, int) or batch < 1:
            raise ValueError("chunk batch must be a positive integer")
        for z0, z1, y0, y1, x0, x1 in bboxes:
            ids.update(
                self._chunk_ids_for_bbox(*self._clip_bbox((z0, z1, y0, y1, x0, x1)))
            )
        self.cache = {}
        todo = sorted(ids)
        if (
            len(todo) > self.max_chunks
            or len(todo) * self.chunk_bytes > self.max_cache_bytes
        ):
            raise MemoryError(
                "chunk prefetch exceeds cache byte budget; use smaller tile groups"
            )
        for i in range(0, len(todo), batch):
            keys = [self._key(*cid) for cid in todo[i : i + batch]]
            got = self.fs.cat(
                keys, on_error="return"
            )  # concurrent; retain error identity
            for cid, key in zip(todo[i : i + batch], keys, strict=False):
                raw = got.get(key)
                self.cache[cid] = self._read_chunk_result(key, raw)
        return len(todo)

    def __call__(self, z0, z1, y0, y1, x0, x1):
        z0, z1, y0, y1, x0, x1 = self._clip_bbox((z0, z1, y0, y1, x0, x1))
        if (z1 - z0) * (y1 - y0) * (
            x1 - x0
        ) * self.dtype.itemsize > self.max_cache_bytes:
            raise MemoryError("volume bbox exceeds byte budget; use smaller tiles")
        out = np.full((z1 - z0, y1 - y0, x1 - x0), self.fill_value, self.dtype)
        for cid in self._chunk_ids_for_bbox(z0, z1, y0, y1, x0, x1):
            chunk = self.cache.get(cid, "MISS")
            if chunk is None:
                continue  # uninitialized chunk -> fill_value already in out
            if isinstance(chunk, str):  # not warmed: fetch this one chunk now
                key = self._key(*cid)
                # Scalar cat() can raise even with on_error='return' in fsspec.
                try:
                    raw = self.fs.cat(key)
                except FileNotFoundError as exc:
                    raw = exc
                chunk = self._read_chunk_result(key, raw)
                if (
                    len(self.cache) < self.max_chunks
                    and (len(self.cache) + 1) * self.chunk_bytes <= self.max_cache_bytes
                ):
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
    obj_grid_size=None,
):
    """Full pipeline for one region -> label-free fragment dir. Returns (out_seg, stats).

    The obj `v` is (x,y,z); the sampler needs (z,y,x) at the sampled pyramid `level`. We
    reorder and divide by `obj_level_div` (default 2**level, i.e. obj coords assumed to be
    level-0 voxels). This convention was validated on Scroll 1 via the tifxyz path
    (reports/detector/render_validation.md); on scrolls without ground truth it is
    inferred (see scroll3_render's coherence check)."""
    from repro.sota_data.obj_geometry import read_obj_uv

    validate_level_sign(level, sign)
    if obj_grid_size is None and (y0 != 0 or x0 != 0):
        raise ValueError("OBJ region offsets require obj_grid_size (the full UV grid)")
    full_shape = grid_shape(obj_grid_size if obj_grid_size is not None else size)
    validate_region(y0, x0, size, full_shape)
    div = float(obj_level_div if obj_level_div is not None else 2**level)
    if not np.isfinite(div) or div <= 0:
        raise ValueError("OBJ coordinate divisor must be positive and finite")
    v, vt = read_obj_uv(obj_path)
    pm_xyz, valid = build_point_map(v, vt, size, origin=(y0, x0), grid_size=full_shape)
    fetch, vol_shape = zarr_fetch(volume_zarr_uri, level)
    pm = pm_xyz[..., ::-1] / div  # (x,y,z) -> (z,y,x), scaled to the level
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats, sampled_valid = sample_layers(
        pm, valid, normals, fetch, tile=32, volume_shape=vol_shape, return_valid=True
    )
    if not sampled_valid.any():
        raise ValueError("region has no pixels supported at every requested depth")
    layers = np.clip(layers, 0, 255).astype(np.uint8)
    layers[:, ~sampled_valid] = 0
    fid = frag_id or f"{seg}_render"
    prov = {
        "segment": seg,
        "geometry": "obj",
        "obj": os.fspath(obj_path),
        "obj_level_div": div,
        "obj_grid_shape": list(full_shape),
        "uv_bbox": [vt.min(axis=0).tolist(), vt.max(axis=0).tolist()],
        "region_px": [y0, x0, size if isinstance(size, int) else list(size)],
        "level": level,
        "normal_sign": sign,
        "volume": os.fspath(volume_zarr_uri),
        "render_contract_version": 2,
        "valid_frac": stats["valid_frac"],
        "clamped_frac": stats["clamped_frac"],
        "geometry_valid_frac": stats["geometry_valid_frac"],
        "depth_offsets": list(range(-13, 13)),
        "intensity_units": "byte range; uint16 divided by 256 before interpolation",
        "extra": extra_prov or {},
    }
    out_seg = write_render_fragment(layers, sampled_valid, out_root, fid, prov)
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
    validate_level_sign(level, sign)
    xyz = read_tifxyz(tifxyz_path)
    if isinstance(size, (int, np.integer)) and size == 0:
        if y0 != 0 or x0 != 0:
            raise ValueError("whole-grid region (size=0) requires zero origins")
        size = tuple(xyz.shape[:2])
    h, w = validate_region(y0, x0, size, xyz.shape[:2])
    xyz = xyz[y0 : y0 + h, x0 : x0 + w]
    pm, valid = pointmap_from_tifxyz(xyz, level_div=2**level)
    fetch, vol_shape = zarr_fetch(volume_zarr_uri, level)
    assert_bounds_fit(pm, valid, vol_shape)
    normals = surface_normals(pm, valid, sign=sign)
    layers, stats, sampled_valid = sample_layers(
        pm, valid, normals, fetch, tile=32, volume_shape=vol_shape, return_valid=True
    )
    if not sampled_valid.any():
        raise ValueError("region has no pixels supported at every requested depth")
    layers = np.clip(layers, 0, 255).astype(np.uint8)
    layers[:, ~sampled_valid] = 0
    fid = frag_id or f"{seg}_render"
    prov = {
        "segment": seg,
        "geometry": "tifxyz",
        "tifxyz": os.fspath(tifxyz_path),
        "coordinate_divisor": 2**level,
        "region_px": [y0, x0, size if isinstance(size, int) else list(size)],
        "level": level,
        "normal_sign": sign,
        "volume": os.fspath(volume_zarr_uri),
        "render_contract_version": 2,
        "valid_frac": stats["valid_frac"],
        "clamped_frac": stats["clamped_frac"],
        "geometry_valid_frac": stats["geometry_valid_frac"],
        "depth_offsets": list(range(-13, 13)),
        "intensity_units": "byte range; uint16 divided by 256 before interpolation",
        "extra": extra_prov or {},
    }
    out_seg = write_render_fragment(layers, sampled_valid, out_root, fid, prov)
    return out_seg, stats
