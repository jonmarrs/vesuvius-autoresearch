"""Geometry for registering the OLD hand-labeled flattening onto the SOTA re-flattening
via the published tifxyz meshes. The old<->new 3D transform is estimated FROM THE MESHES
THEMSELVES (both sample the same physical papyrus surface): PCA-sign-search init + trimmed
ICP with Umeyama updates. No dependence on undocumented scan-frame conventions."""
import os

import cv2
import numpy as np
import tifffile
from scipy.spatial import cKDTree


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
    raise ValueError(f"not a tifxyz (expected HxWx3 or 3xHxW): shape {arr.shape} in {path}")


def _valid_points(xyz):
    pts = xyz.reshape(-1, 3)
    ok = np.isfinite(pts).all(axis=1)
    # meshes commonly mark off-surface pixels with zeros; drop exact-zero triplets
    ok &= ~(np.abs(pts) < 1e-9).all(axis=1)
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
    var_s = (sc ** 2).sum() / len(src)
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
    s0 = float(np.sqrt((cd ** 2).sum() / len(cd)) / np.sqrt((cs ** 2).sum() / len(cs)))

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
    ok = np.isfinite(opts).all(axis=1) & ~(np.abs(opts) < 1e-9).all(axis=1)
    tree = cKDTree(opts[ok])
    ocoords = ocoords[ok]

    sub = new_xyz[::stride, ::stride]
    nh, nw = sub.shape[:2]
    npts = sub.reshape(-1, 3)
    valid = np.isfinite(npts).all(axis=1) & ~(np.abs(npts) < 1e-9).all(axis=1)
    field = np.full((nh, nw, 2), np.nan, np.float32)
    residuals = np.full(nh * nw, np.nan, np.float32)
    if valid.any():
        moved = s * npts[valid] @ R.T + t
        d, idx = tree.query(moved, k=1)
        field.reshape(-1, 2)[valid] = ocoords[idx]
        residuals[valid] = d
    return field, residuals.reshape(nh, nw)


def warp_via_field(image, field, out_shape, interpolation=cv2.INTER_LINEAR):
    """Sample `image` at the field's (row, col) coords, upscaled to out_shape."""
    fh = cv2.resize(field[..., 0], (out_shape[1], out_shape[0]), interpolation=cv2.INTER_LINEAR)
    fw = cv2.resize(field[..., 1], (out_shape[1], out_shape[0]), interpolation=cv2.INTER_LINEAR)
    bad = ~np.isfinite(fh) | ~np.isfinite(fw)
    mapx = np.nan_to_num(fw, nan=-1.0).astype(np.float32)  # cv2.remap: x = col
    mapy = np.nan_to_num(fh, nan=-1.0).astype(np.float32)
    out = cv2.remap(image, mapx, mapy, interpolation,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out[bad] = 0
    return out


def ncc(a, b):
    a = np.asarray(a, np.float64).ravel()
    b = np.asarray(b, np.float64).ravel()
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok] - a[ok].mean(), b[ok] - b[ok].mean()
    denom = np.sqrt((a ** 2).sum() * (b ** 2).sum())
    return float((a * b).sum() / denom) if denom > 0 else 0.0


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
    M, mask = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                          ransacReprojThreshold=3.0)
    n_inl = int(mask.sum()) if mask is not None else 0
    if M is None or n_inl < 25:
        raise ValueError(f"affine fit failed ({n_inl} inliers)")
    return M, n_inl
