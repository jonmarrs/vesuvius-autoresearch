# Pre-registration: does `--surface-interpolation smooth` agree better with villa's ink labels?

**Written 2026-10-03, before any metric was computed on any segment.** Chain
`repro/spiral_render/run_interp_vs_labels.sh`, analysis `scripts/analyse_interp_vs_labels.py`. Both are
committed with this file.

## Why

Finding 70: villa #1818's `smooth` mode moves where the scorer finds ink by up to ±20% per window, with a
small net change, beyond a meaningless-perturbation control. It could not say **which rendering is more
faithful**, because there was no ground truth. villa now publishes ink labels on the current 2.4 µm frame
for 8 Scroll-1 segments (`segments/<id>/ink-labels/2.4um-volume-20260411134726/20260918/inklabels.zarr`),
so the question is now answerable for this product.

## What was checked before writing (reachability; no metric computed)

* All 8 segments have a mesh on the 2.4 µm scan (`mesh/<id>-on-20260411134726-2.4um.tifxyz`, grid scale
  0.05) and labels dated 20260918. The labels' level 2 is at 9.6 µm.
* `vc_render_tifxyz --group-idx 2 --scale 1 --scale-segmentation 1 --num-slices 16 --slice-step 0.5` on
  the 3D ink volume (`ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr`) renders onto
  exactly the label canvas: `20231031143852` gave 8545 × 11005 = the label shape, in 270 s.
* On a crop of `20231210121321`, that render correlates 0.961 with villa's own published
  `...-L2-3d-ink-max.zarr`, **peaking at offset (0, 0)**. It is not byte-identical: the published
  product is brighter (mean 51.2 vs 44.4). The likely cause is a different build or band; I tried 4
  band variants and none matched. Alignment is what this test needs, and it holds.

## Method

* **Segments:** all 8 above. **Arms:** `vc-render:sampler-f637f3b35` at the default (`linear`) and
  with `--surface-interpolation smooth`, with the arguments above. Each is a full-segment render,
  max over the 16 slices (as villa's tutorial does), kept as one uint8 image per arm.
* **Labels:** level 2 of the 20260918 `inklabels.zarr`, binarised at > 127.
* **Domain:** canvas pixels whose source grid cell is valid (`x.tif` ≠ −1, upsampled 5×). It is the
  same for both modes, so smooth's slightly larger rendered area cannot count for or against it.
* **Metrics per segment and mode:** average precision (AP, primary), ROC-AUC and best F1 of the
  max-composite intensity against the labels. Computed exactly from 256-bin histograms, since the
  scores are uint8.
* **Uncertainty:** a paired block bootstrap over 512 × 512 px blocks (2000 resamples, seed 20261003),
  giving a 95% interval for ΔAP = AP(smooth) − AP(linear) and for ΔAUC, per segment.
* **Alignment gate, per segment:** the linear render's AUC is computed at label offsets −3..+3 px in y
  and x. If the peak is more than 1 px from (0, 0), the segment is **excluded** as misaligned and
  reported. This is decided before any smooth number is looked at.
* **Integrity:** a skipped or failed render, `smooth` not engaging, or a canvas that is not exactly
  the label shape fails that segment.

## Reported

Per segment: AP, AUC and best F1 for both modes, ΔAP and ΔAUC with intervals, and the alignment peak.
Across segments: how many have ΔAP > 0, < 0, and resolved (interval excludes 0) in each direction;
the median ΔAP.

## Predictions, fixed now

1. **|ΔAP| < 0.02 in at least 6 of the 8 segments.** Confidence moderate. Finding 70's net change was
   small (−1.3%), though the local moves were large.
2. **No consistent gain from smooth:** ΔAP > 0 in at most 5 of the 8. Confidence low.

**Decision rule:** "smooth agrees better with villa's labels" is claimed only if ΔAP > 0 is resolved
(interval excludes 0) in at least 6 of the 8 segments. "Linear agrees better" requires the same in
the other direction. Anything else is reported as no consistent difference.

## Known confounds (stated now, not discovered later)

* **The labels are not independent of linear rendering.** villa's README says the scroll labels are
  hand strokes refined by iterative pseudo-labelling, and the 3D ink model (`fullsup`) was presumably
  trained on labels of this kind. Both were made with default-mode (linear) geometry. That favours
  linear. A smooth win would therefore be the stronger result; a linear win is ambiguous between
  "more faithful" and "home advantage".
* This measures agreement of the **rendered 3D ink prediction** with labels, not legibility to a
  papyrologist.
* One scroll and one ink volume. The segments are not independent of each other (shared model).

## Cost

16 full-segment renders (≈ 5–20 min each, about 2–3 h), streamed from the open-data bucket into the
existing chunk cache, then CPU metrics. No fits, no scorer runs.
