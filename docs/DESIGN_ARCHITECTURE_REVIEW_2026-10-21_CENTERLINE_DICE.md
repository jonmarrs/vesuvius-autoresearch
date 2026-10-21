# Design and architecture review — what villa's centerline_dice measures

Date: 2026-10-21. Baseline: `42b5244e` (main after #173).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the topology metric the loop still uses after the July rewire.
- `train.select_topology_threshold` picks the binarization threshold for the reported topology metrics by maximising
  villa's `centerline_dice`.
- The prize-readiness gate requires it to be at least `min_prize_centerline_dice` (0.01 in config.json).
- `repro/gp_winner/prize_gate_eval.py` reports the threshold that maximises it.

The independent review of #173 noticed it can exceed 1. No review had looked at its definition, and `METHOD.md`
described it only as a "topological score".

Main has not moved since #173. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **`METHOD.md` now says what the metric is and that it is not bounded by 1.**
  - Villa's `segmentation/evaluation/metrics/centerline_dice.py`, at the pinned commit, skeletonizes each slice of the
    label and of the prediction. It then computes 2·|S_pred ∩ T(S_gt)| / (|S_gt| + |S_pred|), where T(S_gt) is the
    3-px tube around the label's skeleton.
  - That is not the symmetric clDice, whose two terms are each a fraction of one skeleton. Here only the prediction's
    skeleton is tested against a tube. So a prediction whose skeleton is longer than the label's, and lies inside the
    tube, scores above an exact copy, up to 2. Its "sensitivity" (the same numerator over the label's length) exceeds
    1 too.
  - On a 56-px stroke:

    | prediction | centerline_dice | skeleton length (label 56) | sensitivity |
    |---|---|---|---|
    | exact copy | 1.000 | 56 | 1.00 |
    | ragged: 35% of the 9-px band around the stroke filled | 1.101 | 133 | 1.86 |
    | the stroke with 3-px teeth either side, every 2 px | 1.325 | 270 | 3.86 |
    | the same stroke 25 px away | 0.000 | 56 | 0.00 |

  - So a threshold that maximises it can settle on a raggeder mask than one that matches the ink. `METHOD.md` also
    says that the metric decides no promotion. Promotion has been on val_f1 with the AP-lift gate since 2026-07-11, and
    `is_model_improvement`, the earlier rule that used it, is no longer called. It is reported, and gated only at
    ≥ 0.01.
- **`tests/test_villa_centerline_dice_range.py`** (2 tests) pins those cases against villa's metric as `train.py`
  imports it:
  - the exact copy scores 1 and the distant one 0;
  - the ragged and comb predictions have longer skeletons, score above 1.05 and 1.25 respectively, and stay below 2,
    with a sensitivity above 1.

  They skip when villa's metric does not import. They join the standard suite, as
  `test_validation_suite_covers_the_loop` requires of a test that imports `train`. If the pinned metric ever becomes
  bounded, they fail, and `METHOD.md`'s statement with them.
- **`train.py`'s comment above `TOPOLOGY_THRESHOLD_CANDIDATES`** says the same in four lines. Only the comment
  changed.
- **`scripts/diagnose_topology_postproc.py`'s docstring** still introduced the tool by the skel_dist ≤ 2.0 gate.
  #173 made it measure what the loop measures, but that gate was dropped on 2026-06-26 (`12303c3e`): skel_dist
  compares branch-length histograms and is blind to location (`scripts/probe_skel_dist_validity.py`). The docstring
  now says so, and repeats the centerline_dice caveat.

## Verified, no change needed

- **The cases are villa's own metric.** `train.compute_centerline_dice` is villa's `compute`, imported from the pinned
  checkout, with `tolerance_radius=3.0` as the loop passes it.
- **No promotion depends on it.** `promotion_decision` decides on val_f1 with the AP-lift gate. `is_model_improvement`
  survives in `train.py`, but nothing calls it.
- **The gate.** `min_prize_centerline_dice` is 0.01 in config.json and in each experiment config that sets it, so a value above 1
  only passes a gate that a correct prediction passes too.

## Observations for the owner (not changed)

- **Whether to keep maximising it.**
  - `select_topology_threshold` and `prize_gate_eval.py` both take the threshold with the largest mean
    centerline_dice.
  - A bounded variant would remove the pull toward ragged masks: the harmonic mean of |S_pred ∩ T(S_gt)| / |S_pred|
    and |S_gt ∩ T(S_pred)| / |S_gt|. So would a threshold chosen on F1.
  - Either changes the reported topology numbers, and the metric is villa's official one, so the choice is the
    owner's.
- **Upstream.** The definition is villa's. Raising it there, or not, is the owner's call. This round drafted and
  posted nothing.
- **The reported values are far below 1** (the incumbent's 0.198 in June, ~0.1 for the GP-winner models in
  `FINDINGS.md`), so they are not inflated past 1. A comparison between two models or thresholds can still favour the
  raggeder mask.

## Verification

- `pytest tests/test_villa_centerline_dice_range.py tests/test_diagnose_topology_postproc.py tests/test_topology_threshold.py tests/test_validation_suite_covers_the_loop.py`:
  23 passed.
- `test_audit_doc_references` reports nothing new for `METHOD.md`: its one flagged path is the existing exemption.
- Ruff 0.9.10 and ruff format are clean on the changed Python files.
- PLACEHOLDER: standard suite and smoke.
- PLACEHOLDER: independent review.
