"""Geometry for registering the OLD hand-labeled flattening onto the SOTA re-flattening
via the published tifxyz meshes. The old<->new 3D transform is estimated FROM THE MESHES
THEMSELVES (both sample the same physical papyrus surface): PCA-sign-search init + trimmed
ICP with Umeyama updates. No dependence on undocumented scan-frame conventions."""

import json
import os

import cv2
import numpy as np
import tifffile
from scipy.spatial import cKDTree

# Per-segment SOTA surface-volume level-0 shape (y, x), from the 2.4um OME-Zarr.
#
# SINGLE SOURCE OF TRUTH. This lived as a hardcoded module constant in TWO places
# (register_run.py and gt_register.py), each pinned to 20230702185753's geometry and applied
# to every segment. That produced the retracted 2026-07 held-out result, and the second copy
# went unnoticed when the first was fixed. It is defined here, in the dependency-free
# library module, so there is one place to be wrong.
#
# A missing entry must RAISE, never fall back to a default: silently borrowing another
# segment's geometry is precisely the failure mode. Verify entries against the bucket with
# `python -m repro.sota_data.register_run verify_shapes`.
LEVEL0_SHAPES = {
    "20230702185753": (50600, 36400),
    "20231005123336": (34880, 97280),
    "20231210121321": (51000, 39980),
}


def level0_shape(seg):
    """Level-0 (y, x) for a segment. Raises rather than guessing."""
    if seg not in LEVEL0_SHAPES:
        raise ValueError(
            f"no level-0 shape recorded for segment {seg}. Add it to "
            "register.LEVEL0_SHAPES (get it with register_run.fetch_level0_shape). "
            "Refusing to fall back to another segment's geometry."
        )
    return LEVEL0_SHAPES[seg]


def read_tifxyz(path):
    if os.path.isdir(path):
        # the released bucket format: a directory of meta.json + x.tif/y.tif/z.tif planes
        planes = []
        for name in ("x.tif", "y.tif", "z.tif"):
            p = os.path.join(path, name)
            if not os.path.exists(p):
                raise ValueError(f"not a tifxyz dir (missing {name}): {path}")
            planes.append(np.asarray(tifffile.imread(p), np.float32))
        if not (planes[0].shape == planes[1].shape == planes[2].shape):
            raise ValueError(f"tifxyz planes disagree in shape in {path}")
        return np.stack(planes, axis=-1)
    arr = np.asarray(tifffile.imread(path), np.float32)
    if arr.ndim == 3 and arr.shape[-1] == 3:
        return arr
    if arr.ndim == 3 and arr.shape[0] == 3:
        return np.ascontiguousarray(arr.transpose(1, 2, 0))
    raise ValueError(
        f"not a tifxyz (expected HxWx3 or 3xHxW): shape {arr.shape} in {path}"
    )


def _valid_points(xyz):
    pts = xyz.reshape(-1, 3)
    ok = np.isfinite(pts).all(axis=1)
    # meshes commonly mark off-surface pixels with zeros; drop exact-zero triplets
    ok &= ~(np.abs(pts) < 1e-9).all(axis=1)
    # real bucket meshes mark invalid pixels as (-1,-1,-1)
    ok &= ~(np.abs(pts + 1.0) < 1e-6).all(axis=1)
    return pts[ok]


def _umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    sc, dc = src - mu_s, dst - mu_d
    cov = dc.T @ sc / len(src)
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    var_s = (sc**2).sum() / len(src)
    s = float(np.trace(np.diag(D) @ S) / var_s)
    t = mu_d - s * R @ mu_s
    return s, R.astype(np.float32), t.astype(np.float32)


def fit_similarity(src, dst, iters=3, sample=20000, trim=0.8, seed=0):
    """Fit dst ~= s*R*src + t from two UNPAIRED point sets sampling the same surface."""
    rng = np.random.default_rng(seed)
    src = _valid_points(np.asarray(src, np.float32).reshape(-1, 3))
    dst = _valid_points(np.asarray(dst, np.float32).reshape(-1, 3))
    src_s = src[rng.choice(len(src), min(sample, len(src)), replace=False)]
    dst_s = dst[rng.choice(len(dst), min(sample, len(dst)), replace=False)]
    tree = cKDTree(dst_s)

    def centered_axes(pts):
        # SVD on an (N, 3) matrix is economy-sized (cost ~N, not N^2/N^3), so there is
        # no compute reason to subsample further here -- and doing so is actively harmful:
        # src_s/dst_s are independently drawn, so an extra independent 5k-point subsample
        # of each gives the two point clouds slightly different covariance estimates,
        # which biases the recovered rotation axes by ~1 degree (verified empirically) and
        # ICP cannot correct that bias afterwards (NN correspondences reinforce it). Use
        # the full (already up-to-`sample`-sized) point set for exact PCA axes instead.
        mu = pts.mean(0)
        c = pts - mu
        _, _, Vt = np.linalg.svd(c, full_matrices=False)
        return mu, c, Vt

    mu_s, cs, Vs = centered_axes(src_s)
    mu_d, cd, Vd = centered_axes(dst_s)
    s0 = float(np.sqrt((cd**2).sum() / len(cd)) / np.sqrt((cs**2).sum() / len(cs)))

    # det(R0) = det(Vd) * det(F) * det(Vs). np.linalg.svd's sign convention for Vt is
    # arbitrary (LAPACK does not guarantee det(Vt)=+1), so det(Vs)*det(Vd) can come out
    # either +1 or -1 depending on the data. A fixed F = diag([fy, fx, fy*fx]) always has
    # det(F)=+1, which only reaches det(R0)=+1 in the +1 case -- in the -1 case every one
    # of the 4 candidates is skipped and `best` stays None. Target the determinant that
    # F actually needs to supply so a valid candidate always exists.
    target_det = float(np.linalg.det(Vs) * np.linalg.det(Vd))
    best = None
    for fy in (1, -1):
        for fx in (1, -1):
            fz = fy * fx * target_det
            F = np.diag([fy, fx, fz]).astype(np.float32)
            R0 = (Vd.T @ F @ Vs).astype(np.float32)
            if np.linalg.det(R0) < 0:
                continue
            moved = s0 * src_s @ R0.T + (mu_d - s0 * R0 @ mu_s)
            d, _ = tree.query(moved, k=1)
            med = float(np.median(d))
            if best is None or med < best[0]:
                best = (med, R0)
    s, R, t = s0, best[1], (mu_d - s0 * best[1] @ mu_s)

    for _ in range(iters):
        moved = s * src_s @ R.T + t
        d, idx = tree.query(moved, k=1)
        keep = d <= np.quantile(d, trim)
        s, R, t = _umeyama(src_s[keep], dst_s[idx[keep]])
    moved = s * src_s @ R.T + t
    med_res = float(np.median(tree.query(moved, k=1)[0]))
    return s, R, t, med_res


def correspondence_field(new_xyz, s, R, t, old_xyz, stride=8):
    """old-mesh (row, col) coords for each stride-th new-mesh pixel, + NN residuals."""
    oh, ow = old_xyz.shape[:2]
    orr, occ = np.mgrid[0:oh:stride, 0:ow:stride]
    opts = old_xyz[::stride, ::stride].reshape(-1, 3)
    ocoords = np.stack([orr.reshape(-1), occ.reshape(-1)], axis=1).astype(np.float32)
    ok = (
        np.isfinite(opts).all(axis=1)
        & ~(np.abs(opts) < 1e-9).all(axis=1)
        & ~(np.abs(opts + 1.0) < 1e-6).all(axis=1)
    )
    tree = cKDTree(opts[ok])
    ocoords = ocoords[ok]

    sub = new_xyz[::stride, ::stride]
    nh, nw = sub.shape[:2]
    npts = sub.reshape(-1, 3)
    valid = (
        np.isfinite(npts).all(axis=1)
        & ~(np.abs(npts) < 1e-9).all(axis=1)
        & ~(np.abs(npts + 1.0) < 1e-6).all(axis=1)
    )
    field = np.full((nh, nw, 2), np.nan, np.float32)
    residuals = np.full(nh * nw, np.nan, np.float32)
    if valid.any():
        moved = s * npts[valid] @ R.T + t
        d, idx = tree.query(moved, k=1)
        field.reshape(-1, 2)[valid] = ocoords[idx]
        residuals[valid] = d
    return field, residuals.reshape(nh, nw)


# Recorded with every registration that `region_in_mesh` and `warp_via_field` make. One
# without it was warped by the rounded crop and pixel-centre stretch they replaced.
WARP_ALIGNMENT = "vertex-aligned field sampling of a fractional crop (2026-10-17)"
OLD_WARP_NOTE = (
    "registered by the warp before 2026-10-17. Under the tifxyz vertex convention "
    "(unverified against the release render), its rounded crop and pixel-centre stretch "
    "shift content down and right by several level-2 px: 7.8 in rows and 5.6 in columns "
    "on average for the 20230702185753 region, up to 18 at the edges. Re-run the warp "
    "before relying on it"
)

# An exported label (ScrollGT's gt_ink.png) has no stats beside it to say which warp made it.
SCROLLGT_WARP_NOTE = (
    "it carries no warp record. Unless its registration was re-made by the warp of "
    "2026-10-17 or later, it carries the old warp's shift of several px (under the tifxyz "
    "vertex convention, about (-8, -6) on the agreement peak in 20230702185753's geometry, "
    "-15.8 to +0.5 per axis in general). Re-export it from a re-warped registration before "
    "reading placements measured on it as current"
)


def warp_provenance(label_path):
    """A caveat for a registered label not made by the current warp, else None.

    A label `register_run` wrote has its `registration_stats.json` beside it, which records
    the warp (`WARP_ALIGNMENT`). An exported one (ScrollGT's gt_ink.png) has none.
    """
    stats = os.path.join(os.path.dirname(label_path), "registration_stats.json")
    if not os.path.exists(stats):
        return f"NOTE: {label_path}: {SCROLLGT_WARP_NOTE}."
    with open(stats) as f:
        if json.load(f).get("warp_alignment") == WARP_ALIGNMENT:
            return None
    return f"NOTE: {label_path} was {OLD_WARP_NOTE}."


def region_in_mesh(xyz, level0, region, level=2):
    """Crop a mesh grid to a square region of the level-`level` surface volume, and say
    where each of the region's rows and columns falls in the crop.

    The tifxyz convention is vertex-aligned: grid vertex r sits at surface coordinate
    r / scale (`villa/lasagna/tifxyz_format.md`, sections 2 and 5.1; villa's reader maps
    full-resolution index p to grid coordinate p * scale, `Tifxyz.__getitem__`). So with
    sy mesh rows per level-`level` row, the region's row y0 + i is mesh row (y0 + i) * sy,
    generally between two vertices. The crop takes every vertex the region's rows fall
    between, and the returned coordinates are relative to it.

    Until 2026-10-17 the crop bounds were rounded to whole cells and `warp_via_field`
    stretched the crop over the region pixel-centre to pixel-centre. At the 7.91 um mesh's
    ~16.3 level-2 px per cell that placed the (4000, 2500, 4096) region of 20230702185753
    1.8-13.8 px off in rows (7.8 on average) and 0-18.3 px in columns (5.6; 0.7-10.6 away
    from the edges, where cv2.resize clamps), shifting content down and right on average.

    A level-`level` pixel is taken at its level-0 origin; a pooled pyramid would put it
    (2**level - 1) / 2 level-0 px further on, 0.375 level-2 px at level 2.

    Returns (crop, (rows, cols)): the crop, and float64 crop coordinates of the region's
    rows and columns. Coordinates past the mesh's edge are left there, and
    `warp_via_field` zeroes the pixels they reach.
    """
    mh, mw = xyz.shape[:2]
    down = 2**level
    sy, sx = mh / (level0[0] / down), mw / (level0[1] / down)
    y0, x0, size = region
    rows = (y0 + np.arange(size)) * sy
    cols = (x0 + np.arange(size)) * sx
    ys, xs = max(int(np.floor(rows[0])), 0), max(int(np.floor(cols[0])), 0)
    ye, xe = int(np.floor(rows[-1])) + 2, int(np.floor(cols[-1])) + 2
    return xyz[ys:ye, xs:xe], (rows - ys, cols - xs)


def _axis_weights(at, n):
    """Lower vertex, fraction and in-range flag for linear sampling of n vertices."""
    lo = np.clip(np.floor(at).astype(np.int64), 0, max(n - 2, 0))
    return lo, np.minimum(lo + 1, n - 1), at - lo, (at >= 0) & (at <= n - 1)


def _lerp(a, b, f):
    """(1 - f) a + f b, but a NaN with zero weight does not contaminate the result."""
    out = (1 - f) * a + f * b
    out = np.where(f == 0, a, out)
    return np.where(f == 1, b, out)


def stride_coords(out_shape, stride):
    """`coords` for a stride-k field over the image it was computed on
    (`correspondence_field`): field vertex j sits on pixel j * stride."""
    return np.arange(out_shape[0]) / stride, np.arange(out_shape[1]) / stride


def sample_field(field, out_shape, *, coords):
    """The field's (row, col) values at each output pixel, linearly between its vertices.

    `coords` = (rows, cols) gives the field-grid coordinate of each output row and column:
    from `region_in_mesh` for a mesh crop, or `stride_coords` for a stride field. It is
    required: stretching the field over the output instead is the misalignment this
    replaced (about half a cell, plus the crop's rounding).

    Returns (row, col, bad); `bad` marks pixels off the field's grid or reached by an
    invalid (NaN) vertex with non-zero weight.
    """
    fh, fw = field.shape[:2]
    rows, cols = (np.asarray(c, np.float64) for c in coords)
    if (len(rows), len(cols)) != tuple(out_shape[:2]):
        raise ValueError(
            f"sample_field: {len(rows)} x {len(cols)} coordinates for an output of "
            f"{tuple(out_shape[:2])}"
        )
    r0, r1, fr, r_ok = _axis_weights(rows, fh)
    c0, c1, fc, c_ok = _axis_weights(cols, fw)
    out = []
    # the full-size pass in float32, as cv2.remap takes it
    fc = fc.astype(np.float32)[None, :]
    for k in (0, 1):
        f = field[..., k].astype(np.float64)
        by_row = _lerp(f[r0], f[r1], fr[:, None]).astype(np.float32)
        out.append(_lerp(by_row[:, c0], by_row[:, c1], fc))
    bad = ~np.isfinite(out[0]) | ~np.isfinite(out[1])
    bad |= ~r_ok[:, None] | ~c_ok[None, :]
    return out[0], out[1], bad


def warp_via_field(image, field, out_shape, interpolation=cv2.INTER_LINEAR, *, coords):
    """Sample `image` at the field's (row, col) coords, resampled to out_shape.

    `coords` places each output row and column on the field's grid (see `sample_field`);
    pass the ones `region_in_mesh` returns with the crop the field was computed on.
    Pixels with no valid field value are 0.
    """
    fh, fw, bad = sample_field(field, out_shape, coords=coords)
    mapx = np.where(bad, np.float32(-1), fw)  # cv2.remap: x = col
    mapy = np.where(bad, np.float32(-1), fh)
    out = cv2.remap(
        image, mapx, mapy, interpolation, borderMode=cv2.BORDER_CONSTANT, borderValue=0
    )
    out[bad] = 0
    return out


def ncc(a, b):
    a = np.asarray(a, np.float64).ravel()
    b = np.asarray(b, np.float64).ravel()
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok] - a[ok].mean(), b[ok] - b[ok].mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    return float((a * b).sum() / denom) if denom > 0 else 0.0


def label_line_periodicity(label, band=(40, 260)):
    """Teacher-FREE coherence check: correctly-registered text has strong horizontal
    line-periodicity (row-wise ink density is periodic at the text-line pitch); a
    scrambled/off-manifold mapping destroys it. Returns the peak row-autocorrelation in
    the plausible line-pitch band (0..1). Convention-BLIND (a vertical flip preserves it),
    so it confirms 'real text landed on the manifold', not the 2D orientation."""
    lab = np.asarray(label)
    if lab.ndim == 3:
        lab = lab[..., 0]
    ink = (lab > 127).astype(np.float64)
    rows = ink.mean(axis=1)
    rows = rows - rows.mean()
    ac = np.correlate(rows, rows, "full")[len(rows) - 1 :]
    if ac[0] <= 0:
        return 0.0
    ac = ac / ac[0]
    lo, hi = band
    hi = min(hi, len(ac))
    if hi <= lo:
        return 0.0
    return float(ac[lo:hi].max())


def fit_affine_orb(old_img, new_img, n_features=5000):
    orb = cv2.ORB_create(nfeatures=n_features)
    k1, d1 = orb.detectAndCompute(old_img, None)
    k2, d2 = orb.detectAndCompute(new_img, None)
    if d1 is None or d2 is None:
        raise ValueError("ORB found no descriptors")
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    if len(matches) < 25:
        raise ValueError(f"only {len(matches)} ORB matches")
    src = np.float32([k1[m.queryIdx].pt for m in matches])
    dst = np.float32([k2[m.trainIdx].pt for m in matches])
    M, mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0
    )
    n_inl = int(mask.sum()) if mask is not None else 0
    if M is None or n_inl < 25:
        raise ValueError(f"affine fit failed ({n_inl} inliers)")
    return M, n_inl


class PlacementNotLocated(ValueError):
    """placement_peak found no peak that locates the label (strict mode)."""


def placement_peak(label, reference, max_shift=256, coarse=4, refine=8, strict=True):
    """Where does label-vs-reference agreement actually peak, in label pixels?

    A registration is only correct if agreement is maximised at ZERO shift. Residual
    statistics do NOT test this: they measure correspondence scatter, and a label can have
    a tight residual while sitting bodily displaced. That conflation is exactly what let a
    ~1766-voxel misplacement ship in 2026-07 (see
    reports/detector/registration_offset_2026-08-07.md), so this is a gate, not a diagnostic.

    Both inputs are boolean-ised at >127 and compared on a common interior crop -- never
    via np.roll, whose wraparound would contaminate the score. Searches a downsampled grid
    first, then refines at full resolution.

    Returns (dy, dx, dice_at_zero, dice_at_peak) with the shifts in input pixels. A correct
    registration gives (0, 0) up to a couple of pixels.

    ``strict`` (the gates' setting) raises PlacementNotLocated instead of returning a peak
    that does not locate anything. Until 2026-10-16 these returned a shift a gate could pass:
      * no comparison window had any ink, so the "peak" was the initial (0, 0) with a Dice
        of -1, read as zero offset;
      * the best agreement is a Dice of 0, so the "peak" is an arbitrary shift;
      * the coarse peak lies on the search boundary (a flat landscape tie-breaks to a
        corner, and a label displaced beyond ``max_shift`` peaks at the edge), so the true
        peak is outside the search.
    Probes that map placement over many tiles pass ``strict=False`` and read the clamp.
    """

    def _binarise(x, what):
        x = np.asarray(x)
        # Accept bool masks as-is. Thresholding a bool array at >127 yields all-False,
        # which would make every comparison degenerate and return a PERFECT (0, 0) --
        # a gate silently passing on garbage input. Guard it explicitly.
        m = x if x.dtype == bool else x > 127
        if not m.any():
            raise ValueError(
                f"placement_peak: {what} is empty after binarisation "
                f"(dtype={x.dtype}, min={x.min()}, max={x.max()}). Pass a labelled image, "
                "not an all-zero or already-inverted mask."
            )
        return m

    if np.shape(label) != np.shape(reference):
        raise ValueError(
            f"placement_peak: shape mismatch {np.shape(label)} vs {np.shape(reference)}"
        )
    a = _binarise(label, "label")
    b = _binarise(reference, "reference")

    def dice(g, p):
        s = int(g.sum()) + int(p.sum())
        return 2.0 * float((g & p).sum()) / s if s else float("nan")

    def scan(g_img, p_img, margin, lo, hi, step):
        h, w = g_img.shape
        core = g_img[margin : h - margin, margin : w - margin]
        best = (-1.0, 0, 0)
        for dy in range(lo[0], hi[0] + 1, step):
            for dx in range(lo[1], hi[1] + 1, step):
                d = dice(
                    core,
                    p_img[margin + dy : h - margin + dy, margin + dx : w - margin + dx],
                )
                if d > best[0]:
                    best = (d, dy, dx)
        return best

    # coarse pass on a downsampled copy -- same peak, far cheaper
    ds = max(int(coarse), 1)
    if ds > 1:
        small = (a.shape[0] // ds, a.shape[1] // ds)
        a_s = (
            cv2.resize(a.astype(np.uint8), small[::-1], interpolation=cv2.INTER_NEAREST)
            > 0
        )
        b_s = (
            cv2.resize(b.astype(np.uint8), small[::-1], interpolation=cv2.INTER_NEAREST)
            > 0
        )
    else:
        a_s, b_s = a, b
    m_s = max_shift // ds + 2
    if min(a_s.shape) <= 2 * m_s + 2:
        m_s = max(min(a_s.shape) // 4, 1)
    coarse_dice, cy, cx = scan(a_s, b_s, m_s, (-m_s, -m_s), (m_s, m_s), 1)
    if strict and not coarse_dice > 0:  # -1 (nothing scored), 0 or NaN
        raise PlacementNotLocated(
            f"placement_peak: no shift agrees at all at the coarse step ({ds} px; thin "
            "ink can vanish when downsampled); the placement is unknown, not zero"
        )
    if strict and max(abs(cy), abs(cx)) >= m_s:
        raise PlacementNotLocated(
            f"placement_peak: the agreement peak is on the search boundary "
            f"({cy * ds}, {cx * ds}) px of +/-{m_s * ds}: the label may be displaced "
            "beyond the search, or the landscape is flat; the placement is not located"
        )
    cy, cx = cy * ds, cx * ds

    # refine at full resolution around the coarse peak
    margin = max_shift + refine + 2
    if min(a.shape) <= 2 * margin + 2:
        margin = max(min(a.shape) // 4, 1)
    clipped = (
        int(np.clip(cy, -margin + refine, margin - refine)),
        int(np.clip(cx, -margin + refine, margin - refine)),
    )
    if strict and max(abs(clipped[0] - cy), abs(clipped[1] - cx)) > ds:
        raise PlacementNotLocated(
            f"placement_peak: the coarse peak ({cy}, {cx}) is outside the full-resolution "
            f"search (+/-{margin - refine} px); the placement is not located"
        )
    cy, cx = clipped
    peak, by, bx = scan(
        a, b, margin, (cy - refine, cx - refine), (cy + refine, cx + refine), 1
    )
    if strict and not peak > 0:
        raise PlacementNotLocated(
            "placement_peak: no shift agrees at all at full resolution; the placement is "
            "unknown"
        )

    h, w = a.shape
    zero = dice(
        a[margin : h - margin, margin : w - margin],
        b[margin : h - margin, margin : w - margin],
    )
    return int(by), int(bx), float(zero), float(peak)
