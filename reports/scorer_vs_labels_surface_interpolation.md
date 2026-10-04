# In villa's own scoring pipeline, smooth vs linear moves the ink count a little and its faithfulness not at all

> **Correction (2026-10-04, `reports/supervised_reanalysis.md`):** agreement here was computed on the whole surface, but villa's labels exist only inside its supervision mask. On the supervised region the faithfulness conclusion **survives** (|ΔAP| < 0.01 in 8 of 8; scorer median AP 0.34, strip 0.63). The count results do not involve the labels and are unchanged.

**2026-10-03.** Result of `docs/preregistration/2026-10-03_scorer_sensitivity_vs_labels.md` (committed
`581e065e` before any metric). Data: `reports/scorer_vs_labels.json`.

## The question

Finding 70 found villa's 2D-scorer count moving ±20% per window under `--surface-interpolation smooth`.
Finding 71 found the rendered 3D ink prediction agreeing with villa's labels identically in both modes.
The inference, that the swings are scorer sensitivity rather than reading, crossed two pipelines. This
study runs the **metric's own pipeline** on the 8 labelled Scroll-1 segments:
* the render at `--group-idx 1 --scale 0.25`, 5 slices;
* the `render_ink` strip, with one p95 normalisation over the whole strip;
* the pinned scorer, keeping its probability map;
* comparison against villa's labels at level 3 (19.2 µm), which the canvas matches exactly.

## Result

All 8 segments pass the alignment gate (peaks within 1 px), so nothing is excluded.

| segment | count Δ (total) | count Δ per 2048-px window | scorer-prob AP linear → smooth | ΔAP [95% CI] |
|---|---:|---|---|---|
| 20230702185753 | −0.83% | −1.0, −0.8 | 0.0407 → 0.0410 | +0.0003 [−0.0008, +0.0011] |
| 20230929220926 | +0.73% | −2.0, +3.0, +2.2, −1.7 | 0.0175 → 0.0173 | −0.0002 [−0.0012, +0.0003] |
| 20231007101619 | +0.22% | +7.4, +0.6, −1.1, −1.2, +0.6, −0.7 | 0.0216 → 0.0216 | +0.0000 [−0.0002, +0.0002] |
| 20231012184424 | −0.37% | +3.1, −0.0, −1.6, −1.1 | 0.0437 → 0.0438 | +0.0001 [−0.0001, +0.0003] |
| 20231016151002 | −1.53% | −2.8, −1.0, +1.5 | 0.0216 → 0.0216 | +0.0000 [−0.0003, +0.0003] |
| 20231031143852 | +4.15% | +1.4, +7.4 | 0.0249 → 0.0240 | −0.0009 [−0.0026, +0.0012] |
| 20231106155351 | −3.60% | +7.1, +0.0, −9.0 | 0.0306 → 0.0305 | −0.0002 [−0.0006, +0.0002] |
| 20231210121321 | +0.93% | +1.2, +0.9 | 0.0446 → 0.0448 | +0.0002 [−0.0002, +0.0007] |

* **Count:** 26 windows; median |Δ| **1.3%**, 13 up and 13 down; range −9.0% to +7.4%; 4 of 26 at ≥ 5%.
  Segment totals: median |Δ| 0.9%, range −3.6% to +4.1%, pooled +0.17%.
* **Faithfulness:** the scorer probability's |ΔAP| < 0.001 in all 8, and **none resolved**. The raw strip's
  ΔAP is ≤ 0.0002 (finding 71, now at the metric's settings).

## Predictions, as registered

1. **"The count is sensitive" (|Δ| ≥ 5% in ≥ 25% of windows): FAILED.** It was 15%.
2. **"Faithfulness is not" (|ΔAP| < 0.01 in ≥ 6 segments): HELD**, in 8 of 8 by more than 10×.

Registered reading: **finding 70's ±20% swings did not replicate at that size on segment meshes.** In
the metric's own pipeline, smooth moves the count by about 1% (tail to ±9%) and its agreement with
villa's labels not at all.

## What changes in the picture

* **Finding 70's magnitude must not be generalised.** Its ±20% came from a fitted spiral surface,
  where this study's segment meshes give about 1%.
  * **Not the normalisation.** Finding 70's windows re-scored with one shared p95 per mode still give
    median |Δ| 4.7%, range −17.5% to +21.1% (`reports/shared_p95_rescore.json`; pre-registered
    prediction "< 2.5%" FAILED).
  * **Measured difference:** grid cell size. The spiral flat's cells are ~80 × 74 voxels (~10 output
    px), the segment meshes' ~20 × 20 (~2.5 px). Smooth and linear agree at grid points and differ only
    inside cells, so coarse cells should amplify the difference. Leading hypothesis, tested next by
    subsampling the segment meshes 4×.
* **What holds across all three studies:** smooth mode does not change agreement with villa's labels.
  That is so for the rendered prediction (f71) and for the scorer's output (f72).
* **For villa / #1818:** by these labels, smooth is neither better nor worse for reading. Switching the
  default would shift the loop's metric by about 1% per segment (up to ±4% here), which is below seed
  noise (CV ≈ 7%). It is enough to bias a comparison that mixes modes, which inkdelta 0.5.0 flags.

## Limits

* One scroll, one 3D ink model, 8 segments sharing it. Labels partly pseudo-labelled with linear
  geometry, which favours linear; that did not show.
* No meaningless-perturbation control in this pipeline, so the ±9% window tail is not certified as
  beyond scorer noise (finding 70's control, ≤ 2.8%, was in the other pipeline).
* Windows within a segment are not independent.
