# villa's scorer is a coarser instrument than the render it reads; at region scale, neither tracks label density

> **Correction (2026-10-04, `reports/supervised_reanalysis.md`):** computed on the whole surface; villa's labels exist only inside its supervision mask, which explains much of Q1's 'ambiguous null'. On the supervised region Q2 **survives** (ratio 0.55 → 0.74). Q1 is undetermined under the registered rule. A **post-hoc** version on supervised tiles finds the render tracks label density (ρ = +0.61) but the scorer count only weakly (ρ = +0.15). That is a lead, not a finding. Tested in finding 78 (`reports/scorer_tracking_gap.md`): it holds across tile sizes, but the strip may be in-sample for villa's 3D ink model; the scorer marks about 2% of annotated ink.

**2026-10-04.** Result of `docs/preregistration/2026-10-04_objective_vs_labels.md` (committed `3a60253d`
before either statistic was computed). Inputs: finding 72's stored outputs (8 labelled segments, default
mode, villa's metric settings, label level 3 at 19.2 µm/px). Data: `reports/objective_vs_labels.json`.

## The starting observation (post hoc, which is why this was then registered)

Per pixel, villa's 2D scorer agrees with villa's labels about half as well (AP) as the rendered strip it
reads, on all 8 segments:

| | AP | AUC |
|---|---|---|
| rendered strip (the scorer's input) | 0.029 – 0.101 | 0.66 – 0.74 |
| scorer probability (its output) | 0.018 – 0.045 | 0.56 – 0.62 |

## Q1: does the objective's count track labelled ink across regions?

26 windows (2048 px, full height, ≥ 25% on the surface). Densities per window, inside the surface:

| quantity vs label density | Spearman ρ | 95% CI (bootstrap over segments) |
|---|---:|---|
| scorer fg density (what `total_fg_pixels` counts) | **+0.04** | [−0.22, +0.45] |
| strip mean intensity (the render) | +0.10 | [−0.27, +0.58] |

* **Prediction 1 ("the objective tracks labelled ink across windows, ρ > 0.3"): FAILED.**
* **Prediction 2 ("the strip tracks it at least as well"): held,** but both are near zero.

**This null is ambiguous, and it is not "the objective does not track ink".** The raw 3D-ink render agrees
with the labels per pixel (AUC 0.66–0.74), yet its window density does not track label density either.
That points at the labels as much as at the objective. If villa's labels are not exhaustive (ink
annotated in some regions and not others), label density across windows measures **annotation coverage**,
not ink amount. These data cannot tell the two readings apart. The intervals are also wide: 26 windows in
8 clusters.

## Q2: is the scorer measuring coverage rather than strokes?

AP against labels dilated by r px (pooled over the 8 segments):

| r (px; µm) | AP scorer | AP strip | ratio scorer / strip |
|---|---:|---:|---:|
| 0 (stroke labels) | 0.0286 | 0.0633 | 0.452 |
| 1 (19 µm) | 0.0301 | 0.0632 | 0.475 |
| 2 (38 µm) | 0.0315 | 0.0630 | 0.500 |
| 4 (77 µm) | 0.0342 | 0.0622 | 0.550 |
| 8 (154 µm) | 0.0395 | 0.0609 | 0.648 |

* **Prediction 3 ("the ratio rises with r, and r = 8 > r = 0"): HELD.** The scorer's agreement improves as
  the labels are coarsened, while the strip's slightly declines. The scorer measures at a coarser scale
  than strokes, consistent with an ink-**coverage** model.
* Even at 154 µm it has not caught up with its own input (ratio 0.65).

## What it means

* **The scorer is a coverage-scale instrument.** Part of its low per-pixel agreement with stroke labels
  is scale, not error. Within 154 µm, though, it still agrees less with villa's labels than the render it
  reads.
* **Whether villa's objective tracks ink at region scale is not established either way.** Answering it
  needs labels known to be exhaustive within the regions compared, or another ground truth. A natural
  next check is whether villa's label release documents its coverage.

## Limits

The labels are partly pseudo-labels; one scroll, one 3D ink model. 26 windows clustered in 8 segments.
Default mode only.
