# Removing the min-spacing barrier did not produce duplicate coverage

**2026-08-31.** Pre-registered in
`docs/preregistration/2026-08-31_satisfaction_vs_fit_produced_duplication.md` with two addenda, all
committed before the fit existed. **Prediction 1 failed. By the rule fixed in advance, this arm
learns nothing about the question it was built to answer.**

## What was being asked

`reports/duplicate_coverage_inflates_the_objective.md` shows the ink objective cannot price
duplicated coverage, with one limit I could not argue away: all five arms duplicated at the **mesh**
level, post-fit, so the fit's satisfaction metrics were untouched by construction and villa's third
guard stayed untested. Their loop edits `fit_spiral.py` and cannot copy mesh folders, so the
realistic threat is a fit that produces overlap.

`loss_weight_min_spacing` gates what `fit_spiral.py:4323` calls "the native min-spacing barrier".
Setting it to 0, changing nothing else, was the most direct way to try to induce overlap through a
fit.

## Result

| measurement | MINSPACE0 | honest baseline | verdict |
|---|---|---|---|
| gap>=2, full 120 windings | **0.10%** (11,237 cells) | 0.0897 to 0.1042% | **inside the range** |
| gap>=2, registered ten-winding span | **0.00%** | 0.00% (all four seeds) | **no change** |
| satisfied_area_fraction | 0.8295 | 0.8382 to 0.8404 | outside the band by 0.0003 |
| satisfied_patches_fraction | 0.6543 | 0.6542 (baseline01) | unchanged |
| total_fg_pixels | 242,128 | 240,088 | `dT` +0.0085 |
| line / column | 0.432 / 0.151 | 0.438 / 0.232 | |

**Duplicate coverage did not move.** Not on the registered ten-winding span, and not on the full fit,
where it landed at 0.10% against an honest range of 0.0897 to 0.1042%.

The registered rule for this outcome:

> duplication does NOT rise above 1.0% -> **prediction 1 failed, nothing is learned about
> satisfaction.** The barrier is not what controls overlap, and the manipulation was wrong

That is the branch that fires. The open limit in the duplicate-coverage report **stays open**.

## The tempting misreading, stated so it is not made later

Satisfied area did drift outside the band, 0.8295 against 0.8398. It would be easy to present that
as "the guard responded to the manipulation". **It did not, because there was no duplication for it
to respond to.** `satisfied_patches_fraction` is unchanged at 0.6543 against 0.6542, and the drift is
0.0003 beyond a band I chose. The fit settled slightly differently without the barrier term; that is
all this shows.

`total_fg_pixels` moved +0.85%, far inside the 21.7% different-fit floor from
`reports/seed_spread_four_fits.md`, so it is uninterpretable and is not evidence of anything in
either direction.

## What this does and does not suggest

**It does not show** that fit-produced duplication is impossible, or hard, or that villa's loop is
safe. One manipulation failing shows that *this knob* is not the one.

**It weakly suggests** duplicate coverage is not governed by the min-spacing barrier, and that the
0.09 to 0.10% baseline seen in every converged fit is produced by something else. Given how stable
that figure is across seeds (CV 0.0667, tighter than the objective's 0.1086), duplicate coverage
looks like a structural property of the fitted geometry rather than something a single loss weight
tunes.

**A point against my own concern**, worth stating plainly: I demonstrated the exploit by copying mesh
folders, which an optimiser cannot do. The first attempt to reach it through the fit did not get
there. That does not make the metric less blind, but it does mean the reachability of the exploit
remains unestablished, and my report should not be read as though an optimiser would find it easily.

## What would actually settle it

A manipulation that demonstrably raises gap>=2 overlap in a converged fit. Candidates not tried:
`loss_weight_dense_spacing` (12.0) and `loss_weight_dense_spacing_density` (12.0), which are ten
times heavier than the barrier and may be what really holds sheets apart. Until one of those moves
the overlap, the satisfaction guard cannot be tested at all.

One fit, one seed, one ROI, no repeat.
