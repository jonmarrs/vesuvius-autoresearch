# Geometry quality and recovered ink decouple at seed scale

**2026-09-01.** A property of the four-seed set in `reports/seed_spread_four_fits.md` that was
visible in the table but not stated. It refines `autoresearch.md`'s central premise rather than
contradicting it.

## Result

The same four fits, identical but for seed, measured on villa's geometry diagnostic and on its ink
objective:

| metric | mean | sd | CV |
|---|---:|---:|---:|
| `satisfied_area_fraction` | 0.83957 | 0.00095 | **0.00114** |
| `satisfied_patches_fraction` | 0.6568 | 0.00347 | 0.00528 |
| `total_fg_pixels` | 226,810 | 24,640 | **0.10863** |

**The ink objective is 96x noisier across seeds than satisfied area, and 21x noisier than satisfied
patches.** Changing only the random seed leaves the fit's geometry quality essentially fixed while
recovered ink swings by 25% worst-case.

The rank orders also barely relate:

```
by satisfied_area ascending   seed3 < seed1 < seed4 < seed2
by total_fg       ascending   seed2 < seed3 < seed1 < seed4
```

`seed2` has the **highest** satisfied area and the **lowest** ink of the four. The correlation is
-0.121, but at n=4 that number carries almost no information and is not the basis for anything here.
**The CV ratio is the robust part**: it needs only the two spreads, not their relationship.

## What this does and does not say about the premise

`autoresearch.md` states:

> A better fit, one that produces a more coherent, correctly-flattened surface that lands on the
> inked papyrus, recovers more ink. That is the whole game.

**At coarse scale this holds, and we measured it**: a 100-step fit at 0.100 satisfied area scores
59.5% less ink than a 30,000-step fit at 0.840
(`reports/objective_does_track_fit_quality.md`). Gross fit quality does drive ink recovery.

**At the scale the loop actually operates it does not.** Among converged fits whose geometry is
indistinguishable, ink recovery varies by 25%. Whatever produces that variation is not captured by
satisfaction.

## Consequence for the prescribed cross-check

The same doc directs the loop to watch satisfaction as a guard:

> if ink coverage climbs while the satisfaction metrics fall off a cliff, be suspicious that you are
> contorting the surface to catch stray ink

That is sound for gross breakage, which is exactly the regime where we confirmed it works. But
satisfaction is a **stiff** instrument: at CV 0.114% it will read as unchanged for anything short of
a cliff, so it cannot corroborate or contradict an ink change of ordinary size. A 10% ink gain,
real or noise, will leave satisfaction looking flat either way.

This is not an argument against the cross-check. It is an argument that passing it means less than
it appears: it rules out catastrophe, not error.

## An aside worth keeping

Low variance makes satisfaction a **precise** instrument where it does respond. `GAP133` moved it
+8.8 sd, which is only interpretable because the seed sd is 0.00095. A quantity this stiff is poor
for corroborating small effects and excellent for detecting real ones.

## Limits

Four fits, one dataset, one ROI, one architecture. The CV ratio rests on two four-point spreads and
inherits their uncertainty; the rank comparison and correlation are n=4 and are reported only to be
dismissed. Satisfaction and `total_fg_pixels` measure different things by construction, so decoupling
is not by itself a defect in either.
