# Cross-Scroll Distillation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the controlled diversity experiment — legacy baseline vs the existing Scroll-1 student vs a fixed-budget multi-scroll student (2 Scroll-1 + 2 PHerc-0139 regions), all measured on one held-out PHerc-1667 region — answering whether training-scroll diversity buys cross-scroll generalization.

**Architecture:** Generalize `distill_run.py`'s helpers with a scroll registry (`scroll1`/`pherc0139`/`pherc1667` → bucket prefixes, keyword args defaulting to `scroll1` so Phase-2 behavior is unchanged), then add a thin operational experiment module `xscroll_run.py` (prep/baselines/train/measure) that reuses those helpers, `distill_prep`, and the detector.

**Tech Stack:** Same as Phase 2 — s3fs (anonymous), zarr, tifffile, opencv, numpy; `vesuvius_autoresearch.detector` unchanged.

## Global Constraints

- **All metrics are "agreement with teacher"** — report title/disclaimer/JSON keys carry "vs teacher"; teacher provenance (dtype/range, binarize ≥128) persisted per scroll. Never presented as ground-truth accuracy.
- Student recipe unchanged: `detector.train`, config-only. No detector code changes; no edits to `run_autoresearch_loop.py` / `scripts/training/train.py`.
- Phase-2 workflows must keep working: `distill_run.py`'s existing subcommands and constants behave identically after the generalization (keyword defaults = `scroll1`).
- Anonymous S3 (`s3fs.S3FileSystem(anon=True)`), bucket `vesuvius-challenge-open-data`. Scroll registry (verbatim): `{"scroll1": "PHercParis4", "pherc0139": "PHerc0139", "pherc1667": "PHerc1667"}`; unknown key ⇒ `ValueError`.
- Isolation: code under `repro/sota_data/` + `tests/`; data under `local_data/sota_xscroll/` (+ shared `local_data/sota_distill_teachers/`), git-ignored; reports under `reports/detector/`.
- No AI-authorship markers. Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Modify `repro/sota_data/distill_run.py` — add `SCROLLS` registry, `_scroll_prefix`, `xfrag_id`; generalize `fetch_teacher`/`extract_region` (keyword `scroll_key="scroll1"`) and `_measure` (keyword `data_root=DATA_ROOT`).
- Create `repro/sota_data/xscroll_run.py` — the experiment (arms, prep/baselines/train/measure).
- Test: `tests/test_sota_xscroll.py`.

---

### Task 1: Scroll registry + generalized helpers in `distill_run.py`

**Files:**
- Modify: `repro/sota_data/distill_run.py`
- Test: `tests/test_sota_xscroll.py`

**Interfaces:**
- Produces (all in `repro/sota_data/distill_run.py`):
  - `SCROLLS = {"scroll1": "PHercParis4", "pherc0139": "PHerc0139", "pherc1667": "PHerc1667"}`
  - `_scroll_prefix(scroll_key, seg, sub) -> str` returning `f"{BUCKET}/{SCROLLS[scroll_key]}/segments/{seg}/{sub}"`; unknown key ⇒ `ValueError` mentioning the key.
  - `xfrag_id(scroll_key, seg, y0, x0) -> str` = `f"{scroll_key}_{seg}_y{y0}_x{x0}"`.
  - `fetch_teacher(seg, scroll_key="scroll1")` — cache file `{scroll_key}_{seg}.tif`; for `scroll1`, falls back to the legacy `{seg}.tif` cache if present (avoids re-downloading Phase-2's ~5 GB).
  - `extract_region(seg, y0, x0, size=SIZE, scroll_key="scroll1")`.
  - `_measure(ckpt, fid, data_root=DATA_ROOT)`.
  - Phase-2 call sites (`cmd_prep`/`cmd_baseline`/`cmd_measure`) unchanged in behavior.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_xscroll.py
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.distill_run import BUCKET, SCROLLS, _scroll_prefix, xfrag_id


def test_scroll_registry_keys():
    assert SCROLLS == {"scroll1": "PHercParis4", "pherc0139": "PHerc0139",
                       "pherc1667": "PHerc1667"}


def test_scroll_prefix_builds_bucket_paths():
    assert _scroll_prefix("scroll1", "segA", "ink-detection") == \
        f"{BUCKET}/PHercParis4/segments/segA/ink-detection"
    assert _scroll_prefix("pherc0139", "segB", "surface-volumes") == \
        f"{BUCKET}/PHerc0139/segments/segB/surface-volumes"
    assert _scroll_prefix("pherc1667", "segC", "surface-volumes") == \
        f"{BUCKET}/PHerc1667/segments/segC/surface-volumes"


def test_scroll_prefix_unknown_key_raises():
    with pytest.raises(ValueError, match="nosuch"):
        _scroll_prefix("nosuch", "segA", "ink-detection")


def test_xfrag_id_format():
    assert xfrag_id("pherc0139", "20250108000000-w025", 4000, 2500) == \
        "pherc0139_20250108000000-w025_y4000_x2500"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_xscroll.py -v`
Expected: FAIL with `ImportError: cannot import name 'SCROLLS'`

- [ ] **Step 3: Implement the generalization**

In `repro/sota_data/distill_run.py`:

(a) Immediately after the `BUCKET = "vesuvius-challenge-open-data"` line, add:

```python
SCROLLS = {
    "scroll1": "PHercParis4",
    "pherc0139": "PHerc0139",
    "pherc1667": "PHerc1667",
}


def _scroll_prefix(scroll_key, seg, sub):
    if scroll_key not in SCROLLS:
        raise ValueError(f"unknown scroll key '{scroll_key}'; known: {sorted(SCROLLS)}")
    return f"{BUCKET}/{SCROLLS[scroll_key]}/segments/{seg}/{sub}"


def xfrag_id(scroll_key, seg, y0, x0):
    return f"{scroll_key}_{seg}_y{y0}_x{x0}"
```

(b) Replace the existing `fetch_teacher` function with:

```python
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
    return dst
```

(c) Replace the existing `extract_region` function with:

```python
def extract_region(seg, y0, x0, size=SIZE, scroll_key="scroll1"):
    fs = _fs()
    pref = _scroll_prefix(scroll_key, seg, "surface-volumes")
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
```

(d) Change `_measure`'s signature line from `def _measure(ckpt, fid):` to
`def _measure(ckpt, fid, data_root=DATA_ROOT):` and its config line from
`cfg = DetectorConfig(data_root=DATA_ROOT)` to `cfg = DetectorConfig(data_root=data_root)`.

No other lines change; the Phase-2 subcommands keep their exact behavior via the keyword
defaults.

- [ ] **Step 4: Run tests to verify they pass (new + Phase-2 suites)**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_xscroll.py tests/test_sota_distill_prep.py -v && CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.distill_run 2>&1 | tail -1`
Expected: all tests PASS (4 new + 6 existing) and the usage line prints (no import errors).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/distill_run.py tests/test_sota_xscroll.py
git commit --no-verify -m "feat(sota): scroll registry + multi-scroll helpers in distill_run (scroll1 defaults unchanged)"
```

---

### Task 2: `xscroll_run.py` — the experiment orchestrator (operational)

**Files:**
- Create: `repro/sota_data/xscroll_run.py`

**Interfaces:**
- Consumes: `distill_run` helpers from Task 1 (`fetch_teacher`, `extract_region`, `_measure`, `xfrag_id`, `frag_id`, `HELD_SEG`, `HELD_REGION`, `DATA_ROOT` as `dr.*`), `distill_prep.prep_distill_fragment`/`teacher_region_for`, `detector.train`.
- Produces: subcommands `prep`, `baselines`, `train`, `measure` (run in that order). Constants (`TRAIN`, `HELD`, `SECONDARY_0139_HELD`, segment ids, region offsets) at the top are the one place to adjust targets.

Operational (network + GPU) — verified by the usage check; complete code below.

- [ ] **Step 1: Write the orchestrator**

```python
# repro/sota_data/xscroll_run.py
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
SECONDARY_0139_HELD = ("pherc0139", "20250108000002-w027_2025010845", 4000, 2500)

REPORT_MD = "reports/detector/cross_scroll_distill.md"
REPORT_JSON = "reports/detector/cross_scroll_distill.json"
BASELINES_JSON = "reports/detector/cross_scroll_baselines.json"
COLS = dr.COLS


def _fid(target):
    scroll_key, seg, y0, x0 = target
    return dr.xfrag_id(scroll_key, seg, y0, x0)


def cmd_prep():
    targets = TRAIN + [HELD, SECONDARY_0139_HELD]
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
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(os.path.join(DATA_ROOT, "teacher_provenance.json"), "w") as f:
        json.dump({"binarize_threshold": 128,
                   "note": "teacher = released canon model prediction, binarized at >=128 "
                           "after uint8 scaling; NOT ground truth",
                   "teachers": provenance}, f, indent=2)


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
        json.dump({"fragment": held_fid, "arms": rows}, f, indent=2, default=float)


def cmd_train():
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.train import train
    cfg = DetectorConfig(data_root=DATA_ROOT, model_dir=MODEL_DIR,
                         train_fragment_ids=[_fid(t) for t in TRAIN],
                         valid_fragment_id=_fid(HELD))
    print(train(cfg))


def _best_epoch(fid):
    ckpts = sorted(glob.glob(os.path.join(MODEL_DIR, "detector_epoch=*.ckpt")),
                   key=lambda p: int(p.split("epoch=")[1].split(".")[0]))
    if not ckpts:
        raise ValueError(f"no checkpoints found in {MODEL_DIR}; run the train step first")
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


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "baselines": cmd_baselines, "train": cmd_train,
            "measure": cmd_measure}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.xscroll_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
```

- [ ] **Step 2: Verify it imports and rejects bad usage**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.xscroll_run 2>&1 | tail -1`
Expected: `usage: python -m repro.sota_data.xscroll_run {prep|baselines|train|measure}` (exit non-zero; no import errors).

- [ ] **Step 3: Commit**

```bash
git add repro/sota_data/xscroll_run.py
git commit --no-verify -m "feat(sota): cross-scroll distillation experiment orchestrator (3 arms, held-out PHerc1667)"
```

---

### Task 3: Operational run — the diversity experiment (manual, network + GPU)

**Files:** none (operational); produces `reports/detector/cross_scroll_distill.{md,json}`, `cross_scroll_baselines.json`, and three renders.

Run by a human. This is the definition-of-done.

- [ ] **Step 1: Prep (network; loop may keep running).**

Run: `uv run python -m repro.sota_data.xscroll_run prep`
Expected: teacher provenance line per (scroll, segment) — the PHerc-0139 and PHerc-1667 teachers are downloaded for the first time (record their dtype/range) — then `prepped … teacher-positive=0.xxx` for all 6 fragments. **Check:** every teacher-positive is in the 0.02–0.4 band. If a region is degenerate (≈0 or ≈1) or the segment's level-2 area is smaller than the offsets (extract returns a short region → prep raises), adjust that entry's `y0/x0` (or pick a different segment id from `discover`) in the constants and re-run — do not train on degenerate targets.

- [ ] **Step 2: Pause the loop; run the two no-training arms.**

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4
uv run python -m repro.sota_data.xscroll_run baselines
```
Expected: two lines — `baseline_epoch7 on held-out 1667: val_f1=… lift=…` and `armA_scroll1_student on held-out 1667: …` — and `reports/detector/cross_scroll_baselines.json`. **This is already a publishable datapoint:** does the Scroll-1 student transfer to 1667 at all (arm A lift vs the baseline's ~1.0)?

- [ ] **Step 3: Train arm B (~10 h GPU).**

Run: `nohup uv run python -m repro.sota_data.xscroll_run train > reports/detector/xscroll_train.log 2>&1 &`
Expected: 12 epochs over the 4 multi-scroll fragments, checkpoints in `models/detector_xscroll/`. If it aborts with "need at least one array to stack", a train fragment had no ink-positive tiles — revisit Step 1's region choices.

- [ ] **Step 4: Measure.**

Run: `uv run python -m repro.sota_data.xscroll_run measure`
Expected: per-epoch `val_f1` lines, then `ARM B vs teacher on held-out 1667: val_f1=… (arm A …, baseline …)`; writes the report, JSON, and three renders. **Read the verdict against the interpretation table:** B ≫ A ⇒ diversity drives generalization; B ≈ A ⇒ diversity alone insufficient at this scale; A ≫ baseline ⇒ even single-scroll distillation transfers. Also read the secondary rows: did diversity cost arm B same-scroll performance vs arm A (Scroll-1 read-out), and how does arm B do on its own second scroll (0139 read-out)?

- [ ] **Step 5: Commit the artifacts and resume the loop.**

```bash
git add reports/detector/cross_scroll_distill.md reports/detector/cross_scroll_distill.json \
        reports/detector/cross_scroll_baselines.json reports/detector/xscroll_armB_1667.png \
        reports/detector/xscroll_armA_1667.png reports/detector/xscroll_teacher_1667.png
git commit --no-verify -m "chore(sota): cross-scroll diversity experiment result (held-out PHerc 1667)"
bash start.sh
```
Expected: loop resumes. Record the verdict honestly either way; do NOT re-tune blindly.

---

## Self-Review

**Spec coverage:**
- Scroll registry + generalized helpers, Phase-2 behavior preserved → Task 1 (keyword defaults; Phase-2 suites re-run in Step 4). ✓
- Experiment arms as data; arm A = existing checkpoint, no training → Task 2 constants (`ARM_A_CKPT`, `TRAIN`, `HELD`). ✓
- Three-arm measurement on one held-out 1667 region + secondary same-scroll read-outs + renders + one comparative report → Task 2 `cmd_baselines`/`cmd_measure`, Task 3 Steps 2/4. ✓
- Honesty framing (vs-teacher disclaimer, per-scroll provenance persisted, selection-set note) → Task 2 report lines + `cmd_prep` provenance. ✓
- Tests: registry paths, unknown key, xfrag format → Task 1. Prep geometry/guards already covered by Phase-2 suites (re-run, not re-written). ✓
- One new training run only; loop pause; degenerate-region rule; interpretation table → Task 3. ✓

**Placeholder scan:** none — all code complete; segment ids are real (verified in the bucket during brainstorming); region offsets are named constants governed by Task 3 Step 1's documented adjustment rule. ✓

**Type consistency:** `_scroll_prefix(scroll_key, seg, sub)`, `xfrag_id(scroll_key, seg, y0, x0)`, `fetch_teacher(seg, scroll_key=)`, `extract_region(seg, y0, x0, size=, scroll_key=)`, `_measure(ckpt, fid, data_root=)` — used identically in Task 2 (`dr.*` calls) as defined in Task 1; `COLS`/`frag_id`/`HELD_SEG`/`HELD_REGION`/`DATA_ROOT`/`BASELINE_CKPT` referenced via `dr.` match `distill_run.py` as read. Report JSON keys written by `cmd_baselines` (`arms.{label}.vs_teacher`) are consumed identically in `cmd_measure`. ✓

**Known follow-ups (out of scope):** ground-truth label registration; scaling beyond 3 scrolls; Sub-project C; July filing refresh with this result.
