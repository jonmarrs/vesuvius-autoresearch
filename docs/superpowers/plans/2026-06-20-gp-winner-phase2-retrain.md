# GP-Winner Phase 2 — Tractable-Subset TimeSformer Retrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train the winner's TimeSformer recipe on 5 real labeled Scroll-1 segments (1 held out) and show it learns ink (held-out val discrimination rises above chance) — proving we can reproduce the *training* in our environment, not just the inference.

**Architecture:** An isolated **copy** of the vendored `train_timesformer_og.py` with a small CFG/driver diff (subset segments, single-GPU, 4090-fit batch, fewer epochs), run in the Phase-1 `.venv-gp`. Vendored code stays pristine; the loop's `.venv` is never touched.

**Tech Stack:** the vendored `villa/ink-detection/` pipeline, `timesformer-pytorch`, `pytorch-lightning==2.0.9` (torch 2.12 cu130, `cuda True`), `rclone` (data), the Phase-1 `inference_timesformer.py` + `repro/gp_winner/render_eval.py` for eval.

**Spec:** `docs/superpowers/specs/2026-06-20-gp-winner-phase2-retrain-design.md`

## Global Constraints

- **Never edit vendored `villa/ink-detection/` files** (copy + edit instead) and **never install into / use the loop's `.venv`** — use `villa/ink-detection/.venv-gp`.
- **Never edit** `run_autoresearch_loop.py` / `scripts/training/train.py`.
- **Pause the loop before any GPU step** (`.loop_paused` + kill `run_autoresearch_loop` then `train.py --config`), restart with `bash start.sh` after.
- Segment data, labels, env, checkpoints are **gitignored** (already covered by `villa/ink-detection/train_scrolls/`, `.venv-gp/`, `repro/gp_winner/runs/`); add `villa/ink-detection/models/` to gitignore in Task 0.
- Public data creds: `dl.ash2txt.org` basic-auth `registeredusers:only`. Repo root = `$ROOT` = `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`. rclone at `~/bin/rclone`.
- **Run all training/inference from CWD `$ROOT/villa/ink-detection/`** (the scripts use relative paths `train_scrolls/`, `all_labels/`, `./models`).
- Segments — train: `20231210121321` (already present), `20230702185753`, `20230826170124`, `20230903193206`, `20231005123336`; held-out valid: `20230820203112`. Layers 17–42 only.

---

## Task 0: Gitignore models dir + preconditions

**Files:** Modify `.gitignore`

- [ ] **Step 1: Verify Phase-1 assets still present**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python -c "import torch; print('cuda', torch.cuda.is_available())"
ls timesformer_weights.ckpt && ls train_scrolls/20231210121321/layers/17.tif
ls all_labels/20230820203112_inklabels.png all_labels/20231210121321_inklabels.png
df -h "$PWD" | tail -1   # expect >120GB free
```
Expected: `cuda True`; weights + the already-downloaded segment + the needed labels exist; ample disk.

- [ ] **Step 2: Gitignore the training output dir + commit**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
printf '%s\n' 'villa/ink-detection/models/' 'villa/ink-detection/gp_weights_dl/' >> .gitignore
git add .gitignore
git commit -m "chore(repro): gitignore GP-winner Phase 2 training outputs"
```

---

## Task 1: Download the 5 additional segments

**Files:** Create `villa/ink-detection/train_scrolls/<id>/` for the 5 segments (gitignored)

- [ ] **Step 1: Fetch layers 17–42 + mask per-file (robust, no self-kill)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
export USERNAME=registeredusers PASSWORD=only
URL="http://$USERNAME:$PASSWORD@dl.ash2txt.org/"
BASE=":http:/full-scrolls/Scroll1/PHercParis4.volpkg/paths"
for SEG in 20230702185753 20230826170124 20230903193206 20231005123336 20230820203112; do
  ~/bin/rclone copyto "$BASE/$SEG/${SEG}_mask.png" "./train_scrolls/$SEG/${SEG}_mask.png" --http-url "$URL" 2>>/tmp/gp_dl2.log
  for i in $(seq 17 42); do
    L=$(printf "%02d" $i)
    ~/bin/rclone copyto "$BASE/$SEG/layers/$L.tif" "./train_scrolls/$SEG/layers/$L.tif" --http-url "$URL" --multi-thread-streams=8 2>>/tmp/gp_dl2.log
  done
done
echo "DOWNLOAD DONE"
```
(Long-running ~tens of minutes; run in the background.)

- [ ] **Step 2: Verify all 6 segments have layers 17–42 + mask**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
RANGE="{17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42}"
for SEG in 20231210121321 20230702185753 20230826170124 20230903193206 20231005123336 20230820203112; do
  N=$(eval ls train_scrolls/$SEG/layers/$RANGE.tif 2>/dev/null | wc -l)
  echo "$SEG: 17-42=$N/26 mask=$(test -f train_scrolls/$SEG/${SEG}_mask.png && echo yes)"
done
```
Expected: every segment `26/26` and `mask=yes`. (If a `.tif` 404s, that segment may use a different path — substitute another labeled∩downloadable id from the spec's intersection.)

No commit (gitignored). Deliverable: 6 segments on disk in the expected layout.

---

## Task 2: Inject ink labels

**Files:** writes `train_scrolls/<id>/<id>_inklabels.png` (gitignored)

- [ ] **Step 1: Run only `prepare_data()` (NOT prepare.py's `__main__`)**

`prepare.py`'s `__main__` also calls `run_sanity_checks()`, which asserts a fixed full
segment set (incl. `20231022170901`) we don't have — it would crash. Call only the
copy function:

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python -c "import prepare; prepare.prepare_data()"
```

- [ ] **Step 2: Verify each of the 6 segments now has an inklabels.png**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
for SEG in 20231210121321 20230702185753 20230826170124 20230903193206 20231005123336 20230820203112; do
  echo "$SEG inklabels: $(test -f train_scrolls/$SEG/${SEG}_inklabels.png && echo yes || echo MISSING)"
done
```
Expected: all `yes`. (`prepare_data()` copies `all_labels/<id>_inklabels.png` → `train_scrolls/<id>/<id>_inklabels.png`.)

No commit. Deliverable: labels injected for all 6 segments.

---

## Task 3: Create `train_subset.py` (isolated copy + edits) + VRAM smoke

**Files:** Create `repro/gp_winner/train_subset.py`

- [ ] **Step 1: Copy the vendored trainer**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
cp villa/ink-detection/train_timesformer_og.py repro/gp_winner/train_subset.py
```

- [ ] **Step 2: Apply the CFG + driver edits** (exact string replacements in `repro/gp_winner/train_subset.py`)

1. Batch (4090-fit):
   - old: `    train_batch_size = 196 # 32`
   - new: `    train_batch_size = 32`
2. Epochs:
   - old: `    epochs = 30 # 30`
   - new: `    epochs = 12`
3. Training segment set (the `get_train_valid_dataset` default list) — replace the entire default list with our 6:
   - old: `def get_train_valid_dataset(fragment_ids=['20231210121321','20231022170901','20231106155351','20231005123336','20230820203112','20230826170124','20230702185753','20230522215721','20230531193658','20230903193206','20230902141231','20231007101615','20230929220926','recto','20231016151000','20231012184423','20231031143850']):`
   - new: `def get_train_valid_dataset(fragment_ids=['20231210121321','20230702185753','20230826170124','20230903193206','20231005123336','20230820203112']):`
4. Validation fold (held-out):
   - old: `fragments=['20231210121321']`
   - new: `fragments=['20230820203112']`
5. Honor CFG.epochs (the Trainer hardcodes 20):
   - old: `        max_epochs=20,`
   - new: `        max_epochs=CFG.epochs,`
6. Single-GPU (avoid DDP on one 4090):
   - old: `        devices=-1,`
   - new: `        devices=1,`
   - old: `        strategy='ddp_find_unused_parameters_true',`
   - new: `        strategy='auto',`
7. Swap WandbLogger → CSVLogger (no wandb dependency; per-epoch metrics to CSV):
   - old: `    wandb_logger = WandbLogger(project="vesivus",name=run_slug+f'timesformer_big6_finetune')`
   - new: `    from pytorch_lightning.loggers import CSVLogger\n    wandb_logger = CSVLogger(save_dir="./models", name=run_slug)`
   - old: `    wandb_logger.watch(model, log="all", log_freq=100)`
   - new: `    # CSVLogger has no .watch()`
   - old: `    wandb.finish()`
   - new: `    # CSVLogger: nothing to finish`

- [ ] **Step 3: VRAM smoke — confirm batch 32 fits (≤120 s)**

Temporarily verify a forward/backward fits before the full run. Run a 1-batch check using the model class from the copy:

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python - <<'PY'
import torch
from timesformer_pytorch import TimeSformer
m = TimeSformer(dim=512, image_size=64, patch_size=16, num_frames=26, num_classes=16*16,
                depth=8, heads=6, dim_head=64, attn_dropout=0.1, ff_dropout=0.1).cuda()
opt = torch.optim.AdamW(m.parameters(), lr=3e-5)
torch.cuda.reset_peak_memory_stats()
x = torch.rand(32, 26, 1, 64, 64).cuda()  # [B, frames, channels, H, W]
with torch.cuda.amp.autocast(dtype=torch.float16):
    out = m(x); loss = out.float().mean()
loss.backward(); opt.step()
print("OK batch=32 peakGPU=%.1fGB" % (torch.cuda.max_memory_allocated()/1e9))
PY
```
Expected: `OK batch=32 peakGPU=<~Ngb>` under 24 GB. If it OOMs, set `train_batch_size = 16` (then 8) in `train_subset.py` and re-run this smoke until it fits. (The TimeSformer ctor args mirror the model in the copy; if they differ, read `RegressionPLModel`/`TimeSformer(...)` in `train_subset.py` and match them.)

- [ ] **Step 4: Commit the trainer copy**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/train_subset.py
git commit -m "feat(repro): GP-winner subset trainer (5 seg/1 holdout, 4090-fit, single-GPU)"
```

Deliverable: a runnable, VRAM-safe subset trainer.

---

## Task 4: Train (GPU, loop paused)

**Files:** writes checkpoints under `villa/ink-detection/models/` (gitignored)

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

- [ ] **Step 2: Run the subset training (background; ~hours)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
export WANDB_MODE=disabled
.venv-gp/bin/python ../../repro/gp_winner/train_subset.py \
  > ../../repro/gp_winner/runs/train_subset.log 2>&1 &
echo "train PID $!"
```
Watch `train_subset.log` for dataset reads (`reading <id>`), then per-epoch loss. If it
crashes on import/log/checkpoint, capture the error and fix in `train_subset.py` (the
copy only).

- [ ] **Step 3: Confirm it is learning (per-epoch loss falling) and checkpoints appear**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
grep -iE "epoch|loss" ../../repro/gp_winner/runs/train_subset.log | tail -10
ls -t models/**/timesformer_wild16_20230820203112_fr*epoch*.ckpt 2>/dev/null | head
find models -name "*.ckpt" -newermt "-6 hours" | tail -5
```
Expected: total_loss trends down across epochs; one `.ckpt` per epoch in `models/`.

Deliverable: trained per-epoch checkpoints.

---

## Task 5: Held-out eval, verdict, record, restart loop

**Files:** Modify `FINDINGS.md`; create report image under `reports/gp_winner_repro/`

- [ ] **Step 1: Pick the latest checkpoint and run held-out inference**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
CKPT=$(find models -name "timesformer_wild16_20230820203112_fr*epoch*.ckpt" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
echo "using checkpoint: $CKPT"
export WANDB_MODE=disabled
.venv-gp/bin/python inference_timesformer.py \
  --model_path "$CKPT" \
  --segment_path "$PWD/train_scrolls" \
  --segment_id 20230820203112 \
  --out_path "$PWD/../../repro/gp_winner/runs/phase2" \
  > ../../repro/gp_winner/runs/infer_phase2.log 2>&1
ls -la ../../repro/gp_winner/runs/phase2/
```
Expected: a `20230820203112_prediction_*.png` written. If the checkpoint won't load into
`inference_timesformer.py` (key mismatch), capture the error — our copy uses the same
`RegressionPLModel`/`TimeSformer` as the inference script, so a mismatch is diagnostic.

- [ ] **Step 2: Compute held-out pixel-AUC + thumbnail**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p reports/gp_winner_repro
PRED=$(ls repro/gp_winner/runs/phase2/*20230820203112*prediction*.png 2>/dev/null | head -1)
.venv/bin/python repro/gp_winner/render_eval.py \
  --pred "$PRED" --out "reports/gp_winner_repro/phase2_heldout_20230820203112_thumb.png" --scale 6 \
  --label "villa/ink-detection/all_labels/20230820203112_inklabels.png"
```
Expected: prints `pixel_auc=<x>` and writes the thumbnail. (Uses the loop's `.venv`
read-only for PIL/numpy/sklearn — no install.)

- [ ] **Step 3: Judge the verdict**

Combine the per-epoch loss trend (Task 4 Step 3), the held-out `pixel_auc`, and the
thumbnail:
- **Pass (primary):** held-out `pixel_auc` clearly above 0.5 and the loss fell across
  epochs → the recipe learns ink in our environment on real data.
- **Stretch:** `pixel_auc` ≳0.7 and partially legible thumbnail.
- **Fail:** `pixel_auc` ~0.5 / flat loss → a reproduction/compute problem (record it as
  such; do not proceed to Phase 3 until understood).

- [ ] **Step 4: Record + commit**

Add a `FINDINGS.md` bullet (per-epoch trend, held-out AUC, verdict) and write memory
file `gp-winner-phase2-result.md` (type project), linking `[[gp-winner-replication-result]]`.
Add the thumbnail under `reports/gp_winner_repro/`.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add FINDINGS.md reports/gp_winner_repro/phase2_heldout_20230820203112_thumb.png
git commit -m "docs(findings): GP-winner Phase 2 subset-retrain verdict"
```

- [ ] **Step 5: Restart the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 3
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | head -1 || echo "WARN: loop not running"
```

Deliverable: an evidence-backed Pass/Stretch/Fail verdict; the loop running again.

---

## Self-Review

**Spec coverage:**
- Tractable subset (5 train + 1 holdout, named segments) → Task 1 + Task 3 Step 2 (edits 3–4). ✓
- Layers 17–42 only → Task 1; trainer reads `start_idx=17 end_idx=43`. ✓
- Disk ~108 GB fits → Task 0 Step 1 check + Task 1. ✓
- `batch=32` (VRAM-verified), `epochs=12` → Task 3 (edits 1–2, smoke Step 3). ✓
- Isolated copy, vendored untouched, `.venv-gp` → Task 3 Step 1 + Global Constraints. ✓
- `prepare.py` label injection (data-only, skip sanity asserts) → Task 2. ✓
- Eval via Phase-1 inference + `render_eval.py` on held-out → Task 5 Steps 1–2. ✓
- Success = rising-above-chance primary, ≳0.7+legible stretch → Task 5 Step 3. ✓
- Loop paused for GPU, restarted → Task 4 Step 1 + Task 5 Step 5. ✓
- Record FINDINGS + memory + report → Task 5 Step 4. ✓
- Phase 3 (our data) out of scope → not planned here. ✓

**Placeholder scan:** none — every edit is an exact old→new string; every command is concrete. The VRAM-smoke model ctor is flagged to be matched against the copy if the args differ.

**Type/name consistency:** segment ids, the held-out `20230820203112`, paths
(`train_scrolls/`, `models/`, `repro/gp_winner/runs/phase2/`, `reports/gp_winner_repro/`),
the checkpoint glob `timesformer_wild16_20230820203112_fr*epoch*.ckpt` (matches the
`ModelCheckpoint(filename=...)` in `train_subset.py`), and `render_eval.py --pred/--out/--label`
(matches Phase-1's helper) are consistent across tasks.

**Known risks:** (1) the TimeSformer ctor in the Step-3 smoke must match `train_subset.py`'s
actual `TimeSformer(...)`/`RegressionPLModel` — read and match if it errors. (2) a segment
layer `.tif` may 404 → substitute another labeled∩downloadable id. (3) batch 32 may OOM →
drop to 16/8 via the smoke. (4) CSVLogger metric keys differ from wandb — rely on the
held-out inference AUC as the primary measurement, not log parsing.
