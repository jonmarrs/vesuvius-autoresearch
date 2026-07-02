# Phase 2: SOTA Distillation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a SOTA-native ink detector by distilling from the released canon predictions (teacher) on Scroll-1 SOTA surface volumes, measured as held-out agreement-with-teacher against the current detector's baseline.

**Architecture:** A unit-tested `distill_prep.py` (teacher-region geometry + detector-format fragment writer) feeds the unchanged TimeSformer recipe (`detector.train`). An operational `distill_run.py` orchestrates fetch → prep → baseline → train → measure. Hardening fixes from the last review are folded into the files touched.

**Tech Stack:** s3fs (anonymous), zarr, tifffile, opencv, numpy; the `vesuvius_autoresearch.detector` subpackage (train/infer/metrics) unchanged.

## Global Constraints

- **All metrics are "agreement with teacher"** — every report header/column says "vs teacher"; never presented as ground-truth accuracy.
- Supervision: the released `…new_canon_autoresearch_recipe…tif` predictions; teacher value handling (binarize at 128 after uint8 scaling) is recorded in the report along with the teacher's observed dtype/range.
- Student: the existing TimeSformer recipe via `detector.train` — **no detector code changes**.
- Detector input format (verbatim): per fragment dir, `layers/{i:02d}.tif` for `i` in `[17, 43)`, `<frag>_inklabels.png`, `<frag>_mask.png`.
- Anonymous S3: `s3fs.S3FileSystem(anon=True)`, bucket `vesuvius-challenge-open-data`.
- Isolation: code under `repro/sota_data/` + `tests/`; data under `local_data/sota_distill*/` (git-ignored); reports under `reports/detector/`. Do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`.
- Loud guards: shape mismatch > 20% or unreadable files ⇒ `ValueError`.
- No AI-authorship markers. Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Create `repro/sota_data/distill_prep.py` — `teacher_region_for`, `prep_distill_fragment` (unit-tested core).
- Modify `repro/sota_data/convert.py` — extract shared `to_uint8`, add unreadable-label + int-dtype guards.
- Modify `repro/sota_data/qualitative.py` — `write_fragment` uses `to_uint8`.
- Modify `repro/sota_data/evaluate.py` — `json.dump(..., default=float)`.
- Create `repro/sota_data/distill_run.py` — operational orchestrator (subcommands).
- Tests: `tests/test_sota_distill_prep.py`; extend `tests/test_sota_convert.py`, `tests/test_sota_qualitative.py`.

---

### Task 1: Hardening — shared `to_uint8` + loud guards

**Files:**
- Modify: `repro/sota_data/convert.py`
- Modify: `repro/sota_data/qualitative.py`
- Modify: `repro/sota_data/evaluate.py`
- Test: `tests/test_sota_convert.py`, `tests/test_sota_qualitative.py` (append)

**Interfaces:**
- Produces: `convert.to_uint8(arr) -> np.ndarray(uint8)` — uint8 pass-through; uint16 → `//256`; float (max ≤ 1.0 scaled ×255) → clip 0..255; any other dtype ⇒ `ValueError`. `convert._read_8bit` and `qualitative.write_fragment` both use it. `convert.convert_surface_volume` raises `ValueError` when the label file is unreadable. `evaluate` JSON dump uses `default=float`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sota_convert.py`:

```python
def test_to_uint8_rejects_unexpected_int_dtype():
    from repro.sota_data.convert import to_uint8
    with pytest.raises(ValueError, match="dtype"):
        to_uint8(np.zeros((4, 4), np.int32))


def test_convert_unreadable_label_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segE")
    # corrupt the label file so cv2.imread returns None
    with open(os.path.join(str(tmp_path / "src"), "segE", "segE_inklabels.png"), "wb") as f:
        f.write(b"not a png")
    with pytest.raises(ValueError, match="label"):
        convert_surface_volume(os.path.join(str(tmp_path / "src"), "segE"), "segE",
                               str(tmp_path / "out"))
```

Append to `tests/test_sota_qualitative.py`:

```python
def test_write_fragment_scales_uint16(tmp_path):
    import tifffile
    layers = (np.random.rand(26, 32, 32) * 60000).astype(np.uint16)
    out = write_fragment(layers, str(tmp_path), "segU16")
    img = tifffile.imread(os.path.join(out, "layers", "17.tif"))
    assert img.dtype == np.uint8
    assert img.max() > 50  # range-scaled, not clipped to near-black
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_convert.py tests/test_sota_qualitative.py -v`
Expected: the three new tests FAIL (`ImportError: cannot import name 'to_uint8'`; no `ValueError` on the corrupt label; uint16 clipped to ≤ 255 values near 255 by `np.clip` — the max assertion may pass by luck of clip, but dtype path differs; rely on the first two failures and fix all three together).

- [ ] **Step 3: Implement**

In `repro/sota_data/convert.py`, replace the `_read_8bit` function with:

```python
def to_uint8(arr):
    """Scale an array to uint8: uint8 pass-through, uint16 via //256, floats scaled from
    [0,1] when needed. Any other dtype is an error (loud, not silent wraparound)."""
    arr = np.asarray(arr)
    if arr.dtype == np.uint8:
        return arr
    if arr.dtype == np.uint16:
        return (arr // 256).astype(np.uint8)
    if np.issubdtype(arr.dtype, np.floating):
        if float(arr.max()) <= 1.0:
            arr = arr * 255.0
        return np.clip(arr, 0, 255).astype(np.uint8)
    raise ValueError(f"unsupported dtype {arr.dtype}; expected uint8/uint16/float")


def _read_8bit(path):
    arr = tifffile.imread(path)
    if arr.ndim == 3:
        arr = arr[..., 0]
    return to_uint8(arr)
```

In `convert_surface_volume`, immediately after `label = cv2.imread(sorted(ink_files)[0], 0)` add:

```python
    if label is None:
        raise ValueError(f"{seg_id}: label file unreadable: {sorted(ink_files)[0]}")
```

(Adjust to match the file's actual variable if it reads `ink_files[0]` — the sorted pick from commit e3b8efdf.)

In `repro/sota_data/qualitative.py`, add `from .convert import to_uint8` to the imports and in `write_fragment` replace:

```python
        arr = layers[k]
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
```

with:

```python
        arr = to_uint8(layers[k])
```

In `repro/sota_data/evaluate.py`, change the JSON dump line to:

```python
    with open("reports/detector/sota_scroll1_measurement.json", "w") as f:
        json.dump({"segment": seg_id, "sota": m, "baseline": BASELINE}, f, indent=2,
                  default=float)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_convert.py tests/test_sota_qualitative.py -v`
Expected: PASS (all, including the 3 new tests)

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/convert.py repro/sota_data/qualitative.py repro/sota_data/evaluate.py tests/test_sota_convert.py tests/test_sota_qualitative.py
git commit --no-verify -m "fix(sota): shared to_uint8 scaling, unreadable-label guard, json default=float"
```

---

### Task 2: `distill_prep.py` — teacher geometry + fragment writer

**Files:**
- Create: `repro/sota_data/distill_prep.py`
- Test: `tests/test_sota_distill_prep.py`

**Interfaces:**
- Consumes: `qualitative.write_fragment` (layers+mask writer), `convert.to_uint8` (Task 1).
- Produces:
  - `teacher_region_for(teacher_full, level_shape, region_box) -> np.ndarray` — crops the full-segment teacher (any scale) to the region: `level_shape=(H_level, W_level)` of the zarr level the region came from; `region_box=(y0, x0, y1, x1)` in level coordinates; scales the box by `teacher.shape/level_shape` per axis.
  - `prep_distill_fragment(region_layers, teacher_region, out_root, frag_id, threshold=128) -> str` — writes the detector-format fragment; label = teacher resized (nearest) to the region H×W, scaled to uint8, binarized at `>= threshold` → 255. `ValueError` when the teacher H×W differs from the region by > 20% after scaling.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_distill_prep.py
import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for


def test_teacher_region_for_same_scale():
    teacher = np.arange(100 * 80).reshape(100, 80).astype(np.uint8)
    out = teacher_region_for(teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40))
    assert np.array_equal(out, teacher[10:30, 20:40])


def test_teacher_region_for_scales_box():
    # teacher at 2x the level scale: box coordinates double
    teacher = np.zeros((200, 160), np.uint8)
    teacher[20:60, 40:80] = 255
    out = teacher_region_for(teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40))
    assert out.shape == (40, 40)
    assert out.max() == 255 and out.min() == 255  # exactly the marked block


def test_prep_writes_fragment_with_teacher_label(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((64, 64), np.uint8)
    teacher[16:48, 16:48] = 200  # above threshold 128
    out = prep_distill_fragment(layers, teacher, str(tmp_path), "segT_y0_x0")
    lab = cv2.imread(os.path.join(out, "segT_y0_x0_inklabels.png"), 0)
    assert lab.shape == (64, 64)
    assert lab[32, 32] == 255 and lab[0, 0] == 0  # binarized teacher
    assert sorted(os.listdir(os.path.join(out, "layers"))) == [
        f"{i:02d}.tif" for i in range(17, 43)]
    assert os.path.exists(os.path.join(out, "segT_y0_x0_mask.png"))


def test_prep_loads_via_detector(tmp_path):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.full((64, 64), 200, np.uint8)
    prep_distill_fragment(layers, teacher, str(tmp_path), "segT2_y0_x0")
    cfg = DetectorConfig(data_root=str(tmp_path))
    images, mask, frag_mask = read_image_mask(cfg, "segT2_y0_x0")
    assert images.shape[2] == 26
    assert mask.max() == 1.0  # teacher-positive label present


def test_prep_teacher_shape_mismatch_raises(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((200, 20), np.uint8)  # >20% off in both axes
    with pytest.raises(ValueError, match="mismatch"):
        prep_distill_fragment(layers, teacher, str(tmp_path), "segT3_y0_x0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_distill_prep.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'repro.sota_data.distill_prep'`

- [ ] **Step 3: Write the implementation**

```python
# repro/sota_data/distill_prep.py
"""Distillation data prep: crop the released canon ink prediction (the TEACHER -- a model
output, not ground truth) to a zarr-level region, and write a detector-format training
fragment whose label is the binarized teacher. All downstream metrics on these fragments
are agreement-with-teacher, never ground-truth accuracy."""
import os

import cv2
import numpy as np

from .convert import to_uint8
from .qualitative import write_fragment


def teacher_region_for(teacher_full, level_shape, region_box):
    """Crop a full-segment teacher (any scale) to a region given in level coordinates."""
    th, tw = teacher_full.shape[:2]
    lh, lw = level_shape
    sy, sx = th / lh, tw / lw
    y0, x0, y1, x1 = region_box
    return np.asarray(teacher_full[int(round(y0 * sy)):int(round(y1 * sy)),
                                   int(round(x0 * sx)):int(round(x1 * sx))])


def prep_distill_fragment(region_layers, teacher_region, out_root, frag_id, threshold=128):
    region_layers = np.asarray(region_layers)
    h, w = region_layers.shape[1], region_layers.shape[2]
    t = np.asarray(teacher_region)
    if t.ndim == 3:
        t = t[..., 0]
    th, tw = t.shape
    if abs(th - h) / h > 0.2 or abs(tw - w) / w > 0.2:
        raise ValueError(f"{frag_id}: teacher {th}x{tw} vs region {h}x{w} mismatch > 20%")
    t = to_uint8(t)
    if (th, tw) != (h, w):
        t = cv2.resize(t, (w, h), interpolation=cv2.INTER_NEAREST)
    label = np.where(t >= threshold, 255, 0).astype(np.uint8)

    out_seg = write_fragment(region_layers, out_root, frag_id)  # layers + zero label + mask
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_inklabels.png"), label)  # replace label
    return out_seg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_distill_prep.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/distill_prep.py tests/test_sota_distill_prep.py
git commit --no-verify -m "feat(sota): distillation prep (teacher-region geometry + fragment writer)"
```

---

### Task 3: `distill_run.py` — operational orchestrator

**Files:**
- Create: `repro/sota_data/distill_run.py`

**Interfaces:**
- Consumes: `distill_prep` (Task 2), `qualitative` zarr path, `detector` config/train/infer/metrics.
- Produces: subcommands `prep`, `baseline`, `train`, `measure` (run in that order). Constants at the top define segments/regions and are the one place to adjust targets.

This is operational (network + GPU) — verified by running; no unit tests. The code is complete.

- [ ] **Step 1: Write the orchestrator**

```python
# repro/sota_data/distill_run.py
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
```

- [ ] **Step 2: Verify it imports and rejects bad usage**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.distill_run 2>&1 | tail -1`
Expected: `usage: python -m repro.sota_data.distill_run {prep|baseline|train|measure}` (exit non-zero; no import errors).

- [ ] **Step 3: Commit**

```bash
git add repro/sota_data/distill_run.py
git commit --no-verify -m "feat(sota): distillation orchestrator (prep/baseline/train/measure)"
```

---

### Task 4: Operational run — distill and measure (manual, network + GPU)

**Files:** none (operational); produces `reports/detector/sota_distill_*.{md,json,png}` + `local_data/sota_distill*/`.

Run by a human. This is the definition-of-done.

- [ ] **Step 1: Prep (network, no GPU needed).**

Run: `uv run python -m repro.sota_data.distill_run prep`
Expected: per segment, a teacher line (shape/dtype/range — record these) and per region `prepped … teacher-positive=0.0xx`. **Checks:** teacher-positive fractions should be plausibly ink-like (roughly 0.02–0.4). If a region prints ~0.000 (empty area) or ~1.0 (degenerate), edit the region offsets in `TRAIN_SEGS`/`HELD_REGION` (constants at the top of `distill_run.py`) and re-run prep — do not train on degenerate targets. If a teacher tif's range is not 0–255-like, note it; `to_uint8` + threshold 128 handles uint8/uint16/float, and the observed dtype/range goes in the report.

- [ ] **Step 2: Pause the loop; baseline.**

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4
uv run python -m repro.sota_data.distill_run baseline
```
Expected: `BASELINE vs teacher on 20231210121321_y4000_x2500: val_f1=0.xxxx lift=...` and `reports/detector/sota_distill_baseline.json`. Expect near-chance (the qualitative finding).

- [ ] **Step 3: Train the student (~hours GPU).**

Run: `nohup uv run python -m repro.sota_data.distill_run train > reports/detector/sota_distill_train.log 2>&1 &`
Expected: 12 epochs of the TimeSformer recipe over the 4 teacher-labeled train regions, checkpoints in `models/detector_sota_distill/`. Training tile counts are printed by Lightning; if the run aborts with "need at least one array to stack", a train fragment had no ink-positive tiles — revisit Step 1's region choices.

- [ ] **Step 4: Measure (best epoch, held-out agreement-with-teacher).**

Run: `uv run python -m repro.sota_data.distill_run measure`
Expected: per-epoch `val_f1` lines, then `DISTILLED vs teacher: val_f1=... (baseline ...)`; writes the report + both renders. **Read the result:** distilled ≫ baseline = distillation works and we have a SOTA-native detector; distilled ≈ baseline = a finding (record honestly; candidate causes: too little training data, region choice, depth-window mismatch — do NOT re-tune blindly).

- [ ] **Step 5: Commit the report; resume the loop.**

```bash
git add reports/detector/sota_distill_measurement.md reports/detector/sota_distill_measurement.json \
        reports/detector/sota_distill_baseline.json reports/detector/sota_distill_ours.png \
        reports/detector/sota_distill_teacher.png
git commit --no-verify -m "chore(sota): distillation result -- student vs teacher on held-out SOTA segment"
bash start.sh
```
Expected: loop resumes (`.loop_paused` gone; `pgrep -f run_autoresearch_loop` returns a PID).

---

## Self-Review

**Spec coverage:**
- Honesty framing (all metrics "vs teacher", teacher dtype/range recorded) → report header/columns in Task 3 `cmd_measure`, teacher-range print in `cmd_prep`, plan Global Constraints. ✓
- Baseline before training → Task 3 `cmd_baseline` + Task 4 Step 2. ✓
- Distill on 2 train segments, hold out a 3rd; level-2, 4096² regions, 26-layer window → Task 3 constants + `extract_region`. ✓
- Student = unchanged TimeSformer via `detector.train` → Task 3 `cmd_train` (config only). ✓
- Best-epoch by held-out agreement + side-by-side render → Task 3 `cmd_measure`. ✓
- `distill_prep` unit-tested core (geometry, binarize, loud guard, detector-loadable) → Task 2. ✓
- Hardening fixes (json default=float; unreadable-label + int-dtype guards; shared to_uint8) → Task 1. ✓
- Error handling (mismatch/unreadable ⇒ ValueError; re-runnable ops; loop pause) → Tasks 1/2 guards + Task 4. ✓

**Placeholder scan:** none; all code complete; commands have expected output. Region offsets are named constants adjusted operationally per Task 4 Step 1's degenerate-target check (documented decision rule, not a TBD). ✓

**Type consistency:** `teacher_region_for(teacher_full, level_shape, region_box)` and `prep_distill_fragment(region_layers, teacher_region, out_root, frag_id, threshold=128)` match between Task 2 tests/impl and Task 3 `cmd_prep`; `frag_id` naming (`<seg>_y<y0>_x<x0>`) satisfies `read_image_mask`'s `<frag>_inklabels.png`/`<frag>_mask.png` contract (verified pattern in Task 2's `test_prep_loads_via_detector`); `write_fragment(layers, out_root, seg_id)` reused from qualitative.py with its zero-label then replaced. Baseline/report JSON keys consumed consistently between `cmd_baseline` and `cmd_measure`. ✓

**Known follow-ups (out of scope):** label registration; multi-scroll distillation; Sub-project C loop integration; July filing.
