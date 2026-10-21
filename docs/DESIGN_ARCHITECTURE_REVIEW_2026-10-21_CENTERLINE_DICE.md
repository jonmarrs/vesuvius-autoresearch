# Design and architecture review — what villa's centerline_dice measures

Date: 2026-10-21. Baseline: `42b5244e` (main after #173).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the topology metric the loop still uses after the July rewire.
- `train.select_topology_threshold` picks the binarization threshold for the reported topology metrics by maximising
  villa's `centerline_dice`.
- The prize-readiness record requires it to be at least `min_prize_centerline_dice` (0.01 in config.json).
- `repro/gp_winner/prize_gate_eval.py` reports the threshold whose value is largest. It takes one value per
  threshold, on the label's bounding box.

Earlier reviews found one way it exceeds 1: a slice with no ground-truth skeleton.
- `DESIGN_ARCHITECTURE_REVIEW_2026-10-12_TRAINING_STEP.md` and `…_2026-10-13_LABELED_DATASET.md` found it.
- The 2026-10-13 round drafted the villa fix, `docs/VILLA_DRAFT_centerline_dice_empty_slices.md` with its patch.
- The independent review of #173 found it above 1 by another route, on slices that do have ground truth.
- `METHOD.md` described the metric only as a "topological score".

Main has not moved since #173. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches.

## What changed

- **`METHOD.md` now gives the definition and both ways it exceeds 1.**
  - Villa's `segmentation/evaluation/metrics/centerline_dice.py`, at the pinned commit, Lee-skeletonizes each slice
    of the label and of the prediction. It then computes 2·|S_pred ∩ T(S_gt)| / (|S_gt| + |S_pred| + eps), where T is
    the set of pixels within 3.0 px (Euclidean) of the label's skeleton.
  - It equals the harmonic mean of its "sensitivity", the numerator over |S_gt|, and its "precision", the numerator
    over |S_pred|. The sensitivity is unbounded, so the metric is not the symmetric clDice: it is not bounded by 1,
    though it stays below 2.
  - **Route 1, a slice with no ground-truth skeleton:**
    - its distance map stays 0, so its tolerance region is the whole slice. Every predicted skeleton pixel on it
      counts as a hit, and an ink-free label with any prediction scores just under 2;
    - every value above 1 in the record came this way: 15 rows of `history.tsv` (2026-07-10/11) at 1.36–1.86, and
      the 1.349 incumbent of that time. The loop then scored each batch as one stack of slices;
    - it now scores each patch, and its per-patch metrics use only the ink-containing ones;
    - `scripts/evaluate_villa_metrics.py` still scores whole volumes;
    - the villa draft fixes this route.
  - **Route 2, a prediction skeleton longer than the ground truth's, mostly inside the tube.** It outscores an exact
    copy. On a 56-px stroke:

    | prediction | centerline_dice | skeleton length (label 56) | sensitivity |
    |---|---|---|---|
    | exact copy | 1.000 | 56 | 1.00 |
    | ragged: the stroke, with 35% of the pixels of the 9-px band around it set at random | 1.101 | 133 | 1.86 |
    | the stroke with 3-px teeth either side, every 2 px (80% of its skeleton inside the tube) | 1.325 | 270 | 3.86 |
    | the same stroke 25 px away | 0.000 | 56 | 0.00 |

  - So a threshold that maximises it can settle on a raggeder mask than one that matches the ink.
  - **Promotion:** `METHOD.md` says when the metric decides one. While `enforce_prize_gates` is false, as in
    config.json and the experiment configs, it decides none: promotion is on val_f1 with the AP-lift gate (since
    `3e28b182`, 2026-07-11). With it true, the `ExperimentConfig` default and `train.py`'s fallback for a missing key,
    a run that is not submittable is not promoted. Submittable needs a finite value, enough samples and ≥ 0.01.
- **`tests/test_villa_centerline_dice_range.py`** (3 tests) pins the cases against villa's metric as `train.py`
  imports it:
  - the exact copy scores 1 and the distant one 0;
  - the ragged and comb predictions give the cited values (1.10 and 1.33, within 0.005), the cited skeleton lengths,
    and a sensitivity above 1;
  - a label with no skeleton and a stroke predicted scores just under 2.

  They skip when villa's metric does not import, and they join the standard suite, as
  `test_validation_suite_covers_the_loop` requires of a test that imports `train`. If the pinned metric changes,
  they fail, and `METHOD.md`'s numbers with them.
- **The villa draft claimed too much.** Its one-sentence summary said the fix keeps the metric "in [0, 1]".
  - Applied to a copy of the metric, the patch leaves the comb at 1.3252.
  - The summary now says only what the patch does. A dated note under Details says what it leaves unchanged.
  - Nothing was posted.
- **Comments and docstrings:**
  - `train.py`'s comment above `TOPOLOGY_THRESHOLD_CANDIDATES` notes route 2.
  - `scripts/cldice_loss.py` called soft-clDice "the same notion the villa centerline_dice gate measures". It is the
    symmetric clDice, bounded by 1, and the docstring now says villa's is not.
  - `scripts/diagnose_topology_postproc.py`'s docstring notes that its skel_dist gate was dropped on 2026-06-26
    (`12303c3e`) as location-blind (`scripts/probe_skel_dist_validity.py`). It still prints that gate, now marked
    "dropped 2026-06-26".

## Verified, no change needed

- **The cases are villa's own metric.** `train.compute_centerline_dice` is villa's `compute`, imported from the pinned
  checkout (`ccb43181`), with `tolerance_radius=3.0` as the loop passes it.
- **`is_model_improvement`**, the pre-July rule that selected on centerline_dice, has no production caller. Only its
  tests call it.
- **Nothing else assumes the metric is at most 1.**
  - The ≥ 0.01 gate is one-sided.
  - `select_topology_threshold` handles values above 1.
  - `plot_results`' axis limit is on val_bpb.

## Observations for the owner (not changed)

- **Whether to keep maximising it.**
  - `select_topology_threshold` and `prize_gate_eval.py` both take the threshold with the largest value.
  - The bounded variant would rank the exact copy first: the harmonic mean of |S_pred ∩ T(S_gt)| / |S_pred| and
    |S_gt ∩ T(S_pred)| / |S_gt|. It scores the cases above 1.00, 0.88 and 0.89. A threshold chosen on F1 would also
    avoid the pull toward a raggeder mask.
  - Either changes the reported topology numbers, and the metric is villa's official one, so the choice is the
    owner's.
- **Upstream.** The local draft covers route 1 only. Whether to raise route 2 with villa, and whether to post the
  draft, are the owner's calls.
- **Current values:**
  - the tracked `best_model.pt`, re-scored under protocol v3, stores 0.169, from 10 samples;
  - `FINDINGS.md` gives about 0.34 for the loop's resenc_unet, and 0.10–0.12 for the GP-winner models.
  - These are far below 1, but a comparison between models or thresholds can still favour a raggeder mask.
- **A target can pass `ink_containing` yet be empty once binarized.** `ink_containing` keeps a patch whose target
  sums to at least 1, and the metrics binarize at > 0.5. A soft target summing to 1 or more with no pixel above 0.5
  would reach route 1. The loop's labels are binary today.

## Verification

- `pytest tests/test_villa_centerline_dice_range.py tests/test_diagnose_topology_postproc.py tests/test_cldice_loss.py tests/test_validation_suite_covers_the_loop.py`:
  23 passed. In a worktree without villa, the new tests skip cleanly.
- `test_audit_doc_references` reports nothing new for `METHOD.md`: its one flagged path is the existing exemption.
- Ruff 0.9.10 and ruff format are clean on the changed Python files.
- **The standard suite** on the first commit (`ffcc8d6d`) ran as on main: 2703 passed, with the same 42 failures and
  2 errors, all environmental. That is 2 more passes, this round's first two tests. The smoke test gave 9 of 11
  passed and 2 skipped, as on main.
- **Independent review** of the first commit. It reproduced the table exactly, using the metric copied from the
  pinned checkout, and confirmed the formula, the supremum of 2, the commits and the repository's uses.
  - Its blocking finding: this document said no review had looked at the metric, and missed the earlier draft,
    whose "[0, 1]" this round disproves.
  - Its should-fix findings:
    - the empty-slice route, which produced every value above 1 in the record;
    - "decides no promotion" holds only while `enforce_prize_gates` is false;
    - the stale 0.198.
  - Its nits:
    - the comb is not wholly inside the tube;
    - the ragged case's description;
    - the test asserted bounds, not the cited numbers;
    - `is_model_improvement`'s test caller;
    - `prize_gate_eval.py`'s single value;
    - the printed skel_dist gate;
    - `cldice_loss.py`'s docstring.

  All are addressed above.
