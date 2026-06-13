# Same-Scroll Pseudo-Label Self-Training — Design

**Date:** 2026-06-13
**Status:** approved
**Goal:** Lift the detector's held-out ink AUC (~0.60) by exploiting same-scroll
unlabeled CT via confidence-filtered pseudo-label self-training, measured
rigorously with zero validation leakage. Third Tier-3 experiment toward closing
the topology gap (which is downstream of weak detection).

## Context

The autoresearch loop has plateaued: `val_bpb` frozen at 0.262675 for ~10
consecutive cycles, hyperparameter/augmentation sweeps not moving the model. The
binding bottleneck is ink discrimination (train AUC ~0.74 vs val ~0.60 — an
overfitting gap on a *single* labeled fragment, PHercParis2 Fr47). The prize
topology gate (`skel_dist ≤ 2` vs current ~20) is unreachable while detection is
this weak, so the honest target is **val AUC**, with topology improving as a
byproduct.

The chosen lever is semi-supervised learning on **same-scroll unlabeled CT**.
Two data facts shape the design:

1. PHercParis2 exists locally only as two **fully-labeled** fragments (Fr47
   train, Fr143 val) — no separate unlabeled same-scroll CT, no `_Large` bulk.
   The nearest other Paris scroll (PHercParis1 Fr34/Fr39) is the misaligned
   `(H, depth, W)` data shelved on 2026-06-13, so it cannot serve as a clean
   unlabeled proxy.
2. Fr143 is large: `vol=(33, 14830, 9506)`, mask ≈ 98M px. It can be **spatially
   split** into disjoint regions, one acting as held-out "unlabeled" CT.

A prior `use_uamt=True` cycle was inert because its `unlabeled_uris` collapsed to
the training fragment itself (the leak-guard strips the val fragment, leaving
Fr47 = the supervised data → no new signal). This design avoids that failure by
sourcing genuinely-held-out CT.

## Architecture: the no-leakage pipeline

No model is ever supervised or model-selected on the validation region.

1. **Spatial split of Fr143** along width `W=9506` into:
   - **U-region** (unlabeled): columns `[0, 4689)`, masked px ≈ 54.1M.
   - **buffer**: columns `[4689, 4817)` (width 128 = 2× patch_size) — discarded.
   - **V-region** (validation): columns `[4817, 9506)`, masked px ≈ 42.1M.

   The 128px buffer guarantees no 64px patch can straddle the boundary or share
   receptive field, so U and V are spatially independent.
2. **Baseline model** = resenc trained on **Fr47 only** (fresh; never sees any
   Fr143). Serves as *both* the honest control *and* the pseudo-labeler — keeping
   `best_model.pt` (selected on full Fr143) out of the pipeline entirely.
3. **Pseudo-label the U-region** with the baseline model: soft sigmoid
   predictions → confidence filter. Pixels with `prob > τ_high` → ink (1),
   `prob < τ_low` → background (0); the uncertain band `[τ_low, τ_high]` →
   **ignore mask** (excluded from the loss). Defaults: `τ_high=0.65`,
   `τ_low=0.15` (tunable from the pseudo-label quality report below).
4. **Self-train model** = resenc trained on **Fr47-labeled + Fr143 U-region
   pseudo-labeled** (ignored pixels excluded), validated on **Fr143 V-region**.
5. **Oracle model** = resenc trained on **Fr47-labeled + Fr143 U-region TRUE
   labels**, validated on **V-region**. Upper bound on how much *any* U-region
   supervision could help — isolates pseudo-label noise from data value.
6. **Compare** V-region AUC: baseline → self-train → oracle.

## Components (each small and testable)

- **`scripts/spatial_split_mask.py`** — given a fragment's `mask.png` plus split
  axis/fraction/buffer, emit `mask_Uregion.png` and `mask_Vregion.png` (each =
  `mask AND region`, buffer zeroed). Unit-testable: regions disjoint, buffer
  width correct, union ⊆ original mask.
- **`scripts/generate_pseudo_labels.py`** — run a checkpoint over a fragment's
  U-region (restricted by `mask_Uregion.png`), tile inference, write
  `PHercParis2Fr143_pseudo.png` (hard labels) + `PHercParis2Fr143_ignore.png`
  (1 = ignore) into `local_data/pseudo_labels/`. Args: `--checkpoint`,
  `--fragment`, `--region-mask`, `--tau-high`, `--tau-low`.
- **train.py per-pixel ignore-mask support** — the one core change. When a
  fragment provides an ignore mask, the ink loss must skip those pixels. Add an
  optional ignore-mask path parallel to the existing `pseudo_label_dir` label
  swap (train.py:1166-1173); the ink BCE/Dice multiply by `(1 - ignore)` so
  ignored pixels contribute zero gradient. TDD: a test asserting ignored pixels
  produce zero gradient on the ink head.
- **Configs** — `cfg_baseline.json` (uris=[Fr47], val=Fr143 V-region via
  `mask_Vregion.png`), `cfg_selftrain.json` (uris=[Fr47, Fr143 U-region with
  pseudo labels+ignore], val=Fr143 V-region), `cfg_oracle.json` (uris=[Fr47,
  Fr143 U-region with true labels], val=Fr143 V-region). Each staged
  **smoke → probe(~20min) → full(~1h)** like the LeJEPA/multi-scroll runs.
- **Eval** — `measure_ink_auc.py` on the V-region for all three models, plus a
  **pseudo-label quality report**: U-region coverage (% pixels kept after the
  confidence filter) and pseudo-label AUC/precision/recall vs the U-region's
  *true* labels (we hold ground truth, so we can quantify target quality).

### Validation region & the loader

The loader finds valid patch coordinates from `mask.png`. To validate on only the
V-region, the val fragment is pointed at `mask_Vregion.png` (a region-restricted
mask). To train on the U-region pseudo-labels, that fragment entry uses
`mask_Uregion.png` + the pseudo label/ignore PNGs. No change to coordinate-finding
logic is required — only different mask/label files per fragment entry.

## Success criteria

- **Win:** self-train V-region AUC ≥ **+0.02** over baseline, without an
  overfitting blowup (train/val gap not widening materially vs baseline).
- **Neutral/negative:** no lift → recorded honestly in FINDINGS.md (same
  discipline as the clDice / TimeSformer@64px / LeJEPA negatives). The
  pseudo-label quality report and the oracle delta explain *why*: if the oracle
  also fails to lift, U-region data adds little (the ceiling is elsewhere); if
  the oracle lifts but self-train doesn't, the pseudo-labels are too noisy at the
  chosen τ.
- **Recorded numbers:** baseline / self-train / oracle V-region AUC; pseudo-label
  coverage and accuracy; a one-line FINDINGS entry.

## Operational / parallel-safety

- Long GPU runs → pause the loop: `touch .loop_paused`, kill the loop +
  `train.py` PIDs (the watchdog respects the flag). Resume with `bash start.sh`
  and remove the flag afterward.
- Verify the GPU is free via `nvidia-smi` (not `pgrep -f`, which self-matches).
- Back up `best_model.pt` → `best_model.pt.prebkup_pseudolabel` before runs. All
  experiment runs write to experiment-scoped checkpoints; the loop's
  `best_model.pt` is never overwritten.
- The split masks and pseudo-labels are new files under `local_data/`; they do
  not affect the running loop (which uses Fr47 + full-Fr143 `mask.png`).

## Prize compliance

Spatial disjointness with a 128px (2× patch_size) buffer ensures train/predict
non-overlap. Same scroll → no domain shift. Unchanged 64px resenc → within the
0.5 mm (~64px) hallucination window. The pseudo-labels are generated by a model
that never saw any Fr143, so the V-region remains a clean held-out measurement.

## Verification

- Split masks: U and V disjoint, buffer ≥ 128px, each a strict subset of the
  original mask; both have substantial ink (sanity > 0).
- Ignore-mask: unit test shows ignored pixels yield zero ink-head gradient.
- Pseudo-labels: quality report produced (coverage + AUC vs truth) before any
  self-train run; a degenerate all-one/all-zero pseudo-label aborts loudly.
- Baseline trains on Fr47, validates on V-region, finite AUC recorded.
- Self-train + oracle complete; V-region AUC measured for all three; compared.
- `best_model.pt` recoverable (backup exists); loop restarted clean, flag removed.

## Out of scope

- Downloading additional PHercParis2 segments (no confirmed availability).
- Cross-scroll unlabeled CT (domain shift; and the Paris1 fragments are
  misaligned — see [[cross-scroll-gap-quantified]]).
- Online mean-teacher / UA-MT (Approach A) and FixMatch (Approach C) — deferred;
  revisit only if offline self-training shows signal but plateaus.
- Repointing the loop to self-training by default (only if this experiment wins).
