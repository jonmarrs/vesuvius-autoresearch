# Cross-Scroll Measurement Foundation — Design

**Status:** Approved design (brainstorming). Sub-project A of the "cross-scroll Dice autoresearch" pivot.

## Context & motivation

The Vesuvius community's active frontier is **segmentation quality (Dice/F1) and cross-scroll
generalization** — the Kaggle *Surface Detection* competition (nnU-Net/ResEncUNet, Dice), the villa
`model_optimization_framework` (an nnU-Net autoresearch that ranks on Dice, currently a stub), and an
automated ink-detection agent swarm reporting near-doubled **validation Dice** on a held-out scroll. The
accepted "Vesuvius AutoResearch" tool's metric contract is **`val_f1` (main, threshold-swept)** plus
`average_precision`, `ap_prevalence_lift`, `precision`, `recall`, `F0.5` — notably **AP (PR-curve), not
ROC-AUC**, which is the imbalance-robust honest-ranking choice for sparse ink.

Our repo currently reports ROC pixel-AUC (an honest signal, but over-optimistic under class imbalance and
not the community's language) and has **no F1/AP code**. Our cross-scroll generalization gap is **UNMEASURED**
(the 2026-06-12 attempt was invalidated by an axis-order/label-alignment bug affecting the raw `local_data`
cross-scroll fragments).

This sub-project builds the **honest measurement foundation** the pivot stands on: a community-aligned metric
module, and the project's **first valid cross-scroll number** — obtained by scoring the existing detector
(`models/detector/detector_epoch=7.ckpt`, trained on Scroll-2 `PHercParis2Fr47`) on a held-out **Scroll-1**
segment. No training; no retraining.

**Key data finding that de-risks this:** `villa/ink-detection/train_scrolls/` already holds aligned,
detector-format segments from **two different scrolls** — seven timestamp-named **Scroll-1** GP-winner ink
segments (26 layers + inklabels + mask each) and the **Scroll-2** `PHercParis2Fr47/Fr143`. This is a valid
cross-scroll pair already in the correct format, so we **avoid the (H,depth,W) axis / label-resampling bug**
entirely (that bug only affects the raw `local_data` fragments like PHerc1667, which are out of scope here).

## Goals / success criteria

1. A reusable, unit-tested **metric module** implementing the community contract, mask-restricted and pooled.
2. The detector **eval switched** to this contract (F1-swept primary; AP/prevalence-lift gates; ROC-AUC kept
   only as a secondary diagnostic, never an optimization target).
3. A committed **cross-scroll measurement report**: the existing detector's **same-scroll** (Fr143) vs
   **cross-scroll** (a Scroll-1 segment) F1 / AP / prevalence-lift — the project's first honest cross-scroll
   number — produced with no training.

## Non-goals (explicit scope boundary)

- **No retraining / no new model** (cross-scroll-trained model is Sub-project B/C).
- **No full-resolution architecture** (ResEncUNet/SegFormer is Sub-project B).
- **No raw-fragment axis/label alignment** (PHerc1667 etc.) — deferred; we use the aligned `train_scrolls` pair.
- **No search loop** (Sub-project C).

## Architecture & components

Three units under `src/vesuvius_autoresearch/detector/`, isolated by clear interfaces:

### 1. `metrics.py` (new) — pure numpy/sklearn, no torch

```
segmentation_metrics(prob, label, mask, thresholds=None) -> dict
```
- Inputs: `prob` (HxW float in [0,1]), `label` (HxW {0,1}), `mask` (HxW bool). All restricted to `mask`.
- Threshold sweep: default `np.linspace(0.05, 0.95, 19)` (configurable).
- Returns (the community contract):
  - `val_f1` — **primary**: max F1 over the sweep.
  - `best_threshold` — threshold achieving `val_f1`.
  - `f1_at_0.5` — F1 at the community default fixed threshold (honest fixed-threshold counterpart to the
    oracle-swept `val_f1`).
  - `val_f05` — max F0.5 over the sweep.
  - `precision`, `recall` — at `best_threshold`.
  - `average_precision` — `sklearn.metrics.average_precision_score` (threshold-free PR-AUC; honest ranking).
  - `ap_prevalence_lift` — `average_precision / positive_rate` (base-rate control; ≈1 ⇒ no real signal).
  - `positive_rate` — label prevalence within mask.
  - `pred_positive_rate` — predicted-positive fraction at `best_threshold` (catches paint-everything).
  - `roc_auc` — **secondary diagnostic only** (`scripts/pixel_auc.pooled_pixel_auc` or sklearn); explicitly
    NOT an optimization target.
- Side output: `metrics_by_threshold` (list of dicts: threshold, precision, recall, f1, f05) for CSV export.
- Edge handling: zero label-positives in mask ⇒ AP/F1 undefined ⇒ return `nan` for those keys with a
  `note` field, never raise.

### 2. `eval.py` (modified) — consume `metrics.py`

`evaluate(prob_map, label, mask, cfg, fragment_id)` replaces the Youden-J/ROC path with
`segmentation_metrics`, writes: scorecard JSON (full contract), `<fragment_id>_metrics_by_threshold.csv`,
and the existing thumbnail. Headline keys: `val_f1`, `average_precision`, `ap_prevalence_lift`.

**Backward compatibility (keep Sub-project A contained):** existing consumers gate on the old keys —
`cli.assert_auc(scorecard)` reads `scorecard["pixel_auc"]`, `cli._reproduce` calls it, and
`tests/test_detector_eval.py` / `tests/test_detector_cli.py` assert `pixel_auc` / `threshold`. To avoid
churning the reproduce gate now, `evaluate` retains a **`pixel_auc` alias** (= `roc_auc`) and a `threshold`
alias (= `best_threshold`) alongside the new keys. `cli.assert_auc` and the `>=0.70` reproduce gate are left
unchanged (moving the gate to `val_f1` is deferred to the retrain in B/C). `tests/test_detector_eval.py` is
**extended** (not rewritten) to also assert the new headline keys. Net: no existing test or CLI path breaks.

### 3. `measure.py` (new) + a `measure` CLI subcommand — the harness

```
measure(cfg, checkpoint_path, targets) -> dict
```
- `targets`: list of `(fragment_id, scroll_label)`, e.g.
  `[("PHercParis2Fr143", "scroll2_same"), ("20230702185753", "scroll1_cross")]`.
- For each target: `infer(cfg, ckpt, fragment_id)` (existing, batched, uniform) → `read_image_mask` →
  `segmentation_metrics` → per-target scorecard.
- Writes `reports/detector/cross_scroll_measurement.md` (+ `.json`): a table of same-scroll vs cross-scroll
  `val_f1` / `average_precision` / `ap_prevalence_lift` / `precision` / `recall`, and the **gap**.
- CLI: `python -m vesuvius_autoresearch.detector.cli measure` (defaults to the epoch-7 ckpt + the two targets
  above).

## Data flow

```
checkpoint (epoch 7, Scroll-2 Fr47-trained)
   └─ infer(cfg, ckpt, fragment) ─► prob map (HxW)
read_image_mask(cfg, fragment) ─► label, frag_mask
   └─ segmentation_metrics(prob, label, mask) ─► scorecard
measure(...) loops targets ─► cross_scroll_measurement.md   (same-scroll vs cross-scroll gap)
```

## Testing

`tests/test_detector_metrics.py` (CPU, synthetic, fast):
- **Perfect** pred ⇒ `val_f1≈1.0`, `average_precision≈1.0`.
- **Chance** pred (random) ⇒ `average_precision ≈ positive_rate`, `ap_prevalence_lift ≈ 1.0`.
- **Paint-everything** (all-ones) ⇒ `recall≈1`, `precision≈positive_rate`, `ap_prevalence_lift≈1.0`
  (collapse is *not* rewarded — the core guard).
- **Zero-positive mask** ⇒ returns `nan` + `note`, no raise.
- `metrics_by_threshold` length == number of thresholds.

`tests/test_detector_measure.py`: `measure` over two tiny synthetic fragments writes the report and returns a
dict with both targets' `val_f1`. (Uses the fake-fragment helper; injects a model, no checkpoint/GPU.)

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_metrics.py tests/test_detector_measure.py -v`

## Error handling

- Undefined metrics (empty positives / degenerate prob) ⇒ `nan` + `note`, never raise.
- Missing checkpoint or fragment ⇒ surface the underlying error clearly (harness does not swallow).
- `measure` continues over remaining targets if one fragment fails, recording the failure in the report.

## Operational note

The autoresearch loop is running on `main` and commits artifact paths; this work lives only under
`src/vesuvius_autoresearch/detector/` + `tests/` + `reports/detector/`, so it does not touch the loop. The
GPU `measure` run (~4 min/target) needs the loop paused (`.loop_paused` + kill, then `bash start.sh`).

## Follow-ups (documented, out of scope)

- Sub-project B: full-resolution segmentation model (ResEncUNet/SegFormer) optimized for F1.
- Sub-project C: bandit search loop optimizing held-out cross-scroll F1 with a fast per-cycle proxy.
- Raw-fragment cross-scroll alignment (PHerc1667/PHercParis1/PHerc51) — axis-order + label resampling.
- Retrain Scroll-1 → eval Scroll-2 as the "train one scroll, generalize to another" headline.
