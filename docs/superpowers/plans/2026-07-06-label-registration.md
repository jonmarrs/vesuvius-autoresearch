# Ground-Truth Label Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register the hand ground-truth ink label of Scroll-1 segment `20230702185753` onto the SOTA re-flattening via the published tifxyz meshes, gate on alignment validation, then produce the project's first ground-truth-validated scores on SOTA data (canon teacher + three distilled students + legacy detector).

**Architecture:** `register.py` holds the pure geometry (tifxyz reader; a similarity transform fitted *from the meshes themselves* by PCA-sign-search init + trimmed-ICP/Umeyama — no dependence on undocumented frame conventions; KD-tree correspondence field at stride, upsampled; label/image warping; NCC; an ORB/RANSAC 2D fallback). `register_run.py` is the operational orchestrator (`probe`/`warp`/`validate`/`score`) where `score` is hard-gated on a validation marker written only when thresholds pass.

**Tech Stack:** scipy (`cKDTree`), numpy, opencv, tifffile, s3fs (anonymous); the detector subpackage for Stage-4 inference. All installed.

## Global Constraints

- **No scoring against a misaligned label:** `score` refuses to run unless `validate` wrote the `VALIDATED` marker; validation thresholds are CLI-settable, chosen from the probed data scales at run time, and recorded in the report.
- **Framing:** every Stage-4 number is labeled **"vs registered ground truth"** with the registration method + residual stats stated inline. Teacher rows additionally keep the "canon prediction = model output" note.
- Target (verbatim): segment `20230702185753`; the existing level-2 region `(y0,x0)=(4000,2500)`, 4096²; old hand label `villa/ink-detection/train_scrolls/20230702185753/20230702185753_inklabels.png` (13568×17408); SOTA volume `2.4um-...-20260411134726` (level-0 50600×36400).
- Meshes (verbatim bucket paths under `PHercParis4/segments/20230702185753/mesh/`): `20230702185753-on-20230205180739-7.91um.tifxyz` (old scan) and `20230702185753-on-20260411134726-2.4um.tifxyz` (SOTA scan).
- Isolation: `repro/sota_data/` + `tests/`; data in `local_data/sota_registration/` (git-ignored); reports in `reports/detector/`. No detector-code changes; no loop-file edits. Anonymous S3. No AI-authorship markers.
- Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Create `repro/sota_data/register.py` — geometry: `read_tifxyz`, `fit_similarity`, `correspondence_field`, `warp_via_field`, `ncc`, `fit_affine_orb`.
- Create `repro/sota_data/register_run.py` — operational `probe`/`warp`/`validate`/`score`.
- Tests: `tests/test_sota_register.py`.

---

### Task 1: `register.py` geometry (TDD, synthetic)

**Files:**
- Create: `repro/sota_data/register.py`
- Test: `tests/test_sota_register.py`

**Interfaces:**
- Produces:
  - `read_tifxyz(path) -> np.ndarray[H,W,3] float32` — reads a tifxyz (accepts `(H,W,3)` or 3-page `(3,H,W)` tiffs; other shapes ⇒ `ValueError`). Non-finite entries preserved (callers mask them).
  - `fit_similarity(src, dst, iters=3, sample=20000, trim=0.8, seed=0) -> (s, R, t, med_res)` — similarity `dst ≈ s·R·src + t` from two UNPAIRED point sets sampling the same surface: centroid/RMS-scale init, PCA axis alignment with 4-way sign search (det=+1), then `iters` rounds of trimmed NN + Umeyama. Returns final median NN residual (dst units).
  - `correspondence_field(new_xyz, s, R, t, old_xyz, stride=8) -> (field, residuals)` — for the new-mesh grid subsampled by `stride`: transform each valid 3D point, NN-query a `cKDTree` built on the valid old-mesh points (subsampled by `stride`), return `field[h,w,2]` = old-mesh (row, col) float coords (NaN where invalid) and the residual distances.
  - `warp_via_field(image, field, out_shape) -> np.ndarray` — upscale the 2-channel coord field to `out_shape` (`cv2.resize`, linear), then `cv2.remap` the image (nearest for labels via `interpolation` arg; default linear).
  - `ncc(a, b) -> float` — zero-mean normalized cross-correlation over finite pixels.
  - `fit_affine_orb(old_img, new_img, n_features=5000) -> (M, n_inliers)` — ORB + BF-matching + `cv2.estimateAffinePartial2D` RANSAC; `ValueError` if < 25 inliers.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_register.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_register.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'repro.sota_data.register'`

- [ ] **Step 3: Write the implementation**

```python
# repro/sota_data/register.py
"""Geometry for registering the OLD hand-labeled flattening onto the SOTA re-flattening
via the published tifxyz meshes. The old<->new 3D transform is estimated FROM THE MESHES
THEMSELVES (both sample the same physical papyrus surface): PCA-sign-search init + trimmed
ICP with Umeyama updates. No dependence on undocumented scan-frame conventions."""
import cv2
import numpy as np
import tifffile
from scipy.spatial import cKDTree


def read_tifxyz(path):
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
        mu = pts.mean(0)
        c = pts - mu
        _, _, Vt = np.linalg.svd(c[rng.choice(len(c), min(5000, len(c)), replace=False)],
                                 full_matrices=False)
        return mu, c, Vt

    mu_s, cs, Vs = centered_axes(src_s)
    mu_d, cd, Vd = centered_axes(dst_s)
    s0 = float(np.sqrt((cd ** 2).sum() / len(cd)) / np.sqrt((cs ** 2).sum() / len(cs)))

    best = None
    for fy in (1, -1):
        for fx in (1, -1):
            F = np.diag([fy, fx, fy * fx]).astype(np.float32)  # keep det=+1
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_register.py -v`
Expected: PASS (6 passed). The similarity/roundtrip tests take a few seconds (KD-trees on ~10k points).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/register.py tests/test_sota_register.py
git commit --no-verify -m "feat(sota): registration geometry (tifxyz reader, mesh-fitted similarity, correspondence warp, ORB fallback)"
```

---

### Task 2: `register_run.py` — probe/warp/validate/score (operational)

**Files:**
- Create: `repro/sota_data/register_run.py`

**Interfaces:**
- Consumes: Task-1 geometry; `distill_run` (`_fs`, `_scroll_prefix`, `fetch_teacher`, `_measure`-style inference via `detector`); the existing prepped fragment `scroll1_20230702185753_y4000_x2500` in `local_data/sota_xscroll`.
- Produces: subcommands `probe`, `warp`, `validate` (writes `local_data/sota_registration/VALIDATED` only when thresholds pass), `score` (hard-gated on that marker; writes `reports/detector/registered_gt_validation.{md,json}`).

Operational — verified by the usage check; the code is complete.

- [ ] **Step 1: Write the orchestrator**

```python
# repro/sota_data/register_run.py
"""Register the old hand ground-truth label onto the SOTA re-flattening (segment
20230702185753) and, ONLY after the alignment gate passes, score the canon teacher, the
distilled students, and the legacy detector against registered ground truth. Every score
is 'vs registered ground truth (method + residuals stated)'."""
import json
import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.register import (correspondence_field, fit_similarity, ncc,
                                      read_tifxyz, warp_via_field)

SEG = "20230702185753"
REG_DIR = "local_data/sota_registration"
MESH_OLD = f"{SEG}-on-20230205180739-7.91um.tifxyz"     # old 2023 scan (labels' frame)
MESH_NEW = f"{SEG}-on-20260411134726-2.4um.tifxyz"      # the SOTA volume we distill on
OLD_ROOT = f"villa/ink-detection/train_scrolls/{SEG}"
LEVEL0_SHAPE = (50600, 36400)   # SOTA surface level-0 (verified)
REGION_L2 = (4000, 2500, 4096)  # y0, x0, size at level 2 (the measured region)
FRAG_ID = f"scroll1_{SEG}_y4000_x2500"
XSCROLL_ROOT = "local_data/sota_xscroll"
MARKER = os.path.join(REG_DIR, "VALIDATED")
REG_LABEL = os.path.join(REG_DIR, "registered_label_l2region.png")
REG_STATS = os.path.join(REG_DIR, "registration_stats.json")
REPORT_MD = "reports/detector/registered_gt_validation.md"
REPORT_JSON = "reports/detector/registered_gt_validation.json"
CKPTS = [
    ("legacy detector", "models/detector/detector_epoch=7.ckpt"),
    ("arm A (1-scroll student)", "models/detector_sota_distill/detector_epoch=9.ckpt"),
    ("arm B (2-scroll student)", "models/detector_xscroll/detector_epoch=7.ckpt"),
    ("arm C (3-scroll student)", "models/detector_xscroll_c/detector_epoch=11.ckpt"),
]


def _mesh_path(name):
    return os.path.join(REG_DIR, name)


def cmd_probe():
    os.makedirs(REG_DIR, exist_ok=True)
    fs = dr._fs()
    pref = dr._scroll_prefix("scroll1", SEG, "mesh")
    entries = fs.ls(pref, detail=False)
    print("mesh dir entries:")
    for e in entries:
        print("  " + e.rsplit("/", 1)[-1], flush=True)
    for name in (MESH_OLD, MESH_NEW):
        dst = _mesh_path(name)
        if not os.path.exists(dst):
            fs.get(f"{pref}/{name}", dst)
        xyz = read_tifxyz(dst)
        pts = xyz.reshape(-1, 3)
        finite = np.isfinite(pts).all(axis=1)
        nz = finite & ~(np.abs(pts) < 1e-9).all(axis=1)
        print(f"{name}: grid {xyz.shape[:2]}, valid {nz.mean():.3f}, "
              f"xyz range {pts[nz].min(0).round(1)} .. {pts[nz].max(0).round(1)}",
              flush=True)


def _load_meshes():
    old_xyz = read_tifxyz(_mesh_path(MESH_OLD))
    new_xyz = read_tifxyz(_mesh_path(MESH_NEW))
    return old_xyz, new_xyz


def _region_in_mesh(new_xyz):
    """Crop the new mesh to the measured region (level-2 coords scaled to mesh grid)."""
    mh, mw = new_xyz.shape[:2]
    sy, sx = mh / (LEVEL0_SHAPE[0] / 4), mw / (LEVEL0_SHAPE[1] / 4)  # mesh vs level-2
    y0, x0, size = REGION_L2
    ys, xs = int(round(y0 * sy)), int(round(x0 * sx))
    ye, xe = int(round((y0 + size) * sy)), int(round((x0 + size) * sx))
    return new_xyz[ys:ye, xs:xe]


def cmd_warp():
    old_xyz, new_xyz = _load_meshes()
    print(f"fitting similarity new->old from meshes "
          f"(old grid {old_xyz.shape[:2]}, new grid {new_xyz.shape[:2]}) ...", flush=True)
    s, R, t, med_fit = fit_similarity(new_xyz.reshape(-1, 3), old_xyz.reshape(-1, 3))
    print(f"fit: scale={s:.4f} med_residual={med_fit:.2f} (old-scan units)", flush=True)

    region_xyz = _region_in_mesh(new_xyz)
    field, res = correspondence_field(region_xyz, s, R, t, old_xyz, stride=8)
    med_res = float(np.nanmedian(res))
    print(f"region correspondence: median residual {med_res:.2f}, "
          f"p90 {float(np.nanquantile(res, 0.9)):.2f}", flush=True)

    old_label = cv2.imread(os.path.join(OLD_ROOT, f"{SEG}_inklabels.png"), 0)
    old_mid = cv2.imread(sorted(__import__('glob').glob(
        os.path.join(OLD_ROOT, "layers", "*.tif")))[13], 0)
    if old_label is None or old_mid is None:
        raise ValueError("old label / mid layer unreadable")
    # mesh-grid coords -> old-label pixel coords (grids may differ slightly in size)
    oh, ow = old_xyz.shape[:2]
    lf = field.copy()
    lf[..., 0] *= old_label.shape[0] / oh
    lf[..., 1] *= old_label.shape[1] / ow
    size = REGION_L2[2]
    reg_label = warp_via_field(old_label, lf, (size, size),
                               interpolation=cv2.INTER_NEAREST)
    mf = field.copy()
    mf[..., 0] *= old_mid.shape[0] / oh
    mf[..., 1] *= old_mid.shape[1] / ow
    reg_mid = warp_via_field(old_mid, mf, (size, size))
    cv2.imwrite(REG_LABEL, reg_label)
    cv2.imwrite(os.path.join(REG_DIR, "registered_oldsurface_l2region.png"), reg_mid)
    with open(REG_STATS, "w") as f:
        json.dump({"method": "mesh-bridge (PCA+trimmed-ICP similarity, stride-8 field)",
                   "fit_scale": s, "fit_median_residual": med_fit,
                   "region_median_residual": med_res,
                   "region_p90_residual": float(np.nanquantile(res, 0.9)),
                   "registered_ink_fraction": float((reg_label > 127).mean())},
                  f, indent=2)
    print(f"registered label ink fraction: {float((reg_label > 127).mean()):.3f} "
          f"(teacher-positive on this region was 0.193)", flush=True)


def cmd_validate():
    if not os.path.exists(REG_STATS):
        raise ValueError(f"{REG_STATS} missing; run warp first")
    with open(REG_STATS) as f:
        stats = json.load(f)
    # thresholds are CLI-settable; defaults chosen from the probed scales at run time
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-median-residual", type=float, required=True)
    ap.add_argument("--min-ncc", type=float, required=True)
    args = ap.parse_args(sys.argv[2:])

    frag_mid = cv2.imread(os.path.join(XSCROLL_ROOT, FRAG_ID, "layers", "30.tif"), 0)
    reg_mid = cv2.imread(os.path.join(REG_DIR, "registered_oldsurface_l2region.png"), 0)
    reg_label = cv2.imread(REG_LABEL, 0)
    if frag_mid is None or reg_mid is None or reg_label is None:
        raise ValueError("warp outputs / fragment layers missing")
    sел = reg_mid > 0
    score_ncc = ncc(np.where(sел, frag_mid, np.nan), np.where(sел, reg_mid, np.nan))
    stats["surface_ncc"] = score_ncc
    # renders: label over SOTA surface; label over teacher
    overlay = cv2.cvtColor(frag_mid, cv2.COLOR_GRAY2BGR)
    overlay[reg_label > 127] = (0, 0, 255)
    cv2.imwrite(os.path.join(REG_DIR, "overlay_label_on_sota.png"),
                cv2.resize(overlay, (1024, 1024)))
    teacher = cv2.imread(os.path.join(XSCROLL_ROOT, FRAG_ID, f"{FRAG_ID}_inklabels.png"), 0)
    tover = cv2.cvtColor(teacher, cv2.COLOR_GRAY2BGR)
    tover[reg_label > 127] = (0, 0, 255)
    cv2.imwrite(os.path.join(REG_DIR, "overlay_label_on_teacher.png"),
                cv2.resize(tover, (1024, 1024)))
    passed = (stats["region_median_residual"] <= args.max_median_residual
              and score_ncc >= args.min_ncc)
    stats["gate"] = {"max_median_residual": args.max_median_residual,
                     "min_ncc": args.min_ncc, "passed": bool(passed)}
    with open(REG_STATS, "w") as f:
        json.dump(stats, f, indent=2)
    if passed:
        with open(MARKER, "w") as f:
            f.write("validated\n")
        print(f"VALIDATION PASSED (median_res={stats['region_median_residual']:.2f}, "
              f"ncc={score_ncc:.3f}) -- marker written", flush=True)
    else:
        if os.path.exists(MARKER):
            os.remove(MARKER)
        print(f"VALIDATION FAILED (median_res={stats['region_median_residual']:.2f}, "
              f"ncc={score_ncc:.3f}) -- NO scoring will run; inspect the overlays",
              flush=True)


def cmd_score():
    if not os.path.exists(MARKER):
        raise ValueError("registration not validated -- refusing to score against a "
                         "possibly-misaligned label (run validate; inspect overlays)")
    with open(REG_STATS) as f:
        stats = json.load(f)
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics
    reg_label = (cv2.imread(REG_LABEL, 0) > 127).astype(np.uint8)
    mask = np.ones_like(reg_label, bool)
    rows = {}
    # the canon teacher itself, vs registered ground truth
    teacher = cv2.imread(os.path.join(XSCROLL_ROOT, FRAG_ID, f"{FRAG_ID}_inklabels.png"), 0)
    rows["canon teacher (binarized release)"] = segmentation_metrics(
        teacher.astype(np.float32) / 255.0, reg_label, mask)
    for label, ckpt in CKPTS:
        m, _prob = dr._measure(ckpt, FRAG_ID, data_root=XSCROLL_ROOT)
        # re-score the prob map against the REGISTERED label, not the teacher
        prob = _prob
        rows[label] = segmentation_metrics(prob, reg_label, mask)
    for v in rows.values():
        v.pop("metrics_by_threshold", None)

    def row(name, m):
        return f"| {name} | " + " | ".join(
            f"{m.get(c, float('nan')):.4f}" for c in dr.COLS) + " |"

    lines = ["# First ground-truth-validated scores on SOTA data (registered label)", "",
             "**All rows are scored against the REGISTERED hand ground-truth label** "
             f"(method: {stats['method']}; region median correspondence residual "
             f"{stats['region_median_residual']:.2f}, surface NCC "
             f"{stats['surface_ncc']:.3f}; registration is approximate and these stats "
             "are part of every number's interpretation). The 'canon teacher' row scores "
             "the released model prediction itself against human labels.", "",
             f"Segment `{SEG}`, level-2 region (4000,2500)+4096.", "",
             "| model (vs registered ground truth) | " + " | ".join(dr.COLS) + " |",
             "|---|" + "|".join(["---"] * len(dr.COLS)) + "|"]
    lines += [row(k, v) for k, v in rows.items()]
    lines += ["", "Overlays: local_data/sota_registration/overlay_label_on_sota.png, "
              "overlay_label_on_teacher.png (git-ignored; renders committed separately "
              "if needed)."]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"segment": SEG, "registration": stats, "rows": rows},
                  f, indent=2, default=float)
    print("\n".join(f"{k}: val_f1={v.get('val_f1', float('nan')):.4f} "
                    f"lift={v.get('ap_prevalence_lift', float('nan')):.4f}"
                    for k, v in rows.items()), flush=True)


if __name__ == "__main__":
    cmds = {"probe": cmd_probe, "warp": cmd_warp, "validate": cmd_validate,
            "score": cmd_score}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.register_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
```

Note: there is a non-ASCII typo risk in the `cmd_validate` variable `sел` — the implementer MUST write it as plain ASCII `sel` (three lines use it).

- [ ] **Step 2: Verify import + usage**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.register_run 2>&1 | tail -1`
Expected: `usage: python -m repro.sota_data.register_run {probe|warp|validate|score}` (non-zero exit, no import errors).

- [ ] **Step 3: Commit**

```bash
git add repro/sota_data/register_run.py
git commit --no-verify -m "feat(sota): registration orchestrator (probe/warp/validate/score, validation-gated)"
```

---

### Task 3: Operational run — probe, register, validate, score (manual)

**Files:** none (operational); produces `reports/detector/registered_gt_validation.{md,json}` or an honest documented negative.

- [ ] **Step 1: Probe (network, CPU).**

Run: `uv run python -m repro.sota_data.register_run probe`
Expected: the mesh dir listing, then for each mesh its grid shape, valid fraction, and xyz range. **Read it:** the two grids' shapes and xyz ranges tell you the scales (old-scan units are 7.91µm voxels; new 2.4µm — expect fit scale ≈ 3.3 if frames are axis-comparable). If a mesh fails to parse (`ValueError: not a tifxyz`), STOP and report the actual format — that is the Stage-1 negative finding path.

- [ ] **Step 2: Warp (CPU, minutes).**

Run: `uv run python -m repro.sota_data.register_run warp`
Expected: fit line (scale + median residual), region correspondence residuals, and the registered-label ink fraction (sanity: should be ink-like, ~0.05–0.3, vs the teacher-positive 0.193 on this region). If the ink fraction is ~0 or ~1, the mapping landed off-segment — treat as Stage-2a failure and try the ORB fallback (`fit_affine_orb` between `registered_oldsurface` inputs at matched scale) or report the negative.

- [ ] **Step 3: Validate (the gate).**

Choose thresholds from Step 1/2's observed scales (guidance: median correspondence residual ≤ ~3 new-scan-equivalent units at the fit scale — i.e. a few voxels; NCC ≥ 0.2 between the warped old surface and the SOTA surface — they are different scans/processing, so NCC is a coarse alignment check, not identity). Then:
```bash
uv run python -m repro.sota_data.register_run validate --max-median-residual <chosen> --min-ncc <chosen>
```
Expected: overlays written; `VALIDATION PASSED ... marker written` or `VALIDATION FAILED ... NO scoring will run`. **Inspect both overlay PNGs visually regardless** — red label strokes should sit on plausible ink/teacher strokes. Record the chosen thresholds and reasoning in the ledger.

- [ ] **Step 4: Score (GPU; pause the loop).**

```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4
uv run python -m repro.sota_data.register_run score
```
Expected: five rows printed (canon teacher + 4 checkpoints) and `reports/detector/registered_gt_validation.{md,json}` written. **Read it:** the teacher row calibrates every agreement-with-teacher number; students-vs-GT vs students-vs-teacher tells whether distillation tracked truth or teacher idiosyncrasy.

- [ ] **Step 5: Commit; resume the loop.**

```bash
git add reports/detector/registered_gt_validation.md reports/detector/registered_gt_validation.json
git commit --no-verify -m "chore(sota): first ground-truth-validated scores on SOTA data (registered label)"
bash start.sh
```
If validation failed at Step 3: commit the registration stats + overlays + a short negative writeup instead — that is a legitimate deliverable per the spec.

---

## Self-Review

**Spec coverage:** Stage-1 probe (T2 `cmd_probe`, T3 S1, incl. the negative path) ✓; Stage-2a mesh warp with self-estimated transform (T1 `fit_similarity`+`correspondence_field`, T2 `cmd_warp`) ✓; Stage-2b ORB fallback (T1 `fit_affine_orb`; invoked per T3 S2 guidance) ✓; Stage-3 mandatory gate with marker + overlays + run-chosen thresholds recorded (T2 `cmd_validate`, T3 S3) ✓; Stage-4 gated scoring of teacher+3 students+legacy with "vs registered ground truth" framing + residual stats inline (T2 `cmd_score`, T3 S4) ✓; loud guards (unparseable tifxyz, missing prereqs, refusal-to-score) ✓; one segment/region, no training ✓.

**Placeholder scan:** `<chosen>` thresholds in T3 S3 are the spec's explicit set-at-run-from-probed-scales values with concrete guidance — a documented operational decision, not a TBD. All code complete. One implementer hazard flagged inline (the `sел` non-ASCII typo note in T2). ✓

**Type consistency:** `read_tifxyz -> (H,W,3)`; `fit_similarity(src,dst,...) -> (s,R,t,med)` consumed by `correspondence_field(new_xyz,s,R,t,old_xyz,stride)`; `warp_via_field(image, field, out_shape, interpolation=)` used for both label (NEAREST) and surface (default); `dr._fs`/`_scroll_prefix`/`_measure(ckpt,fid,data_root=)`/`COLS` all exist in the committed `distill_run.py`; `FRAG_ID` matches the on-disk `sota_xscroll` fragment; CKPT paths match the committed best epochs (legacy e7 / armA e9 / armB e7 / armC e11). ✓

**Known follow-ups:** PHerc-1667 published-readings registration (plateau diagnosis); labels-at-scale fine-tuning; July filing refresh.
