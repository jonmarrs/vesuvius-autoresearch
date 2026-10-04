# Pre-registration: does villa's ink-count objective track villa's own ink labels?

**Written 2026-10-04, before either statistic below was computed.** Script
`scripts/analyse_objective_vs_labels.py`, committed with this file. Inputs: finding 72's stored outputs
(`spiral_out/gt_interp/scorer_study/<seg>/linear/`, the default-mode arm), so nothing is rendered.

## What prompted it (already seen, post hoc)

In finding 72's data, on all 8 labelled segments at label level 3, villa's 2D scorer's probability map
agrees with villa's labels much less per pixel than the rendered strip it reads. AP falls from
0.029–0.101 to 0.018–0.045, about half in every segment, and AUC from 0.66–0.74 to 0.56–0.62. The scorer
is an ink-**coverage** model built to count inked area, so this may reflect a coarser target rather than
lost information. Two questions follow, registered here before computing.

## Q1: does the objective's count track labelled ink across regions?

* **Units:** 2048-px full-height column windows of each segment's canvas (as in finding 72), with at
  least 25% of the window on the mesh-valid domain.
* **Densities, not counts.** Raw counts both scale with a window's domain area, which would correlate
  them trivially. So per window, inside the domain:
  * **scorer density** = scorer mask pixels (`seg_mask.png`, what `total_fg_pixels` counts) / domain px;
  * **label density** = labelled-ink px / domain px;
  * **strip density**, as a reference = mean strip intensity / 255.
* **Statistic:** Spearman ρ between scorer density and label density, pooled over all windows, with a
  95% bootstrap interval resampling **segments** (2000 resamples, seed 20261004), since windows within a
  segment are not independent. The same for strip density.

## Q2: is the scorer measuring coverage rather than strokes?

* Dilate the labels by r ∈ {0, 1, 2, 4, 8} px (level-3 px = 19.2 µm; up to about 154 µm).
* For each r, compute the AP of the scorer probability (quantised to 256 levels) and of the strip against
  the dilated labels on the domain, pooled over segments, and the ratio AP(scorer) / AP(strip).

## Predictions, fixed now

1. **Q1: the objective tracks labelled ink across windows:** scorer-density ρ > 0.3, with its interval
   excluding 0. Confidence moderate.
2. **Q1: the raw strip tracks it at least as well:** strip ρ ≥ scorer ρ. Confidence low.
3. **Q2: the scorer is the coarser instrument:** AP(scorer) / AP(strip) rises with r, and is higher at
   r = 8 than at r = 0. Confidence low.

## What would follow

* If (1) fails, villa's loop optimises a count that does not track where villa's labels put ink, at
  region scale.
* If (1) holds and (3) holds, the scorer measures coverage, and its low per-pixel agreement with stroke
  labels is a matter of scale, not error.

## Confounds

The labels are partly pseudo-labels; one scroll, one 3D ink model. The windows are few (about 26) and
clustered in 8 segments; the bootstrap over segments is the honest interval.
