# ScrollGT's fiber rankings hold against villa's current annotations; its reference mask's coverage was overstated

**2026-10-10.** Result of `docs/preregistration/2026-10-10_scrollgt_current_annotations.md` (pre-registration
`6185a0a6`, before any scoring). Data: `reports/scrollgt_current_annotations.json`. Script:
`scripts/scrollgt_current_annotations_analysis.py`.

**Question.** ScrollGT's 11 fiber targets come from villa's `fiber-skeletons` Dataset001 (2025-01). villa's latest
release, Dataset004 (2025-07-28), revises three of them, adding 28–53% more fibers. The other eight are byte-identical,
and so is the CT of all three, so the reference mask and every floor labelling are unchanged. Do the published
comparisons survive the current annotations?

## Fidelity: exact

Against the shipped ground truth, every recomputed row equals its published value on all three cubes: the oracle, the
four floors, finding 80's tracer row, and finding 81's frozen-configuration numbers.

## Results (fiber scoring version 2, tolerance 2.0; shipped → current ground truth)

| cube | fibers | oracle ERL | cc ERL | tracer ERL | cc ERLpen | tracer ERLpen | frozen ERLpen | cc coverage | tracer coverage |
|---|---|---|---|---|---|---|---|---|---|
| s1_00497_02497_02997 | 109 → 140 | 219.38 → 228.92 | 213.41 → 196.39 | 55.07 → 52.39 | 65.37 → 45.37 | 40.61 → 35.46 | 42.83 → 38.04 | 0.9322 → 0.8197 | 0.7038 → 0.6136 |
| s1_08997_02997_02497 | 105 → 161 | 257.43 → 246.70 | 201.51 → 174.24 | 44.91 → 44.97 | 112.16 → 62.90 | 40.58 → 36.25 | 40.75 → 36.86 | 0.9001 → 0.7617 | 0.6707 → 0.5598 |
| s5_14997_01497_01497 | 147 → 179 | 242.23 → 242.18 | 188.89 → 172.25 | 46.62 → 44.96 | 33.09 → 24.29 | 38.56 → 33.62 | 40.28 → 35.72 | 0.8841 → 0.8185 | 0.6586 → 0.5932 |

Merges and precision, the other two registered quantities:

| cube | cc merges | tracer merges | cc precision | tracer precision |
|---|---|---|---|---|
| s1_00497_02497_02997 | 63 → 87 | 47 → 48 | 0.2929 → 0.3077 | 0.3285 → 0.3474 |
| s1_08997_02997_02497 | 46 → 89 | 15 → 53 | 0.2963 → 0.3249 | 0.3224 → 0.3729 |
| s5_14997_01497_01497 | 103 → 133 | 51 → 78 | 0.3373 → 0.3612 | 0.4012 → 0.4339 |

* **P1 HELD, 3 of 3.** Connected components keeps its raw-ERL lead over the tracer (3.7–3.9× on current ground truth).
* **P2 HELD, 3 of 3.** Precision rises for both. Predicted voxels near the newly annotated fibers become hits.
* **P3 HELD, 3 of 3.** Merges rise for both. The tracer's one-merge rise on `s1_00497_02497_02997` (47 → 48) is the
  smallest.
* **P4 HELD.** On `s5_14997_01497_01497` the tracer's ERLpen stays above connected components' (33.62 vs 24.29). The lead
  widens from +16.5% to +38.4%.

**Descriptive:**
* **No published ranking reverses.** The tracer still trails connected components on ERLpen on both s1 cubes. The frozen
  configuration still beats the baseline on all three, as finding 81 reported.
* **Every labelling's coverage falls**, connected components' by 6.6 to 13.8 points. Connected components labels the whole
  reference mask, so its coverage is the mask's. The annotations grew by 5,441, 9,347 and 6,186 voxels of fiber. The
  length within 2 voxels of the mask grew by only 1,622, 3,722 and 3,086, which is 30%, 40% and 50%. This is net of the
  4–11% of old length the revisions moved. Half to 70% of the fiber the revisions added lies outside the reference mask.
* **Connected components' ERLpen falls by 27–44%, the tracer's by 11–13%.** Large instances absorb more of the new fibers.
* The oracle's splits on `s1_00497_02497_02997` fall from 327 to 265 and stay far above the other two revised cubes
  (12 and 14). The current annotation still has fibers that leave and re-enter the cube.

## What it means

ScrollGT's comparisons were measured against incomplete ground truth on three cubes. None of them changes direction. The
magnitudes do: connected components' merge-penalized lead on the s1 cubes shrinks from 1.6–2.8× to 1.3–1.7×.

The larger correction concerns the reference mask. On the shipped annotations, `fiber_hz_vt` at P ≥ 0.5 reaches
0.88–0.93 of ground-truth length within 2 voxels. On the current annotations it reaches 0.76–0.82, because half or more
of the fiber the revisions added lies outside it.

A likely explanation, inferred and not tested: the mask trained on the annotations the revisions corrected. Its
`dataset_fingerprint.json` matches villa's Dataset002 exactly (13 cubes at 256³, 5 at 512³), and Dataset002 holds all 11
targets in their earlier versions. A model trained on annotations that missed some fibers would tend to miss them too.
Its coverage on these targets would then be training-set coverage, measured against the same omissions it learned.

## Limits

* Three cubes. Added and corrected fibers cannot be separated, since the revisions do both.
* Whether the eight unchanged cubes are complete cannot be checked. They match villa's latest release.
* The reference mask and the tracer's semantic layer trained on these cubes. Nothing here measures generalization.

## What follows

ScrollGT adopts the Dataset004 annotations for the three cubes, recomputes their oracle and floor rows, records each
target's NML version and hash, and discloses that the reference mask was trained on every target. A held-out fiber split
is possible: Dataset004 holds 10 annotated cubes absent from Dataset002 and 003 (eight Scroll 3 at 512³, two Scroll 5 at
256³), published after `fiber_hz_vt`.
