# Pre-registration: do ScrollGT's published fiber conclusions hold against villa's current annotations?

**Written 2026-10-10, before any labelling was scored against the current annotations.** Analysis
`scripts/scrollgt_current_annotations_analysis.py`, committed with this file on branch `scrollgt-current-annotations`.

## The question

ScrollGT's 11 fiber targets were exported from villa's `fiber-skeletons` Dataset001 (2025-01-24). villa's latest release,
Dataset004 (2025-07-28), revises three of them. If the revisions change who beats whom, ScrollGT has been publishing
rankings measured against incomplete ground truth. That includes finding 80's one 256³ cube where our tracer beats
connected components, `s5_14997_01497_01497`, which is one of the three. If nothing changes, the correction is
bookkeeping. Either way ScrollGT should carry the current annotations. This study decides which published claims
survive the change.

## Already measured: ground truth against ground truth, no labelling scored

* **What changed.** All 11 Dataset004 NMLs were hash-compared with the files ScrollGT was built from. Eight are
  byte-identical. Three are new versions:

  | cube | NML version | fibers scored | in-bounds length | new length > 2 vx from old | old length > 2 vx from new |
  |---|---|---:|---:|---:|---:|
  | s1_00497_02497_02997_256 | v00 → v01 | 109 → 140 | +21% | 26.3% | 10.5% |
  | s1_08997_02997_02497_256 | v00 → v01 | 105 → 161 | +37% | 34.5% | 10.2% |
  | s5_14997_01497_01497_256 | v01 → v02 | 147 → 179 | +21% | 20.5% | 4.2% |

  Length is approximate (0.5-voxel resampling, ScrollGT's step, counting in-bounds samples). Control: the unchanged
  `s1_00497_01497_03997` gives 0.0% both ways.
* **The CT did not change.** For the three cubes, Dataset004's `imagesTr` files are byte-identical to the ones ScrollGT's
  reference mask was computed from. The mask, and therefore every floor labelling, is unchanged. Only the ground truth
  moves.
* **The reference mask is in-sample (context; it changes nothing measured here).** `scrollprize/fiber_hz_vt`'s
  `dataset_fingerprint.json` lists 18 training cases, 13 at 256³ and 5 at 512³. That is exactly Dataset002's
  composition, and Dataset002 contains all 11 ScrollGT cubes. ScrollGT does not say so. It will.

## Method

* **Scorer:** ScrollGT 0.4.1 (`score_tracing`, fiber scoring version 2), tolerance 2.0, unchanged.
* **Old ground truth:** each target's shipped skeleton (`load_fiber_target`).
* **Current ground truth:** the Dataset004 NML (`spiral_out/fiber_d004/nml/`), parsed with ScrollGT's own `parse_nml`,
  same origin, same filter (fibers with more than one in-bounds node).
* **Labellings, each scored against both:**
  * the oracle (`oracle_from_skeleton` of that ground truth itself);
  * the four floors (`_floor_rows` on the unchanged mask);
  * the tracer baseline: finding 80's labellings (`spiral_out/tracer_rescore/`);
  * the tracer frozen configuration: finding 81's labellings (`spiral_out/tracer_frozen/`).
* **Fidelity gate.** Against the old ground truth, every recomputed row must equal the published one exactly:
  * the five computed rows (oracle and four floors) and the `tracer_strict_relink` row, from each target's `meta.json`;
  * the frozen configuration's ERL, ERLpen, coverage, splits, merges and instance count, from
    `reports/tracer_frozen_v2.json`.

  One mismatch and the script reports FIDELITY FAILED and no verdict.

## Predictions, fixed now

Each applies to the three revised cubes, current against old ground truth.

1. **Connected components keeps its raw-ERL lead over the baseline tracer on all 3.** Confidence high. Its lead is 3.9–4.5×
   on these cubes, and new ground truth adds fibers inside the same mask components.
2. **Precision rises for both connected components and the baseline tracer, on all 3.** Confidence high. New ground truth
   adds 20–35% of length that lies more than 2 voxels from any old fiber. Predicted voxels near it become hits. Only
   4–11% of old length moved away.
3. **Merges rise for both connected components and the baseline tracer, on all 3.** Confidence moderate-high. More
   annotated fibers inside the same instances means more instances touch two or more of them.
4. **On `s5_14997`, the baseline tracer's ERLpen stays above connected components'** (38.56 vs 33.09 published).
   Confidence moderate, about 60%. Both labellings gain merges, and I cannot say which gains more.

**Descriptive, with no prediction:**
* coverage, whose direction depends on whether the new fibers lie inside the mask;
* the oracle's splits on `s1_00497_02497_02997` (327 against old ground truth; 2–44 on the other s1 cubes);
* whether the tracer overtakes connected components on ERLpen on either s1 cube;
* the frozen configuration's standing.

## Decision rule

| outcome | conclusion |
|---|---|
| fidelity gate fails | the instrument is wrong. No verdict; find the mismatch first. |
| gate passes | report every row, both ground truths, side by side. Each prediction is held or failed as registered. |
| finding 80's `s5_14997` lead does not survive (P4 fails) | finding 80's "ahead on 4 of 11" and ScrollGT's matching claim become 3 of 11 on current annotations, with a correction notice. Finding 81's "same 4 cubes" sentence gets the same treatment. |
| any ranking between published rows reverses on an s1 cube | stated as a reversal in ScrollGT's correction notice, cube by cube. |

ScrollGT moves to the current annotations whatever the outcome; this rule decides only what the notice says. The
decision to adopt them does not depend on the scores.

## What the result cannot do

* It cannot separate added fibers from corrected ones: the revisions do both (4–11% of old length moved).
* It cannot say whether the remaining eight cubes are complete. They match villa's latest release, which is all that can
  be checked.
* It says nothing about generalization. The mask trained on these cubes, and so did the tracer's semantic layer.
* Three cubes. Any count out of three is a description of these cubes, not a rate.

## Cost

CPU only, about 2–4 minutes per cube per ground truth (the connected-components floor dominates). No new tracing, no
GPU, no network.
