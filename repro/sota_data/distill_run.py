"""Phase-2 distillation orchestration (operational): fetch canon teacher predictions,
extract SOTA surface regions, prep detector-format fragments, baseline the current
detector's agreement-with-teacher on a held-out region, train the student, and measure.
All metrics are AGREEMENT WITH TEACHER (a model, not ground truth)."""
import glob
import json
import os
import sys

import cv2
import numpy as np
import s3fs
import tifffile
import zarr
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for

BUCKET = "vesuvius-challenge-open-data"
LEVEL = "2"
SIZE = 4096
TRAIN_SEGS = {
    "20230702185753": [(4000, 2500), (7000, 4000)],
    "20231005123336": [(4000, 2500), (7000, 4000)],
}
HELD_SEG = "20231210121321"
HELD_REGION = (4000, 2500)
DATA_ROOT = "local_data/sota_distill"
TEACHER_DIR = "local_data/sota_distill_teachers"
BASELINE_CKPT = "models/detector/detector_epoch=7.ckpt"
MODEL_DIR = "models/detector_sota_distill"
REPORT_MD = "reports/detector/sota_distill_measurement.md"
REPORT_JSON = "reports/detector/sota_distill_measurement.json"
BASELINE_JSON = "reports/detector/sota_distill_baseline.json"
COLS = ["val_f1", "f1_at_0.5", "average_precision", "ap_prevalence_lift",
        "precision", "recall", "positive_rate", "roc_auc"]


def _fs():
    return s3fs.S3FileSystem(anon=True)


def frag_id(seg, y0, x0):
    return f"{seg}_y{y0}_x{x0}"


def fetch_teacher(seg):
    os.makedirs(TEACHER_DIR, exist_ok=True)
    dst = os.path.join(TEACHER_DIR, f"{seg}.tif")
    if os.path.exists(dst):
        return dst
    fs = _fs()
    pref = f"{BUCKET}/PHercParis4/segments/{seg}/ink-detection"
    tifs = sorted(p for p in fs.ls(pref, detail=False) if p.endswith(".tif"))
    if not tifs:
        raise ValueError(f"{seg}: no teacher tif under {pref}")
    fs.get(tifs[0], dst)
    return dst


def extract_region(seg, y0, x0, size=SIZE):
    fs = _fs()
    pref = f"{BUCKET}/PHercParis4/segments/{seg}/surface-volumes"
    zarrs = sorted(p for p in fs.ls(pref, detail=False) if p.endswith(".zarr"))
    if not zarrs:
        raise ValueError(f"{seg}: no .zarr under {pref}")
    g = zarr.open(zarr.storage.FSStore(zarrs[0], fs=fs), mode="r")  # 2.4um sorts first
    arr = g[LEVEL]
    d, h, w = arr.shape
    y1, x1 = min(y0 + size, h), min(x0 + size, w)
    lo = max(0, d // 2 - 13)
    region = np.asarray(arr[lo:lo + 26, y0:y1, x0:x1])
    return region, (h, w), (y0, x0, y1, x1)


def cmd_prep():
    targets = list(TRAIN_SEGS.items()) + [(HELD_SEG, [HELD_REGION])]
    for seg, regions in targets:
        tpath = fetch_teacher(seg)
        teacher_full = tifffile.imread(tpath)
        print(f"{seg}: teacher shape={teacher_full.shape} dtype={teacher_full.dtype} "
              f"range=[{teacher_full.min()},{teacher_full.max()}]", flush=True)
        for (y0, x0) in regions:
            region, level_shape, box = extract_region(seg, y0, x0)
            t_region = teacher_region_for(teacher_full, level_shape, box)
            fid = frag_id(seg, y0, x0)
            out = prep_distill_fragment(region, t_region, DATA_ROOT, fid)
            lab = cv2.imread(os.path.join(out, f"{fid}_inklabels.png"), 0)
            print(f"prepped {out} teacher-positive={float((lab > 0).mean()):.3f}", flush=True)


def _measure(ckpt, fid):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask
    from vesuvius_autoresearch.detector.infer import infer
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics
    cfg = DetectorConfig(data_root=DATA_ROOT)
    prob = infer(cfg, ckpt, fid)
    _, label, mask = read_image_mask(cfg, fid)
    h, w = label.shape
    m = segmentation_metrics(prob[:h, :w], (label > 0.5).astype(np.uint8),
                             mask[:h, :w].astype(bool))
    m.pop("metrics_by_threshold", None)
    return m, prob[:h, :w]


def cmd_baseline():
    fid = frag_id(HELD_SEG, *HELD_REGION)
    m, _ = _measure(BASELINE_CKPT, fid)
    os.makedirs("reports/detector", exist_ok=True)
    with open(BASELINE_JSON, "w") as f:
        json.dump({"checkpoint": BASELINE_CKPT, "fragment": fid, "vs_teacher": m},
                  f, indent=2, default=float)
    print(f"BASELINE vs teacher on {fid}: val_f1={m.get('val_f1', float('nan')):.4f} "
          f"lift={m.get('ap_prevalence_lift', float('nan')):.4f}", flush=True)


def cmd_train():
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.train import train
    train_ids = [frag_id(s, y, x) for s, rs in TRAIN_SEGS.items() for (y, x) in rs]
    cfg = DetectorConfig(data_root=DATA_ROOT, model_dir=MODEL_DIR,
                         train_fragment_ids=train_ids,
                         valid_fragment_id=frag_id(HELD_SEG, *HELD_REGION))
    print(train(cfg))


def cmd_measure():
    fid = frag_id(HELD_SEG, *HELD_REGION)
    with open(BASELINE_JSON) as f:
        baseline = json.load(f)["vs_teacher"]
    ckpts = sorted(glob.glob(os.path.join(MODEL_DIR, "detector_epoch=*.ckpt")),
                   key=lambda p: int(p.split("epoch=")[1].split(".")[0]))
    best = None
    for ck in ckpts:
        m, prob = _measure(ck, fid)
        print(f"{os.path.basename(ck)}: val_f1={m.get('val_f1', float('nan')):.4f}",
              flush=True)
        if best is None or m.get("val_f1", 0) > best[0].get("val_f1", 0):
            best = (m, ck, prob)
    m, ck, prob = best
    Image.fromarray((np.clip(prob, 0, 1) * 255).astype(np.uint8)).resize(
        (prob.shape[1] // 4, prob.shape[0] // 4)).save(
        "reports/detector/sota_distill_ours.png")
    lab = cv2.imread(os.path.join(DATA_ROOT, fid, f"{fid}_inklabels.png"), 0)
    Image.fromarray(lab).resize((lab.shape[1] // 4, lab.shape[0] // 4)).save(
        "reports/detector/sota_distill_teacher.png")
    lines = ["# Distilled detector vs teacher (held-out SOTA segment region)", "",
             "**All metrics are agreement-with-teacher (the released canon prediction), "
             "NOT ground-truth accuracy.**", "",
             f"Held-out: `{fid}`  |  best student ckpt: `{os.path.basename(ck)}`", "",
             "| model | " + " | ".join(COLS) + " |",
             "|---|" + "|".join(["---"] * len(COLS)) + "|",
             "| current detector (baseline) | "
             + " | ".join(f"{baseline.get(c, float('nan')):.4f}" for c in COLS) + " |",
             "| distilled student | "
             + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in COLS) + " |",
             "", "Renders: [ours](sota_distill_ours.png) vs "
             "[teacher](sota_distill_teacher.png)."]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"fragment": fid, "best_checkpoint": os.path.basename(ck),
                   "baseline_vs_teacher": baseline, "distilled_vs_teacher": m},
                  f, indent=2, default=float)
    print(f"DISTILLED vs teacher: val_f1={m.get('val_f1', float('nan')):.4f} "
          f"(baseline {baseline.get('val_f1', float('nan')):.4f})", flush=True)


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "baseline": cmd_baseline, "train": cmd_train,
            "measure": cmd_measure}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.distill_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
