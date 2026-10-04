# Grid cell size drives the linear/smooth difference; on coarse grids smooth renders slightly more faithfully but the count swings far more

> **Correction (2026-10-04, `reports/supervised_reanalysis.md`):** agreement was computed on the whole surface; villa's labels exist only inside its supervision mask. On the supervised region prediction 2 still **fails** as registered (smooth's scorer ≥ linear in 3 of 8). The secondary raw-render result **survives, smaller**: resolved in 8 of 8, median **+0.84%** of AP (not ~1–2%).

**2026-10-03.** Result of `docs/preregistration/2026-10-03_coarse_grid_interpolation.md` (committed
`f59ff84b` before any arm was scored). Data: `reports/scorer_vs_labels_coarse.json`. The fine-grid
comparison is finding 72, `reports/scorer_vs_labels.json`.

## The question

* **Finding 70** (a fitted spiral flat, ~80-voxel grid cells): smooth vs linear moved the 2D-scorer
  count up to ±20% per window.
* **Finding 72** (villa's labelled segment meshes, ~20-voxel cells): about 1%, with no change in label
  agreement.
* **Not the normalisation:** tested, and that prediction failed.
* Linear and smooth agree at grid points and differ only inside cells, so this study subsamples the 8
  labelled segment meshes 4× (to ~80-voxel cells, like the spiral surfaces villa's loop scores). It
  reruns finding 72's pipeline unchanged.

## Result

All 8 segments pass the alignment gate.

| | fine grid, 20 vx (finding 72) | **coarse grid, 80 vx (this study)** |
|---|---:|---:|
| median window \|Δ count\| | 1.3% | **6.2%** |
| windows with \|Δ\| ≥ 5% | 4 of 26 | **15 of 26** |
| window range | −9.0% … +7.4% | **−31.9% … +41.5%** |
| segment totals | −3.6% … +4.1% | **−7.9% … +19.4%** |
| scorer-probability ΔAP, resolved + / − | 0 / 0 | 1 / 0 (smooth ≥ linear in 2 of 8) |
| raw-render ΔAP, resolved + / − | 0 / 0 (\|ΔAP\| ≤ 0.0002) | **6 / 0** (smooth > linear in 7 of 8) |

Raw-render ΔAP on coarse grids, per segment: +0.00083, +0.00028, +0.00056, +0.00102, −0.00006,
+0.00131, +0.00081, +0.00168, on linear APs of 0.029–0.099. That is about +1–2% relative.

## Predictions, as registered

1. **"Cell size drives the count difference" (coarse median window |Δ| ≥ 3%): HELD** (6.2%, vs 1.3% on
   fine grids). This explains why finding 70 and finding 72 disagreed.
2. **"Smooth reads better on coarse grids" (scorer-probability AP ≥ linear's in ≥ 6 of 8): FAILED**
   (2 of 8). By the decision rule: no consistent difference in the scorer's agreement with the labels.

**Secondary, pre-specified (finding 72's pipeline reports it):** the raw rendered 3D-ink prediction
agrees **slightly better** with villa's labels under smooth on coarse grids. ΔAP > 0 is resolved in 6 of
8, which would meet the decision rule's threshold had this been the primary outcome. It was not, and it
is reported as secondary. Its size is ~1–2% of AP.

## What it means

* **The mechanism is confirmed.** The render-mode effect scales with grid cell size. On villa's 20-voxel
  segment meshes it is about 1%. On the ~80-voxel cells of the spiral surfaces villa's loop scores, it
  moves the scorer count by up to +19% per segment and −32% to +42% per window.
* **On coarse grids, smooth renders slightly more faithful ink, as #1818 intends,** but the 2D scorer
  does not pass that on. Its agreement with the labels does not consistently change.
* **For villa's loop, this is the decision-relevant size.** If anyone renders the loop's spiral surfaces
  with `smooth`, or the default flips, the objective shifts by up to tens of percent per region against
  a ~1–2% change in raw faithfulness and none in the scorer's. Mixed-mode comparisons on spiral surfaces
  are badly biased. Never mix modes (inkdelta flags it); on these surfaces, report the mode with every
  number.
* **Synthesis f70–f73:** the count's sensitivity to render interpolation is real, grows with grid
  coarseness, and is far larger than any change in agreement with villa's labels.

## Limits

* The coarse grids are subsampled segment meshes, not fitted spiral surfaces. They match the spiral
  surfaces in cell size, not in how they were made. Same 8 segments, one scroll, one 3D ink model;
  the labels are partly pseudo-labels from fine-grid linear geometry.
* The descriptive fine-vs-coarse comparison of linear AP is mixed (coarse higher in 6 of 8). The domains
  and normalisations differ slightly, so it is not interpreted.
* No meaningless-perturbation control in this pipeline. On coarse grids the effects are far above
  finding 70's control maximum (2.8%), but that control was in another pipeline.

## Post hoc, descriptive: grid density alone moves the default-mode count, but the loop cannot change it

Computed from the two committed JSONs, with no new run. For the same 8 surfaces under the **default
(linear)** mode, the scorer count on the 4×-coarser grid vs the original:
* −4.48%, +2.91%, +4.61%, **+15.85%**, **−9.37%**, −8.82%, −0.83%, +2.95%;
* median +1.0%, pooled +3.1%.

A coarser grid is also a cruder approximation of the surface between points, so this is "density
changes the objective", not a pure render artefact.

**Not a loop lever.** The flat grid's spacing is set by `flatten_output_step: 20.0` in villa's
`lasagna/configs/flatten_fast_nofilter.json`, one of the frozen "flatten settings" in `autoresearch.md`.
It matters only if villa itself changes that setting: comparisons across the change would then shift
by up to about ±10–16% per segment. Not pre-registered; recorded so the observation is not lost.
