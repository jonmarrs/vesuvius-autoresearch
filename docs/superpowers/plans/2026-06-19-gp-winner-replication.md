# GP-Winner Ink-Detection Replication (Phase 1, inference-only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the published Grand-Prize TimeSformer + its weights on canonical Scroll-1 segments through the vendored `villa/ink-detection/inference_timesformer.py`, and determine whether it renders legible ink in this environment (Outcome A) or not (Outcome B).

**Architecture:** Use the vendored winner code **unmodified** in a **dedicated, isolated venv** (the loop's `.venv` is never touched). Download two demo segments + the published checkpoint, run inference, render/score the output, record the verdict.

**Tech Stack:** Python (separate venv), `timesformer-pytorch`, `pytorch-lightning==2.0.9`, CUDA torch, `rclone` (segment download), `gdown` (weights), the vendored `villa/ink-detection/` pipeline.

**Spec:** `docs/superpowers/specs/2026-06-19-gp-winner-replication-design.md`

## Global Constraints

- **Never modify or install into the loop's `.venv`** (`/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.venv`) — the running autoresearch loop depends on it. All deps go in a dedicated env.
- **Never edit** `run_autoresearch_loop.py`, `scripts/training/train.py`, or any vendored file under `villa/ink-detection/` (run it as-is).
- **Pause the loop before any GPU step** (set `.loop_paused`, kill `run_autoresearch_loop` then `train.py --config` PIDs), and **restart it** (`bash start.sh`) after.
- Segment data + weights are **gitignored** (large); only docs/findings/helper scripts are committed.
- Public data creds: `dl.ash2txt.org` basic-auth `registeredusers:only`. Weights: the repo's public Google Drive folder `1rn3GMOvtJRMBHOxVhWFVSY6IVI6xUnYp`.
- Repo root: `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch` (referred to as `$ROOT`).

---

## Task 0: Preconditions & gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Verify the vendored pipeline + disk + GPU are present**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
ls villa/ink-detection/inference_timesformer.py villa/ink-detection/download.sh villa/ink-detection/requirements.txt
df -h . | tail -1                       # expect >100GB free
nvidia-smi --query-gpu=memory.total --format=csv,noheader
command -v uv && command -v rclone; command -v gdown || echo "gdown missing (installed in Task 1)"
```
Expected: all three files exist; ample disk; a GPU is listed; `uv` present. `rclone`/`gdown` may be missing (installed next).

- [ ] **Step 2: Gitignore the data + env dirs**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
printf '%s\n' \
  'villa/ink-detection/train_scrolls/' \
  'villa/ink-detection/eval_scrolls/' \
  'villa/ink-detection/.venv-gp/' \
  'villa/ink-detection/timesformer_weights.ckpt' \
  'repro/gp_winner/runs/' >> .gitignore
git add .gitignore
git commit -m "chore(repro): gitignore GP-winner replication data/env/outputs"
```

---

## Task 1: Dedicated isolated environment

**Files:**
- Create: `villa/ink-detection/.venv-gp/` (env; gitignored)

- [ ] **Step 1: Create the separate venv and install requirements**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
uv venv .venv-gp --python 3.10
uv pip install --python .venv-gp/bin/python -r requirements.txt
uv pip install --python .venv-gp/bin/python gdown
```

- [ ] **Step 2: Install a CUDA-matched torch and verify GPU**

The loop's env uses CUDA 12.x (cu128). Install a matching torch build, then verify:

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
uv pip install --python .venv-gp/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cu121
.venv-gp/bin/python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
```
Expected: `cuda True`. If `False`, try the `cu124`/`cu128` index URL to match the driver before proceeding (do not continue until `cuda True`).

- [ ] **Step 3: Verify the winner's imports resolve**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python -c "from timesformer_pytorch import TimeSformer; import pytorch_lightning, segmentation_models_pytorch, albumentations; print('GP imports OK')"
```
Expected: `GP imports OK`. If a dep fails to import, pin/resolve it (e.g. `numpy==1.26.4` is already in requirements) before continuing.

No commit (env is gitignored). Deliverable: a working isolated env with `cuda True`.

---

## Task 2: Fetch the published checkpoint

**Files:**
- Create: `villa/ink-detection/timesformer_weights.ckpt` (gitignored)

- [ ] **Step 1: Download the weights from the public Drive folder**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/gdown --folder "https://drive.google.com/drive/folders/1rn3GMOvtJRMBHOxVhWFVSY6IVI6xUnYp" -O ./gp_weights_dl
find ./gp_weights_dl -iname "*.ckpt" -exec ls -la {} \;
# place the canonical checkpoint at the expected name:
cp "$(find ./gp_weights_dl -iname '*timesformer*.ckpt' | head -1)" timesformer_weights.ckpt 2>/dev/null || \
cp "$(find ./gp_weights_dl -iname '*.ckpt' | head -1)" timesformer_weights.ckpt
ls -la timesformer_weights.ckpt
```
Expected: a `.ckpt` file (hundreds of MB) at `timesformer_weights.ckpt`. If `gdown --folder` is rate-limited, download the single file by its Drive id with `.venv-gp/bin/gdown <file_id> -O timesformer_weights.ckpt`.

- [ ] **Step 2: Verify the checkpoint loads as a state-dict**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python -c "
import torch
ck = torch.load('timesformer_weights.ckpt', map_location='cpu', weights_only=False)
sd = ck.get('state_dict', ck) if isinstance(ck, dict) else ck
print('keys:', len(sd)); print('sample:', list(sd.keys())[:3])
"
```
Expected: a non-zero key count and TimeSformer-like tensor names. If it errors, the wrong Drive file was fetched — re-fetch the canonical `timesformer_weights.ckpt`.

No commit (weights gitignored). Deliverable: a loadable checkpoint.

---

## Task 3: Download the two canonical demo segments

**Files:**
- Create: `villa/ink-detection/train_scrolls/20231210121321/` and `.../20231221180251/` (gitignored)

- [ ] **Step 1: Install rclone if missing**

```bash
command -v rclone || (curl -fsSL https://rclone.org/install.sh | sudo bash) || \
  echo "If sudo unavailable, install rclone to ~/bin and add to PATH"
rclone version | head -1
```

- [ ] **Step 2: Fetch only the two demo segments (mask + layers)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
export USERNAME=registeredusers PASSWORD=only
for SEG in 20231210121321 20231221180251; do
  rclone copy ":http:/full-scrolls/Scroll1/PHercParis4.volpkg/paths/$SEG/${SEG}_mask.png" "./train_scrolls/$SEG/" \
    --http-url "http://$USERNAME:$PASSWORD@dl.ash2txt.org/" --progress --transfers=8
  rclone copy ":http:/full-scrolls/Scroll1/PHercParis4.volpkg/paths/$SEG/layers/" "./train_scrolls/$SEG/layers/" \
    --http-url "http://$USERNAME:$PASSWORD@dl.ash2txt.org/" --progress --multi-thread-streams=8 --transfers=8
done
```
(Long-running; run in the background. Tens of GB total.)

- [ ] **Step 3: Verify segment layout matches what inference expects**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
for SEG in 20231210121321 20231221180251; do
  echo "$SEG: layers=$(ls train_scrolls/$SEG/layers/*.tif 2>/dev/null | wc -l) mask=$(test -f train_scrolls/$SEG/${SEG}_mask.png && echo yes)"
done
```
Expected: each shows a layer stack (tens of `.tif`, typically ~65) and `mask=yes`. `inference_timesformer.py` uses `start_idx=17`, `size=64` depth, so it needs at least layers `17..17+26`.

No commit (data gitignored). Deliverable: two segments in the expected on-disk layout.

---

## Task 4: Run inference with the published weights (GPU)

**Files:**
- Create: `repro/gp_winner/runs/` outputs (gitignored)

- [ ] **Step 1: Pause the autoresearch loop and free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 2
ps -eo pid,cmd | grep -E "train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~0 MiB
```

- [ ] **Step 2: Run the vendored inference on both demo segments**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
mkdir -p "$PWD/../../repro/gp_winner/runs"
.venv-gp/bin/python inference_timesformer.py \
  --model_path timesformer_weights.ckpt \
  --segment_path "$PWD/train_scrolls" \
  --segment_id 20231210121321 20231221180251 \
  --out_path "$PWD/../../repro/gp_winner/runs" \
  2>&1 | tee "$PWD/../../repro/gp_winner/runs/infer.log" | tail -20
```
Expected: the run loads the checkpoint, processes tiles (progress bars), and writes a prediction image per segment under `repro/gp_winner/runs/`. If the checkpoint fails to load into the model, capture the exact error (this is diagnostic for Outcome B) before adjusting.

- [ ] **Step 3: Confirm prediction outputs exist**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
ls -la repro/gp_winner/runs/
```
Expected: at least one prediction image (e.g. a PNG/`.png` per segment). Note the exact output filenames for Task 5.

Deliverable: raw prediction outputs for the two segments.

---

## Task 5: Render, judge legibility, record verdict, restart loop

**Files:**
- Create: `repro/gp_winner/render_eval.py`
- Modify: `FINDINGS.md`
- Create: report image(s) under `reports/gp_winner_repro/`

- [ ] **Step 1: Write a small render/thumbnail helper**

```python
# repro/gp_winner/render_eval.py
"""Downscale a GP-winner inference prediction to an inspectable thumbnail, and
(optionally) compute pixel-AUC against an inklabels.png if one is provided."""
import argparse
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="prediction PNG from inference")
    ap.add_argument("--out", required=True, help="thumbnail PNG path")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--label", default="", help="optional inklabels.png for AUC")
    args = ap.parse_args()

    p = np.array(Image.open(args.pred).convert("L")).astype(np.float32)
    h, w = p.shape
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    Image.fromarray(p.astype(np.uint8)).resize((w // args.scale, h // args.scale)).save(args.out)
    print(f"thumbnail {args.out} ({w // args.scale}x{h // args.scale})")

    if args.label and os.path.exists(args.label):
        from sklearn.metrics import roc_auc_score

        y = (np.array(Image.open(args.label).convert("L")) > 127).astype(int)
        m = y.shape == p.shape
        if m and y.min() != y.max():
            print(f"pixel_auc={roc_auc_score(y.ravel(), (p / 255.0).ravel()):.4f}")
        else:
            print("label/pred shape mismatch or single-class; skipping AUC")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Render thumbnails of the predictions**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p reports/gp_winner_repro
for SEG in 20231210121321 20231221180251; do
  PRED=$(ls repro/gp_winner/runs/*${SEG}* 2>/dev/null | grep -iE '\.png$' | head -1)
  test -n "$PRED" && .venv/bin/python repro/gp_winner/render_eval.py \
    --pred "$PRED" --out "reports/gp_winner_repro/${SEG}_pred_thumb.png"
done
ls -la reports/gp_winner_repro/
```
(Uses the loop's `.venv` only for PIL/numpy/sklearn — read-only, no install.)

- [ ] **Step 3: Judge legibility (the verdict)**

Open each `reports/gp_winner_repro/<seg>_pred_thumb.png`. Decide:
- **Outcome A:** legible Greek letterforms (matching the winners' public reveal of these segments) → the published pipeline reproduces here; our chance-result is isolated to our own data/labels/preprocessing.
- **Outcome B:** noise, *with* the checkpoint having loaded cleanly in Task 4 → an environment/plumbing/data bug in running even the published model.

- [ ] **Step 4: Record the verdict**

Add a `FINDINGS.md` bullet stating Outcome A or B with the evidence (legibility, any AUC, the checkpoint-load result). Write a memory file `gp-winner-replication-result.md` (type project) summarizing the verdict and linking `[[ink-detection-reproduction-result]]` and `[[model-barely-discriminates-ink]]`. Add the legible thumbnail(s) under `reports/gp_winner_repro/`.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/render_eval.py reports/gp_winner_repro/ FINDINGS.md
git commit -m "docs(findings): GP-winner replication Phase 1 verdict (inference-only)"
```

- [ ] **Step 5: Restart the autoresearch loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 3
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | head -1 || echo "WARN: loop not running"
```

Deliverable: a written, evidence-backed Outcome A/B verdict; the loop running again.

---

## Self-Review

**Spec coverage:**
- Dedicated isolated env (protect loop `.venv`) → Task 1. ✓
- Published checkpoint fetch + load verification → Task 2. ✓
- Canonical segment download (demo segments `20231210121321`/`20231221180251`) via rclone + public creds → Task 3. ✓
- Unmodified `inference_timesformer.py` run, GPU, loop paused → Task 4. ✓
- Render + legibility verdict (Outcome A/B) + optional AUC → Task 5. ✓
- Record in FINDINGS + memory + report image → Task 5 Step 4. ✓
- Loop restart → Task 5 Step 5. ✓
- Phase 2 (retrain) is out of scope (separate spec) → not planned here, per spec. ✓

**Placeholder scan:** none — every step has concrete commands; the only judgment step (legibility) is inherent to the success criterion and spelled out as Outcome A vs B.

**Type/name consistency:** segment ids (`20231210121321`, `20231221180251`), paths (`train_scrolls/`, `repro/gp_winner/runs/`, `reports/gp_winner_repro/`), env (`.venv-gp`), and the weights filename (`timesformer_weights.ckpt`) are used identically across Tasks 1–5. `render_eval.py` flags (`--pred/--out/--scale/--label`) match their Task 5 Step 2 invocation.

**Known risk:** if `inference_timesformer.py` writes outputs to a default location rather than honoring `--out_path`, Task 4 Step 3 / Task 5 Step 2 globs must be adjusted to the actual output dir (check `infer.log`).
