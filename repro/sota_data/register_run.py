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
            # a .tifxyz is a DIRECTORY (meta.json + x/y/z.tif planes) -- fetch recursively
            fs.get(f"{pref}/{name}", dst, recursive=True)
        meta = os.path.join(dst, "meta.json")
        if os.path.exists(meta):
            with open(meta) as f:
                print(f"{name} meta.json: {f.read().strip()}", flush=True)
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
    sel = reg_mid > 0
    score_ncc = ncc(np.where(sel, frag_mid, np.nan), np.where(sel, reg_mid, np.nan))
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
