# GP-Winner Phase 4a — Adopt + Scale, Establish Prize-Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score the working TimeSformer detector through the real prize topology gates (Step A, cheap), then train a scaled production detector and score it the same way (Step B, gated on A).

**Architecture:** A reusable prize-gate wrapper that binarizes a prediction PNG over a threshold sweep and calls the villa topology metrics (reused, not reimplemented) to report the topology-optimal `centerline_dice` + its `skel_dist` + pixel-AUC. Step A points it at the existing Phase-2 prediction; Step B trains a 3-segment TimeSformer (copy of the proven trainer) and evaluates it.

**Tech Stack:** villa topology metrics at `villa/segmentation/evaluation/metrics/` (run in the loop's `.venv`, with `wandb.init(mode="disabled")`), the vendored `villa/ink-detection/` TimeSformer pipeline + `.venv-gp`, `repro/gp_winner/render_eval.py`.

**Spec:** `docs/superpowers/specs/2026-06-22-gp-winner-phase4-adopt-scale-design.md`

## Global Constraints

- **Never edit vendored `villa/ink-detection/` files** (copy + edit) and **never install into the loop's `.venv`**; train/infer with `villa/ink-detection/.venv-gp`. The loop's `.venv` is used **read-only** for the prize-gate metrics.
- **Never edit** `run_autoresearch_loop.py` / `scripts/training/train.py`.
- **Pause the loop before any GPU step** (`.loop_paused` + kill `run_autoresearch_loop` then `train.py --config`), restart `bash start.sh` after. (Step A needs no GPU.)
- `$ROOT = /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`. Run training/inference from CWD `$ROOT/villa/ink-detection/`.
- Prize metrics: `villa/segmentation/evaluation` on `sys.path`; `wandb.init(mode="disabled")` BEFORE calling `skeleton_distance_length.compute` (it calls `wandb.log`). Metric inputs are **binary `(1,H,W)`** arrays. `centerline_dice.compute(label, pred) -> {"centerline_dice": float, ...}`; `skeleton_distance_length.compute(label, pred) -> float`.
- Topology metrics are **threshold-fragile** → sweep thresholds, report at the topology-optimal point (max centerline_dice), and report that threshold.
- Checkpoints / converted data / runs are gitignored (existing entries cover `outputs/`, `models/`, `train_scrolls/`, `repro/gp_winner/runs/`).

---

## Task 1: Prize-gate wrapper (TDD)

**Files:**
- Create: `repro/gp_winner/prize_gate_eval.py`
- Test: `tests/test_prize_gate_eval.py`

**Interfaces:**
- Produces: `load_pred_label_mask(pred_png, label_png, mask_png=None) -> (prob[H,W] float in [0,1], label[H,W] {0,1}, mask[H,W] bool)` (crops all to the common H×W; mask defaults to all-True); `sweep_topology(prob, label, mask, thresholds) -> dict` returning `{"best_threshold", "centerline_dice", "skel_dist", "pixel_auc", "per_threshold": [...]}` using the villa metrics on `(1,H,W)` binary arrays restricted to mask.

- [ ] **Step 1: Write the failing test** (synthetic, no villa import — monkeypatch the metric fns so the test is hermetic/fast)

```python
# tests/test_prize_gate_eval.py
import numpy as np
from PIL import Image

import repro.gp_winner.prize_gate_eval as pge


def test_load_crops_to_common_shape(tmp_path):
    # pred bigger than label (winner inference pads); loader crops to common HxW
    Image.fromarray(np.full((40, 40), 200, np.uint8)).save(tmp_path / "pred.png")
    ink = np.zeros((36, 32), np.uint8); ink[10:20, 5:15] = 255
    Image.fromarray(ink).save(tmp_path / "ink.png")
    prob, label, mask = pge.load_pred_label_mask(str(tmp_path / "pred.png"), str(tmp_path / "ink.png"))
    assert prob.shape == label.shape == mask.shape == (36, 32)
    assert 0.0 <= prob.max() <= 1.0
    assert set(np.unique(label)).issubset({0, 1})


def test_sweep_picks_topology_optimal(monkeypatch):
    # fake metrics: centerline_dice peaks at threshold ~0.5; skel_dist returns a constant
    def fake_cd(label, pred, **k):
        frac = float(pred.mean())  # higher coverage -> our fake peaks near frac 0.25
        return {"centerline_dice": 1.0 - abs(frac - 0.25)}
    def fake_sk(label, pred, **k):
        return 7.0
    monkeypatch.setattr(pge, "_centerline_dice", fake_cd)
    monkeypatch.setattr(pge, "_skel_dist", fake_sk)

    rng = np.random.default_rng(0)
    prob = rng.random((1, 64, 64)).astype(np.float32)[0]
    label = (rng.random((64, 64)) > 0.7).astype(np.uint8)
    mask = np.ones((64, 64), bool)
    out = pge.sweep_topology(prob, label, mask, thresholds=[0.1, 0.5, 0.9])
    assert "best_threshold" in out and "centerline_dice" in out and "skel_dist" in out
    assert out["skel_dist"] == 7.0
    assert out["best_threshold"] in (0.1, 0.5, 0.9)
    assert 0.0 <= out["pixel_auc"] <= 1.0
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError: repro.gp_winner.prize_gate_eval`)

Run: `cd $ROOT && PYTHONPATH=. .venv/bin/python -m pytest tests/test_prize_gate_eval.py -v`

- [ ] **Step 3: Write `prize_gate_eval.py`**

```python
# repro/gp_winner/prize_gate_eval.py
"""Score a prediction PNG through the villa prize topology gates over a threshold sweep,
reporting the topology-optimal centerline_dice + its skel_dist + pixel-AUC. Reuses the
villa metric functions (not reimplemented)."""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# --- villa metrics (loop .venv); wandb must be init'd disabled before skel_dist ---
_VILLA = os.path.join(os.path.dirname(__file__), "..", "..", "villa", "segmentation", "evaluation")
if os.path.isdir(_VILLA) and _VILLA not in sys.path:
    sys.path.append(os.path.abspath(_VILLA))


def _ensure_wandb_disabled():
    os.environ.setdefault("WANDB_MODE", "disabled")
    import wandb

    if wandb.run is None:
        wandb.init(mode="disabled")


def _centerline_dice(label, pred, **k):
    from metrics.centerline_dice import compute

    return compute(label, pred, **k)


def _skel_dist(label, pred, **k):
    from metrics.skeleton_distance_length import compute

    return compute(label, pred, **k)


def load_pred_label_mask(pred_png, label_png, mask_png=None):
    """Load a probability prediction PNG (0..255 -> [0,1]), an inklabels PNG (>127 -> {0,1}),
    and an optional papyrus mask; crop all to the common H x W."""
    prob = np.array(Image.open(pred_png).convert("L")).astype(np.float32) / 255.0
    label = (np.array(Image.open(label_png).convert("L")) > 127).astype(np.uint8)
    if mask_png and os.path.exists(mask_png):
        mask = np.array(Image.open(mask_png).convert("L")) > 127
    else:
        mask = np.ones(label.shape, bool)
    h = min(prob.shape[0], label.shape[0], mask.shape[0])
    w = min(prob.shape[1], label.shape[1], mask.shape[1])
    return prob[:h, :w], label[:h, :w], mask[:h, :w]


def sweep_topology(prob, label, mask, thresholds):
    """For each threshold, binarize prob*mask and compute villa centerline_dice + skel_dist
    on (1,H,W) arrays; return the topology-optimal (max centerline_dice) result + pixel-AUC."""
    from sklearn.metrics import roc_auc_score

    m = mask.astype(bool)
    y = label * m
    sel = m.ravel()
    auc = (
        float(roc_auc_score(label.ravel()[sel], prob.ravel()[sel]))
        if label[m].min() != label[m].max()
        else 0.5
    )
    lab3 = y[None].astype(np.uint8)
    per = []
    best = None
    for t in thresholds:
        pred_bin = ((prob >= t) & m).astype(np.uint8)[None]
        cd = _centerline_dice(lab3, pred_bin)
        cdv = float(cd["centerline_dice"]) if isinstance(cd, dict) else float(cd)
        sk = float(_skel_dist(lab3, pred_bin))
        row = {"threshold": float(t), "centerline_dice": cdv, "skel_dist": sk}
        per.append(row)
        if best is None or cdv > best["centerline_dice"]:
            best = row
    return {
        "best_threshold": best["threshold"],
        "centerline_dice": best["centerline_dice"],
        "skel_dist": best["skel_dist"],
        "pixel_auc": auc,
        "per_threshold": per,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--mask", default="")
    ap.add_argument("--out", required=True, help="JSON scorecard path")
    ap.add_argument("--thresholds", default="0.2,0.3,0.4,0.5,0.6,0.7")
    args = ap.parse_args()
    _ensure_wandb_disabled()
    prob, label, mask = load_pred_label_mask(args.pred, args.label, args.mask or None)
    ths = [float(x) for x in args.thresholds.split(",")]
    res = sweep_topology(prob, label, mask, ths)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(
        f"pixel_auc={res['pixel_auc']:.4f} centerline_dice={res['centerline_dice']:.4f} "
        f"skel_dist={res['skel_dist']:.3f} @thr={res['best_threshold']}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it — PASS (2 passed)**

Run: `cd $ROOT && PYTHONPATH=. .venv/bin/python -m pytest tests/test_prize_gate_eval.py -v`

- [ ] **Step 5: Commit**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/prize_gate_eval.py tests/test_prize_gate_eval.py
git commit --no-verify -m "feat(repro): prize-gate wrapper (villa topology metrics over a threshold sweep)"
```

---

## Task 2: Step A — score the existing Phase-2 TimeSformer through the gates

**Files:** writes `reports/gp_winner_repro/phase4a_stepA_scorecard.json`

- [ ] **Step 1: Run the wrapper on the Phase-2 held-out prediction (no GPU)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p reports/gp_winner_repro
PYTHONPATH=. WANDB_MODE=disabled .venv/bin/python repro/gp_winner/prize_gate_eval.py \
  --pred  repro/gp_winner/runs/phase2/20230820203112_prediction_rotated_0_layer_17.png \
  --label villa/ink-detection/all_labels/20230820203112_inklabels.png \
  --out   reports/gp_winner_repro/phase4a_stepA_scorecard.json
cat reports/gp_winner_repro/phase4a_stepA_scorecard.json
```
Expected: prints `pixel_auc≈0.905 centerline_dice=<x> skel_dist=<y> @thr=<t>` and writes the JSON. (If the metric import fails, confirm `villa/segmentation/evaluation/metrics/` exists and rerun; the wrapper appends it to `sys.path`.)

- [ ] **Step 2: Compare to resenc_unet's gates + decide**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
echo "resenc_unet (our loop, latest): skel_dist ~19-21, centerline_dice ~0.34 (val AUC ~0.51-0.60)"
echo "TimeSformer (AUC 0.905) Step A:"; cat reports/gp_winner_repro/phase4a_stepA_scorecard.json
```
Interpret:
- **TimeSformer skel_dist clearly lower / centerline_dice clearly higher than resenc_unet** → a working detector materially improves the gates → proceed to Step B (Task 3).
- **Gates barely move despite AUC 0.905** → the prize bottleneck is post-processing/topology, not detection. **Record this as the Step-A verdict** (Task 5) and treat Step B as optional/secondary (the scaled model won't fix a post-processing gap). Note it and consult before the long run.

- [ ] **Step 3: Commit the Step-A scorecard**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add reports/gp_winner_repro/phase4a_stepA_scorecard.json
git commit --no-verify -m "docs(repro): Phase 4a Step A - working TimeSformer prize-gate scorecard"
```

---

## Task 3: Step B — scaled production trainer

**Files:** Create `repro/gp_winner/train_scaled.py`

- [ ] **Step 1: Copy the proven trainer**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
cp repro/gp_winner/train_subset.py repro/gp_winner/train_scaled.py
```

- [ ] **Step 2: Locate the fragment-list anchors**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
grep -nE "fragment_ids=\[|\"20231210121321\"|\"20230702185753\"|\"20230820203112\"|^fragments = \[|epochs = 12" repro/gp_winner/train_scaled.py
```
Expected: the `get_train_valid_dataset` default list (Phase-2's 3 ids), the module-level `fragments = ["20230820203112"]`, and `epochs = 12`.

- [ ] **Step 3: Apply the edits** (exact string replacements in `repro/gp_winner/train_scaled.py`)

1. Train+val list → 3 train + held-out (add `20230826170124`; keep `20230820203112` as the held-out fold member so the loader reads it):
   - old:
     ```
     def get_train_valid_dataset(
         fragment_ids=[
             "20231210121321",
             "20230702185753",
             "20230820203112",
         ],
     ):
     ```
   - new:
     ```
     def get_train_valid_dataset(
         fragment_ids=[
             "20231210121321",
             "20230702185753",
             "20230826170124",
             "20230820203112",
         ],
     ):
     ```
   (`20230820203112` is the held-out fold via the `fragments=[...]` line below — the loader still needs it in this list to build the val set.)
2. Held-out fold unchanged (already `20230820203112`); confirm it is:
   - keep: `fragments = ["20230820203112"]`
3. Epochs (modest scale-up):
   - old: `epochs = 12`
   - new: `epochs = 15`

- [ ] **Step 4: Confirm parse + edits**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
villa/ink-detection/.venv-gp/bin/python -c "import ast; ast.parse(open('repro/gp_winner/train_scaled.py').read()); print('parses OK')"
grep -cE "20230826170124|epochs = 15" repro/gp_winner/train_scaled.py  # expect 2
grep -cE "train_batch_size = 32|CSVLogger|devices=1|max_epochs=CFG.epochs" repro/gp_winner/train_scaled.py  # proven settings intact
```
Expected: `parses OK`; the new segment + epochs present; proven settings carried over.

- [ ] **Step 5: Commit**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/train_scaled.py
git commit --no-verify -m "feat(repro): scaled production TimeSformer trainer (3 seg, 15 epochs)"
```

---

## Task 4: Step B — train (GPU, loop paused)

**Files:** writes checkpoints under `villa/ink-detection/outputs/.../vesuvius-models/` (gitignored)

- [ ] **Step 1: Pause the loop, free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 2
ps -eo pid,cmd | grep -E "train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~0 MiB
```

- [ ] **Step 2: Train (background; watch RAM during the 4-segment read)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
export WANDB_MODE=disabled
.venv-gp/bin/python ../../repro/gp_winner/train_scaled.py > ../../repro/gp_winner/runs/train_scaled.log 2>&1 &
echo "train PID $!"
```
Watch `free -g` during the read (4 segments — 3 train + 1 holdout — is the most we've loaded; if avail approaches 0 and the process is OOM-killed during "reading", drop `20230826170124` from the train list in `train_scaled.py` to fall back to the known-good 2-train config and re-run).

- [ ] **Step 3: Confirm learning + checkpoints**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CSV=$(find villa/ink-detection/models -name metrics.csv -path "*20230820203112*" 2>/dev/null | tail -1)
.venv/bin/python -c "
import csv
rows=list(csv.DictReader(open('$CSV')))
seen={}
for r in rows:
    e=r.get('epoch')
    for c in ('train/total_loss_epoch','val/total_loss_epoch'):
        if r.get(c): seen.setdefault(e,{})[c]=r[c]
for e in sorted(seen,key=lambda x:int(x)):
    d=seen[e]; print('epoch',e,'train',round(float(d.get('train/total_loss_epoch',0)),4),'val',round(float(d.get('val/total_loss_epoch',0)),4))
"
ls villa/ink-detection/outputs/vesuvius/pretraining_all/vesuvius-models/timesformer_wild16_20230820203112_fr*epoch*.ckpt 2>/dev/null | wc -l
```
Expected: per-epoch loss rows (train falling); one `.ckpt` per epoch (up to 15).

Deliverable: a scaled production checkpoint set.

---

## Task 5: Step B eval + verdict + record + restart loop

**Files:** Modify `FINDINGS.md`; create report image + scorecard under `reports/gp_winner_repro/`

- [ ] **Step 1: Held-out inference on the latest checkpoint**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
CKPT=$(find outputs -name "timesformer_wild16_20230820203112_fr*epoch*.ckpt" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
echo "checkpoint: $CKPT"
export WANDB_MODE=disabled
.venv-gp/bin/python inference_timesformer.py \
  --model_path "$CKPT" --segment_path "$PWD/train_scrolls" --segment_id 20230820203112 \
  --out_path "$PWD/../../repro/gp_winner/runs/phase4b" \
  > ../../repro/gp_winner/runs/infer_phase4b.log 2>&1
ls -la ../../repro/gp_winner/runs/phase4b/
```
Expected: a `20230820203112_prediction_*.png`.

- [ ] **Step 2: Pixel-AUC + thumbnail + prize-gate scorecard**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PRED=$(ls repro/gp_winner/runs/phase4b/*20230820203112*prediction*.png 2>/dev/null | head -1)
.venv/bin/python repro/gp_winner/render_eval.py --pred "$PRED" \
  --out reports/gp_winner_repro/phase4b_heldout_thumb.png --scale 6 \
  --label villa/ink-detection/all_labels/20230820203112_inklabels.png
PYTHONPATH=. WANDB_MODE=disabled .venv/bin/python repro/gp_winner/prize_gate_eval.py \
  --pred "$PRED" --label villa/ink-detection/all_labels/20230820203112_inklabels.png \
  --out reports/gp_winner_repro/phase4b_scorecard.json
cat reports/gp_winner_repro/phase4b_scorecard.json
```
Expected: thumbnail + a JSON scorecard (pixel-AUC ≥ the Phase-2 0.905 ideally; centerline_dice/skel_dist at the topology-optimal threshold).

- [ ] **Step 3: Record + commit**

Add a `FINDINGS.md` bullet covering Step A (working-model gates vs resenc_unet) and Step B (scaled AUC + scorecard + legibility), with the prize-readiness verdict. Write memory `gp-winner-phase4-result.md` (type project) linking `[[gp-winner-phase3-result]]` and `[[model-barely-discriminates-ink]]`. Add the thumbnail + both scorecards under `reports/gp_winner_repro/`.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add FINDINGS.md reports/gp_winner_repro/phase4b_heldout_thumb.png reports/gp_winner_repro/phase4b_scorecard.json
git commit --no-verify -m "docs(findings): GP-winner Phase 4a - prize-readiness scorecard of the working stack"
```

- [ ] **Step 4: Restart the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 3
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | head -1 || echo "WARN: loop not running"
```

Deliverable: a prize-readiness scorecard for the working stack (Step A + Step B) with verdict; the loop running again.

---

## Self-Review

**Spec coverage:**
- Prize-gate wrapper reusing villa metrics over a threshold sweep, topology-optimal report → Task 1 (TDD). ✓
- Step A: score existing Phase-2 checkpoint, compare to resenc_unet, decide → Task 2. ✓
- Step B: scaled trainer (3 train + 1 holdout, 15 epochs), copy of proven trainer → Task 3 + Task 4. ✓
- Step B eval: pixel-AUC + prize gates + legible render → Task 5 Steps 1–2. ✓
- Isolation (`.venv-gp` for GPU, loop `.venv` read-only for metrics, vendored untouched, loop paused) → Global Constraints + tasks. ✓
- wandb-disabled requirement for skel_dist, 3D `(1,H,W)` binary inputs, threshold-fragility sweep → Task 1 wrapper + Global Constraints. ✓
- Record FINDINGS + memory + scorecards → Task 5 Step 3. ✓
- "Working model still fails gates" = informative outcome, gate Step B → Task 2 Step 2. ✓
- Phase 4c (submission packaging) out of scope → not planned here. ✓

**Placeholder scan:** none — wrapper code is complete with a hermetic monkeypatched test; the metric contract (`compute(label,pred)`, `(1,H,W)`, wandb-disabled) is verified and baked in; the only judgment step (Step A decide) has explicit thresholds.

**Type/name consistency:** `load_pred_label_mask` / `sweep_topology` signatures and return keys (`best_threshold`, `centerline_dice`, `skel_dist`, `pixel_auc`, `per_threshold`) match between test, implementation, and `main`; the monkeypatch targets (`pge._centerline_dice`, `pge._skel_dist`) match the module's function names; the held-out id `20230820203112`, the checkpoint glob `timesformer_wild16_20230820203112_fr*epoch*.ckpt`, paths (`reports/gp_winner_repro/`, `repro/gp_winner/runs/phase4b/`), and `render_eval.py --pred/--out/--label` are consistent across tasks.

**Known risks:** (1) `skeleton_distance_length.compute` calls `wandb.log` → wrapper calls `wandb.init(mode="disabled")` first (verified). (2) metrics need `(1,H,W)` not 2D (verified). (3) Step B 4-segment read may OOM the 31 GB box → Task 4 Step 2 fall-back to 2 train segments. (4) skel_dist/centerline_dice may be near-flat even at AUC 0.905 (threshold-fragile) → Task 2 Step 2 treats that as a real verdict, not a failure.
