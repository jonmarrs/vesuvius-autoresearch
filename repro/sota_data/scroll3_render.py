"""Render the two PHerc0332 (Scroll 3) segments from original.obj + the masked volume, run
arm C, and write an honestly-captioned first look.

Scroll 3 is UNREAD: no ground truth, and (unlike Scroll 1) no released surface volume to
calibrate the obj coordinate scale against. So the level-div is INFERRED teacher-free: we
render at candidate scales and keep the one whose surface layer shows the most papyrus-like
structure (high-pass std over valid pixels) — a coherence proxy, not a validation. This is a
qualitative look at the renderer + arm C, NOT a reading claim.
"""
import glob
import json
import os
import sys
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.render_surface import render_region

SEGS = ["20240711124827-20240618142020", "20240828190516-20240716140050"]
BASE = "vesuvius-challenge-open-data/PHerc0332"
VOL = f"{BASE}/volumes/20251211183505-2.399um-0.2m-78keV-masked.zarr"
ARM_C = "models/detector_xscroll_c/detector_epoch=11.ckpt"
OUT_ROOT = "local_data/rendered_scroll3"
SIGN = 1.0
SIZE = 2048
LEVEL = 2
CANDIDATE_DIVS = [4.0, 1.0, 2.0]   # obj-as-L0 (/4 for L2), obj-as-L2, obj-as-L1


def _fetch_obj(seg):
    import s3fs
    fs = s3fs.S3FileSystem(anon=True)
    dst = f"local_data/scroll3_meshes/{seg}_original.obj"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        fs.get(f"{BASE}/segments/{seg}/mesh/intermediate/{seg}_original.obj", dst)
    return dst


def _structure(layer_path, mask):
    """High-pass std over valid pixels: papyrus surface has fiber texture (high); a
    wrong-scale / empty render is flat (low)."""
    img = cv2.imread(layer_path, 0).astype(np.float32)
    hp = img - cv2.GaussianBlur(img, (0, 0), 6)
    m = (mask > 127) & (img > 0)
    return float(hp[m].std()) if m.any() else 0.0


def infer_no_label(frag_root, frag_id):
    """Run arm C on a label-free fragment: write a transient all-zero label ONLY to satisfy
    the loader, run infer, then delete it (never persisted/shipped)."""
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.infer import infer
    seg_dir = os.path.join(frag_root, frag_id)
    dummy = os.path.join(seg_dir, f"{frag_id}_inklabels.png")
    lay0 = sorted(glob.glob(os.path.join(seg_dir, "layers", "*.tif")))[0]
    h, w = cv2.imread(lay0, 0).shape
    cv2.imwrite(dummy, np.zeros((h, w), np.uint8))
    try:
        prob = infer(DetectorConfig(data_root=frag_root), ARM_C, frag_id)
    finally:
        os.remove(dummy)  # honesty invariant: no label persists
    return prob


def main():
    os.makedirs("reports/detector", exist_ok=True)
    rows: list[dict[str, Any]] = []
    for seg in SEGS:
        obj = _fetch_obj(seg)
        # infer the coordinate scale teacher-free
        cand = {}
        for div in CANDIDATE_DIVS:
            fid = f"scroll3_{seg}_div{int(div)}"
            try:
                out_seg, stats = render_region(seg, obj, VOL, 0, 0, SIZE, level=LEVEL,
                                               sign=SIGN, out_root=OUT_ROOT, frag_id=fid,
                                               obj_level_div=div,
                                               extra_prov={"scroll": "PHerc0332",
                                                           "no_ground_truth": True,
                                                           "obj_level_div": div})
                mid = sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13]
                s = _structure(mid, cv2.imread(f"{out_seg}/{fid}_mask.png", 0))
                cand[div] = (s, out_seg, stats)
                print(f"{seg} div={div}: structure={s:.3f} valid={stats['valid_frac']:.3f}",
                      flush=True)
            except Exception as e:
                print(f"{seg} div={div}: FAILED {type(e).__name__}: {e}", flush=True)
        if not cand:
            rows.append({"segment": seg, "error": "all candidate scales failed"})
            continue
        best_div = max(cand, key=lambda d: cand[d][0])
        _, out_seg, stats = cand[best_div]
        fid = f"scroll3_{seg}_div{int(best_div)}"
        prob = infer_no_label(OUT_ROOT, fid)
        surf = cv2.imread(sorted(glob.glob(f"{out_seg}/layers/*.tif"))[13], 0)
        cv2.imwrite(f"reports/detector/scroll3_{seg}_surface.png",
                    cv2.resize(surf, (surf.shape[1] // 2, surf.shape[0] // 2)))
        pv = (np.clip(prob, 0, 1) * 255).astype(np.uint8)
        cv2.imwrite(f"reports/detector/scroll3_{seg}_armC_ink.png",
                    cv2.resize(pv, (pv.shape[1] // 2, pv.shape[0] // 2)))
        rows.append({"segment": seg, "chosen_obj_level_div": best_div,
                     "structure_by_div": {d: cand[d][0] for d in cand},
                     "valid_frac": stats["valid_frac"], "clamped_frac": stats["clamped_frac"],
                     "pred_positive_rate": float((prob > 0.5).mean())})
        print(f"{seg}: chose div={best_div} pred+={rows[-1]['pred_positive_rate']:.4f}",
              flush=True)

    with open("reports/detector/scroll3_first_look.json", "w") as f:
        json.dump({"sign": SIGN, "level": LEVEL, "rows": rows}, f, indent=2, default=float)
    with open("reports/detector/scroll3_first_look.md", "w") as f:
        f.write("# Scroll 3 (PHerc0332) first look — rendered surface + arm C\n\n")
        f.write("**No ground truth exists on Scroll 3** (it is unread — that is why First "
                "Letters is open), and unlike Scroll 1 there is no released surface volume "
                "to calibrate the obj coordinate scale. The renderer is placement-validated "
                "on Scroll 1 (NCC ~0.59, reports/detector/render_validation.md); here the "
                "obj-level-div was INFERRED teacher-free by surface-texture structure (a "
                "coherence proxy, NOT a validation). This is a qualitative look at (a) our "
                "renderer on mesh-only segments and (b) what arm C — a cross-scroll model "
                "with weak unseen-scroll transfer (lift ~2.1) — predicts. **NOT a reading "
                "claim**; any legibility is by eye and must be independently corroborated "
                "before any prize consideration.\n\n")
        for r in rows:
            f.write(f"## {r['segment']}\n\n")
            if "error" in r:
                f.write(f"- render failed: {r['error']}\n\n")
                continue
            f.write(f"- inferred obj_level_div: {r['chosen_obj_level_div']} "
                    f"(structure by div: {r['structure_by_div']})\n")
            f.write(f"- render valid_frac {r['valid_frac']:.3f}, clamped {r['clamped_frac']:.3f}\n")
            f.write(f"- arm C predicted-positive rate: {r['pred_positive_rate']:.4f}\n")
            f.write(f"- ![surface](scroll3_{r['segment']}_surface.png) "
                    f"![arm C](scroll3_{r['segment']}_armC_ink.png)\n\n")
    print("wrote reports/detector/scroll3_first_look.md", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
