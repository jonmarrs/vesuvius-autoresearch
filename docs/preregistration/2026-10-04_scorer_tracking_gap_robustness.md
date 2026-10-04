# Pre-registration: is the scorer-vs-render tracking gap robust across render conditions and tile sizes?

**Written 2026-10-04, before any statistic below was computed.** Script `scripts/scorer_tracking_gap.py`,
committed with this file.

## What prompted it (post hoc)

Finding 77's post-hoc analysis used 256-px tiles that are ≥ 50% mesh-valid and supervised, on the default
(linear) arm of finding 72 (8 labelled segments, villa's metric settings, label level 3). Within villa's
annotated regions:
* the rendered strip's ink density tracks labelled-ink density: Spearman ρ = **+0.61** [+0.42, +0.69];
* villa's scorer fg density (what `total_fg_pixels` counts) tracks it only weakly: ρ = **+0.15**
  [+0.01, +0.21].

A gap that large, found after the fact, needs testing before it is reported as a property of villa's
objective.

## What this can and cannot test

The only labels on the current frame are those 8 segments, so this is a **robustness** test, not a
replication on new data. It asks whether the gap survives three other stored render conditions of the same
surfaces, which differ in render mode, grid, and therefore in both strip and scorer output, and two other
tile sizes. Generalisation to other segments stays untested.

## Method

* **Arm sets** (each with the strip the scorer read and the scorer's saved mask):
  * `scorer_study/<seg>/smooth`: finding 72, smooth mode;
  * `scorer_study_coarse/<seg>/linear` and `.../smooth`: finding 73, meshes subsampled 4×.

  The original `scorer_study/<seg>/linear` is reported as the reference, not counted toward the test.
* **Tiles** of 128, 256 and 512 px that are ≥ 50% mesh-valid ∩ supervised (labels and supervision at
  level 3).
* **Per tile:** strip density (mean intensity / 255), scorer density (mask fraction), label density.
  Spearman ρ against label density, 95% bootstrap over segments (2000 resamples, seed 20261004).

## Predictions, fixed now

1. **At 256 px, in each of the three new arm sets, ρ(strip) − ρ(scorer) ≥ 0.3.** Confidence moderate.
2. **In all 9 new cells (3 arm sets × 3 tile sizes), ρ(strip) > ρ(scorer).** Confidence moderate.

If both hold, the gap is reported as robust **on these 8 segments** across render mode, grid and tile
scale. If either fails, it is reported as condition-dependent and does not go in the October filing.

## Confounds

The same 8 segments and labels throughout; the labels are partly pseudo-labels; the arm sets share
surfaces. A tile's strip density and its label density can both rise with papyrus texture, so the strip's
higher ρ is not by itself proof that the strip is "right". The test is of the **gap**.
