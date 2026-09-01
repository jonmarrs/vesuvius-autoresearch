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


---

## Addendum 1, 2026-08-31, written while the arm is fitting and before it is measured

**Instrument sensitivity, checked because the arms differ in kind.** Every duplicate arm measured so
far used an exact mesh copy, so cells coincided perfectly at any quantisation. Fit-produced overlap
is approximate. If `measure_winding_overlap.py` only fired on near-exact coincidence, a null here
would be an instrument limit misread as absence.

Two synthetic windings five apart in index, one displaced by delta voxels, quant 4:

| displacement | gap>=2 detected |
|---:|---:|
| 0 vx | 100.00% |
| 1 vx | 75.84% |
| 2 vx | 56.41% |
| 3 vx | 41.24% |
| 4 vx | 28.36% |
| 6 vx | 15.28% |
| 8 vx | 10.09% |
| 12 vx | 6.48% |
| 16 vx | 4.56% |

Detection falls with displacement but never to zero across the range that matters: the fit's own
sheet spacing is 16.17 voxels, and even a full spacing still registers 4.56%.

**Two consequences for reading the result, fixed now.**

1. **A null is real.** The 0.00% on all four honest arms is genuine absence of co-location, not
   co-location too diffuse to see.
2. **A positive understates.** Any percentage reported for MINSPACE0 is a lower bound on true
   overlap, because displaced sheets are counted at a discount. Prediction 1's 1.0% threshold is
   therefore conservative in the right direction, and I am not moving it.

Guarded by `tests/test_measure_winding_overlap.py::test_it_detects_approximate_not_only_exact_overlap`.


---

## Addendum 2, 2026-08-31, full-fit duplication baseline, before MINSPACE0 is measured

The registered comparison is the ten-winding span w010..w019, where all four honest fits read
**0.00%**. That stands. But MINSPACE0 will also be measurable over its full 120 windings, and the
honest baseline there is not zero, so it is recorded now rather than after.

| fit | occupied cells | multi-claimed | gap>=2 |
|---|---:|---:|---:|
| baseline01 | 11,539,167 | 0.20% | 10,345 (0.0897%) |
| seed02 | 11,559,283 | 0.21% | 11,895 (0.1029%) |
| seed03 | 11,556,455 | 0.20% | 12,040 (0.1042%) |
| seed04 | 11,546,847 | 0.20% | 11,319 (0.0980%) |

```
gap>=2 fraction   mean 0.0987%   sd 0.0066%   CV 0.0667   range 0.0897% .. 0.1042%
```

**Duplicate coverage is markedly more reproducible across seeds than the objective it can inflate**:
CV 0.0667 against 0.1086 for `total_fg_pixels`. A property of the fit that varies by 6% seed to seed
is a better-behaved quantity than the ink count that varies by 11%.

For the full-fit comparison, MINSPACE0 must therefore clear **0.0897% to 0.1042%**, not zero. The
registered ten-winding threshold of 1.0% against 0.00% is unchanged and remains the primary test;
this is a secondary reading with its own baseline, stated before the arm exists so neither can be
chosen after the fact.
