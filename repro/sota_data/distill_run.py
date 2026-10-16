"""Phase-2 distillation orchestration (operational): fetch canon teacher predictions,
extract SOTA surface regions, prep detector-format fragments, baseline the current
detector's agreement-with-teacher on a held-out region, train the student, and measure.
All metrics are AGREEMENT WITH TEACHER (a model, not ground truth)."""
import glob
import json
import os
import re
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
SCROLLS = {
    "scroll1": "PHercParis4",
    "pherc0139": "PHerc0139",
    "pherc1667": "PHerc1667",
    "pherc0172": "PHerc0172",
}


def _scroll_prefix(scroll_key, seg, sub):
    if scroll_key not in SCROLLS:
        raise ValueError(f"unknown scroll key '{scroll_key}'; known: {sorted(SCROLLS)}")
    return f"{BUCKET}/{SCROLLS[scroll_key]}/segments/{seg}/{sub}"


def xfrag_id(scroll_key, seg, y0, x0):
    return f"{scroll_key}_{seg}_y{y0}_x{x0}"


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


def _source_record(tpath):
    return tpath + ".source.json"


def fetch_teacher(seg, scroll_key="scroll1"):
    os.makedirs(TEACHER_DIR, exist_ok=True)
    dst = os.path.join(TEACHER_DIR, f"{scroll_key}_{seg}.tif")
    legacy = os.path.join(TEACHER_DIR, f"{seg}.tif")  # Phase-2 cache name (scroll1 only)
    if os.path.exists(dst):
        return dst
    if scroll_key == "scroll1" and os.path.exists(legacy):
        return legacy
    fs = _fs()
    pref = _scroll_prefix(scroll_key, seg, "ink-detection")
    tifs = sorted(p for p in fs.ls(pref, detail=False) if p.endswith(".tif"))
    if not tifs:
        raise ValueError(f"{seg}: no teacher tif under {pref}")
    fs.get(tifs[0], dst)
    # Which released prediction is the teacher: the first of the candidates, by name.
    with open(_source_record(dst), "w") as f:
        json.dump({"source": tifs[0], "candidates": tifs}, f, indent=2)
    return dst


def teacher_provenance(tpath, teacher):
    """What a report says about one teacher: its pixels and the bucket file it is."""
    record = {
        "shape": list(teacher.shape),
        "dtype": str(teacher.dtype),
        "min": int(teacher.min()),
        "max": int(teacher.max()),
        "source": None,
        "candidates": None,
    }
    if os.path.exists(_source_record(tpath)):
        with open(_source_record(tpath)) as f:
            record.update(json.load(f))
    return record  # source None: a teacher cached before its source was recorded


def extract_region(seg, y0, x0, size=SIZE, scroll_key="scroll1"):
    fs = _fs()
    pref = _scroll_prefix(scroll_key, seg, "surface-volumes")
    zarrs = sorted(p for p in fs.ls(pref, detail=False) if p.endswith(".zarr"))
    if not zarrs:
        raise ValueError(f"{seg}: no .zarr under {pref}")
    # Prefer the 2.4um volume EXPLICITLY: "2.4um sorts first" is false for segments
    # that also ship 1.129um scans (e.g. 20231221180251), where lexicographic sort
    # would pick a volume whose pyramid lacks the expected levels/scale.
    preferred = [z for z in zarrs if "2.4um" in z and "-L1" not in z]
    g = zarr.open(zarr.storage.FSStore((preferred or zarrs)[0], fs=fs), mode="r")
    arr = g[LEVEL]
    d, h, w = arr.shape
    y1, x1 = min(y0 + size, h), min(x0 + size, w)
    lo = max(0, d // 2 - 13)
    region = np.asarray(arr[lo:lo + 26, y0:y1, x0:x1])
    return region, (h, w), (y0, x0, y1, x1)


def cmd_prep():
    targets = list(TRAIN_SEGS.items()) + [(HELD_SEG, [HELD_REGION])]
    provenance = {}
    for seg, regions in targets:
        tpath = fetch_teacher(seg)
        teacher_full = tifffile.imread(tpath)
        print(f"{seg}: teacher shape={teacher_full.shape} dtype={teacher_full.dtype} "
              f"range=[{teacher_full.min()},{teacher_full.max()}]", flush=True)
        provenance[seg] = teacher_provenance(tpath, teacher_full)
        for (y0, x0) in regions:
            region, level_shape, box = extract_region(seg, y0, x0)
            t_region = teacher_region_for(teacher_full, level_shape, box)
            fid = frag_id(seg, y0, x0)
            out = prep_distill_fragment(region, t_region, DATA_ROOT, fid)
            lab = cv2.imread(os.path.join(out, f"{fid}_inklabels.png"), 0)
            print(f"prepped {out} teacher-positive={float((lab > 0).mean()):.3f}", flush=True)
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(os.path.join(DATA_ROOT, "teacher_provenance.json"), "w") as f:
        json.dump({
            "binarize_threshold": 128,
            "note": "teacher = released canon model prediction, binarized at >=128 "
                    "after uint8 scaling; NOT ground truth",
            "teachers": provenance,
        }, f, indent=2)


def provenance_line(prov):
    """The report's line on the teachers (teacher_provenance.json)."""
    def one(name, p):
        source = f", `{p['source']}`" if p.get("source") else ", source not recorded"
        return f"`{name}` {p['dtype']} range [{p['min']},{p['max']}]{source}"

    return (
        "Teacher provenance: "
        + "; ".join(one(name, p) for name, p in prov["teachers"].items())
        + f". Labels binarized at >= {prov['binarize_threshold']} after uint8 scaling."
    )


# Until 2026-10-16 the reports said AP and roc_auc were unaffected by choosing the
# epoch on the reported region; being threshold-free spares them threshold tuning, not
# epoch selection.
THRESHOLD_NOTE = (
    "Every row's val_f1, precision and recall sit at its own best threshold on this "
    "region (f1_at_0.5 does not); AP and roc_auc are threshold-free, which spares them "
    "threshold tuning, not epoch selection. positive_rate is the label's.")


def best_is_last(run):
    """Whether a run's best epoch on the region (measure_epochs) is its last."""
    return run["best"][1] == run["last"][1]


def epoch_caveat(name, run):
    """How ``name``'s reported epoch was chosen on the region it is reported on."""
    n = run["epochs"]
    if best_is_last(run):
        return (f"{name}'s best of {n} epochs by val_f1 on this region is its last, so "
                "its row follows a fixed rule.")
    return (f"{name}'s best epoch is the best of {n} by val_f1 on this region, so that "
            "row is optimistic here by an unmeasured amount; its last-epoch row follows "
            "a fixed rule.")


def epoch_rows(name, run):
    """(label, metrics) report rows for a run: its best epoch and its last, or one row
    when they are the same checkpoint."""
    (m, ck, _), (m_last, ck_last) = run["best"], run["last"]
    if best_is_last(run):
        return [(f"{name}, last epoch (`{os.path.basename(ck)}`, also its best here)", m)]
    return [(f"{name}, best epoch (`{os.path.basename(ck)}`, selected here)", m),
            (f"{name}, last epoch (`{os.path.basename(ck_last)}`)", m_last)]


def table_row(label, m):
    return f"| {label} | " + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in COLS) + " |"


def selection_note(run):
    """The Phase-2 report's caveat."""
    return ("Note: " + epoch_caveat("The student", run)
            + " The baseline is one checkpoint, not selected here. " + THRESHOLD_NOTE)


# Lightning saves detector_epoch=<n>-v<k>.ckpt when detector_epoch=<n>.ckpt exists.
_EPOCH_CHECKPOINT = re.compile(r"^detector_epoch=(\d+)(-v\d+)?\.ckpt$")


def epoch_checkpoints(model_dir):
    """A training run's checkpoints in epoch order. A -v<k> name means model_dir holds
    a second run, whose epochs cannot be told from the first's: refused."""
    found = []
    for path in glob.glob(os.path.join(model_dir, "detector_epoch=*.ckpt")):
        match = _EPOCH_CHECKPOINT.match(os.path.basename(path))
        if not match:
            continue
        if match.group(2):
            raise ValueError(
                f"{path}: {model_dir} holds checkpoints of more than one run; train "
                "into a fresh model_dir")
        found.append((int(match.group(1)), path))
    if not found:
        raise ValueError(f"no checkpoints found in {model_dir}; run the train step first")
    return [path for _, path in sorted(found)]


def measure_epochs(fid, model_dir, data_root=DATA_ROOT):
    """Every checkpoint of a run, measured on ``fid``.

    Returns the best by val_f1, which is selected on ``fid`` and so optimistic there,
    and the last epoch, a fixed rule selected on nothing, with each epoch's scores.
    """
    ckpts = epoch_checkpoints(model_dir)
    best = last = None
    per_epoch = {}
    for ck in ckpts:
        m, prob = _measure(ck, fid, data_root=data_root)
        print(f"{os.path.basename(ck)}: val_f1={m.get('val_f1', float('nan')):.4f}",
              flush=True)
        per_epoch[os.path.basename(ck)] = {c: m.get(c) for c in COLS}
        score = m.get("val_f1", float("nan"))
        if isinstance(score, float) and score != score:  # NaN
            score = -1.0
        if best is None or score > best[3]:
            best = (m, ck, prob, score)
        last = (m, ck)
    return {"best": best[:3], "last": last, "per_epoch": per_epoch,
            "epochs": len(ckpts)}


def _measure(ckpt, fid, data_root=DATA_ROOT):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask
    from vesuvius_autoresearch.detector.infer import infer
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics
    cfg = DetectorConfig(data_root=data_root)
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
    if not os.path.exists(BASELINE_JSON):
        raise ValueError(f"{BASELINE_JSON} missing; run the baseline step first")
    with open(BASELINE_JSON) as f:
        baseline = json.load(f)["vs_teacher"]
    prov_path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    prov = None
    if os.path.exists(prov_path):
        with open(prov_path) as f:
            prov = json.load(f)
    run = measure_epochs(fid, MODEL_DIR)
    m, ck, prob = run["best"]
    m_last, ck_last = run["last"]
    Image.fromarray((np.clip(prob, 0, 1) * 255).astype(np.uint8)).resize(
        (prob.shape[1] // 4, prob.shape[0] // 4)).save(
        "reports/detector/sota_distill_ours.png")
    lab = cv2.imread(os.path.join(DATA_ROOT, fid, f"{fid}_inklabels.png"), 0)
    Image.fromarray(lab).resize((lab.shape[1] // 4, lab.shape[0] // 4)).save(
        "reports/detector/sota_distill_teacher.png")
    lines = ["# Distilled detector vs teacher (held-out SOTA segment region)", "",
             "**All metrics are agreement-with-teacher (the released canon prediction), "
             "NOT ground-truth accuracy.**", ""]
    if prov is not None:
        lines += [provenance_line(prov), ""]
    lines += [selection_note(run), ""]
    lines += [
             f"Held-out: `{fid}`  |  best student ckpt: `{os.path.basename(ck)}`", "",
             "| model | " + " | ".join(COLS) + " |",
             "|---|" + "|".join(["---"] * len(COLS)) + "|",
             table_row("current detector (baseline)", baseline),
             *(table_row(label, mm) for label, mm in epoch_rows("distilled student", run)),
             "", "Renders: [ours](sota_distill_ours.png) vs "
             "[teacher](sota_distill_teacher.png)."]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"fragment": fid, "best_checkpoint": os.path.basename(ck),
                   "baseline_vs_teacher": baseline, "distilled_vs_teacher": m,
                   "last_checkpoint": os.path.basename(ck_last),
                   "distilled_last_epoch_vs_teacher": m_last,
                   "per_epoch": run["per_epoch"],
                   "selection": {
                       "distilled": f"best of {run['epochs']} epochs by val_f1 on {fid}"
                                    + (" (the last epoch)" if best_is_last(run) else ""),
                       "distilled_last_epoch": "the last epoch, a fixed rule",
                       "baseline": "one checkpoint, not selected on this fragment"},
                   "teacher_provenance": prov},
                  f, indent=2, default=float)
    print(f"DISTILLED vs teacher: val_f1={m.get('val_f1', float('nan')):.4f} "
          f"(baseline {baseline.get('val_f1', float('nan')):.4f})", flush=True)


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "baseline": cmd_baseline, "train": cmd_train,
            "measure": cmd_measure}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.distill_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
