# Pre-registration: how much does the post-#1146 slice step move `total_fg_pixels`, across surfaces?

**Written 2026-09-27 ~00:00, before any step-2 arm rendered.** Summary code `scripts/analyse_step2_surfaces.py`,
tests `tests/test_analyse_step2_surfaces.py`, chain `repro/spiral_render/run_step2_surfaces.sh`. All are
committed with this file.

## The question

Finding 65 measured **+5.32%** on one surface (`detfit_up1`). That was the published image against a
post-#1146 source build, whose only sampling difference is a slice step twice as large. The reply on
villa #1588 says the size "will vary with how much ink sits just off the surface". **By how much?**
This characterises that range. It is descriptive: no hypothesis test, and no bound claimed.

## Method, reachability verified

* The published image with `--slice-step 2` reproduces a post-#1146 build's stack **to rounding**
  (centre slice byte-identical; others differ in 12–24 of ~404 M px by ≤ 1 grey level), so no source
  build is needed.
* **Arms:** `step2_s4`, `step2_s5`, `step2_s6`. Each is a copy of `detfit_s4/s5/s6` with:
  * its own saved flat, reused (x/y/z checked byte-equal to the source dir);
  * the copied per-slice TIFFs **deleted**, since the published binary skips when they exist (the
    finding-65 lesson);
  * the chain **failing if the log shows a skip**;
  * `--slice-step 2` added to the sampler wrapper, the only change.
* **Default-step comparators:** the same dirs' existing scores (published image, same render tree
  `be09a8503`, same image `1f3a7985`, deterministic flatten).
* **Fourth surface:** `up1` enters via its measured source-build score.

## Reported

* Per-surface effect: step2 / default − 1.
* Mean and range.
* Whether every effect is positive and clears 10× the re-score floor (59 px on 3.28 M).

## Prediction, fixed now

**All positive; magnitudes 2–10%. Confidence moderate on the sign, low on the size.** Reasoning: a
thicker max-composite can only raise or hold each pixel's maximum, but the scorer's response is not
monotone in general.

## Cost

Three serial renders on the published pipeline, uncapped as the originals ran (~1.5–2 h each), plus
scoring. No new fits.
