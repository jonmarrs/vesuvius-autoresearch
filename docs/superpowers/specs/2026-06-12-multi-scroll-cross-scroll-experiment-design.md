# Multi-Scroll / Cross-Scroll Generalization Experiment — Design

**Date:** 2026-06-12
**Status:** approved (pending spec review)
**Goal:** Measure the true cross-scroll generalization gap and test whether training the 64px resenc CNN on multiple scrolls closes it. Second Tier-3 experiment toward the Grand Prize (the cross-scroll "generalization gap" is the stated bottleneck).

## Context

The detector is trained on one fragment (PHercParis2Fr47) and validated on a **same-scroll** fragment (Fr143) — so the "val AUC 0.61" understates the real cross-scroll gap, which has never been measured. Six labeled fragments across **four scrolls** are already on disk (no download needed; they use the bare OME-Zarr `0/` layout):

- PHercParis2: Fr47 (train), Fr143
- PHercParis1: Fr34, Fr39
- PHerc51: Fr8
- PHerc1667: Fr3

train.py already supports multi-URI training (`config.uris` list → per-fragment `VesuviusLabeledDataset` → `ConcatDataset`). The experiment is fully prize-compliant (same 64px resenc CNN).

**Prerequisite (correctness):** train.py's label resolution prefers `inklabels_filled.png` over `inklabels.png`, and the four cross-scroll fragments' `inklabels_filled.png` is **over-filled garbage (89–97% ink)** vs the real `inklabels.png` (0.057–0.079). Without intervention the model would train/validate on garbage labels. Fix: move each over-filled `inklabels_filled.png` → `inklabels_filled.png.overfilled.bak` (reversible) so the loader falls through to the good `inklabels.png`. PHercParis2Fr47 has no filled label (unaffected).

## Experiment design

- **Held-out scroll (cross-scroll validation):** PHerc1667 (Fr3) — never in training.
- **Training scrolls:** PHercParis2Fr47 + PHercParis1Fr34 + PHercParis1Fr39 + PHerc51Fr8 (3 distinct scrolls).
- **Model:** resenc_unet at 64px, warm-started from the current `best_model.pt` (so the comparison shares a starting point with the baseline). Ink-focused losses; `use_ridges` matches the baseline (True).
- **Metric:** per-patch ink AUC on the held-out PHerc1667Fr3 (the honest cross-scroll signal).

### Three parts

1. **Cross-scroll baseline (diagnostic, ~minutes, no training):** measure the current `best_model` (resenc, Fr47-only) per-patch AUC on PHerc1667Fr3. This is the *true* cross-scroll gap (vs the same-scroll 0.61). Informative on its own.
2. **Multi-scroll training:** train resenc (warm-started from best_model) on the 4-fragment `ConcatDataset`, validating on Fr3, staged smoke → probe → full run (same de-risking discipline as the LeJEPA experiment).
3. **Compare:** the multi-scroll model's PHerc1667Fr3 AUC vs the part-1 baseline. **Win** = cross-scroll AUC improves by a meaningful margin (≥ +0.03) — multi-scroll training helps generalization. **Neutral/negative** = no improvement — more scrolls alone don't close the gap; record and reconsider (augmentation strength, SSL-at-64px, pseudo-labels).

### Measurement tool

The existing `/tmp/auc_check.py` is hardcoded to Fr47/Fr143. Generalize it (or add a sibling) to take a fragment directory so it can measure per-patch AUC on PHerc1667Fr3 (and on the training scrolls for a train-AUC reference). Same method: `roc_auc_score(target.ravel(), sigmoid(model(x)).ravel())` over `require_ink` patches.

## Components & data flow

- **Label fix:** `local_data/{PHercParis1Fr34,PHercParis1Fr39,PHerc51Cr4Fr8,PHerc1667Cr1Fr3}/inklabels_filled.png` → `.overfilled.bak`.
- **Config** (`/tmp/cfg_multiscroll.json`): `uris=[Fr47, Fr34, Fr39, Fr8 surface volumes]`, `val_uri=PHerc1667Fr3`, `architecture=resenc_unet`, ink-focused, `time_budget` per stage.
- **Backup:** `cp best_model.pt best_model.pt.prebkup_multiscroll` before the run — the training writes `last_model.pt` (or `best_model.pt` if it "improves" by the loop's Fr143-stored criterion, which is now apples-to-oranges vs cross-scroll Fr3). Measure the resulting model; keep or restore based on the result.

## Operational / parallel-safety

- Long GPU run → pause the loop: `touch .loop_paused`, kill PIDs (watchdog respects the flag). Resume with `bash start.sh`.
- Verify GPU is free via `nvidia-smi` (not `pgrep -f`, which self-matches).
- Back up `best_model.pt` first; the loop's resenc baseline must be recoverable.
- The over-filled-label move is a safe permanent improvement (those labels are garbage) and doesn't affect the running loop (which only uses Fr47/Fr143).

## Verification

- Label fix: the 4 fragments now resolve to `inklabels.png` (ink fraction 0.057–0.079, not 0.9).
- Baseline: PHerc1667Fr3 AUC for best_model recorded (the true cross-scroll number).
- Smoke: multi-URI ConcatDataset builds, foundation/best_model warm-start loads, `PREFLIGHT OK`.
- Probe: loss decreases, finite val metrics on Fr3, no NaN.
- Full run completes; multi-scroll model's PHerc1667Fr3 AUC measured and compared to baseline; recorded in FINDINGS.md.
- `best_model.pt` recoverable (backup exists); loop restarted clean.

## Out of scope

- Adding PHercParis4_Monster (no local CT volume).
- Pseudo-labeling the unlabeled other scrolls (PHerc0009B/0125/0139) — a later lever.
- Re-pointing the loop to multi-scroll by default (only if this experiment wins).
