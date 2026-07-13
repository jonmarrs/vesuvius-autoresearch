"""Renderer acceptance gate (clean triple, Scroll 1 20230702185753).

Geometry, volume, and reference all share ONE frame (20260411134726, 2.4um):
  - geometry: segment mesh `{seg}-on-20260411134726-2.4um.tifxyz` (level-0 voxel coords),
  - volume:   `PHercParis4/volumes/20260411134726-2.400um-...masked.zarr` (raw scan),
  - reference: the released `surface-volumes/2.4um-...-20260411134726.zarr` (the core
    team's surface volume from the SAME scan + SAME flattening).
So the ONLY unknown is our sampling code: render from the tifxyz geometry, then NCC the
depth-center layer against the released surface volume (same (row,col) parameterization,
pixel-aligned — no shift needed). This validates the sampler + coordinate conventions
(x,y,z->z,y,x, level-0->level-2) against ground truth before the obj path is trusted on
Scroll 3.
"""
import io
import json
import os
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.register import ncc
from repro.sota_data.render_surface import (
    pointmap_from_tifxyz,
    sample_layers,
    surface_normals,
    zarr_fetch,
)

SEG = "20230702185753"
SCAN = "20260411134726"
BASE = f"vesuvius-challenge-open-data/PHercParis4"
TIFXYZ = f"{BASE}/segments/{SEG}/mesh/{SEG}-on-{SCAN}-2.4um.tifxyz"
RAW_VOL = f"{BASE}/volumes/{SCAN}-2.400um-0.2m-78keV-masked.zarr"
SURF_VOL = f"{BASE}/segments/{SEG}/surface-volumes/2.4um-0.22m-78keV-volume-{SCAN}.zarr"
LEVEL = 2
GRID_DOWN = 4     # render at tifxyz-grid / 4 to keep the Delaunay-free path fast (~630x455)


def _read_tifxyz_s3(fs, path):
    planes = [tifffile.imread(io.BytesIO(fs.cat(f"{path}/{c}.tif"))) for c in "xyz"]
    return np.stack(planes, axis=-1).astype(np.float32)


def main():
    import s3fs
    import zarr
    fs = s3fs.S3FileSystem(anon=True)

    xyz = _read_tifxyz_s3(fs, TIFXYZ)
    xyz = xyz[::GRID_DOWN, ::GRID_DOWN]          # coords are frame-absolute; subsampling ok
    pm, valid = pointmap_from_tifxyz(xyz, level_div=2 ** LEVEL)
    print(f"grid {pm.shape[:2]} valid {valid.mean():.3f}", flush=True)

    fetch, vol_shape = zarr_fetch(RAW_VOL, LEVEL)
    print(f"raw vol L{LEVEL} shape {vol_shape}", flush=True)

    # reference: released surface volume, pick the pyramid level whose (H,W) matches our grid
    sg = zarr.open(zarr.storage.FSStore(SURF_VOL, fs=fs), mode="r")
    lv = min((k for k in sg.keys()),
             key=lambda k: abs(sg[k].shape[1] - xyz.shape[0]) + abs(sg[k].shape[2] - xyz.shape[1]))
    surf = sg[lv]
    mid = surf[surf.shape[0] // 2]
    ref = cv2.resize(np.asarray(mid, np.float32), (pm.shape[1], pm.shape[0]),
                     interpolation=cv2.INTER_AREA)
    print(f"reference surface-vol level {lv} shape {surf.shape} -> resized {ref.shape}",
          flush=True)

    results = {}
    for sign in (1.0, -1.0):
        normals = surface_normals(pm, valid, sign=sign)
        layers, stats = sample_layers(pm, valid, normals, fetch, tile=32)
        rendered = layers[layers.shape[0] // 2]
        m = valid
        c = ncc(np.where(m, rendered, np.nan), np.where(m, ref, np.nan))
        results[f"sign{int(sign)}"] = {"ncc": float(c), **stats}
        print(f"sign={sign:+.0f}: center-layer NCC={c:.4f} "
              f"valid={stats['valid_frac']:.3f} clamped={stats['clamped_frac']:.3f}",
              flush=True)

    best = max(results.values(), key=lambda r: r["ncc"])
    best_sign = max(results, key=lambda k: results[k]["ncc"])
    verdict = "PASS" if best["ncc"] >= 0.60 else "FAIL"
    os.makedirs("reports/detector", exist_ok=True)
    with open("reports/detector/render_validation.json", "w") as f:
        json.dump({"seg": SEG, "scan": SCAN, "level": LEVEL, "grid_down": GRID_DOWN,
                   "results": results, "best_sign": best_sign, "verdict": verdict,
                   "gate": "center-layer NCC >= 0.60 vs released surface volume (same frame)"},
                  f, indent=2, default=float)
    with open("reports/detector/render_validation.md", "w") as f:
        f.write(f"# Renderer validation (Scroll 1 {SEG}, scan {SCAN}) — {verdict}\n\n")
        f.write("Clean triple: tifxyz geometry + raw volume + released surface volume all "
                "in one frame; only our sampler is unknown. Center-depth layer vs the "
                "released surface volume, same (row,col) parameterization.\n\n")
        for k, r in results.items():
            f.write(f"- {k}: NCC {r['ncc']:.4f} valid {r['valid_frac']:.3f} "
                    f"clamped {r['clamped_frac']:.3f}\n")
        f.write(f"\nBest sign: {best_sign}. Gate: NCC >= 0.60.\n")
    print(f"VERDICT: {verdict} (best {best_sign} NCC={best['ncc']:.4f})", flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
