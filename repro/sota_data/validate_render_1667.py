"""Renderer acceptance gate #2 (clean triple, PHerc1667 w011) — SECOND SCROLL.

Same design as validate_render.py (Scroll 1), on a different scroll: geometry, volume,
and reference share ONE frame (scan 20251217075048, 2.399um):
  - geometry: `mesh/20260108140509-on-20251217075048-2.399um.tifxyz` (level-0 voxel
    coords, scale 0.05 -> grid (1975,736) == surface-volume L0 (39500,14720) / 20),
  - volume:   `PHerc1667/volumes/20251217075048-2.399um-0.2m-78keV-masked.zarr`,
  - reference: the released `surface-volumes/2.399um-...-20251217075048.zarr`.
Only our sampler is unknown. PRE-REGISTERED GATE (stated before running, same bar as
Scroll 1): center-layer NCC >= 0.60 vs the released surface volume. The Scroll-1 run
scored 0.5936 (FAIL against the gate, placement-correct) — this run tests whether the
same conventions transfer to a second scroll, and is reported however it lands.

Sign: only sign=+1 is rendered — the compared layer is the depth CENTER (k=0), which the
Scroll-1 harness measured to be sign-invariant (both signs tied at 0.5936).
"""

import json
import os
import sys

import cv2
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
GATE = 0.60


def main():
    import s3fs
    import zarr

    fs = s3fs.S3FileSystem(anon=True)

    xyz = read_tifxyz(TIFXYZ)
    pm, valid = pointmap_from_tifxyz(xyz, level_div=2**LEVEL)
    print(f"grid {pm.shape[:2]} valid {valid.mean():.3f}", flush=True)

    fetch, vol_shape = zarr_fetch(RAW_VOL, LEVEL)
    print(f"raw vol L{LEVEL} shape {vol_shape}", flush=True)

    sg = zarr.open(zarr.storage.FSStore(SURF_VOL, fs=fs), mode="r")
    lv = min(
        (k for k in sg.keys()),
        key=lambda k: abs(sg[k].shape[1] - pm.shape[0])
        + abs(sg[k].shape[2] - pm.shape[1]),
    )
    surf = sg[lv]
    dc = surf.shape[0] // 2
    refs = []
    for dz in range(-4, 5, 2):
        sl = np.asarray(surf[dc + dz], np.float32)
        refs.append(
            cv2.resize(sl, (pm.shape[1], pm.shape[0]), interpolation=cv2.INTER_AREA)
        )
    print(
        f"reference surface-vol level {lv} shape {surf.shape}, "
        f"{len(refs)} depth slices around {dc}",
        flush=True,
    )

    normals = surface_normals(pm, valid, sign=1.0)
    layers, stats = sample_layers(pm, valid, normals, fetch, tile=32)
    rendered = layers[layers.shape[0] // 2]
    m = valid
    best_c = max(
        ncc(np.where(m, rendered, np.nan), np.where(m, r, np.nan)) for r in refs
    )
    print(
        f"best center-layer NCC={best_c:.4f} valid={stats['valid_frac']:.3f} "
        f"clamped={stats['clamped_frac']:.3f}",
        flush=True,
    )

    verdict = "PASS" if best_c >= GATE else "FAIL"
    os.makedirs("reports/detector", exist_ok=True)
    with open("reports/detector/render_validation_1667.json", "w") as f:
        json.dump(
            {
                "seg": SEG,
                "scan": SCAN,
                "level": LEVEL,
                "surf_level": lv,
                "ncc": float(best_c),
                **stats,
                "verdict": verdict,
                "gate": f"center-layer NCC >= {GATE} vs released surface volume "
                "(same frame; pre-registered before the run)",
            },
            f,
            indent=2,
            default=float,
        )
    print(f"VERDICT: {verdict} (NCC={best_c:.4f}, gate {GATE})", flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
