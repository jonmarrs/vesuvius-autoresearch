"""Incremental inference + stitching + scoring for the full-band merged-1667 render.

The band (y=[100,1950) x 30097) is rendered in overlapping chunks by
merged_fullband_render.py. This module:
  1. runs arm C + legacy inference on each COMPLETED chunk fragment (incremental —
     safe to invoke while the render is still going; per-chunk maps are cached),
  2. once all chunks are inferred, stitches them into one (1850, 30097) map with
     seams in the middle of each overlap (per-chunk inference edge artifacts are
     trimmed away),
  3. scores the stitched maps via `scrollgt score-columns --origin 100 0` — the full
     n=18v17 column-baseline measurement.

Run `--incremental` from a poll loop during the render; run without flags at the end.
"""

import glob
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.merged_fullband_render import (
    CHUNK_W,
    OUT_ROOT,
    OVERLAP,
    W_TOTAL,
    Y0,
    chunk_specs,
)

SCROLLGT = os.path.abspath("../scrollgt")
TARGET = os.path.join(SCROLLGT, "data/pherc1667_merged_columns")
MODELS = {
    "arm_C": "models/detector_xscroll_c/detector_epoch=11.ckpt",
    "legacy": "models/detector/detector_epoch=7.ckpt",
}
CACHE = "local_data/fullband_preds"
OUT = "reports/detector"


def chunk_trims(specs, overlap):
    """Per-chunk (x0, left_trim, right_trim) placing seams mid-overlap."""
    half = overlap // 2
    out = []
    for i, (x0, w) in enumerate(specs):
        lt = half if i > 0 else 0
        rt = half if i < len(specs) - 1 else 0
        out.append((x0, lt, rt))
    return out


def stitch(preds, specs, overlap, total_w):
    """Assemble per-chunk maps {x0: (H,w) array} into one (H, total_w) map."""
    missing = [x0 for x0, _ in specs if x0 not in preds]
    if missing:
        raise ValueError(f"missing chunks at x0={missing}")
    H = next(iter(preds.values())).shape[0]
    for x0, w in specs:
        if preds[x0].shape != (H, w):
            raise ValueError(
                f"chunk x0={x0} has shape {preds[x0].shape}, expected {(H, w)}"
            )
    full = np.empty((H, total_w), np.float32)
    full[:] = np.nan
    for (x0, w), (_, lt, rt) in zip(specs, chunk_trims(specs, overlap), strict=False):
        full[:, x0 + lt : x0 + w - rt] = preds[x0][:, lt : w - rt]
    if not np.isfinite(full).all():
        raise ValueError("stitched map has uncovered pixels")
    return full


def _chunk_done(fid):
    return len(glob.glob(os.path.join(OUT_ROOT, fid, "layers", "*.tif"))) == 26


def infer_available():
    """Run inference for every completed, not-yet-inferred chunk. Returns
    (n_done, n_total) per model."""
    os.makedirs(CACHE, exist_ok=True)
    specs = chunk_specs()
    status = {}
    for name, ckpt in MODELS.items():
        done = 0
        for x0, _w in specs:
            fid = f"merged_band_x{x0:05d}"
            cache = os.path.join(CACHE, f"{name}_x{x0:05d}.npy")
            if os.path.exists(cache):
                done += 1
                continue
            if not _chunk_done(fid):
                continue
            import repro.sota_data.scroll3_render as s3r

            s3r.ARM_C = ckpt
            from repro.sota_data.scroll3_render import infer_no_label

            print(f"inferring {name} on {fid} ...", flush=True)
            prob = infer_no_label(OUT_ROOT, fid).astype(np.float32)
            np.save(cache, prob)
            done += 1
        status[name] = (done, len(specs))
        print(f"{name}: {done}/{len(specs)} chunks inferred", flush=True)
    return status


def stitch_and_score():
    specs = chunk_specs()
    results = {}
    for name in MODELS:
        preds = {}
        for x0, _w in specs:
            cache = os.path.join(CACHE, f"{name}_x{x0:05d}.npy")
            preds[x0] = np.load(cache)
        full = stitch(preds, specs, OVERLAP, W_TOTAL)
        pred_path = os.path.join(CACHE, f"{name}_fullband.npy")
        np.save(pred_path, full)
        import cv2

        cv2.imwrite(
            os.path.join(OUT, f"columns_fullband_{name}_pred.png"),
            (np.clip(full, 0, 1) * 255).astype(np.uint8)[::6, ::6],
        )
        card_path = os.path.join(OUT, f"columns_fullband_{name}.json")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "scrollgt.cli",
                "score-columns",
                pred_path,
                TARGET,
                "--origin",
                str(Y0),
                "0",
                "--json-out",
                card_path,
            ],
            check=True,
            env={**os.environ, "PYTHONPATH": os.path.join(SCROLLGT, "src")},
        )
        results[name] = json.load(open(card_path))["metrics"]
    print(json.dumps(results, indent=1, default=float))
    return results


def main():
    status = infer_available()
    if "--incremental" in sys.argv:
        return 0
    if any(done < total for done, total in status.values()):
        raise SystemExit(
            "not all chunks rendered/inferred yet — "
            "use --incremental while the render runs"
        )
    stitch_and_score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
