# Method

## Goal

Produce honest, reproducible ink-detection results on the Vesuvius Challenge with
every claim gated by evidence rather than ad-hoc judgement. Two strands: a
**productionized detector pipeline** (replication → measurement → distillation onto
the open SOTA data) and an **autonomous search loop** over training configurations.

## Detector pipeline (2026-06/07)

1. **Replicate the proven reference.** The 2023 Grand-Prize TimeSformer recipe was
   replicated end-to-end (vendored scripts), then re-trained from scratch on our own
   fragments to verify environment, data, and recipe independently (held-out ROC-AUC
   0.905 on reference segments; 0.711 on our Fr47→Fr143 split).
2. **Productionize.** The recipe became the tested `vesuvius_autoresearch.detector`
   subpackage (config/data/model/train/infer/eval/cli, one-command `reproduce`),
   with each defect found on the way (inference normalization, checkpoint loading,
   shape alignment) fixed under a regression test.
3. **Measure under the community contract** (below), same-scroll and cross-scroll.
4. **Distill onto the open SOTA data.** With no ground-truth labels aligned to the
   re-flattened SOTA surface volumes, the recipe is trained against the released
   canon ink predictions (teacher–student distillation): disjoint train/held-out
   segments, a chance-floor baseline measured first, teacher provenance
   (dtype/range/threshold) persisted, and every metric labeled
   *agreement-with-teacher* — never ground-truth accuracy.

## Search loop

Each cycle of `run_autoresearch_loop.py`:

1. **Sample a configuration.** A bandit-style sampler draws from a configuration
   space — architecture (gated UNet-transformer, TimeSformer, ResNet3D-101,
   Inception-I3D), loss terms, augmentation settings, and related hyperparameters.
   Families that have produced improvements are weighted up; duplicates are
   re-sampled for diversity.
2. **Preflight smoke check.** Before spending the training budget, the candidate is
   built and run through one forward/backward pass on a synthetic batch
   (`train.py --smoke`). A configuration that cannot build or run is skipped
   immediately rather than consuming a cycle.
3. **Train under a fixed budget.** The candidate trains for a fixed wall-clock
   budget (≈60 minutes) on the training fragment.
4. **Evaluate on held-out data.** The model is scored on a separate validation
   fragment it never trained on (train/predict non-overlap), producing `val_bpb`
   plus topological metrics.
5. **Keep only if better.** The new configuration is promoted only if it improves
   on the current baseline; otherwise it is reverted. The outcome of every cycle is
   appended to `results.tsv`.

## Evaluation metrics

The **community metric contract** (`detector/metrics.py`), used for all detector and
distillation results — mask-restricted and pooled over the fragment:

- **`val_f1`** (threshold-swept F1; = Dice for binary) — primary, with the fixed-0.5
  counterpart `f1_at_0.5` reported alongside.
- **`average_precision`** (PR-AUC) and **`ap_prevalence_lift`** (AP ÷ label prevalence;
  ≈1 ⇒ chance) — the imbalance-robust honesty gates. A paint-everything predictor is
  not rewarded.
- **ROC-AUC** — secondary diagnostic only, never an optimization target (it is
  over-optimistic under class imbalance).
- **`centerline_dice`** — topological score, evaluated at the topology-optimal
  binarization threshold (the Dice-optimal threshold understates it ~2×).
- **Removed: `skeleton_distance_length`.** Formerly used as a selection signal and a
  "prize gate" (≤ 2.0); we proved it invalid for ink detection — it compares skeleton
  branch-length *histograms* and is blind to spatial location (a zero-overlap
  prediction scores 0.0 and passes). Probe: `scripts/probe_skel_dist_validity.py`.
- **`val_bpb`** — the loop's historic gate (bits-per-byte on held-out validation);
  retained as a guard rail for the loop, but demonstrated to be a weak discriminator
  (see `FINDINGS.md`), which is why the contract above exists.

## Constraints honored

- **ML window ≤ 64×64 px lateral at ~8 µm** — within the Challenge's
  hallucination-mitigation cap; depth (through-surface slices) is not subject to the
  lateral limit.
- **No train/predict overlap** — training and validation use disjoint fragments; the
  distillation run uses disjoint *segments* (verified in review).
- **No fabricated ground truth** — where no aligned ground-truth label exists (the
  open SOTA data), results are labeled agreement-with-teacher or reported
  qualitatively; we do not score against misaligned labels.

## Honest scope

This is research tooling plus a working-but-not-legible detector, stated plainly:
same-scroll detection at the prize window is real (`val_f1` 0.393 / lift 2.07);
cross-scroll transfer without retraining is weak (lift 1.29) — the quantified open
problem; the SOTA-distilled model (`val_f1` 0.662 / lift 3.24 *vs teacher*) shows the
open data + distillation closing that gap on one GPU. The loop's own from-scratch
stack remains at the chance floor, with the full diagnosis (and every negative
result) in `FINDINGS.md`. The contribution offered is the reproducible,
evidence-gated process and the honest measurement discipline — not a
state-of-the-art model claim.
