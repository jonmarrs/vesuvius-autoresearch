# GP-Winner Phase 4a — Adopt + Scale the Working Stack, Establish Prize-Readiness — Design

**Date:** 2026-06-22
**Status:** approved (design); pending spec review
**Depends on:** Phase 3a (`2026-06-21-gp-winner-phase3-our-data-design.md`) = **our data is fine; the gap is our model/training stack** (proven recipe → 0.711 held-out on our Fr47→Fr143 where our `resenc_unet` gets ~0.56).

## Problem & motivation

Three phases established: the winner's TimeSformer recipe **runs** here (Phase 1),
**trains** here (Phase 2, held-out AUC 0.905 on real Scroll-1 segments), and trains on
**our data** (Phase 3, 0.711) where our own `resenc_unet` is at chance. Crucially the
recipe is **prize-window-compliant** — it uses `size=64` (64×64px = 0.5×0.5mm), so the
"64px is the ceiling" premise our loop ran on is disproven: a 64px architecture reads ink
fine; our *implementation* was the ceiling. We therefore already hold a **working,
prize-compliant ink-detection stack**, while our production `resenc_unet` sits at val
~0.512 and has never passed the prize topology gates (skel_dist ~19–21 vs the 2.0 gate).

The decision (brainstorm): **adopt + scale the winner recipe** rather than keep autopsying
`resenc_unet`. Phase 4a establishes how close the working stack is to a prize submission by
scoring it through the *same* prize topology gates our broken model fails, and produces a
scaled production detector.

## Goal

Measure the working TimeSformer through the real prize gates (`centerline_dice`,
`skel_dist`, 64px window) and produce a scaled, prize-compliant production detector with a
full scorecard — the prize-readiness number our loop never produced from a genuinely
detecting model.

## Scope — two steps, the second gated on the first

### Step A (cheap, decisive — no training)
Score the **existing Phase-2 TimeSformer** (held-out `20230820203112`, pixel-AUC 0.905;
checkpoint `outputs/.../timesformer_wild16_20230820203112_frepoch=11.ckpt`, prediction
`repro/gp_winner/runs/phase2/20230820203112_prediction_rotated_0_layer_17.png`) through
`scripts/evaluate_villa_metrics.py` → `centerline_dice` / `skel_dist` at the
topology-optimal threshold. Compare to our `resenc_unet`'s failing gates. Answers *"does a
genuinely-detecting model pass the topology gates our broken one fails?"* in minutes.

- If gates are **near-passing / promising** → proceed to Step B as the production run.
- If gates are **wildly out of reach even at AUC 0.905** → the remaining issue is the
  *gates / post-processing* (threshold-fragile, weakly coupled to detection — consistent
  with our prior findings), not the detector; record that and reshape before scaling.

### Step B (scaled production run, gated on Step A)
Train one **scaled** TimeSformer — **3 real Scroll-1 segments** (`20231210121321`,
`20230702185753`, `20230826170124`) vs Phase 2's 2, **held out `20230820203112`**,
**~12–15 epochs** — as the production detector. Evaluate the same way: pixel-AUC + prize
gates + legible render. (3 train + 1 holdout is near Phase 2's RAM footprint; watch `free`.
~a day on one 4090.)

Out of scope: full 41-segment / ensemble replication; the actual Progress-Prize submission
packaging (**Phase 4c**, gated on a passing scorecard); any change to `resenc_unet` /
`run_autoresearch_loop.py` / our `train.py`.

## Architecture & components

Isolation preserved: vendored `villa/ink-detection/` files are **not edited** (copy + edit);
training/inference use `.venv-gp`; the loop's `.venv` is used only **read-only** for the
prize-gate evaluator (where the `metrics/` package lives).

1. **Prize-gate evaluation wrapper** — `repro/gp_winner/prize_gate_eval.py`: given a
   prediction PNG + a ground-truth inklabels PNG, binarize at a swept set of thresholds,
   call the villa metrics (`scripts/evaluate_villa_metrics.py` or its underlying
   `metrics.centerline_dice` / `metrics.skeleton_distance_length`) at each, and report the
   **topology-optimal** `centerline_dice` and the `skel_dist` there, plus the pixel-AUC for
   context. Writes a JSON scorecard. Reuses, not reimplements, the metric functions.
2. **Step A run** — point the wrapper at the existing Phase-2 prediction + its label.
3. **`train_scaled.py`** — a copy of `repro/gp_winner/train_ours.py` with the fragment lists
   set to the 3 train + 1 holdout Scroll-1 segments (everything else — batch 32, single-GPU,
   CSVLogger, 64px — identical). Optionally bump `epochs` to 15.
4. **Step B eval** — held-out inference (`inference_timesformer.py`) on `20230820203112`
   with the best checkpoint → `render_eval.py` (pixel-AUC + thumbnail) → the prize-gate
   wrapper (topology scorecard).

## Data flow

1. **Step A:** run `prize_gate_eval.py` on the Phase-2 prediction + `all_labels/20230820203112_inklabels.png`
   → topology scorecard; compare to resenc_unet's gates; **decide** whether to proceed.
2. **Step B (if proceeding):** pause the loop; train `train_scaled.py` (3 seg, ~12–15 epochs,
   checkpoint per epoch); held-out inference + `render_eval.py` + `prize_gate_eval.py`;
   restart the loop.
3. Record both steps' verdicts in `FINDINGS.md` + a memory file; thumbnails + JSON scorecards
   under `reports/gp_winner_repro/`.

## Success criteria

This is a **measurement** milestone — the deliverable is an honest prize-readiness scorecard,
not a fixed target:

- **Step A:** a real `centerline_dice` / `skel_dist` for the AUC-0.905 model at the
  topology-optimal threshold, side-by-side with resenc_unet's (skel_dist ~19 / cd ~0.34).
  A clear verdict on whether a working detector passes/approaches the gates.
- **Step B (if run):** a scaled production checkpoint with held-out pixel-AUC ≥ the Phase-2
  0.905 (more data should hold or improve it) and its prize scorecard; a legible render.
- Written verdict in `FINDINGS.md` + memory; scorecards (JSON) + thumbnails under `reports/`.

## Risks & mitigations

- **villa `metrics/` import path** — the evaluator lives in the loop's `.venv`; run the
  wrapper there (read-only). If `metrics.centerline_dice` isn't importable, call
  `scripts/evaluate_villa_metrics.py` as a subprocess with `--pred/--gt`. Verify imports
  before the full sweep.
- **Prediction/label shape mismatch** — the winner inference pads to tile_size multiples;
  crop both to the common H×W and restrict to the papyrus mask before metrics (as done in
  Phase 3 — pred 14848×9728 vs label 14830×9506).
- **Topology metrics are threshold-fragile** (prior finding) — sweep thresholds and report
  at the topology-optimal point, not a fixed 0.5; report the chosen threshold.
- **Step B RAM** — 3 segments may approach the 31 GB wall (5 OOM'd in Phase 2; 3 fit).
  Watch `free` during the read; fall back to 2 train segments if it OOMs.
- **Step B runtime** — 3 segments × ~15 epochs is multi-day; checkpoint per epoch so an
  early stop yields a usable model; reduce epochs/segments if needed.
- **GPU contention** — loop paused for any GPU step, restarted after.
- **"Working model still fails gates"** — a legitimate, informative outcome: it would mean
  the prize bottleneck is post-processing/topology, not detection — recorded as the Step A
  verdict and handled in a follow-on, not forced.
