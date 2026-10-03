# Against villa's ink labels, smooth and linear renders are equally faithful (ΔAP ≈ −0.0001)

**2026-10-03.** Result of `docs/preregistration/2026-10-03_surface_interpolation_vs_labels.md` (committed
`71b6bd42` before any metric). One post-hoc sensitivity check, labelled as such. Data:
`reports/interp_vs_labels.json` (registered) and `reports/interp_vs_labels_sensitivity.json` (post hoc).

## The question

Finding 70: villa #1818's `--surface-interpolation smooth` moves villa's 2D-scorer ink count by up to ±20%
per window, net about −1%. It could not say which rendering is more faithful. villa now publishes ink
labels on the current 2.4 µm frame for 8 Scroll-1 segments, so this study asks: rendered both ways, which
agrees better with those labels?

## Method (as registered)

* Each of the 8 labelled segments was rendered whole from the 3D ink prediction
  (`v3-78k-fullsup`) by `vc-render:sampler-f637f3b35`, linear vs smooth: `--group-idx 2 --scale 1
  --scale-segmentation 1`, 16 slices at step 0.5, max over slices. The canvas equals the label raster
  in every case.
* AP (primary), AUC and best F1 of render intensity against labels > 127, on the mesh-valid domain
  (identical for both modes). Exact from 256-bin histograms; the self-test equals scikit-learn to 1e-9.
* Paired 512-px block bootstrap for the intervals. An alignment gate excludes a segment whose
  label-agreement peak is more than 1 px from zero offset.

## Result (registered)

| segment | AP linear | AP smooth | ΔAP [95% CI] | ΔAUC | gate |
|---|---:|---:|---|---:|---|
| 20230702185753 | 0.1021 | 0.1021 | −0.0001 [−0.0001, −0.0000] | −0.0001 | (0, +1) ok |
| 20231007101619 | 0.0513 | 0.0512 | −0.0000 [−0.0000, −0.0000] | −0.0002 | (0, +1) ok |
| 20231016151002 | 0.1125 | 0.1124 | −0.0001 [−0.0002, −0.0000] | −0.0003 | (0, +1) ok |
| 20231106155351 | 0.0879 | 0.0878 | −0.0001 [−0.0001, −0.0000] | −0.0002 | (−1, −1) ok |
| 20231210121321 | 0.1192 | 0.1192 | −0.0000 [−0.0001, +0.0000] | −0.0001 | (−1, 0) ok |
| 20230929220926 | — | — | excluded | — | **gate defect**, see below |
| 20231012184424 | — | — | excluded | — | peak (+3, +1) |
| 20231031143852 | — | — | excluded | — | peak (+2, −1) |

* **Verdict by the registered rule: no consistent difference.** ΔAP > 0 resolved in 0 segments;
  ΔAP < 0 resolved in 4 of the 5 included, short of the 6 the rule requires.
* **Prediction 1 ("|ΔAP| < 0.02 in ≥ 6 of 8"): FAILED on a technicality.** All 5 included segments
  are below 0.02 by more than 100×, but three exclusions leave only 5 to count.
* **Prediction 2 ("ΔAP > 0 in ≤ 5 of 8"): held** (0 of 8).

## The exclusions

* **20230929220926 is a defect in my gate, not a misalignment.** The gate's central 4096-px window
  contains **zero labelled-ink pixels**, so every shifted AUC is NaN. `max` over NaNs returned the first
  key, (−3, −3), which the rule read as misaligned. The registered rule did not anticipate an undefined
  peak. Disclosed, not re-ruled.
* **20231012184424 and 20231031143852** peak 2–3 px off zero. These are real small label/render offsets.
  The AUC gain at the peak is small (+0.003, +0.0005).

## Sensitivity (POST HOC): all 8 segments, gate ignored

Both modes share any label misalignment, so the paired difference should not depend on it:
ΔAP ∈ **[−0.00010, −0.00002]** in all 8; ΔAUC ∈ [−0.00026, −0.00009]. Smooth is a hair worse in every
segment (6 of 8 resolved), and never by more than 0.1% of AP. The conclusion does not depend on the
exclusions.

## What it means

* **Against villa's labels, the two modes are equally faithful.** The differences are 1e-4 in AP on
  values of 0.05–0.12. Smooth is consistently fractionally worse. That fits the stated confound (labels
  partly pseudo-labelled with linear geometry), but at this size it does not matter either way.
* **Set beside finding 70, this points at the metric.** The same flag that leaves label agreement
  unchanged to 1e-4 moved villa's 2D-scorer ink count ±20% per window. **Inference, not tested here:**
  those swings are the scorer's sensitivity to small rendering changes, not a difference in what can
  be read. The two studies used different pipelines (fitted spiral surfaces through the 2D scorer vs
  segment meshes scored directly against labels). The direct test is to score these segments' renders
  with villa's 2D scorer and check whether its count swings while its agreement with the labels does
  not. That is the natural next study.
* **For #1818:** switching the default to smooth would not change agreement with the labels. It would
  shift villa's loop metric locally, so runs in different modes must never be compared (inkdelta 0.5.0
  flags this).

## Limits

* One scroll, one 3D ink model, 8 segments that share both. The labels are partly pseudo-labels.
* Render settings follow villa's tutorial, not the spiral metric's (group 1, 5 slices, 2D scorer).
* The registered gate had a NaN defect (above). Fix it before reusing the gate: treat an undefined
  peak as "undetermined" and choose a window with labelled ink.
