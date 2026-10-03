# Pre-registration: did per-crop p95 normalisation make finding 70's ±20%?

**Written 2026-10-03, before any shared-p95 strip was scored.** Script `scripts/shared_p95_rescore.py`,
committed with this file.

## Why

* **Finding 70:** smooth vs linear moved the 2D-scorer count from −20.2% to +17.6% per 2048-px window
  (median |Δ| 5.2%). Each window's strip was normalised by **its own** p95.
* **Finding 72:** in villa's own pipeline (**one** p95 per strip), on other surfaces, the median |Δ| was
  1.3%.
* The October draft names per-crop normalisation as the untested lead for the difference. This tests
  it, on finding 70's own renders.

## Method

* **Inputs:** finding 70's 8 windows × 2 modes (`spiral_out/interp_windows/w<x>/<mode>/tif`, 5 slices
  each), unchanged.
* **The only change:** each mode's strips are normalised by **one shared p95**, the 95th percentile of
  that mode's max-composites pooled over the 8 windows, instead of each window's own. This mirrors
  render_ink normalising each mode's whole strip once. Then JPEG q95 and the pinned scorer, as before.
* **Outcome:** per-window Δ`total_fg_pixels` (smooth/linear − 1), and its median |Δ| and range, beside
  finding 70's own.

## Prediction, fixed now

**Per-crop normalisation is most of it:** the shared-p95 median |Δ| is below 2.5%, under half of
finding 70's 5.2%. Confidence low. Finding 70 found no simple p95-sign relation, so this may well fail.
Then the lead is closed the other way, and the surfaces (fitted spiral vs segment meshes) remain the
explanation.

## Cost

16 scorer runs on existing renders, about 40 minutes. No renders.
