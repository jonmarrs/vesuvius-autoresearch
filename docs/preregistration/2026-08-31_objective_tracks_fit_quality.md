# Pre-registration: does `total_fg_pixels` reward a better fit?

**Written 2026-08-31, before either arm is rendered.** No render or score of the smoke fit exists.

## Why

`reports/duplicate_coverage_inflates_the_objective.md` shows the objective can be raised 92% by
duplicated coverage that reads nothing new. That is a statement about what the metric *wrongly*
rewards. The complementary question is whether it *rightly* rewards the thing it exists for: a
better fit. The loop's entire premise is the sentence in `autoresearch.md`:

> A better fit, one that produces a more coherent, correctly-flattened surface that lands on the
> inked papyrus, recovers more ink. That is the whole game.

Two fits of extremely different quality are already on disk, from the same dataset and the same
z-ROI, so this costs one render and one score.

## Arms

Same ten windings, w010..w019, same render and scoring settings, lasagna path.

* **GOOD**: `baseline01`, 30,000 steps. `satisfied_area_fraction` **0.840**,
  `satisfied_patches_fraction` 0.654. Already scored: `total_fg_pixels` **240,088**,
  `overall_fg_fraction` 0.00897, line 0.438, column 0.232.
* **BAD**: `smoke01`, 100 steps, the same dataset and ROI. `satisfied_area_fraction` **0.100**,
  `satisfied_patches_fraction` 0.00075. Not rendered or scored.

The quality gap is not marginal: 8.4x on satisfied area, 870x on satisfied patches. If the objective
cannot separate these two it cannot separate anything.

## Prediction, fixed now

**`total_fg_pixels`(BAD) is well below GOOD's 240,088, by more than 25% relative.** The premise
above predicts a large gap, and these two fits are about as far apart in quality as the fitter can
produce on this data.

## Decision rule

Let `dT = (total_fg(BAD) - 240,088) / 240,088`.

* **Premise HOLDS** if `dT < -0.25`: the objective strongly penalises the bad fit.
* **Premise FAILS** if `|dT| <= 0.10`: an 8.4x worse fit is worth roughly the same ink, so the
  objective does not track fit quality at the coarsest possible scale.
* **Premise INVERTED** if `dT > +0.10`: the bad fit scores higher, which would be a serious result
  and would need a seed repeat before I believed it.
* Anything in between is **PARTIAL** and reported as an ambiguous middle, not rounded to either side.

## Controls

* The BAD arm must render non-blank (`p95 > 0`). A black strip is a frame failure, not a low score,
  and voids the arm.
* Its lasagna flatten must converge, as it did for every arm so far.
* `scripts/measure_winding_overlap.py` must show the BAD arm is not duplicate-inflated: gap>=2 at or
  near 0%, so any ink it does score is not coming from double counting.

## What this cannot show

One dataset, one ten-winding span, no seed repeats. `smoke01` is a 100-step fit, which is a crude
proxy for "bad": it is undertrained rather than wrong in an interesting way, and an optimiser would
never propose it. A pass here does not mean the objective tracks quality among *good* fits, which is
the regime the loop actually searches, and where the differences are much smaller.
