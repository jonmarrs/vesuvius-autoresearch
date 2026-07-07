# Ground-Truth Fine-Tuning (POC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fine-tune the best distilled detector (arm C) on ground-truth labels registered onto SOTA geometry for 2 Scroll-1 segments, then measure on the held-out `20231210121321` GT — a before/after test of whether ground-truth supervision beats distillation-from-canon (arm C's held-out 0.558).

**Architecture:** A new `gt_register.py` registers a hand label onto a SOTA surface region via the `original.obj` vertex-texture bridge at the fixed `rowHv_colu` convention (teacher-independent), gating each region on residual + text-line periodicity, and writes detector-format GT fragments. A `gt_finetune.py` loads arm C via `DetectorModel.load_from_checkpoint` and fine-tunes on the passing GT fragments at low LR, reusing `detector.data`/`detector.model` without editing the detector package. Scoring reuses the committed held-out registration.

**Tech Stack:** scipy (`cKDTree`), numpy, opencv, tifffile, s3fs (anon); the `vesuvius_autoresearch.detector` subpackage (data/model/metrics) reused, not modified; pytorch_lightning.

## Global Constraints

- **Ground-truth honesty:** every GT-training label comes from a registration that PASSED the teacher-free gate (residual ≤ 12 old-scan voxels AND periodicity ≥ 0.6) for its own region; failing regions are dropped, recorded, never trained on.
- **Framing:** the result is *before/after fine-tuning arm C* (init = the distilled model); no from-scratch claim; the 2-segment data-thinness caveat is stated. Held-out score reuses the committed slice-6 registration of `20231210121321` (in `local_data/sota_registration/heldout/registered_label_l2region.png`).
- **Fixed convention:** the `original.obj` vt orientation is `rowHv_colu` (row = H − v, col = u) — the export-pipeline constant established in slice 5; used directly, teacher-independent (no per-region enrichment pick).
- **No detector-package edits.** Fine-tune init: `DetectorModel.load_from_checkpoint(ckpt, cfg=cfg, pred_shape=(1,1), weights_only=False)`; `configure_optimizers` rebuilds `AdamW(lr=cfg.lr)`, so a low-LR cfg flows through.
- Isolation: code in `repro/sota_data/` + `tests/`; data in `local_data/sota_gt/` (git-ignored); models in `models/detector_gt_finetune/` (git-ignored); reports in `reports/detector/`. Anonymous S3. Loop paused for GPU. No AI-authorship markers.
- Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## Training data (verified on disk / bucket)

Train regions (SOTA surface layers already prepped by Phase-2 distill under
`local_data/sota_distill/<seg>_y<y>_x<x>/`): `20230702185753` @ (4000,2500) & (7000,4000);
`20231005123336` @ (4000,2500) & (7000,4000). Hand labels:
`villa/ink-detection/train_scrolls/<seg>/<seg>_inklabels.png`. Held-out test: `20231210121321`
GT already registered (slice 6). arm C ckpt: `models/detector_xscroll_c/detector_epoch=11.ckpt`.

## File Structure

- Create `repro/sota_data/gt_register.py` — `parse_obj_vt`, `register_label_to_region`, `gt_prep_fragment`.
- Create `repro/sota_data/gt_finetune.py` — operational: `prep`, `finetune`, `score`.
- Tests: `tests/test_sota_gt_register.py`.

---

### Task 1: `gt_register.py` — per-region GT registration + fragment writer

**Files:**
- Create: `repro/sota_data/gt_register.py`
- Test: `tests/test_sota_gt_register.py`

**Interfaces:**
- Consumes: `register.read_tifxyz`, `register.warp_via_field`, `register.label_line_periodicity`; `distill_run` (`_fs`, `_scroll_prefix`, `extract_region`); `qualitative.write_fragment`.
- Produces:
  - `parse_obj_vt(path) -> (v: np.ndarray[N,3], vt: np.ndarray[N,2])` — parses `v`/`vt` lines (1:1 positional); `ValueError` on count mismatch.
  - `register_label_to_region(region_xyz, obj_v, obj_vt, old_label, size) -> (reg_label[size,size] uint8, residual: float, periodicity: float)` — NN-bridge region 3D → nearest obj vertex → vt (row=H−v, col=u) → sample `old_label`; residual = median NN dist; periodicity = `label_line_periodicity(reg_label)`.
  - `gt_prep_fragment(seg, y0, x0, size, out_root, max_residual=12.0, min_periodicity=0.6) -> dict` — fetches obj + on-7.91um tifxyz for `seg`, extracts the region, registers the hand label, gates; on pass writes a detector-format GT fragment (SOTA layers from `local_data/sota_distill/<seg>_y<y0>_x<x0>` if present else via `extract_region`, GT label, mask) to `out_root/<seg>_y<y0>_x<x0>/` and returns `{"passed": True, "frag_id":..., "residual":..., "periodicity":...}`; on fail returns `{"passed": False, ...}` and writes nothing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_gt_register.py
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.gt_register import (parse_obj_vt, register_label_to_region)


def test_parse_obj_vt_positional(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nvt 10 20\nv 4 5 6\nvt 30 40\nf 1/1 2/2\n")
    v, vt = parse_obj_vt(p)
    assert v.shape == (2, 3) and vt.shape == (2, 2)
    assert np.allclose(v[1], [4, 5, 6]) and np.allclose(vt[0], [10, 20])


def test_parse_obj_vt_mismatch_raises(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nv 4 5 6\nvt 10 20\n")
    with pytest.raises(ValueError, match="mismatch"):
        parse_obj_vt(p)


def test_register_label_to_region_recovers_block():
    # synthetic: region grid maps 1:1 to obj vertices; label is a block.
    h = w = 40
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    region_xyz = np.stack([xx, yy, np.zeros_like(xx)], axis=-1)  # (h,w,3)
    obj_v = region_xyz.reshape(-1, 3)                             # vertices = region pts
    H = W = 40
    # vt with row=H-v,col=u convention: choose vt so that vertex at (r,c) -> label (r,c)
    # label pixel (row,col) = (H - vt_v, vt_u). Want that to equal (r,c) for grid pixel r,c
    # so vt_u = c, vt_v = H - r.
    vt = np.stack([xx.reshape(-1), (H - yy).reshape(-1)], axis=1)  # (u, v)
    old_label = np.zeros((H, W), np.uint8)
    old_label[10:25, 12:30] = 255
    reg, residual, period = register_label_to_region(region_xyz, obj_v, vt, old_label, size=40)
    assert residual < 1e-3
    inter = np.logical_and(reg > 127, old_label > 127).sum()
    union = np.logical_or(reg > 127, old_label > 127).sum()
    assert inter / union > 0.9
    assert 0.0 <= period <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_gt_register.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'repro.sota_data.gt_register'`

- [ ] **Step 3: Write the implementation**

```python
# repro/sota_data/gt_register.py
"""Register a 2023 hand ink-label onto a SOTA surface region via the segment's original.obj
vertex texture coordinates (fixed rowHv_colu convention -- the export-pipeline constant from
slice 5, teacher-independent), gate on residual + text-line periodicity, and write a
detector-format GROUND-TRUTH training fragment. Unlike distillation, the label here is human
ground truth, not a teacher prediction."""
import glob
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.register import (label_line_periodicity, read_tifxyz, warp_via_field)
from repro.sota_data.qualitative import write_fragment

LEVEL0_SHAPE = (50600, 36400)
MESH_NEW_TMPL = "{seg}-on-20230205180739-7.91um.tifxyz"


def parse_obj_vt(path):
    vs, vts = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
    v = np.asarray(vs, np.float32)
    vt = np.asarray(vts, np.float32)
    if len(v) != len(vt):
        raise ValueError(f"obj v/vt count mismatch: {len(v)} vs {len(vt)}")
    return v, vt


def register_label_to_region(region_xyz, obj_v, obj_vt, old_label, size):
    """NN-bridge each region 3D point to the nearest obj vertex, read its vt (row=H-v,col=u),
    sample old_label. Returns (reg_label[size,size], median residual, periodicity)."""
    region_xyz = np.asarray(region_xyz, np.float32)
    rh, rw = region_xyz.shape[:2]
    pts = region_xyz.reshape(-1, 3)
    valid = (np.isfinite(pts).all(1) & ~(np.abs(pts + 1) < 1e-6).all(1)
             & ~(np.abs(pts) < 1e-9).all(1))
    d, idx = cKDTree(obj_v).query(pts[valid], k=1)
    uv = obj_vt[idx]
    H = old_label.shape[0]
    rc = np.stack([H - uv[:, 1], uv[:, 0]], axis=1)  # rowHv_colu
    field = np.full((rh, rw, 2), np.nan, np.float32)
    field.reshape(-1, 2)[valid] = rc
    reg = warp_via_field(old_label, field, (size, size), interpolation=cv2.INTER_NEAREST)
    residual = float(np.median(d)) if len(d) else float("inf")
    return reg, residual, label_line_periodicity(reg)


def _region_in_mesh(new_xyz, y0, x0, size):
    mh, mw = new_xyz.shape[:2]
    sy, sx = mh / (LEVEL0_SHAPE[0] / 4), mw / (LEVEL0_SHAPE[1] / 4)
    ys, xs = int(round(y0 * sy)), int(round(x0 * sx))
    ye, xe = int(round((y0 + size) * sy)), int(round((x0 + size) * sx))
    return new_xyz[ys:ye, xs:xe]


def _fetch(seg, reg_dir):
    os.makedirs(reg_dir, exist_ok=True)
    fs = dr._fs()
    pref = dr._scroll_prefix("scroll1", seg, "mesh")
    obj = os.path.join(reg_dir, f"{seg}_original.obj")
    if not os.path.exists(obj):
        fs.get(f"{pref}/intermediate/{seg}_original.obj", obj)
    mesh = os.path.join(reg_dir, MESH_NEW_TMPL.format(seg=seg))
    if not os.path.exists(mesh):
        fs.get(f"{pref}/{MESH_NEW_TMPL.format(seg=seg)}", mesh, recursive=True)
    return obj, mesh


def gt_prep_fragment(seg, y0, x0, size, out_root, max_residual=12.0, min_periodicity=0.6):
    reg_dir = os.path.join("local_data/sota_gt_meshes", seg)
    obj_path, mesh_path = _fetch(seg, reg_dir)
    obj_v, obj_vt = parse_obj_vt(obj_path)
    new_xyz = read_tifxyz(mesh_path)
    region_xyz = _region_in_mesh(new_xyz, y0, x0, size)
    old_label = cv2.imread(
        f"villa/ink-detection/train_scrolls/{seg}/{seg}_inklabels.png", 0)
    if old_label is None:
        raise ValueError(f"{seg}: hand label unreadable")
    reg_label, residual, periodicity = register_label_to_region(
        region_xyz, obj_v, obj_vt, old_label, size)
    frag_id = f"{seg}_y{y0}_x{x0}"
    passed = residual <= max_residual and periodicity >= min_periodicity
    info = {"frag_id": frag_id, "residual": residual, "periodicity": periodicity,
            "gt_ink_fraction": float((reg_label > 127).mean()), "passed": bool(passed)}
    if not passed:
        print(f"DROP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f}",
              flush=True)
        return info
    # SOTA surface layers: reuse the Phase-2 distill fragment if present, else extract.
    src_layers = os.path.join("local_data/sota_distill", frag_id, "layers")
    out_seg = os.path.join(out_root, frag_id)
    if os.path.isdir(src_layers):
        region_stack = np.stack([
            cv2.imread(os.path.join(src_layers, f"{i:02d}.tif"), 0) for i in range(17, 43)],
            axis=0)
    else:
        region_stack, _, _ = dr.extract_region(seg, y0, x0, scroll_key="scroll1")
    write_fragment(region_stack, out_root, frag_id)   # layers + zero label + mask
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_inklabels.png"), reg_label)  # GT label
    print(f"KEEP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f} "
          f"gt_ink={info['gt_ink_fraction']:.3f}", flush=True)
    return info
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_gt_register.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/gt_register.py tests/test_sota_gt_register.py
git commit --no-verify -m "feat(sota): GT registration onto SOTA regions (fixed-convention obj bridge, gated) + fragment writer"
```

---

### Task 2: `gt_finetune.py` — fine-tune arm C on GT + score held-out (operational)

**Files:**
- Create: `repro/sota_data/gt_finetune.py`

**Interfaces:**
- Consumes: `gt_register.gt_prep_fragment`; `detector.config.DetectorConfig`, `detector.data.build_datasets`, `detector.model.DetectorModel`, `detector.metrics.segmentation_metrics`; `distill_run._measure`/`COLS`.
- Produces: subcommands `prep` (register the 4 training regions → GT fragments), `finetune` (load arm C, low-LR fit on the passing GT fragments), `score` (fine-tuned vs the committed held-out `20231210121321` GT; before/after report). Constants at top.

Operational (network + GPU) — verified by the usage check; code complete.

- [ ] **Step 1: Write the orchestrator**

```python
# repro/sota_data/gt_finetune.py
"""Ground-truth fine-tuning POC (operational): register human labels for 2 Scroll-1 segments
onto SOTA geometry, fine-tune the best distilled model (arm C) on them, and measure on the
held-out 20231210121321 GT -- a before/after test of whether ground-truth supervision reads
held-out ink where distillation-from-canon (arm C, 0.558) could not."""
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.gt_register import gt_prep_fragment

TRAIN_REGIONS = [("20230702185753", 4000, 2500), ("20230702185753", 7000, 4000),
                 ("20231005123336", 4000, 2500), ("20231005123336", 7000, 4000)]
SIZE = 4096
GT_ROOT = "local_data/sota_gt"
MODEL_DIR = "models/detector_gt_finetune"
ARM_C_CKPT = "models/detector_xscroll_c/detector_epoch=11.ckpt"
HELDOUT_LABEL = "local_data/sota_registration/heldout/registered_label_l2region.png"
HELDOUT_FRAG_ROOT = "local_data/sota_distill"
HELDOUT_FRAG_ID = "20231210121321_y4000_x2500"
PREP_JSON = "reports/detector/gt_finetune_prep.json"
REPORT_MD = "reports/detector/gt_finetune_heldout.md"
REPORT_JSON = "reports/detector/gt_finetune_heldout.json"
FT_LR = 8e-6
FT_EPOCHS = 6


def cmd_prep():
    os.makedirs("reports/detector", exist_ok=True)
    infos = [gt_prep_fragment(seg, y0, x0, SIZE, GT_ROOT) for (seg, y0, x0) in TRAIN_REGIONS]
    kept = [i["frag_id"] for i in infos if i["passed"]]
    with open(PREP_JSON, "w") as f:
        json.dump({"regions": infos, "kept": kept}, f, indent=2)
    print(f"kept {len(kept)}/{len(infos)} GT training regions: {kept}", flush=True)
    if not kept:
        raise ValueError("no GT training region passed the alignment gate")


def cmd_finetune():
    import pytorch_lightning as pl
    import torch
    from pytorch_lightning.callbacks import ModelCheckpoint
    from pytorch_lightning.loggers import CSVLogger
    from torch.utils.data import DataLoader
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import build_datasets
    from vesuvius_autoresearch.detector.model import DetectorModel
    with open(PREP_JSON) as f:
        kept = json.load(f)["kept"]
    if not kept:
        raise ValueError(f"{PREP_JSON} has no kept regions; run prep")
    cfg = DetectorConfig(data_root=GT_ROOT, model_dir=MODEL_DIR, lr=FT_LR, epochs=FT_EPOCHS,
                         train_fragment_ids=kept, valid_fragment_id=kept[0])
    cfg.validate_window()
    pl.seed_everything(cfg.seed, workers=True)
    torch.set_float32_matmul_precision("medium")
    os.makedirs(MODEL_DIR, exist_ok=True)
    train_ds, valid_ds, _, pred_shape = build_datasets(cfg)
    tl = DataLoader(train_ds, batch_size=cfg.train_batch_size, shuffle=True,
                    num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    vl = DataLoader(valid_ds, batch_size=cfg.train_batch_size, shuffle=False,
                    num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    # init from arm C (distilled); configure_optimizers rebuilds AdamW(lr=cfg.lr=FT_LR)
    model = DetectorModel.load_from_checkpoint(ARM_C_CKPT, cfg=cfg, pred_shape=pred_shape,
                                               weights_only=False)
    ckpt_cb = ModelCheckpoint(filename="ft_{epoch}", dirpath=MODEL_DIR,
                              monitor="train/total_loss", mode="min", save_top_k=-1)
    trainer = pl.Trainer(max_epochs=cfg.epochs, accelerator="auto", devices=1,
                         logger=CSVLogger(save_dir=MODEL_DIR, name="logs"),
                         precision="16-mixed" if torch.cuda.is_available() else "32-true",
                         gradient_clip_val=1.0, gradient_clip_algorithm="norm",
                         callbacks=[ckpt_cb], enable_progress_bar=False)
    trainer.fit(model, train_dataloaders=tl, val_dataloaders=vl)
    print("finetune done:", ckpt_cb.best_model_path, flush=True)


def _score_ckpt(ckpt):
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics
    prob = dr._measure(ckpt, HELDOUT_FRAG_ID, data_root=HELDOUT_FRAG_ROOT)[1]
    gt = (cv2.imread(HELDOUT_LABEL, 0) > 127).astype(np.uint8)
    h, w = gt.shape
    m = segmentation_metrics(prob[:h, :w], gt, np.ones((h, w), bool))
    m.pop("metrics_by_threshold", None)
    return m


def cmd_score():
    if not os.path.exists(HELDOUT_LABEL):
        raise ValueError(f"{HELDOUT_LABEL} missing; the slice-6 held-out registration is "
                         "required (run register_run warp_obj heldout first)")
    fts = sorted(glob.glob(os.path.join(MODEL_DIR, "ft_epoch=*.ckpt")),
                 key=lambda p: int(p.split("epoch=")[1].split(".")[0]))
    if not fts:
        raise ValueError(f"no fine-tuned checkpoints in {MODEL_DIR}; run finetune")
    # final epoch (no selection on the held-out test set)
    ft_ckpt = fts[-1]
    before = _score_ckpt(ARM_C_CKPT)
    after = _score_ckpt(ft_ckpt)
    cols = dr.COLS

    def row(name, m):
        return f"| {name} | " + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in cols) + " |"

    with open(PREP_JSON) as f:
        prep = json.load(f)
    lines = ["# Ground-truth fine-tuning vs distillation (held-out 20231210121321 GT)", "",
             "**Before/after fine-tuning the best distilled model (arm C) on human "
             "ground-truth labels** registered onto SOTA geometry for 2 Scroll-1 segments "
             f"({len(prep['kept'])}/4 regions passed the teacher-free alignment gate). All "
             "rows scored against the held-out registered GACK ground truth of a segment NO "
             "model trained on. POC: only 2 training segments -- a near-chance 'after' is "
             "confounded by data thinness, a clear lift is not.", "",
             f"Fine-tune: init arm C `{os.path.basename(ARM_C_CKPT)}`, lr {FT_LR}, "
             f"{FT_EPOCHS} epochs, final epoch `{os.path.basename(ft_ckpt)}`.", "",
             "| model (vs held-out GT) | " + " | ".join(cols) + " |",
             "|---|" + "|".join(["---"] * len(cols)) + "|",
             row("arm C (distilled, before)", before),
             row("arm C + GT fine-tune (after)", after)]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"before_armC": before, "after_gt_finetune": after,
                   "finetune_ckpt": os.path.basename(ft_ckpt), "prep": prep},
                  f, indent=2, default=float)
    print(f"BEFORE arm C roc_auc={before.get('roc_auc', float('nan')):.4f}  "
          f"AFTER gt-finetune roc_auc={after.get('roc_auc', float('nan')):.4f}", flush=True)


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "finetune": cmd_finetune, "score": cmd_score}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.gt_finetune {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
```

- [ ] **Step 2: Fix the placeholder typo, then verify import + usage**

The report string contains a deliberate typo marker `GACK` — replace it with `registered` before running. Then:
Run: `CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.gt_finetune 2>&1 | tail -1`
Expected: `usage: python -m repro.sota_data.gt_finetune {prep|finetune|score}` (non-zero exit, no import errors). Also run `grep -n GACK repro/sota_data/gt_finetune.py` and confirm it returns nothing.

- [ ] **Step 3: Commit**

```bash
git add repro/sota_data/gt_finetune.py
git commit --no-verify -m "feat(sota): GT fine-tune runner (prep/finetune/score) -- arm C before/after on held-out GT"
```

---

### Task 3: Operational run — GT fine-tune and before/after (manual, network + GPU)

**Files:** none (operational); produces `reports/detector/gt_finetune_heldout.{md,json}` + `gt_finetune_prep.json`, or an honest "too few regions registered" stop.

- [ ] **Step 1: Prep GT training fragments (network + CPU).**

Run: `uv run python -m repro.sota_data.gt_finetune prep`
Expected: per region a `KEEP`/`DROP` line with residual + periodicity, then `kept N/4 GT training regions`. **Check:** at least 2 regions kept (else the fine-tune is too thin — stop and report the alignment finding). Residuals should be ~single-digit old-scan voxels like slice 5/6; periodicity ≥ 0.6.

- [ ] **Step 2: Pause the loop; fine-tune (~1-3 h GPU, few epochs).**

```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 5
nohup uv run python -m repro.sota_data.gt_finetune finetune > reports/detector/gt_finetune_train.log 2>&1 &
```
Expected: 6 epochs over the kept GT fragments, `ft_epoch=*.ckpt` in `models/detector_gt_finetune/`.

- [ ] **Step 3: Score the before/after.**

Run: `uv run python -m repro.sota_data.gt_finetune score`
Expected: `BEFORE arm C roc_auc=0.5576  AFTER gt-finetune roc_auc=X`; writes the before/after report. **Read the verdict:** AFTER ≫ 0.558 ⇒ ground-truth supervision reads held-out ink where distillation could not (the positive); AFTER ≈ 0.558 ⇒ no gain at this data scale (honest, data-thin caveat).

- [ ] **Step 4: Commit; resume the loop.**

```bash
git add reports/detector/gt_finetune_heldout.md reports/detector/gt_finetune_heldout.json reports/detector/gt_finetune_prep.json
git commit --no-verify -m "chore(sota): GT fine-tune before/after on held-out GT (segment 20231210121321)"
bash start.sh
```
Record the verdict honestly either way; no blind re-tuning.

---

## Self-Review

**Spec coverage:** GT registration onto SOTA regions with teacher-free gate + GT-label fragment writer (T1) ✓; fine-tune arm C on passing GT fragments, low LR, no detector edits, load-from-checkpoint init (T2 `cmd_finetune`) ✓; held-out score reuses the committed slice-6 registration, final-epoch (no held-out selection), before/after vs arm C (T2 `cmd_score`) ✓; per-region gate drops failures + records stats (T1 `gt_prep_fragment`, T2 `cmd_prep`) ✓; POC / data-thinness caveat in the report (T2 `cmd_score` lines) ✓; ≥2-regions-or-stop (T3 S1) ✓.

**Placeholder scan:** the `GACK` marker in T2 is an intentional forced-fix (Step 2 replaces it + greps) so the report copy is verified; not a latent TBD. All code complete; commands have expected output. ✓

**Type consistency:** `register_label_to_region(region_xyz, obj_v, obj_vt, old_label, size) -> (reg_label, residual, periodicity)` used identically in T1 tests and `gt_prep_fragment`; `gt_prep_fragment(...) -> dict{frag_id,residual,periodicity,gt_ink_fraction,passed}` consumed by T2 `cmd_prep`; `DetectorModel.load_from_checkpoint(ckpt, cfg=, pred_shape=, weights_only=False)` matches infer.py's working pattern and `configure_optimizers` reads `cfg.lr` (verified); `dr._measure(ckpt, fid, data_root=)` returns `(metrics, prob)` — `cmd_score` uses `[1]` (prob) and re-scores vs the GT label; `dr.COLS` consumed for the table. ✓

**Known follow-ups:** from-scratch GT A/B if fine-tune promising; more segments as the bucket grows; July filing refresh.
