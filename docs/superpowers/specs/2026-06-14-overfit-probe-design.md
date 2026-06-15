# Overfit / Feasibility Probe — Design

**Date:** 2026-06-14
**Status:** approved
**Goal:** Classify the detector's flat ~0.52 pixel-AUC ceiling as **capacity**,
**optimization/augmentation**, **signal-absent (64px window)**, or **pipeline
bug**, so the next architectural lever is chosen from evidence rather than a
guess. A cheap diagnostic (minutes–1h), not a production training change.

## Context

Four converging negative results (TimeSformer@64px, LeJEPA, pseudo-label/oracle,
12h long-schedule) show that data and compute do not lift pixel-level ink
discrimination. The 12h fresh run's curve is flat at ~0.51–0.52 on validation.
**Probe 0** (this session, free) measured the 12h model on its own *training*
fragment (Fr47): pooled pixel AUC **0.581** (per-patch 0.585) vs validation
**0.505** (per-patch 0.533). So the model barely fits even training data — ruling
out a pure generalization gap — but 0.58 is confounded by the full 7,345-patch
set + heavy augmentation, so it cannot separate capacity from
optimization/augmentation from a pipeline bug. This probe removes those
confounds.

The project has a history of silent pipeline bugs (Frangi-zeros, jitter
misalignment, axis misalignment, dead val cache), so "can the model even
memorize?" is a first-class hypothesis, not an afterthought.

## The probe ladder

A standalone `scripts/overfit_probe.py` builds ONE fixed batch and runs a plain
optimization loop on just that batch, logging train pixel AUC over steps. No
dataloader sampling, no augmentation, no validation, no `best_model.pt`.

**Probe 1 — overfit real ink.**
- Fixed set: `K=16` ink-containing Fr47 patches, selected deterministically
  (`require_ink=True`, `jitter=False`, fixed indices), loaded ONCE into a single
  GPU batch.
- Fresh `build_inference_model` (same resenc as production), plain BCE+Dice ink
  loss (no fiber/QC/aux/consistency terms — isolate the ink objective), Adam at a
  high LR (1e-3), up to `S=2000` steps on that one batch.
- Log train pooled pixel AUC + per-patch AUC every 100 steps.
- **Read:** reaches ~0.95+ → architecture *can* represent CT→ink; the full-data
  0.58 ceiling is optimization/augmentation/regularization, **not** capacity →
  bigger model is the wrong lever. Stalls ≲0.6 even on 16 memorized patches →
  capacity-inadequate **or** pipeline/loss bug → run Probe 2.

**Probe 2 — control target (only if Probe 1 stalls).**
- Identical setup, but the target is a *synthetic, definitely-learnable* per-pixel
  label derived from the CT input itself: take the CT channel (index 0) averaged
  over the z axis → a `[K,1,H,W]` map, and set `target = (ct_zmean >
  per_patch_mean_of_ct_zmean)` per patch — a deterministic boolean function of the
  exact tensor the model receives. This signal is unambiguously present in the
  input.
- **Read:** overfits the control but not real ink → real ink is **not
  predictable from the 64px CT** the model sees (signal-absent / window too
  small) — a fundamental result; no architecture helps, and it is worth
  surfacing to the Vesuvius community. Cannot overfit even the control → the
  **training/loss/pipeline is broken** (gradients don't drive pixel
  discrimination) — a bug to fix, and possibly the root cause of the whole
  project's ~0.5 plateau.

## Components

- `scripts/overfit_probe.py` — single focused script:
  - `build_fixed_batch(frag_dir, k, num_layers, patch_size, use_ridges, device, seed)`
    → `(x [K,C,nl,H,W], ink [K,1,H,W])` from `VesuviusLabeledDataset(... require_ink=True, jitter=False)`, taking the first `k` valid indices, center-sliced `[:, 4:4+nl]`.
  - `brightness_control_target(x)` → `[K,1,H,W]` from the CT channel's
    center-slice vs its per-patch mean (the Probe 2 target).
  - `overfit(model, x, target, steps, lr, log_every)` → trains on the one batch,
    returns a list of `(step, pooled_auc, per_patch_auc)` using `pooled_pixel_auc`.
  - `main(--target real|brightness, --k, --steps, --lr, --frag, --out-csv)` —
    runs the loop, writes a curve CSV, prints the trajectory + final verdict line.
- Reuses: `build_inference_model`, `VesuviusLabeledDataset`, `pooled_pixel_auc`,
  `compute_dice_loss` (all existing). No change to `train.py`.

## Decision table (output)

| Probe 1 (real) | Probe 2 (control) | Classification | Implied lever |
| --- | --- | --- | --- |
| ≥ ~0.95 | — | optimization / augmentation / regularization | de-augment, longer/better LR on full data, sharper objective — NOT bigger model |
| stalls ≲0.6 | ≥ ~0.95 | signal-absent at 64px (window) | no architecture helps; document; consider window-feasibility writeup |
| stalls ≲0.6 | stalls ≲0.6 | pipeline / loss bug | debug the training path (likely the project-wide root cause) |

The probe's job is to land us in exactly one row, then the architectural lever is
brainstormed *from that row* (a follow-up spec).

## Operational / safety

- Pause the loop for the run (the probe needs the GPU; runs are short). Verify GPU
  free via `nvidia-smi`. Restore the loop after.
- Fresh models only; `best_model.pt` is never read or written.
- Read-only on `local_data/`; outputs only `experiments/overfit_probe/*.csv`
  (gitignored).

## Testing

- `brightness_control_target`: unit test on a known small tensor (a pixel above
  the patch mean → 1, below → 0).
- `overfit`: a TDD-friendly smoke on a tiny synthetic linearly-separable batch
  (e.g., 2 fake "patches" where ink = input>0.5) — the loop must drive that AUC
  toward 1.0, proving the optimization wiring is correct independent of scroll
  data.
- `pooled_pixel_auc` is already unit-tested.

## Out of scope

- Building the actual architectural change — that is the follow-up, chosen from
  the decision table.
- Any change to the production training loop or `best_model.pt`.
- Re-running the 12h schedule.
