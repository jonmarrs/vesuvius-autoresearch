# LeJEPA SSL-Init Experiment — Design

**Date:** 2026-06-12
**Status:** approved (pending spec review)
**Goal:** Test whether initializing the ink detector from the unused LeJEPA self-supervised pretrain lifts discrimination above the resenc baseline (per-patch ink AUC ~0.74 train / 0.61 val). First Tier-3 experiment toward the Grand Prize / First Letters.

## Context

The model is a mediocre detector (per-patch ink AUC ~0.74 train / 0.61 val; centerline_dice ~0.32). A 1.8 GB **LeJEPA self-supervised pretrain** (`checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth`) exists and is fully wired, but **unused** — `config.json` has `foundation_model_path: None`, so every cycle trains from scratch and ignores the SSL backbone. SSL pretraining is the canonical way to lift discrimination and generalization with limited labels, so this is the highest-leverage ready-to-run lever.

Verified compatibility: the checkpoint's inner `model` state has 348 `encoder.*` keys; `LeJEPAUNet` (`vesuvius_model.py`) wraps a `PrimusNetwork` as `self.backbone`, and train.py's foundation-load path (lines ~1296–1312) strips the `encoder.` prefix and loads into `model.backbone.shared_encoder`. So `architecture=lejepa_unet` + `foundation_model_path=<ckpt>` should warm-start the encoder.

**Known cost/risk:** `LeJEPAUNet` runs the backbone in **fp64** (`self.backbone.double()`) — slow and memory-heavy. The experiment is de-risked in stages (smoke → short probe → full run) so we don't burn hours on a path that can't build, load, or learn.

## Experiment design

A controlled comparison, single variable = the architecture+init (lejepa_unet warm-started from SSL) vs the resenc baseline. Same data (Fr47 train / Fr143 val), same evaluation (per-patch ink AUC, the honest signal).

**Config** (`/tmp/cfg_lejepa.json`, derived from `config.json`):
- `architecture: "lejepa_unet"`
- `foundation_model_path: "checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth"`
- `uris: [Fr47]`, `val_uri: Fr143` (unchanged)
- ink-focused losses (`loss_ink_bce`, `loss_ink_dice`); auxiliary heads/UA-MT off to isolate the SSL-init effect
- `time_budget` set per stage below

The loop pins/loads `best_model.pt` (resenc) — irrelevant here since the architecture differs (train.py will "Starting fresh" and load the foundation encoder instead). The run writes `last_model.pt` (not an improvement vs the resenc baseline by the loop's criterion), which is what we measure.

### Stages (each gates the next)

1. **Smoke** (`train.py --smoke`, seconds): build `lejepa_unet`, load the foundation checkpoint, one fwd/bwd. Confirms the model builds, the encoder weights load (look for the "Loading pretrained backbone" / encoder-load log, and a non-trivial number of matched tensors), and there's no NaN. **Gate:** `PREFLIGHT OK` + foundation weights loaded. If it can't build/load, stop and report.
2. **Probe** (`time_budget ≈ 1200`, ~20 min): confirm it learns — training loss trends down, validation produces a real `val_bpb` (not the 1.0 sentinel), no NaN/instability. **Gate:** loss decreasing + finite val metrics.
3. **Full run** (`time_budget ≈ 3600`, ~1 h): the real training. Then measure per-patch ink AUC on Fr47 and Fr143 from `last_model.pt`.

### Measurement & success criterion

After the full run, measure per-patch ink AUC (Fr47 train / Fr143 val) on `last_model.pt` using the existing `/tmp/auc_check.py` (CPU, so it doesn't fight the loop). Compare to the resenc baseline (0.74 / 0.61):
- **Win:** val AUC meaningfully > 0.61 (e.g. ≥ 0.64) — SSL init helps; worth a longer run / promoting lejepa as a tracked path.
- **Neutral/negative:** val AUC ≤ 0.61 — SSL-init-of-lejepa-at-64px doesn't beat the resenc CNN here (an informative result, consistent with the earlier 64px-window finding); revert to resenc, reconsider levers.

Either way the result is logged honestly in `FINDINGS.md`.

## Operational / parallel-safety

- This is a long GPU run → **pause the loop** for the duration: `touch .loop_paused` then kill the loop PIDs (the watchdog respects the flag). Resume with `bash start.sh` after (it clears the flag).
- `best_model.pt` (resenc baseline) is **not** overwritten — the lejepa run can't satisfy the improvement criterion against a different-architecture baseline, and it writes `last_model.pt`. Verify best_model is untouched before restarting the loop.
- No repo code changes are required for the experiment itself (config-only). Any train.py fix needed to make lejepa build/load is a separate, tested change (pause-protected).

## Verification

- Smoke: `PREFLIGHT OK`, foundation encoder weights loaded (matched-tensor count > 0).
- Probe: training loss decreases; `val_bpb` is a real number (not 1.0); no NaN.
- Full run completes; AUC measured on Fr47/Fr143 and recorded.
- `best_model.pt` unchanged; loop restarted clean (0 import crashes) after the experiment.

## Out of scope

- Multi-scroll / cross-scroll training and validation (the next Tier-3 step; downloads approved, separate spec).
- Re-training the SSL pretrain itself (use the existing checkpoint).
- Wiring lejepa-as-default into the loop (only if this experiment wins).
