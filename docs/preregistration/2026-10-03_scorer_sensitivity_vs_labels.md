# Pre-registration: is villa's 2D scorer sensitive to the render mode while the labels are not?

**Written 2026-10-03, before any metric of this study was computed.** Chain
`repro/spiral_render/run_scorer_vs_labels.sh`, analysis `scripts/analyse_scorer_vs_labels.py` (it reuses
the verified histogram metrics of `scripts/analyse_interp_vs_labels.py`). All are committed with this file.

## Why

* **Finding 70:** `smooth` moves villa's 2D-scorer ink count by up to ±20% per window. A
  meaningless-perturbation control moved it by ≤ 2.8%.
* **Finding 71:** rendered directly, smooth and linear agree with villa's ink labels identically
  (ΔAP ≈ −0.0001).
* **Inference to test:** the swings are the scorer's sensitivity to small render changes, not a
  difference in what can be read. That inference crossed two pipelines. This study runs **one**
  pipeline, the metric's own, on the 8 labelled segments.

## Reachability, checked before writing (no metric computed)

`20231016151002`, rendered by `vc-render:sampler-f637f3b35` with villa's metric settings
(`--group-idx 1 --scale 0.25 --scale-segmentation 1 --num-slices 5`), lands on a 3995 × 6495 canvas.
That is exactly label level 3 (19.2 µm). Built into a strip as `render_ink.py` builds one, and scored by
the pinned scorer (serial folds, plus `keep_probabilities.patch` under `INK_METRIC_KEEP_PROB=1`), it
yields a 3995 × 6495 probability map in 195 s. Every strip here is narrower than `render_ink`'s
16384-px tiling limit, so it is a single JPEG.

## Method

* **Segments:** the 8 of finding 71. **Arms:** linear (default) and `--surface-interpolation smooth`.
  Settings as above.
* **Per arm:** max-composite → p95 → JPEG q95 (render_ink, verbatim), then the scorer with
  probabilities kept.
* **Labels:** level 3 of the 20260918 `inklabels.zarr`, > 127. Where a canvas is one row or column
  short of the label raster (odd grids), both are cropped to the common top-left shape.
* **Domain:** mesh-valid cells, nearest-upsampled to the canvas, the same for both modes.
* **Outcome A, count sensitivity:** the scorer's binary mask (`fg_prob ≥ fg_threshold`, as the scorer
  counts) is summed per 2048-px-wide full-height column window. Δcount = smooth/linear − 1 per window.
  Only windows where the linear count is ≥ 1000 px are reported.
* **Outcome B, faithfulness:** AP and AUC of the scorer's probability (quantised to 256 levels) against
  the labels on the domain, per segment and mode. Paired block bootstrap, 256-px blocks, 2000
  resamples, seed 20261003. The same is computed for the raw strip intensity, which carries finding 71
  over to the metric's settings.
* **Alignment gate (fixed version):** strip-intensity AUC at label offsets −2..+2 px over the whole
  domain. A peak more than 1 px from (0, 0) excludes a segment. **An undefined peak (no labelled ink)
  is "undetermined" and also excluded, reported as such**, not as misaligned.

## Predictions, fixed now

1. **The count is sensitive:** |Δcount| ≥ 5% in at least 25% of the reported windows. Confidence
   moderate. The 5% bar is above finding 70's control maximum of 2.8%.
2. **Faithfulness is not:** |ΔAP| of the scorer probability < 0.01 in at least 6 of the segments that
   pass the gate. Confidence moderate.

**Decision rule:** if both hold, "the scorer's count swings under the render mode while its agreement
with villa's labels does not" is claimed for this scroll and these labels. If (1) fails, finding 70's
swings did not replicate on segment meshes. If (2) fails with a consistent sign, smooth changes the
scorer's faithfulness, and the direction is reported.

## Known confounds

The labels are partly pseudo-labels made with linear geometry, and the 3D ink model may have trained on
them; both favour linear. One scroll, one 3D ink model, 8 segments sharing both. Window counts within a
segment are not independent.

## Cost

16 renders (group 1, about 5–15 min each) and 16 scorer runs (about 3–8 min each): 3–5 h unattended.
