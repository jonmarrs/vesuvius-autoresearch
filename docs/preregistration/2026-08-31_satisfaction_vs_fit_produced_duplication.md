# Pre-registration: do the satisfaction metrics catch duplication produced THROUGH a fit?

**Written 2026-08-31, before the arm is fitted.** No modified fit exists.

## The gap this closes

`reports/duplicate_coverage_inflates_the_objective.md` establishes that the ink objective cannot
price duplicated coverage, and states one limit I could not argue away:

> all five arms duplicate at the MESH level, post-fit. The fit and its satisfaction metrics are
> untouched by construction, so `autoresearch.md`'s third check remains untested. An optimiser that
> produced duplicate coverage *through the fit* might well be caught by it.

That matters because villa's loop edits `fit_spiral.py` and its losses; it cannot copy mesh folders.
So the realistic threat is a fit that produces overlap, and whether satisfaction sees it is the
difference between a curiosity and a live concern.

## The manipulation

`config.py` sets `loss_weight_min_spacing = 2.0`, gating what `fit_spiral.py:4323` calls "the native
min-spacing barrier". A barrier is precisely what stops surfaces occupying the same place, so
removing it is the most direct way to ask the question.

* **Arm MINSPACE0**: identical to `baseline01` in every respect, same dataset, z-ROI 13056..18432,
  30,000 steps, seed unchanged, except `"loss_weight_min_spacing": 0`.

Measured on windings w010..w019 exactly as all previous arms: `scripts/measure_winding_overlap.py`
at quant 4, the fit's own satisfaction metrics, then render and score.

## Predictions, fixed now

1. **Duplicate coverage rises**: gap>=2 overlap above 1.0%, against 0.00% for every honest arm
   measured so far (baseline01, seed02, seed03, seed04, all at 0.00% on this ten-winding span).
2. **Satisfaction is the open question and I am not predicting it.** Registering a guess would
   invite reading the result to match. Both directions are informative and both are stated below.
3. `total_fg_pixels` is a DIFFERENT-FIT comparison, so it is judged against `2*CV = 21.7%` from
   `reports/seed_spread_four_fits.md`, not the 1.42% pipeline floor.

## Decision rule

| outcome | reading |
|---|---|
| duplication rises AND satisfied-area stays within 0.01 of 0.8398 | **the satisfaction guard does NOT catch it.** The open limit closes against villa's guard set: all three checks miss fit-produced duplication |
| duplication rises AND satisfied-area falls materially (outside the band) | **the guard WORKS.** My concern is bounded: an optimiser doing this would be visible in the diagnostics the doc already tells the loop to watch |
| duplication does NOT rise above 1.0% | **prediction 1 failed, nothing is learned about satisfaction.** The barrier is not what controls overlap, and the manipulation was wrong |
| the fit collapses (satisfied area near the 100-step 0.100) | **VOID for this question.** It shows only that the barrier is load-bearing for fitting at all, not whether satisfaction detects duplication |

## What this cannot show even if it works

Removing a loss term is a blunt instrument and not what an optimiser would do; a loop searching for
ink would more likely find some subtler configuration. A positive result shows the guard *can* be
evaded, not that it *would* be. And with a 21.7% different-fit noise floor, only a large
`total_fg_pixels` effect is detectable at all, so a modest duplication-driven gain would be
invisible here and must not be reported as absence.

One fit, one seed, one ROI, no repeat.
