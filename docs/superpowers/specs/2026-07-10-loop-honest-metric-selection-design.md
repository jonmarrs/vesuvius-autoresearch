# Honest-metric selection for the autoresearch loop

**Date:** 2026-07-10
**Status:** approved design, pre-implementation
**Scope:** Option A — metric-honesty rewire only (no window/architecture change)

## Problem

The autonomous research loop (`run_autoresearch_loop.py` → `scripts/training/train.py`)
selects the "best" model on `val_bpb` (1 − swept-threshold Dice) guarded by
`avg_centerline_dice`, and reports `avg_skel_dist` as a prize gate. This project's
own findings retract both signals:

- **`val_bpb` is a weak discriminator** — a 1.9M model and the 36.6M production model
  score near-identical `val_bpb` despite a ~10× `centerline_dice` gap (documented in
  `is_model_improvement`'s own docstring).
- **`skel_dist` is invalid** — it is location-blind (a zero-overlap shifted prediction
  scores 0.0 and "passes"); proven in `scripts/probe_skel_dist_validity.py` and
  recorded in FINDINGS Phase 4b.
- **Dice/`val_bpb` reward constant prediction** — an all-positive map scores a
  deceptively high Dice at low threshold ("predict-constant artifact").

Meanwhile the productionized detector ships an **honest metric contract**
(`src/vesuvius_autoresearch/detector/metrics.py`): threshold-swept F1 (primary),
average-precision prevalence-lift (imbalance-robust gate), ROC-AUC (secondary).
The loop never calls it. The two halves of the repo therefore disagree on what
"better" means. This spec routes the loop's selection through the honest contract.

## Goals

- The loop selects the best model on **threshold-swept F1**, gated by
  **AP-prevalence-lift > 1** (a real-signal guard) and the existing **prize window**
  gate.
- `detector.metrics.segmentation_metrics` is the single source of truth for the
  selection metrics — no re-implementation.
- `val_bpb`, `avg_skel_dist`, `avg_centerline_dice` remain **computed and reported**
  for continuity/auditability, but no longer decide anything.
- Change is surgical, reversible, and prize-window-legal (64px untouched).

## Non-goals

- No change to the model, data pipeline, validation set (Fr143), architecture pinning,
  or the ≤64px prize hallucination window.
- Not expected to make the loop start "improving": per this project's findings, the
  prize-legal 64px window is at chance on this data, so an honest metric will faithfully
  report `val_f1 ≈ chance` rather than manufacture signal. The value here is
  *correctness and alignment of the objective*, not new performance.
- Not pointing the loop at the detector training stack (that is the larger Option C).

## Current flow (as-is)

In `train.py`, at validation:
1. Build `all_probs` (per-patch 2D sigmoid maps) and `all_targets`.
2. `val_bpb = 1 − best_dice` over a swept Dice threshold.
3. Topology metrics (`skel_dist`, `centerline_dice`, `cc_diff`, `mean_ap`) at a
   centerline-dice-optimal threshold via `select_topology_threshold`.
4. `submittable = window_ok and villa_metrics_ok`.
5. `is_improvement`: `False` if `val_bpb` NaN; `False` if `enforce_prize_gates` and not
   `submittable`; else `is_model_improvement(val_bpb, avg_centerline_dice, best_prev_*)`
   (topology-first with a bpb guard rail).
6. On improvement: save `best_model.pt`, append `results.tsv`, `prize_readiness.tsv`.
   Every run appends `history.tsv`. `run_result.json` carries `is_success`.

## Design (to-be)

### 1. Pooled honest metrics (new)

Where `all_probs`/`all_targets` already exist (`if all_probs:` block), pool all
validation patches into flat arrays and call the shipped metric:

```python
from vesuvius_autoresearch.detector.metrics import segmentation_metrics
prob = torch.cat([p.reshape(-1) for p in all_probs]).numpy()
label = torch.cat([t.reshape(-1) for t in all_targets]).numpy()
seg = segmentation_metrics(prob, label, mask=np.ones_like(label, dtype=bool))
val_f1          = seg["val_f1"]              # NaN if degenerate (no contrast)
val_f1_threshold = seg["best_threshold"]
ap_lift         = seg["ap_prevalence_lift"]
roc_auc         = seg["roc_auc"]
val_pos_rate    = seg["positive_rate"]
```

`mask` is all-True because every validation pixel is valid here. `segmentation_metrics`
already handles the degenerate (all-positive/all-negative) case by returning NaN for the
metric keys.

`vesuvius_autoresearch` is import-safe in this runtime (the detector test-suite imports
it and passes).

### 2. Selection criterion (replaces the decision, not the reporting)

New helper alongside the existing `is_model_improvement` (which stays for reference/tests
but leaves the decision path):

```python
F1_NOISE_TOLERANCE = 5e-3   # provisional; recalibrate from observed run-to-run F1 noise
LIFT_MARGIN        = 0.02   # provisional; ap_lift must clear 1 by this margin

def is_f1_improvement(val_f1, ap_lift, best_val_f1):
    if not np.isfinite(val_f1):
        return False
    if not (np.isfinite(ap_lift) and ap_lift > 1.0 + LIFT_MARGIN):
        return False  # real-signal gate: must beat the prevalence baseline
    return val_f1 > best_val_f1 + F1_NOISE_TOLERANCE
```

`is_improvement` becomes:
```python
is_improvement = True
if not np.isfinite(val_f1):
    is_improvement = False
if config.enforce_prize_gates and not submittable:
    is_improvement = False
if is_improvement:
    is_improvement = is_f1_improvement(val_f1, ap_lift, best_previous_val_f1)
```

The window gate (`submittable`) and `enforce_prize_gates` behavior are unchanged.
`val_bpb`/topology no longer gate or rank.

### 3. Baseline migration

`best_model.pt` predates `val_f1`. Read `best_previous_val_f1 = chk.get("val_f1")`.
If absent → `-inf`, so the first submittable, lift-positive cycle stamps `val_f1` into
`best_model.pt` and becomes the reference. No manual backfill.

### 4. Persistence

Add `val_f1`, `val_f1_threshold`, `ap_prevalence_lift`, `roc_auc`, `val_positive_rate`
to the **programmatic artifacts**: `run_result.json` (loop-consumed), `best_model.pt`,
and `last_model.pt`.

**Freeze the `history.tsv` / `results.tsv` / `prize_readiness.tsv` schemas — do not add
columns.** Their headers are written only when the file is absent, and the committed
files already exist with the old schema; appending columns would misalign existing rows
and risk the positional/`config`-last parsers (`generate_daily_report.py` and the
README-documented tooling). Auditability of the honest metrics is preserved through
`best_model.pt` (the selected models) plus the per-cycle sprint-log line (§5). Adding
first-class `history.tsv` columns, if wanted, is a deliberate follow-up with a header
migration, not part of this surgical change.

### 5. Loop-side visibility (minimal)

`run_autoresearch_loop.py` keys off `is_success` (semantics unchanged) and needs no
logic change. Add `val_f1` to the sprint-log stats line for visibility only.

### 6. Tolerances are provisional

`F1_NOISE_TOLERANCE` and `LIFT_MARGIN` have no empirical basis yet (no measured
run-to-run F1 noise on this val set). Set documented conservative defaults and flag for
recalibration after several cycles, mirroring the existing `BPB_NOISE_TOLERANCE` comment.

## Testing

- Unit test the criterion truth table: not-submittable → reject; `ap_lift ≤ 1+margin`
  → reject (constant-prediction guard); `val_f1` within tolerance → reject; `val_f1`
  beyond tolerance with lift and submittable → accept; NaN `val_f1` → reject.
- Unit test the pooling: `all_probs`/`all_targets` → flat arrays → `segmentation_metrics`
  returns the expected keys, incl. the degenerate NaN path.
- Regression: `tests/test_improvement_criterion.py`, `tests/test_prize_promotion_gates.py`,
  `tests/test_prize_readiness.py` still pass (update expectations only where they assert
  the old `val_bpb`-first decision).

## Risks & mitigations

- **Loop is live / parallel agent pushes to main.** Edit only with the loop paused
  (`.loop_paused` present, no PIDs); keep the diff surgical to minimize conflict surface.
- **Schema drift in `history.tsv`.** Avoided entirely: the TSV schemas are frozen
  (§4); the honest metrics live in `best_model.pt` / `run_result.json` / sprint logs.
- **Provisional tolerances mis-tuned.** Conservative defaults + explicit recalibration
  note; worst case is over/under-eager promotion, not corruption.
- **Degenerate val batch.** `segmentation_metrics` returns NaN → criterion rejects
  (fail-closed), same posture as the existing NaN `val_bpb` guard.

## Rollback

Revert the single `train.py` block (and the loop's log-line addition). `best_model.pt`
gains extra keys but keeps all old ones, so a revert reads it unchanged.
