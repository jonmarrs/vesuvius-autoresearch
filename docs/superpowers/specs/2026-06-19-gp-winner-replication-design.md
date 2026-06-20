# Faithful GP-Winner Ink-Detection Replication — Design

**Date:** 2026-06-19
**Status:** approved (design); pending spec review

## Problem & motivation

Our autoresearch loop has been searching the 64px ink-detection regime, but we lack
a **trusted external baseline**. The load-bearing fact: the *literal* Grand-Prize
winning TimeSformer, run through **our** pipeline at 64px, scores pixel-AUC
~0.49 train / ~0.56 val — chance (recorded in `FINDINGS.md`). When the published
winning model produces noise in your pipeline, the bottleneck is almost certainly
*upstream of the model* (data, labels, surface-volume/flattening, or recipe), which
hyperparameter/augmentation search cannot fix. Until we can reproduce the published
winner, every loop cycle is noise on an uncalibrated instrument.

External grounding (2026): the GP winners (Nader/Farritor/Schilliger) used a
**TimeSformer-small, 64×64×26 window at stride 32**, chosen specifically to prevent
the model learning whole characters (overfitting/poor generalization) — i.e. the
64px "hallucination window" is *winner-validated*, not a self-imposed handicap. The
full winning recipe also used ~15 rounds of label cleaning, pretrained weights, and
a 3-model ensemble. The complete pipeline is already vendored in this repo at
`villa/ink-detection/`.

## Goal

Run the **exact published model + weights + data** through the vendored pipeline and
confirm it reproduces the winners' legible ink output in this environment —
establishing the trusted baseline we currently lack, and isolating why our own
pipeline returns chance.

## Scope

Two phases, the second **gated** on the first.

### Phase 1 (primary, decisive): inference-only with the published checkpoint
Download 1–2 canonical Scroll-1 segments + the published `timesformer_weights.ckpt`,
run the vendored `inference_timesformer.py` unmodified, render the ink, and judge
legibility against the winners' public result.

- **Outcome A — reproduces legible ink:** the winning pipeline works here. Our
  chance-result is isolated to how *our* data/labels/preprocessing diverge from the
  winner's; the next step is a direct diff (separate spec).
- **Outcome B — fails to reproduce:** there is an environment/plumbing/data/version
  bug in running even the published model; chase that (separate spec).

Either outcome ends the flying-blind state. This is the entire deliverable of this
spec; Phase 2 is sketched only.

### Phase 2 (gated, sketch only): from-scratch retrain
Only if Phase 1 reproduces. Download the full segment set + `prepare.py` labels,
run `train_timesformer_og.py`, compare to the reported AUC. Confirms we can
reproduce the *training*, not just inference. Detailed in a later spec.

## Architecture & components

All work is **isolated**; nothing touches the loop's `.venv`, `run_autoresearch_loop.py`,
or `scripts/training/train.py`.

- **Dedicated environment** — a separate venv (e.g. `uv venv villa/ink-detection/.venv-gp`)
  with `villa/ink-detection/requirements.txt` (`pytorch-lightning==2.0.9`,
  `timesformer-pytorch`, `monai[einops]`, `warmup_scheduler`, `topolosses`, `kimimaro`,
  `numpy==1.26.4`, …) plus a CUDA-matched `torch`. The loop's `.venv` (smp 0.5.0, etc.)
  is left untouched so the running loop is unaffected.
- **Vendored pipeline (unmodified):** `villa/ink-detection/inference_timesformer.py`
  (TimeSformer, `size=64`, `stride=32`, `start_idx=17`), reading segments laid out as
  `<segment_id>/layers/*.tif` + `<segment_id>/<segment_id>_mask.png`.
- **Data** — gitignored under `villa/ink-detection/train_scrolls/` (and/or `eval_scrolls/`):
  - Segments via `download.sh` (rclone from `dl.ash2txt.org`, public basic-auth
    `registeredusers:only`). Phase-1 targets: README demo segments **`20231210121321`**
    and **`20231221180251`** (the winners' public reveal segments; held-out, no labels →
    judged by legibility).
  - Published weights `timesformer_weights.ckpt` from the repo's Google Drive (via `gdown`).
  - Optional quantitative check: one *labeled* segment present in `all_labels/`
    (e.g. `20230530164535`, also in `download.sh`) to compute a pixel-AUC sanity number
    (note: likely in the model's training set, so high AUC there is expected, not held-out).
- **Tooling** — install `rclone` and `gdown` (into the dedicated env or user-local);
  neither is currently present.
- **Evaluation/render** — reuse the rendering approach from the SegFormer repro
  (`reports/`): save the predicted ink PNG (+ thumbnail) and inspect for legible Greek
  letterforms. Where a label exists, also report pixel-AUC via `scripts/pixel_auc.py`.

## Data flow

1. Set up dedicated venv + install requirements + `rclone`/`gdown`.
2. `download.sh` → segment layers + masks into `train_scrolls/`; `gdown` → `timesformer_weights.ckpt`.
3. (Optional) `prepare.py` → inject `all_labels/` into segment folders (only needed for the labeled-segment AUC check / Phase 2).
4. Pause the autoresearch loop (free the GPU).
5. `python inference_timesformer.py --model_path timesformer_weights.ckpt --segment_path .../train_scrolls --segment_id 20231210121321 20231221180251`.
6. Render ink PNG + thumbnail; judge legibility; (optional) pixel-AUC on the labeled segment.
7. Restart the loop. Record result in `FINDINGS.md` + a memory file.

## Risks & mitigations

- **Dependency conflict breaking the loop's `.venv`** → dedicated separate venv; never
  `pip install` into the loop's `.venv`.
- **`torch`/CUDA mismatch** (requirements.txt doesn't pin torch) → install a torch build
  matching the system CUDA (the loop's env uses cu128); verify `torch.cuda.is_available()`
  before inference.
- **`timesformer-pytorch` / lightning version drift** vs the checkpoint → use the pinned
  `pytorch-lightning==2.0.9`; if the checkpoint won't load, inspect its state-dict keys.
- **Download size/time** (tens of GB of layer stacks) → 280 GB free is ample; run download
  in the background; start with the two demo segments only.
- **Credentials/access** → `dl.ash2txt.org` uses public `registeredusers:only`; Drive
  weights via `gdown` (public folder). If a download is gated, surface it to the user.
- **GPU contention with the loop** → pause the loop for the inference step (brief), restart after.
- **Success ambiguity** (no shipped reference image) → criterion is legibility of Greek
  letterforms matching the winners' public reveal, plus an optional labeled-segment AUC ≫
  our 0.56; if the output is noise *and* the checkpoint loaded cleanly, that is Outcome B.

## Success criteria (Phase 1)

- The published checkpoint loads cleanly into the vendored `inference_timesformer.py`.
- Inference on `20231210121321` (and/or `20231221180251`) renders **legible Greek
  letterforms** consistent with the winners' published result — **Outcome A**.
- If a labeled segment is run, pixel-AUC is high (≫ 0.56), confirming the pipeline.
- A clear written verdict (A or B) recorded in `FINDINGS.md` + memory, with the rendered
  PNG under `reports/`.

## Out of scope

- Phase 2 training (separate spec, gated on Phase 1 = Outcome A).
- Any change to `run_autoresearch_loop.py` or `scripts/training/train.py`.
- Diagnosing/fixing our own pipeline's divergence (follow-on, scoped after the verdict).
- The ResNet3D/I3D ensemble members (TimeSformer is the canonical model; ensemble is a later extension).
