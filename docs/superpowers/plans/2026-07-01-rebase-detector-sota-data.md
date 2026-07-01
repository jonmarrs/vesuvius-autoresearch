# Rebase Ink Detector on SOTA Scroll-1 Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether the newly-open SOTA-quality Scroll-1 (PHerc Paris 4) data lifts our existing detector: convert one released labeled segment to the detector format and evaluate it with Sub-project A's metric contract against the old-data baseline (val_f1 0.222 / lift 1.290).

**Architecture:** A new `repro/sota_data/` with a unit-tested `convert.py` (surface volume → detector format) plus operational `discover.py`/`fetch.py`/`evaluate.py` (S3 streaming + reuse of the `detector` subpackage). No detector code changes.

**Tech Stack:** s3fs (anonymous S3, already installed), tifffile, opencv (cv2), numpy, Pillow; the `vesuvius_autoresearch.detector` subpackage + A's `metrics`.

## Global Constraints

- Reuse A's metric contract (`val_f1` primary; `average_precision` + `ap_prevalence_lift` gates; ROC-AUC secondary). No detector code changes.
- Detector input format (verbatim): per segment dir, `layers/{i:02d}.tif` for `i` in `[17, 43)` (26 8-bit slices), `<seg>_inklabels.png`, `<seg>_mask.png`.
- Old-data Scroll-1 baseline to compare against: **val_f1 0.2218 / f1@0.5 0.2210 / average_precision 0.1445 / ap_prevalence_lift 1.2904 / roc_auc 0.5848** (segment `20230702185753`, epoch-7 detector).
- S3 access is anonymous: `s3fs.S3FileSystem(anon=True)` on bucket `vesuvius-challenge-open-data`.
- Isolation: code under `repro/sota_data/` + `tests/`; data under `local_data/sota_scroll1/` (git-ignored); artifacts under `reports/detector/`. Do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`.
- No AI-authorship markers. Run tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Create `repro/sota_data/__init__.py` — empty package marker.
- Create `repro/sota_data/convert.py` — `convert_surface_volume(...)` (the unit-tested core).
- Create `repro/sota_data/discover.py` — operational: list the open-data bucket for Scroll-1 segments.
- Create `repro/sota_data/fetch.py` — operational: download one segment's layers + label + mask.
- Create `repro/sota_data/evaluate.py` — operational: infer + A's metrics on the converted segment → report.
- Test: `tests/test_sota_convert.py`.

---

### Task 1: `convert.py` — surface volume → detector format

**Files:**
- Create: `repro/sota_data/__init__.py` (empty)
- Create: `repro/sota_data/convert.py`
- Test: `tests/test_sota_convert.py`

**Interfaces:**
- Produces: `convert_surface_volume(src_dir, seg_id, out_root, n_layers=26, start_idx=17) -> str`. Reads `src_dir/layers/*.tif` (sorted; ≥ `n_layers` of them), selects the centered `n_layers` window, writes 8-bit `out_root/seg_id/layers/{start_idx+k:02d}.tif`, plus `out_root/seg_id/<seg_id>_inklabels.png` and `<seg_id>_mask.png` (each resized to the layer H×W). Raises `ValueError` on too-few layers or a label/volume H×W mismatch > 20%. Returns the output segment dir. `src_dir` must contain an ink label matching `*inklabels*` and optionally a `*mask*`; if no mask file exists, an all-255 mask is written.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_convert.py
import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.convert import convert_surface_volume


def _make_src(root, seg, n_src=40, h=128, w=128, label_hw=None):
    layers = os.path.join(root, seg, "layers")
    os.makedirs(layers, exist_ok=True)
    for i in range(n_src):
        tifffile.imwrite(os.path.join(layers, f"{i:02d}.tif"),
                         (np.random.rand(h, w) * 60000).astype(np.uint16))
    lh, lw = label_hw or (h, w)
    lab = np.zeros((lh, lw), np.uint8)
    lab[lh // 4:lh // 2, lw // 4:lw // 2] = 255
    cv2.imwrite(os.path.join(root, seg, f"{seg}_inklabels.png"), lab)
    cv2.imwrite(os.path.join(root, seg, f"{seg}_mask.png"),
                np.full((lh, lw), 255, np.uint8))
    return os.path.join(root, seg)


def test_convert_writes_26_layers_and_labels(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segA")
    out = convert_surface_volume(src, "segA", str(tmp_path / "out"))
    layer_files = sorted(os.listdir(os.path.join(out, "layers")))
    assert layer_files == [f"{i:02d}.tif" for i in range(17, 43)]  # 26 layers, 17..42
    img = tifffile.imread(os.path.join(out, "layers", "17.tif"))
    assert img.shape == (128, 128) and img.dtype == np.uint8  # downcast to 8-bit
    assert os.path.exists(os.path.join(out, "segA_inklabels.png"))
    assert os.path.exists(os.path.join(out, "segA_mask.png"))


def test_convert_output_loads_via_detector(tmp_path):
    import sys
    sys.path.insert(0, os.path.abspath("."))
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask
    src = _make_src(str(tmp_path / "src"), "segB")
    convert_surface_volume(src, "segB", str(tmp_path / "out"))
    cfg = DetectorConfig(data_root=str(tmp_path / "out"))
    images, mask, frag_mask = read_image_mask(cfg, "segB")
    assert images.shape[2] == 26


def test_convert_too_few_layers_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segC", n_src=10)
    with pytest.raises(ValueError, match="layers"):
        convert_surface_volume(src, "segC", str(tmp_path / "out"))


def test_convert_label_mismatch_raises(tmp_path):
    src = _make_src(str(tmp_path / "src"), "segD", h=128, w=128, label_hw=(500, 30))
    with pytest.raises(ValueError, match="mismatch"):
        convert_surface_volume(src, "segD", str(tmp_path / "out"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_convert.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'repro.sota_data.convert'`

- [ ] **Step 3: Write the implementation**

```python
# repro/sota_data/__init__.py
```
(empty file)

```python
# repro/sota_data/convert.py
"""Adapt a released SOTA surface-volume segment (a directory of tiff depth slices + an ink
label) into the detector's input format: 26 8-bit layers 17..42, plus <seg>_inklabels.png
and <seg>_mask.png resized to the layer grid. Fails loudly on too-few layers or a
label/volume shape mismatch (the cross-scroll misalignment lesson)."""
import glob
import os

import cv2
import numpy as np
import tifffile


def _read_8bit(path):
    arr = tifffile.imread(path)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.dtype == np.uint16:
        arr = (arr // 256).astype(np.uint8)
    return arr.astype(np.uint8)


def convert_surface_volume(src_dir, seg_id, out_root, n_layers=26, start_idx=17):
    src_layers = sorted(glob.glob(os.path.join(src_dir, "layers", "*.tif")))
    if len(src_layers) < n_layers:
        raise ValueError(
            f"{seg_id}: found {len(src_layers)} source layers, need >= {n_layers}")
    lo = (len(src_layers) - n_layers) // 2
    chosen = src_layers[lo:lo + n_layers]

    out_seg = os.path.join(out_root, seg_id)
    out_layers = os.path.join(out_seg, "layers")
    os.makedirs(out_layers, exist_ok=True)
    h = w = None
    for k, src in enumerate(chosen):
        img = _read_8bit(src)
        h, w = img.shape
        tifffile.imwrite(os.path.join(out_layers, f"{start_idx + k:02d}.tif"), img)

    ink_files = glob.glob(os.path.join(src_dir, "*inklabels*"))
    if not ink_files:
        raise ValueError(f"{seg_id}: no *inklabels* file in {src_dir}")
    label = cv2.imread(ink_files[0], 0)
    lh, lw = label.shape
    if abs(lh - h) / h > 0.2 or abs(lw - w) / w > 0.2:
        raise ValueError(
            f"{seg_id}: label {lh}x{lw} vs volume {h}x{w} mismatch > 20%")
    label = cv2.resize(label, (w, h), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_inklabels.png"), label)

    mask_files = [f for f in glob.glob(os.path.join(src_dir, "*mask*"))]
    if mask_files:
        mask = cv2.resize(cv2.imread(mask_files[0], 0), (w, h),
                          interpolation=cv2.INTER_NEAREST)
    else:
        mask = np.full((h, w), 255, np.uint8)
    cv2.imwrite(os.path.join(out_seg, f"{seg_id}_mask.png"), mask)
    return out_seg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_convert.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/__init__.py repro/sota_data/convert.py tests/test_sota_convert.py
git commit --no-verify -m "feat(sota): surface-volume -> detector-format converter (26 layers, label/mask, loud guards)"
```

---

### Task 2: `discover.py` / `fetch.py` / `evaluate.py` — S3 + eval tooling (operational)

**Files:**
- Create: `repro/sota_data/discover.py`
- Create: `repro/sota_data/fetch.py`
- Create: `repro/sota_data/evaluate.py`

**Interfaces:**
- Consumes: `convert_surface_volume` (Task 1); `detector` infer + `metrics.segmentation_metrics` (A).
- Produces: `discover.list_prefix(prefix) -> list[str]`; `fetch.fetch_segment(s3_seg_prefix, out_dir) -> str`; `evaluate.evaluate_segment(seg_id, data_root, checkpoint) -> dict`.

These hit the live bucket / GPU, so their acceptance is a successful run, not a unit test. The code below is complete; verification is a dry listing (Step 4).

- [ ] **Step 1: Write `discover.py`**

```python
# repro/sota_data/discover.py
"""List the open Vesuvius data bucket to find Scroll-1 / PHerc Paris 4 segments that have a
surface volume (layers/) and an ink label. Operational: run it, read the output, pick a
target. Anonymous S3, no credentials."""
import sys

import s3fs

BUCKET = "vesuvius-challenge-open-data"


def list_prefix(prefix=""):
    fs = s3fs.S3FileSystem(anon=True)
    path = f"{BUCKET}/{prefix}".rstrip("/")
    return fs.ls(path, detail=False)


def classify(fs, seg_prefix):
    """Return (has_layers, has_ink) for a candidate segment prefix."""
    try:
        entries = fs.ls(seg_prefix, detail=False)
    except Exception:
        return (False, False)
    names = [e.rsplit("/", 1)[-1].lower() for e in entries]
    has_layers = any(n in ("layers", "surface_volume") for n in names)
    has_ink = any("inklabel" in n for n in names)
    return (has_layers, has_ink)


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    for entry in list_prefix(prefix):
        print(entry)
```

- [ ] **Step 2: Write `fetch.py`**

```python
# repro/sota_data/fetch.py
"""Download one segment's layers + ink label + mask from the open bucket to local disk.
Operational. Anonymous S3."""
import os
import sys

import s3fs

BUCKET = "vesuvius-challenge-open-data"


def fetch_segment(s3_seg_prefix, out_dir):
    """s3_seg_prefix: bucket-relative path to the segment dir (contains layers/ + label)."""
    fs = s3fs.S3FileSystem(anon=True)
    os.makedirs(out_dir, exist_ok=True)
    src = f"{BUCKET}/{s3_seg_prefix}".rstrip("/")
    fs.get(src, out_dir, recursive=True)
    return out_dir


if __name__ == "__main__":
    fetch_segment(sys.argv[1], sys.argv[2])
    print("fetched to", sys.argv[2])
```

- [ ] **Step 3: Write `evaluate.py`**

```python
# repro/sota_data/evaluate.py
"""Evaluate the existing detector on a converted SOTA segment with A's metric contract and
write a report comparing to the old-data Scroll-1 baseline. Operational (loads a checkpoint,
runs GPU inference)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("."))
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.data import read_image_mask
from vesuvius_autoresearch.detector.infer import infer
from vesuvius_autoresearch.detector.metrics import segmentation_metrics

BASELINE = {"val_f1": 0.2218, "average_precision": 0.1445,
            "ap_prevalence_lift": 1.2904, "roc_auc": 0.5848}


def evaluate_segment(seg_id, data_root="local_data/sota_scroll1",
                     checkpoint="models/detector/detector_epoch=7.ckpt"):
    cfg = DetectorConfig(data_root=data_root)
    prob = infer(cfg, checkpoint, seg_id)
    _, label, mask = read_image_mask(cfg, seg_id)
    h, w = label.shape
    m = segmentation_metrics(prob[:h, :w], (label > 0.5).astype(np.uint8),
                             mask[:h, :w].astype(bool))
    m.pop("metrics_by_threshold", None)
    os.makedirs("reports/detector", exist_ok=True)
    cols = ["val_f1", "average_precision", "ap_prevalence_lift", "roc_auc"]
    lines = ["# Detector on SOTA Scroll-1 data vs old data", "",
             f"Segment: `{seg_id}`  |  checkpoint: `{checkpoint}`", "",
             "| source | " + " | ".join(cols) + " |",
             "|---|" + "|".join(["---"] * len(cols)) + "|",
             "| old 8-bit Scroll-1 (20230702185753) | "
             + " | ".join(f"{BASELINE[c]:.4f}" for c in cols) + " |",
             "| SOTA data (" + seg_id + ") | "
             + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in cols) + " |"]
    with open("reports/detector/sota_scroll1_measurement.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open("reports/detector/sota_scroll1_measurement.json", "w") as f:
        json.dump({"segment": seg_id, "sota": m, "baseline": BASELINE}, f, indent=2)
    print(f"SOTA {seg_id}: val_f1={m['val_f1']:.4f} ap={m['average_precision']:.4f} "
          f"lift={m['ap_prevalence_lift']:.4f} (old baseline val_f1={BASELINE['val_f1']})",
          flush=True)
    return m


if __name__ == "__main__":
    evaluate_segment(sys.argv[1])
```

- [ ] **Step 4: Verify the S3 lister runs (dry listing)**

Run: `uv run python -m repro.sota_data.discover`
Expected: prints top-level bucket entries (e.g. dataset folders). If it errors on network/S3, report the error — the bucket path may differ; adjust the prefix argument. This confirms anonymous access works before the operational run.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/discover.py repro/sota_data/fetch.py repro/sota_data/evaluate.py
git commit --no-verify -m "feat(sota): S3 discover/fetch + detector evaluate tooling (operational)"
```

---

### Task 3: Operational run — fetch, convert, evaluate one SOTA Scroll-1 segment (manual)

**Files:** none (operational); produces `reports/detector/sota_scroll1_measurement.{md,json}` + `local_data/sota_scroll1/<seg>/`.

Run by a human. This is the definition-of-done.

- [ ] **Step 1: Discover a target segment.**

Run `uv run python -m repro.sota_data.discover` and drill into prefixes (pass a prefix arg to descend, e.g. `uv run python -m repro.sota_data.discover <prefix>`) until you find a **Scroll 1 / PHerc Paris 4** segment whose dir contains both a `layers/` (or `surface_volume/`) and an `*inklabels*` file. Record its bucket-relative prefix `<S3_SEG>` and a short id `<SEG>`.
**Contingency:** if no Scroll-1 segment has a released ink label, stop and report it — switch to a qualitative comparison against a released ink *prediction* (overlay in the report), or pick another read scroll. Do NOT invent a val_f1 without ground truth.

- [ ] **Step 2: Fetch it.**

Run: `uv run python -m repro.sota_data.fetch "<S3_SEG>" "local_data/sota_scroll1_raw/<SEG>"`
Expected: the segment's `layers/` + label (+ mask) land under `local_data/sota_scroll1_raw/<SEG>`. GB-scale.

- [ ] **Step 3: Convert to detector format.**

Run:
```bash
uv run python -c "
from repro.sota_data.convert import convert_surface_volume
print(convert_surface_volume('local_data/sota_scroll1_raw/<SEG>', '<SEG>', 'local_data/sota_scroll1'))
"
```
Expected: `local_data/sota_scroll1/<SEG>/layers/17..42.tif` + `<SEG>_inklabels.png` + `<SEG>_mask.png`. If it raises a mismatch `ValueError`, the label isn't aligned to this volume — pick a different segment (do not force it).

- [ ] **Step 4: Pause the loop and evaluate.**

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4
uv run python -m repro.sota_data.evaluate "<SEG>"
```
Expected: prints `SOTA <SEG>: val_f1=... lift=...` and writes `reports/detector/sota_scroll1_measurement.{md,json}`. **Read the result:** does the SOTA data lift `val_f1`/`ap_prevalence_lift` above the old-data baseline (0.222 / 1.29)? That number — either direction — is the deliverable.

- [ ] **Step 5: Commit the report and resume the loop.**

```bash
git add reports/detector/sota_scroll1_measurement.md reports/detector/sota_scroll1_measurement.json
git commit --no-verify -m "chore(sota): detector on SOTA Scroll-1 data vs old-data baseline"
bash start.sh
```

- [ ] **Step 6: Interpretation (a finding either way).** If SOTA data lifts the numbers, that validates "rebase on better data" and motivates Phase 2 (retrain on SOTA segments). If it does not, record it honestly — the detector's ceiling may be the recipe/window, not the data. Do NOT re-tune blindly.

---

## Self-Review

**Spec coverage:**
- Discover a labeled Scroll-1 segment → Task 2 `discover.py` + Task 3 Step 1. ✓
- Stream it → Task 2 `fetch.py` + Task 3 Step 2. ✓
- Convert to detector format (26 layers, label, mask, loud guards) → Task 1. ✓
- Evaluate with A's metric contract vs old baseline → Task 2 `evaluate.py` + Task 3 Step 4. ✓
- Evaluate-only (Phase 1); retrain deferred → respected; noted in Task 3 Step 6. ✓
- Contingency: no released ink label → Task 3 Step 1. ✓
- Testing: convert unit-tested (synthetic); discover/fetch/evaluate operational → Task 1 tests + Task 2 Step 4. ✓
- Isolation + loop-pause for GPU eval → Task 3 Step 4/5 + Global Constraints. ✓

**Placeholder scan:** `<S3_SEG>`/`<SEG>` in Task 3 are operational inputs resolved at run time from Task 3 Step 1's discovery output (not code placeholders). No TBD/TODO; all code steps complete; commands have expected output. ✓

**Type consistency:** `convert_surface_volume(src_dir, seg_id, out_root, ...)` (Task 1) is called identically in Task 3 Step 3; the output layout (`layers/{17..42}.tif`, `<seg>_inklabels.png`, `<seg>_mask.png`) matches `detector.data.read_image_mask` and is asserted in Task 1's `test_convert_output_loads_via_detector`; `evaluate.evaluate_segment(seg_id, ...)` consumes that layout via `DetectorConfig(data_root=...)`. Baseline values match A's committed measurement. ✓

**Known follow-ups (out of scope):** Phase 2 retrain on SOTA segments; PHerc 1667 / PHerc 139; Volume-Cartographer unwrapping.
