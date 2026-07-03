"""Cross-scroll distillation experiment (operational): does training-scroll DIVERSITY buy
generalization to an unseen scroll at fixed budget? Three arms measured on one held-out
PHerc1667 region no arm trains on: the legacy detector (baseline), the existing Scroll-1
student (arm A, no new training), and a multi-scroll student trained on 2 Scroll-1 +
2 PHerc-0139 regions (arm B, same 4-region budget as A). All metrics are AGREEMENT WITH
TEACHER (the released canon predictions) -- never ground-truth accuracy."""
import glob
import json
import os
import sys

import cv2
import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for

DATA_ROOT = "local_data/sota_xscroll"
MODEL_DIR = "models/detector_xscroll"
ARM_A_CKPT = "models/detector_sota_distill/detector_epoch=9.ckpt"  # Phase-2 best

# (scroll_key, segment_id, y0, x0) -- adjust offsets at prep time if teacher-positive
# is outside the 0.02-0.4 sanity band (the Phase-2 rule).
TRAIN = [
    ("scroll1", "20230702185753", 4000, 2500),
    ("scroll1", "20231005123336", 4000, 2500),
    ("pherc0139", "20250108000000-w025_2025010863", 4000, 2500),
    ("pherc0139", "20250108000001-w026_2025010854", 4000, 2500),
]
HELD = ("pherc1667", "20240304141531-w013_20240304141531_flatboi", 4000, 2500)
SECONDARY_0139_HELD = ("pherc0139", "20250108000002-w027_2025010845", 1500, 1500)

# Arm C (capability run): 3 scrolls x 2 regions. Differs from arm B in BOTH diversity
# (+pherc0172) and volume (6 vs 4 regions) -- stated in the report.
TRAIN_C = TRAIN + [
    ("pherc0172", "20250917143559-w062_20250917143559205_flatboi", 0, 0),
    ("pherc0172", "20250926112011-w078_20250926112011918_flatboi", 0, 0),
]
SECONDARY_0172_HELD = ("pherc0172", "20250926113336-w079_20250926113336891_flatboi", 0, 0)
MODEL_DIR_C = "models/detector_xscroll_c"
SCALE_REPORT_MD = "reports/detector/cross_scroll_scale.md"
SCALE_REPORT_JSON = "reports/detector/cross_scroll_scale.json"

REPORT_MD = "reports/detector/cross_scroll_distill.md"
REPORT_JSON = "reports/detector/cross_scroll_distill.json"
BASELINES_JSON = "reports/detector/cross_scroll_baselines.json"
COLS = dr.COLS


def _fid(target):
    scroll_key, seg, y0, x0 = target
    return dr.xfrag_id(scroll_key, seg, y0, x0)


def _prep_targets(targets):
    """Prep detector-format fragments for (scroll_key, seg, y0, x0) targets; return the
    per-teacher provenance dict for the teachers touched."""
    provenance = {}
    teachers = {}
    for (scroll_key, seg, y0, x0) in targets:
        key = (scroll_key, seg)
        if key not in teachers:
            tpath = dr.fetch_teacher(seg, scroll_key=scroll_key)
            teachers[key] = tifffile.imread(tpath)
            t = teachers[key]
            print(f"{scroll_key}/{seg}: teacher shape={t.shape} dtype={t.dtype} "
                  f"range=[{t.min()},{t.max()}]", flush=True)
            provenance[f"{scroll_key}/{seg}"] = {
                "shape": list(t.shape), "dtype": str(t.dtype),
                "min": int(t.min()), "max": int(t.max()),
            }
        region, level_shape, box = dr.extract_region(seg, y0, x0, scroll_key=scroll_key)
        t_region = teacher_region_for(teachers[key], level_shape, box)
        fid = _fid((scroll_key, seg, y0, x0))
        out = prep_distill_fragment(region, t_region, DATA_ROOT, fid)
        lab = cv2.imread(os.path.join(out, f"{fid}_inklabels.png"), 0)
        print(f"prepped {out} teacher-positive={float((lab > 0).mean()):.3f}", flush=True)
    return provenance


def _write_provenance(provenance):
    """Merge new teacher provenance into DATA_ROOT/teacher_provenance.json."""
    os.makedirs(DATA_ROOT, exist_ok=True)
    path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    merged = {}
    if os.path.exists(path):
        with open(path) as f:
            merged = json.load(f).get("teachers", {})
    merged.update(provenance)
    with open(path, "w") as f:
        json.dump({"binarize_threshold": 128,
                   "note": "teacher = released canon model prediction, binarized at >=128 "
                           "after uint8 scaling; NOT ground truth",
                   "teachers": merged}, f, indent=2)


def cmd_prep():
    provenance = _prep_targets(TRAIN + [HELD, SECONDARY_0139_HELD])
    _write_provenance(provenance)


def cmd_baselines():
    held_fid = _fid(HELD)
    rows = {}
    for label, ckpt in [("baseline_epoch7", dr.BASELINE_CKPT),
                        ("armA_scroll1_student", ARM_A_CKPT)]:
        m, _ = dr._measure(ckpt, held_fid, data_root=DATA_ROOT)
        rows[label] = {"checkpoint": ckpt, "vs_teacher": m}
        print(f"{label} on held-out 1667: val_f1={m.get('val_f1', float('nan')):.4f} "
              f"lift={m.get('ap_prevalence_lift', float('nan')):.4f}", flush=True)
    os.makedirs("reports/detector", exist_ok=True)
    with open(BASELINES_JSON, "w") as f:
        json.dump({"fragment": held_fid, "arms": rows,
                   "note": "All metrics are agreement-with-teacher (released canon "
                           "predictions), NOT ground-truth accuracy."},
                  f, indent=2, default=float)


def cmd_train():
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.train import train
    cfg = DetectorConfig(data_root=DATA_ROOT, model_dir=MODEL_DIR,
                         train_fragment_ids=[_fid(t) for t in TRAIN],
                         valid_fragment_id=_fid(HELD))
    print(train(cfg))


def _best_epoch(fid, model_dir=MODEL_DIR):
    ckpts = sorted(glob.glob(os.path.join(model_dir, "detector_epoch=*.ckpt")),
                   key=lambda p: int(p.split("epoch=")[1].split(".")[0]))
    if not ckpts:
        raise ValueError(f"no checkpoints found in {model_dir}; run the train step first")
    best = None
    for ck in ckpts:
        m, prob = dr._measure(ck, fid, data_root=DATA_ROOT)
        print(f"{os.path.basename(ck)}: val_f1={m.get('val_f1', float('nan')):.4f}",
              flush=True)
        score = m.get("val_f1", float("nan"))
        if isinstance(score, float) and score != score:  # NaN
            score = -1.0
        if best is None or score > best[3]:
            best = (m, ck, prob, score)
    return best[:3]


def cmd_measure():
    held_fid = _fid(HELD)
    if not os.path.exists(BASELINES_JSON):
        raise ValueError(f"{BASELINES_JSON} missing; run the baselines step first")
    with open(BASELINES_JSON) as f:
        base = json.load(f)["arms"]
    m_b, ck_b, prob_b = _best_epoch(held_fid)

    # renders on the held-out 1667 region: arm B + teacher; arm A for comparison
    Image.fromarray((np.clip(prob_b, 0, 1) * 255).astype(np.uint8)).resize(
        (prob_b.shape[1] // 4, prob_b.shape[0] // 4)).save(
        "reports/detector/xscroll_armB_1667.png")
    _, prob_a = dr._measure(ARM_A_CKPT, held_fid, data_root=DATA_ROOT)
    Image.fromarray((np.clip(prob_a, 0, 1) * 255).astype(np.uint8)).resize(
        (prob_a.shape[1] // 4, prob_a.shape[0] // 4)).save(
        "reports/detector/xscroll_armA_1667.png")
    lab = cv2.imread(os.path.join(DATA_ROOT, held_fid, f"{held_fid}_inklabels.png"), 0)
    Image.fromarray(lab).resize((lab.shape[1] // 4, lab.shape[0] // 4)).save(
        "reports/detector/xscroll_teacher_1667.png")

    # secondary read-outs (same-scroll performance)
    sec = {}
    m, _ = dr._measure(ck_b, _fid(SECONDARY_0139_HELD), data_root=DATA_ROOT)
    sec["armB_on_held0139"] = m
    m, _ = dr._measure(ck_b, dr.frag_id(dr.HELD_SEG, *dr.HELD_REGION),
                       data_root=dr.DATA_ROOT)
    sec["armB_on_heldScroll1_phase2"] = m
    m, _ = dr._measure(ARM_A_CKPT, dr.frag_id(dr.HELD_SEG, *dr.HELD_REGION),
                       data_root=dr.DATA_ROOT)
    sec["armA_on_heldScroll1_phase2"] = m

    prov_path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    prov = None
    if os.path.exists(prov_path):
        with open(prov_path) as f:
            prov = json.load(f)

    def row(label, m):
        return f"| {label} | " + " | ".join(
            f"{m.get(c, float('nan')):.4f}" for c in COLS) + " |"

    lines = ["# Cross-scroll distillation: diversity experiment (held-out PHerc 1667)", "",
             "**All metrics are agreement-with-teacher (the released canon predictions), "
             "NOT ground-truth accuracy.** No arm trained on any PHerc-1667 data. "
             "Arms A and B use the same 4-region training budget; training-scroll "
             "diversity is the only variable. The held-out region also serves as arm B's "
             "best-epoch selection set (AP and roc_auc are threshold-free).", ""]
    if prov is not None:
        lines += ["Teacher provenance: " + "; ".join(
            f"`{s}` {p['dtype']} range [{p['min']},{p['max']}]"
            for s, p in prov["teachers"].items())
            + f". Labels binarized at >= {prov['binarize_threshold']} after uint8 scaling.",
            ""]
    lines += [f"Held-out: `{held_fid}`  |  arm B best ckpt: `{os.path.basename(ck_b)}`", "",
              "| model (on held-out 1667) | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("legacy detector (no distillation)",
                  base["baseline_epoch7"]["vs_teacher"]),
              row("arm A: Scroll-1 student (existing)",
                  base["armA_scroll1_student"]["vs_teacher"]),
              row("arm B: multi-scroll student (2xScroll1 + 2xPHerc0139)", m_b),
              "", "Secondary (same-scroll read-outs):", "",
              "| model / fragment | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("arm B on held-out PHerc-0139 region", sec["armB_on_held0139"]),
              row("arm B on Phase-2 held-out Scroll-1 region",
                  sec["armB_on_heldScroll1_phase2"]),
              row("arm A on Phase-2 held-out Scroll-1 region",
                  sec["armA_on_heldScroll1_phase2"]),
              "", "Renders (held-out 1667): [arm B](xscroll_armB_1667.png) | "
              "[arm A](xscroll_armA_1667.png) | [teacher](xscroll_teacher_1667.png)."]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"held_out": held_fid, "armB_best_checkpoint": os.path.basename(ck_b),
                   "on_held_1667": {"baseline": base["baseline_epoch7"]["vs_teacher"],
                                    "armA": base["armA_scroll1_student"]["vs_teacher"],
                                    "armB": m_b},
                   "secondary": sec, "teacher_provenance": prov},
                  f, indent=2, default=float)
    print(f"ARM B vs teacher on held-out 1667: val_f1={m_b.get('val_f1', float('nan')):.4f} "
          f"(arm A "
          f"{base['armA_scroll1_student']['vs_teacher'].get('val_f1', float('nan')):.4f}, "
          f"baseline "
          f"{base['baseline_epoch7']['vs_teacher'].get('val_f1', float('nan')):.4f})",
          flush=True)


def cmd_prep_c():
    held_dir = os.path.join(DATA_ROOT, _fid(HELD))
    if not os.path.isdir(held_dir):
        raise ValueError(f"{held_dir} missing; run the arm-B `prep` step first "
                         "(the held-out 1667 fragment is shared)")
    provenance = _prep_targets(TRAIN_C + [SECONDARY_0172_HELD])
    _write_provenance(provenance)


def cmd_train_c():
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.train import train
    cfg = DetectorConfig(data_root=DATA_ROOT, model_dir=MODEL_DIR_C,
                         train_fragment_ids=[_fid(t) for t in TRAIN_C],
                         valid_fragment_id=_fid(HELD))
    print(train(cfg))


def cmd_measure_c():
    held_fid = _fid(HELD)
    if not os.path.exists(REPORT_JSON):
        raise ValueError(f"{REPORT_JSON} missing; the committed arm-B report is required "
                         "(its baseline/armA/armB numbers are cited, not re-run)")
    with open(REPORT_JSON) as f:
        prior = json.load(f)
    m_c, ck_c, prob_c = _best_epoch(held_fid, model_dir=MODEL_DIR_C)

    Image.fromarray((np.clip(prob_c, 0, 1) * 255).astype(np.uint8)).resize(
        (prob_c.shape[1] // 4, prob_c.shape[0] // 4)).save(
        "reports/detector/xscroll_armC_1667.png")

    sec = {}
    m, _ = dr._measure(ck_c, _fid(SECONDARY_0172_HELD), data_root=DATA_ROOT)
    sec["armC_on_held0172"] = m
    m, _ = dr._measure(ck_c, _fid(SECONDARY_0139_HELD), data_root=DATA_ROOT)
    sec["armC_on_held0139"] = m
    m, _ = dr._measure(ck_c, dr.frag_id(dr.HELD_SEG, *dr.HELD_REGION),
                       data_root=dr.DATA_ROOT)
    sec["armC_on_heldScroll1_phase2"] = m

    prov = None
    prov_path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    if os.path.exists(prov_path):
        with open(prov_path) as f:
            prov = json.load(f)

    def row(label, m):
        return f"| {label} | " + " | ".join(
            f"{m.get(c, float('nan')):.4f}" for c in COLS) + " |"

    on1667 = prior["on_held_1667"]
    lines = ["# Scaled multi-scroll distillation (arm C) on held-out PHerc 1667", "",
             "**All metrics are agreement-with-teacher (the released canon predictions), "
             "NOT ground-truth accuracy.** No arm trained on any PHerc-1667 data. Arm C is a "
             "**capability run**: it differs from arm B in BOTH training-scroll diversity "
             "(+PHerc0172) and data volume (6 vs 4 regions) -- it is not a single-variable "
             "experiment. Caveat: the held-out region serves as the best-epoch selection set "
             "for arms B and C (not for arm A or the legacy baseline) -- the asymmetry-free "
             "anchor is the **arm-vs-legacy-baseline** comparison. Baseline/A/B rows are "
             "cited from the committed cross_scroll_distill.json, not re-run.", ""]
    if prov is not None:
        lines += ["Teacher provenance: " + "; ".join(
            f"`{s}` {p['dtype']} range [{p['min']},{p['max']}]"
            for s, p in prov["teachers"].items())
            + f". Labels binarized at >= {prov['binarize_threshold']} after uint8 scaling.",
            ""]
    lines += [f"Held-out: `{held_fid}`  |  arm C best ckpt: `{os.path.basename(ck_c)}`", "",
              "| model (on held-out 1667) | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("legacy detector (cited)", on1667["baseline"]),
              row("arm A: 1 scroll, 4 regions (cited)", on1667["armA"]),
              row("arm B: 2 scrolls, 4 regions (cited)", on1667["armB"]),
              row("arm C: 3 scrolls, 6 regions", m_c),
              "", "Secondary (arm C same-scroll read-outs):", "",
              "| model / fragment | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("arm C on held-out PHerc-0172 region", sec["armC_on_held0172"]),
              row("arm C on held-out PHerc-0139 region", sec["armC_on_held0139"]),
              row("arm C on Phase-2 held-out Scroll-1 region",
                  sec["armC_on_heldScroll1_phase2"]),
              "", "Renders (held-out 1667): [arm C](xscroll_armC_1667.png) | "
              "[arm B](xscroll_armB_1667.png) | [arm A](xscroll_armA_1667.png) | "
              "[teacher](xscroll_teacher_1667.png)."]
    with open(SCALE_REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(SCALE_REPORT_JSON, "w") as f:
        json.dump({"held_out": held_fid, "armC_best_checkpoint": os.path.basename(ck_c),
                   "on_held_1667": {**on1667, "armC": m_c},
                   "secondary_armC": sec,
                   "cited_from": "reports/detector/cross_scroll_distill.json",
                   "teacher_provenance": prov},
                  f, indent=2, default=float)
    print(f"ARM C vs teacher on held-out 1667: val_f1={m_c.get('val_f1', float('nan')):.4f} "
          f"(armB {on1667['armB'].get('val_f1', float('nan')):.4f}, "
          f"armA {on1667['armA'].get('val_f1', float('nan')):.4f}, "
          f"baseline {on1667['baseline'].get('val_f1', float('nan')):.4f})", flush=True)


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "baselines": cmd_baselines, "train": cmd_train,
            "measure": cmd_measure, "prep_c": cmd_prep_c, "train_c": cmd_train_c,
            "measure_c": cmd_measure_c}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.xscroll_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
