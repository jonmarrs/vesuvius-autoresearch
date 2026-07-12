"""Teacher-FREE orientation check: per UV convention, warp the OLD segment's mid-depth
surface texture through the correspondence field and NCC it against the SOTA surface
mid-slice. Validation-first: two controls with known-correct orientation (enrichment-
validated), then the withheld suspect.

Signal model: where the correspondence (incl. 2D orientation) is right, papyrus fiber
texture correlates; a flipped/mirrored convention decorrelates. Report raw NCC and
high-pass NCC (Gaussian-highpass emphasizes fiber texture over illumination)."""
import json
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.gt_register import _region_in_mesh, parse_obj_vt
from repro.sota_data.register import ncc, read_tifxyz, warp_via_field

SIZE = 4096
CASES = [
    # (tag, seg, y0, x0, obj_path, mesh_path, expected)
    ("CONTROL-A", "20230702185753", 7000, 4000,
     "local_data/sota_gt_meshes/20230702185753/20230702185753_original.obj",
     "local_data/sota_gt_meshes/20230702185753/20230702185753-on-20230205180739-7.91um.tifxyz",
     "rowHv_colu (enrichment 3.13)"),
    ("CONTROL-B", "20231210121321", 4000, 2500,
     "local_data/sota_registration/heldout/20231210121321_original.obj",
     "local_data/sota_registration/heldout/20231210121321-on-20230205180739-7.91um.tifxyz",
     "rowHv_colu (heldout, teacher-free validated)"),
    ("SUSPECT", "20231005123336", 4000, 2500,
     "local_data/sota_gt_meshes/20231005123336/20231005123336_original.obj",
     "local_data/sota_gt_meshes/20231005123336/20231005123336-on-20230205180739-7.91um.tifxyz",
     "UNKNOWN (teacher uninformative)"),
]


def mid_layer(dirpath):
    tifs = sorted(f for f in os.listdir(dirpath) if f.endswith(".tif"))
    return cv2.imread(os.path.join(dirpath, tifs[len(tifs) // 2]), 0)


def depth_mean(dirpath):
    """Depth-averaged surface intensity — robust to old/new mid-slice depth mismatch."""
    tifs = sorted(f for f in os.listdir(dirpath) if f.endswith(".tif"))
    acc = None
    for t in tifs:
        im = cv2.imread(os.path.join(dirpath, t), 0).astype(np.float32)
        acc = im if acc is None else acc + im
    return acc / len(tifs)


def tile_ncc_median(a, b, m, tile=512):
    """Median of per-tile NCC over valid tiles — robust to partially-bad correspondence."""
    vals = []
    for y in range(0, a.shape[0] - tile + 1, tile):
        for x in range(0, a.shape[1] - tile + 1, tile):
            mm = m[y:y + tile, x:x + tile]
            if mm.mean() < 0.8:
                continue
            vals.append(ncc(np.where(mm, a[y:y + tile, x:x + tile], np.nan),
                            np.where(mm, b[y:y + tile, x:x + tile], np.nan)))
    return float(np.median(vals)) if vals else float("nan"), len(vals)


def highpass(img, sigma=8):
    f = img.astype(np.float32)
    return f - cv2.GaussianBlur(f, (0, 0), sigma)


results = {}
for tag, seg, y0, x0, obj_path, mesh_path, expected in CASES:
    frag = f"{seg}_y{y0}_x{x0}"
    print(f"===== {tag} {frag} (expected: {expected}) =====", flush=True)
    obj_v, obj_vt = parse_obj_vt(obj_path)
    new_xyz = read_tifxyz(mesh_path)
    region_xyz = np.asarray(_region_in_mesh(new_xyz, y0, x0, SIZE), np.float32)
    old_mid = depth_mean(f"villa/ink-detection/train_scrolls/{seg}/layers")
    new_mid = depth_mean(f"local_data/sota_distill/{frag}/layers")
    if new_mid.shape != (SIZE, SIZE):
        pad = np.zeros((SIZE, SIZE), np.float32)
        pad[: new_mid.shape[0], : new_mid.shape[1]] = new_mid
        new_mid = pad

    rh, rw = region_xyz.shape[:2]
    pts = region_xyz.reshape(-1, 3)
    valid = (np.isfinite(pts).all(1) & ~(np.abs(pts + 1) < 1e-6).all(1)
             & ~(np.abs(pts) < 1e-9).all(1))
    d, idx = cKDTree(obj_v).query(pts[valid], k=1)
    uv = obj_vt[idx]
    H, W = old_mid.shape
    cands = {
        "rowv_colu": np.stack([uv[:, 1], uv[:, 0]], axis=1),
        "rowHv_colu": np.stack([H - uv[:, 1], uv[:, 0]], axis=1),
        "rowv_colWu": np.stack([uv[:, 1], W - uv[:, 0]], axis=1),
        "rowHv_colWu": np.stack([H - uv[:, 1], W - uv[:, 0]], axis=1),
    }
    new_hp = highpass(new_mid)
    row = {"expected": expected, "residual": float(np.median(d)), "candidates": {}}
    for name, rc in cands.items():
        field = np.full((rh, rw, 2), np.nan, np.float32)
        field.reshape(-1, 2)[valid] = rc
        warped = warp_via_field(old_mid, field, (SIZE, SIZE),
                                interpolation=cv2.INTER_LINEAR).astype(np.float32)
        m = warped > 0  # warp fills invalid with 0
        raw = ncc(np.where(m, warped, np.nan), np.where(m, new_mid, np.nan))
        hp = ncc(np.where(m, highpass(warped), np.nan), np.where(m, new_hp, np.nan))
        tmed, ntiles = tile_ncc_median(warped, new_mid, m)
        row["candidates"][name] = {"ncc_raw": raw, "ncc_highpass": hp,
                                   "tile_ncc_median": tmed, "n_tiles": ntiles,
                                   "valid_frac": float(m.mean())}
        print(f"  {name:13s} ncc_raw={raw:7.4f}  ncc_hp={hp:7.4f}  "
              f"tile_med={tmed:7.4f} ({ntiles} tiles)  valid={m.mean():.3f}",
              flush=True)
    results[f"{tag}_{frag}"] = row

with open("reports/detector/surface_ncc_probe.json", "w") as f:
    json.dump(results, f, indent=2)
print("wrote reports/detector/surface_ncc_probe.json", flush=True)
