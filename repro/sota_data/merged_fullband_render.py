"""Chunked, resumable render of the merged-1667 text band — all 22 reading columns.

Renders y=[100,1950) x full 30097-px width of the merged full-reading geometry in
overlapping chunks (256 px overlap so per-chunk inference edges can be trimmed at
stitch time). Purpose: upgrade the ScrollGT column-baseline rows from the cols-17-19
partial extent (region AUC quantized at n=3v2) to the full n=18v17 measurement.

Design notes:
- The tifxyz dir (~750 MB) is downloaded once to local_data and chunks slice locally.
- The straightened mesh overruns the scan volume's z extent near the scroll ends; those
  points are pre-masked to the tifxyz invalid sentinel (they cannot be sampled) instead
  of tripping assert_bounds_fit. The masked fraction is logged and stored in provenance.
- Resumable: a chunk whose fragment dir already has 26 layers is skipped.
"""

import glob
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.render_surface import render_region_tifxyz

SEG = "20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4"
MESH_S3 = (
    f"vesuvius-challenge-open-data/PHerc1667/segments/{SEG}/mesh/"
    f"20260612121456-on-20251217075048-2.399um.tifxyz"
)
VOL = (
    "vesuvius-challenge-open-data/PHerc1667/volumes/"
    "20251217075048-2.399um-0.2m-78keV-masked.zarr"
)
LOCAL_MESH = "local_data/merged_w011_tifxyz"
OUT_ROOT = "local_data/rendered_1667"
Y0, H = 100, 1850
W_TOTAL = 30097
CHUNK_W = 3800
OVERLAP = 256
LEVEL = 2
Z_MAX_L0 = (9269 - 16) * 4  # scan L2 z-extent minus depth margin, in level-0 coords


def ensure_local_mesh():
    if all(os.path.exists(f"{LOCAL_MESH}/{c}.tif") for c in "xyz"):
        return
    import s3fs

    os.makedirs(LOCAL_MESH, exist_ok=True)
    fs = s3fs.S3FileSystem(anon=True)
    for c in "xyz":
        print(f"downloading {c}.tif ...", flush=True)
        fs.get(f"{MESH_S3}/{c}.tif", f"{LOCAL_MESH}/{c}.tif")


def premask_z_overrun():
    """Mask z-overrun points to the invalid sentinel once, in the local copy."""
    marker = f"{LOCAL_MESH}/.z_premasked"
    if os.path.exists(marker):
        return
    z = tifffile.imread(f"{LOCAL_MESH}/z.tif")
    bad = z >= Z_MAX_L0
    frac = float(bad.mean())
    if bad.any():
        for c in "xyz":
            p = f"{LOCAL_MESH}/{c}.tif"
            a = tifffile.imread(p)
            a[bad] = -1.0
            tifffile.imwrite(p, a)
    with open(marker, "w") as f:
        json.dump({"z_max_l0": Z_MAX_L0, "masked_frac": frac}, f)
    print(f"z-overrun premask: {frac:.5f} of grid px masked invalid", flush=True)


def chunk_specs():
    specs = []
    x = 0
    while x < W_TOTAL:
        w = min(CHUNK_W, W_TOTAL - x)
        specs.append((x, w))
        if x + w >= W_TOTAL:
            break
        x += CHUNK_W - OVERLAP
    return specs


def main():
    ensure_local_mesh()
    premask_z_overrun()
    specs = chunk_specs()
    print(f"{len(specs)} chunks: {specs}", flush=True)
    for i, (x0, w) in enumerate(specs):
        fid = f"merged_band_x{x0:05d}"
        frag = os.path.join(OUT_ROOT, fid)
        if len(glob.glob(os.path.join(frag, "layers", "*.tif"))) == 26:
            print(f"[{i + 1}/{len(specs)}] {fid}: exists, skipped", flush=True)
            continue
        print(
            f"[{i + 1}/{len(specs)}] {fid}: rendering y={Y0} x={x0} {H}x{w}", flush=True
        )
        out_seg, stats = render_region_tifxyz(
            SEG,
            LOCAL_MESH,
            VOL,
            y0=Y0,
            x0=x0,
            size=(H, w),
            level=LEVEL,
            sign=1.0,
            out_root=OUT_ROOT,
            frag_id=fid,
            extra_prov={
                "band": [Y0, H],
                "chunk_x0": x0,
                "overlap": OVERLAP,
                "z_premask_l0": Z_MAX_L0,
            },
        )
        print(
            f"    done: valid={stats['valid_frac']:.3f} "
            f"clamped={stats['clamped_frac']:.3f}",
            flush=True,
        )
    print("ALL CHUNKS DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
