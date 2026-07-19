"""Depth-direction (sign) validation of the renderer vs the released w011 stack.

The center-layer NCC gate (validate_render_1667.py, PASS 0.78) is sign-invariant by
construction. This probe measures what it cannot: whether our 26-layer stack traverses
the papyrus sheet in the SAME depth direction as the released surface volumes. Method:
render a w011 region at sign=+1, NCC every rendered layer k against every released
depth slice d (26x109 matrix), and examine the best-match mapping k->d. Same direction
=> monotonically increasing; flipped => decreasing. The slope also measures the depth
spacing ratio (our k step is 1 level-2 voxel ~ 9.6 um; the released stack's spacing is
its own convention).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.register import ncc
from repro.sota_data.render_surface import (
    pointmap_from_tifxyz,
    read_tifxyz,
    sample_layers,
    surface_normals,
    zarr_fetch,
)

SEG = "20260108140509-w011_20260108140509268_flatboi"
SCAN = "20251217075048"
BASE = "vesuvius-challenge-open-data/PHerc1667"
TIFXYZ = f"{BASE}/segments/{SEG}/mesh/20260108140509-on-{SCAN}-2.399um.tifxyz"
RAW_VOL = f"{BASE}/volumes/{SCAN}-2.399um-0.2m-78keV-masked.zarr"
SURF_VOL = (
    f"{BASE}/segments/{SEG}/surface-volumes/2.399um-0.22m-78keV-volume-{SCAN}.zarr"
)
LEVEL = 2
Y0, X0, SIZE = 730, 112, 512  # interior high-validity crop of the (1975, 736) grid


def main():
    import cv2
    import s3fs
    import zarr

    fs = s3fs.S3FileSystem(anon=True)

    xyz = read_tifxyz(TIFXYZ)[Y0 : Y0 + SIZE, X0 : X0 + SIZE]
    pm, valid = pointmap_from_tifxyz(xyz, level_div=2**LEVEL)
    print(f"region grid {pm.shape[:2]} valid {valid.mean():.3f}", flush=True)
    fetch, _ = zarr_fetch(RAW_VOL, LEVEL)
    normals = surface_normals(pm, valid, sign=1.0)
    layers, stats = sample_layers(pm, valid, normals, fetch, tile=32)
    print(f"rendered 26 layers, clamped {stats['clamped_frac']:.4f}", flush=True)

    sg = zarr.open(zarr.storage.FSStore(SURF_VOL, fs=fs), mode="r")
    surf = sg["4"]  # L4: (109, 2469, 920) ~= grid x 1.25
    ry0, rx0 = int(Y0 * 1.25), int(X0 * 1.25)
    rh, rw = int(SIZE * 1.25), int(SIZE * 1.25)
    ref = np.asarray(surf[:, ry0 : ry0 + rh, rx0 : rx0 + rw], np.float32)
    print(f"released L4 region {ref.shape}", flush=True)

    m = valid
    mat = np.zeros((26, ref.shape[0]), np.float32)
    for d in range(ref.shape[0]):
        r = cv2.resize(ref[d], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        rm = np.where(m, r, np.nan)
        for k in range(26):
            mat[k, d] = ncc(np.where(m, layers[k], np.nan), rm)

    best_d = mat.argmax(axis=1)
    best_c = mat.max(axis=1)
    # direction: slope of best_d over the well-matched layers only
    good = best_c > 0.5
    ks = np.arange(26)[good]
    ds = best_d[good]
    slope = float(np.polyfit(ks, ds, 1)[0]) if good.sum() >= 5 else float("nan")
    spearman = (
        float(np.corrcoef(np.argsort(np.argsort(ks)), np.argsort(np.argsort(ds)))[0, 1])
        if good.sum() >= 5
        else float("nan")
    )
    verdict = (
        "SAME direction (sign=+1 matches the released convention)"
        if slope > 0
        else "FLIPPED (sign=+1 traverses opposite to the released stack)"
    )

    print("k -> best released d (ncc):")
    for k in range(26):
        mark = "*" if good[k] else " "
        print(f"  {k:2d} -> {best_d[k]:3d}  ({best_c[k]:.3f}){mark}", flush=True)
    print(
        f"\nwell-matched layers: {int(good.sum())}/26; slope {slope:.2f} released-slices "
        f"per our-layer; rank corr {spearman:.3f}"
    )
    print(f"VERDICT: {verdict}")

    os.makedirs("reports/detector", exist_ok=True)
    with open("reports/detector/render_validation_1667_depth.json", "w") as f:
        json.dump(
            {
                "seg": SEG,
                "region": [Y0, X0, SIZE],
                "n_well_matched": int(good.sum()),
                "best_d": best_d.tolist(),
                "best_ncc": [float(c) for c in best_c],
                "slope": slope,
                "rank_corr": spearman,
                "verdict": verdict,
            },
            f,
            indent=2,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
