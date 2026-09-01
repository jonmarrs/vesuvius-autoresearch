# The objective is not broken, it is gameable. Both are true.

**2026-08-31.** Pre-registered in `docs/preregistration/2026-08-31_objective_tracks_fit_quality.md`
before either arm was rendered. **Verdict: premise HOLDS.** (Confirmed against the seed spread measured afterwards over FOUR fits, `reports/seed_spread_four_fits.md`: -59.5% is **2.7x** the 2*CV = 21.7% threshold for different-fit comparisons. The earlier statement of 3.1x was against a single pair and is superseded; the margin is smaller but the result still clears it.)

This is the counterweight to `reports/duplicate_coverage_inflates_the_objective.md`. Reporting that
the objective can be inflated 92% by duplicated coverage, without also reporting that it strongly
rewards a genuinely better fit, would misrepresent it.

## Result

Same ten windings, same render and scoring settings, two fits of the same dataset and ROI:

| fit | steps | satisfied area | total_fg_pixels | total_pixels | fg_fraction | line | column |
|---|---:|---:|---:|---:|---:|---:|---:|
| GOOD `baseline01` | 30,000 | 0.840 | 240,088 | 26,754,900 | 0.00897 | 0.438 | 0.232 |
| BAD `smoke01` | 100 | 0.100 | 97,202 | 24,175,800 | 0.00402 | 0.351 | 0.013 |

```
dT = -0.5951      registered rule: HOLDS if dT < -0.25
fg_fraction 0.45x    line -0.087    column -0.219
```

The two fits render nearly the same amount of surface, 203,318 occupied cells against 206,321, so
this is not an area effect. The bad fit simply lands on far less ink.

Controls, all pre-registered and passed: the BAD arm rendered non-blank at p95 5.0, its lasagna
flatten converged in 1m17s, and its gap>=2 duplicate coverage is 0.00%, so nothing it scored came
from double counting.

## The structure metrics discriminate quality but not duplication

`overall_column_score` is the sharpest signal here, collapsing 0.232 to **0.013**, a 94% drop to
effectively zero. `overall_line_score` moves much less, 0.438 to 0.351.

Set against the duplication arms, this is the useful observation:

| failure mode | total_fg | fg_fraction | line | column | gap>=2 overlap |
|---|---|---|---|---|---|
| catastrophically bad fit | catches it (-60%) | catches it (0.45x) | weak (-0.087) | **catches it (-0.219)** | blind (0.00%) |
| duplicated coverage | **rewards it (+92%)** | blind (-0.0004) | blind | blind | **catches it (100%)** |

No single number covers both, and the two guards are complementary rather than redundant: the
structure scores see a fit that has stopped resembling text, and the geometric overlap check sees a
fit that is counting the same text twice.

## What this does and does not license

**It does** support `autoresearch.md`'s premise at the coarse scale. A better fit really does recover
more ink here, by a wide margin, so the loop's objective is measuring something real.

**It does not** show the objective discriminates among *good* fits, which is the regime the loop
actually searches. `smoke01` is undertrained rather than interestingly wrong, no optimiser would
propose it, and the gap between two converged fits would be far smaller than 8.4x satisfied area.
That was registered as a limit before the run and is not weakened by the result.

One dataset, one ten-winding span, no seed repeats.
