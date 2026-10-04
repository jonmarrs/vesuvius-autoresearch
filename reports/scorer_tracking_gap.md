# The scorer-vs-render tracking gap: registered predictions held, but the test was weak; villa's scorer marks about 2% of villa's annotated ink

**2026-10-04.** Result of `docs/preregistration/2026-10-04_scorer_tracking_gap_robustness.md` (committed
`fe3d73ba` before any statistic was computed), plus **unregistered** descriptive checks run afterwards to
bound how far it can be read. Data: `reports/scorer_tracking_gap.json` (registered),
`reports/scorer_tracking_gap_descriptive.json` and `reports/scorer_sparsity_annotated.json` (descriptive).

## Registered result: both predictions held

Spearman ρ against labelled-ink density, over tiles that are ≥ 50% mesh-valid and supervised. 95% bootstrap
over segments.

| arm | tile (px) | n | ρ strip | ρ scorer | gap |
|---|---:|---:|---|---|---:|
| reference (f72 linear, the post-hoc lead) | 128 | 1289 | +0.751 [+0.61, +0.81] | +0.173 [+0.05, +0.23] | +0.579 |
| | 256 | 286 | +0.613 [+0.42, +0.69] | +0.145 [+0.01, +0.22] | +0.468 |
| | 512 | 40 | +0.455 [−0.09, +0.70] | +0.265 [−0.45, +0.49] | +0.190 |
| f72 smooth | 128 | 1289 | +0.752 [+0.61, +0.81] | +0.186 [+0.08, +0.23] | +0.566 |
| | 256 | 286 | +0.614 [+0.43, +0.69] | +0.151 [+0.04, +0.22] | +0.463 |
| | 512 | 40 | +0.453 [−0.09, +0.70] | +0.266 [−0.45, +0.49] | +0.188 |
| f73 coarse linear | 128 | 1289 | +0.743 [+0.60, +0.80] | +0.146 [+0.03, +0.21] | +0.598 |
| | 256 | 286 | +0.597 [+0.37, +0.68] | +0.146 [−0.04, +0.23] | +0.451 |
| | 512 | 40 | +0.416 [−0.18, +0.62] | +0.387 [−0.46, +0.64] | +0.029 |
| f73 coarse smooth | 128 | 1289 | +0.750 [+0.61, +0.81] | +0.167 [+0.04, +0.22] | +0.583 |
| | 256 | 286 | +0.607 [+0.41, +0.69] | +0.128 [−0.01, +0.20] | +0.480 |
| | 512 | 40 | +0.449 [−0.11, +0.66] | +0.231 [−0.57, +0.45] | +0.218 |

* **Prediction 1 (gap ≥ 0.3 at 256 px in each new arm): HELD** (+0.451 to +0.480).
* **Prediction 2 (strip ρ > scorer ρ in all 9 new cells): HELD.** At 512 px only by point estimate: 40 tiles,
  and the two intervals overlap almost entirely (f73 coarse linear's gap is +0.029).
* The reference cell reproduces the post-hoc numbers exactly (ρ 0.6126 and 0.1447).

## Why that is weaker than it looks (found after registering)

**The three "new" arms are near-duplicates of the reference.** Per tile at 256 px, their densities correlate
with the reference's at:

| arm | r (strip) | r (scorer) |
|---|---:|---:|
| f72 smooth | 0.99999 | 0.998 |
| f73 coarse linear | 0.997 | 0.961 |
| f73 coarse smooth | 0.9997 | 0.989 |

Once the reference held, both predictions were nearly guaranteed. I should have measured this before
registering. The registered test adds little beyond the reference, and the prediction's wording, "robust
across render mode and grid", claims more than these arms can show. **What the registered result does
support** is robustness to tile size at 128 and 256 px. 512 px is uninformative.

## Descriptive checks (not registered)

**The gap itself, paired bootstrap over segments, reference arm:**

| tile | gap (strip − scorer) | 95% CI |
|---:|---:|---|
| 128 | +0.579 | [+0.47, +0.69] |
| 256 | +0.468 | [+0.31, +0.55] |
| 512 | +0.190 | [−0.35, +1.05] |

**It is not an artefact of pooling segments.** At 128 px, within every one of the 8 segments, the strip's ρ
(+0.53 to +0.91) exceeds the scorer's (−0.03 to +0.25). At 256 px, it does so in all 8 segments.

**Part of the loss is villa's 0.5 threshold.** The scorer's mean probability, before thresholding, tracks
label density at ρ +0.47 at 128 px (+0.22 at 256), against +0.17 for the count `total_fg_pixels` uses.

**The scorer's count barely follows its own input.** Per tile: ρ(scorer density, strip density) = +0.16
(128 px), +0.19 (256 px). This number involves no labels.

**Why: villa's scorer marks very little of the annotated region.** Pooled over the 8 segments, inside villa's
supervised (annotated) region:

| | value | range over segments |
|---|---:|---|
| pixels the scorer marks as ink | **0.91%** | 0.15 – 1.96% |
| pixels villa's labels mark as ink | 25.9% | 20.8 – 34.1% |
| scorer's ink on labelled ink (precision) | 59.3% | 49.6 – 76.7% |
| labelled ink the scorer marks (recall) | **2.1%** | 0.5 – 3.9% |
| scorer rate inside ÷ outside the annotated region | 1.10× | 0.32 – 2.45× |

* Median scorer density over the 286 supervised 256-px tiles is **0.000**; 95% of tiles are ≤ 5%. The weak ρ
  is a floor effect: most tiles are tied at zero.
* **The recall bound does not depend on alignment.** Even if every pixel the scorer marks were ink, it could
  cover at most 0.91 / 25.9 = 3.5% of labelled ink.
* **What it marks is mostly real ink.** Precision 59% against a 26% base rate.
* **This is the scorer's normal regime, not our inputs.** Its fg fraction on these segment strips
  (0.5–0.8%) matches real spiral-loop renders (0.7–0.9%, e.g. `spiral_out/outer_curbase_s1`). The metric
  preset matches `render_ink.py`'s defaults.
* **The inside/outside ratio is weak evidence.** Outside the annotated region is unannotated, not ink-free.

## Confounds that limit all of the above

1. **The strip is in-sample for the 3D ink model: CONFIRMED (updated 2026-10-04, same day).** The strip
   renders villa's `v3-78k-fullsup` 3D ink prediction. Its model card and `config.json`
   (`scrollprize/ink_3d_dino_guided`, revision `73a79525`, copied to `reports/evidence/`) show:
   * `segments_path` is `/ephemeral/2d_ink_dataset/phercparis4`, villa's PHercParis4 ink dataset, which is
     **exactly these 8 segments** (none has a validation mask);
   * `force_full_supervision: true`;
   * targets partly come from self-distillation of the previous version.

   So the strip's ρ +0.6 to +0.75 **is** training-set agreement. On unlabelled regions, where the objective
   actually runs, the strip is likely worse and the gap likely smaller.
   * **Correction:** the first version of this report said the public metadata had "no model card" and
     that the question "cannot be resolved with public data". Both were wrong. I had checked only the zarr's
     `.zattrs`, not villa's Hugging Face models.
   * The asymmetry runs one way. Better input here should help the scorer. Its 2% recall is therefore unlikely
     to be *worse* than on regions the 3D model never saw.
2. **Same 8 segments, one scroll, one 3D model**, labels partly model output.
3. **Cross-region tracking is not the objective's job.** The loop compares the *same region under different
   fits*. A count that misses 98% of annotated ink can still rank fits correctly if what it does catch moves
   with legibility. This measures what the count contains, not whether it ranks fits wrongly.
4. **The scorer is named a coverage model** (`scrollprize/ink-coverage-32um`, 21 training images of an
   "ink_pred" channel). Its docstring says it segments "inked (foreground) pixels" and "more foreground =>
   more legible ink"; stroke labels test the second reading.

## Verdict

* **Registered:** both predictions held. Honestly stated, this shows the gap is robust to tile size (128 and
  256 px) on these 8 segments, not across render conditions; the arms were near-duplicates.
* **Descriptive, and the more useful fact:** at villa's metric settings, villa's scorer marks 0.91% of
  villa's annotated text region and at most 3.5% (measured 2.1%) of villa's labelled ink. What it marks is
  mostly real. `total_fg_pixels` is therefore a sparse-detection count driven by about 2% of the annotated ink.
* **Not shown:** that villa's objective mis-ranks fits; or that the gap holds where the 3D model has not
  trained.
* **Not for the October filing as a claim about villa's objective.** Confound 1 is confirmed (the strip is
  in-sample), and confound 3 is the one villa would raise first.
