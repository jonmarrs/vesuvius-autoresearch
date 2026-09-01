# The objective moves 18.9% between two equally good fits

**2026-08-31.** Pre-registered in `docs/preregistration/2026-08-31_objective_seed_noise_floor.md`
before the arm was rendered. **My prediction failed, and the registered withdrawal branch fired.**

> **SUPERSEDED as a floor, 2026-08-31: use `reports/seed_spread_four_fits.md`.** This is ONE pair.
> Four fits give CV 0.1086 with pairwise differences from 0.0442 to 0.2527, and the 18.93% here
> ranks fifth of six, so it understated the worst case rather than overstating it. The threshold for
> different-fit comparisons is 2*CV = 21.7%, not this number.
>
> **The withdrawal it triggered was later REVERSED, 2026-08-31.** The 18.9% measurement below stands
> and is the correct floor for comparing two different FITS. Applying it to arms B and D was a
> category error: those come from one fit, so seed variation cannot enter them. See
> `reports/pipeline_determinism_and_which_floor_applies.md`. Read that before using this number to
> judge any same-fit result.

## Result

Same ten windings, same render and scoring settings, two converged fits differing only in seed:

| fit | satisfied area | satisfied patches | total_fg_pixels | total_pixels | fg_fraction | line | column |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline01, seed 1 | 0.8398 | 0.6542 | 240,088 | 26,754,900 | 0.00897 | 0.438 | 0.232 |
| seed02, seed 2 | 0.8404 | 0.6616 | 194,634 | 26,666,600 | 0.00730 | 0.415 | 0.229 |

```
dT = -0.1893      dF = -0.00167      predicted |dT| < 0.05
```

Not an area effect: the two strips are within 0.3% of each other, 26.67M against 26.75M pixels. The
`fg_fraction` falls by the same 19%, so seed02 genuinely lands on less ink. Controls passed: p95 9.0,
lasagna converged, gap>=2 duplicate coverage 0.00%.

seed02 is very slightly the *better* fit by satisfaction, on both measures, and recovers 19% less
ink. Whatever `total_fg_pixels` is responding to here, it is not tracking the satisfaction metrics.

## Consequences for my own earlier reports

Every arm re-expressed as a multiple of this floor:

> **CORRECTED 2026-08-31.** The table below applied this floor to arms B, C, D and E. That was
> wrong: those arms all come from ONE fit, so seed variation cannot enter them, and the applicable
> floor is pipeline non-determinism at 1.42%. B and D are reinstated. See
> `reports/pipeline_determinism_and_which_floor_applies.md`. This floor remains correct for
> comparisons between DIFFERENT fits, which is what it was measured on, and the BAD-fit row below is
> such a comparison and is unaffected.

| arm | dT | kind | applicable floor | status |
|---|---:|---|---|---|
| B, duplicate w015 | +0.1259 | same fit | pipeline 1.42%, 8.9x | reinstated |
| D, duplicate w012 | +0.1763 | same fit | pipeline 1.42%, 12.4x | reinstated |
| E, duplicate all ten | +0.9247 | same fit | pipeline 1.42%, 65.1x | stands |
| BAD, 100-step fit | -0.5951 | different fits | **seed 18.93%, 3.1x** | stands |

The claim that duplicating a single winding inflates the objective was withdrawn here and has since
been reinstated, for the floor-mismatch reason above. The strongest arm remains: doubling the surface with zero new papyrus raises the objective 92.47%,
which is 4.9x the floor and not attributable to seed spread.

I registered this withdrawal branch in advance precisely because it was the outcome I would
otherwise have been tempted to argue around. The control belonged before publication.

## The floor is the more useful finding

`autoresearch.md` already anticipates seed sensitivity and prescribes the right practice:

> The code is sensitive to the random seed and CUDA non-determinism. Prefer changes that are robust
> across seeds/runs... a cheap robustness check is to run the same change under two seeds
> concurrently and see if the ink gain survives.

This puts a number on it for one dataset and ROI: **about 19%**. If that magnitude is typical, then a
single-run ink gain below roughly 19% carries little information, and the two-seed check the doc
recommends is not merely prudent but load-bearing. The same spread also bounds what the satisfaction
metrics can tell you about ink: these two fits differ by 0.0006 in satisfied area and by 19% in
recovered ink.

## Limit, registered in advance

**One seed pair is one difference, not a distribution.** 18.9% is a point estimate, not a confidence
interval, and must not be treated as one. Establishing a real floor needs several seeds; three or
more would give a spread rather than a single number. That is the obvious next run and has not been
done. One dataset, one ten-winding span.
