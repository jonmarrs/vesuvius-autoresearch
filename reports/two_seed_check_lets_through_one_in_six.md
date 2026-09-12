# The prescribed two-seed check lets through one null change in six

**2026-09-01.** `spiral-fitting/autoresearch.md` prescribes a robustness check and does not say what
it can detect. `reports/seed_spread_four_fits.md` measured the noise it has to beat. This puts the
two together.

## What the doc prescribes

> Prefer changes that are robust across seeds/runs, not ones that only help for one specific seed.
> Since you run two at a time, a cheap robustness check is to run the same change under two seeds
> concurrently and see if the ink gain survives.

The instinct is right, and it is the reason this work measured the seed spread at all. The question
is what two seeds buys at a `total_fg_pixels` CV of **0.1086**.

## Result

Two decision rules a reader could reasonably take from that paragraph, scored at a **true effect of
zero**, so every acceptance is a false positive:

| rule | exact, n=4 | parametric, 200,000 sims |
|---|---:|---:|
| **A** accept if both change runs beat both baseline runs | **1/6 = 16.7%** | **16.6%** |
| **B** accept if the mean of two beats the mean of two | **3/6 = 50.0%** | **49.9%** |

The assumption-free enumeration over the four measured values and the simulation agree to a decimal,
which is worth more than either alone: the tiny exact calculation cannot be wrong about its own
arithmetic, and the simulation cannot be accused of resting on three data points.

**Rule B is a coin flip.** Comparing a mean of two against a mean of two, drawn from the same
distribution, is 50/50 by construction. It is not a filter at all.

**Rule A lets through one null change in six.** A loop that evaluates many changes and keeps those
passing a 16.6% filter will accumulate false wins in proportion to how many it tries.

## Power, for the same rules

| true effect | rule A accepts | rule B accepts |
|---:|---:|---:|
| 0% | 16.6% | 49.9% |
| 5% | 28.0% | 66.9% |
| 10% | 41.4% | 80.3% |
| 20% | 67.2% | 94.9% |
| 30% | 85.1% | 99.1% |

A genuine **+10%** improvement is caught by rule A **41%** of the time. Most real gains of that size
are discarded, while one null in six is kept.

## What would fix it

| seeds per arm | rule A false positives | cost in fits |
|---:|---:|---:|
| 2 | 16.6% | 4 |
| 3 | **5.0%** | 6 |
| 4 | 1.5% | 8 |
| 5 | 0.4% | 10 |

**Three seeds per arm brings rule A to 5%** for two extra fits. That is the cheap change. No number
of seeds helps rule B, because averaging does not alter a 50/50 comparison of equal distributions.

## A cheaper fix than more seeds: require two metrics

The scorer already writes `overall_line_score` and `overall_column_score` on every run, at no extra
cost. Their seed CVs differ sharply from the objective's:

```
total_fg_pixels  CV 0.1086
line score       CV 0.0342     <- three times more seed-stable
column score     CV 0.1343
```

A rule of "accept only if `total_fg` AND `line` both survive both seeds" is stronger, but by how much
depends on how the two co-vary across seeds. **At n=4 that correlation cannot be estimated**: the
observed values are +0.55, -0.56 and +0.29 for the three pairs, and a correlation from four points
has a 95% interval spanning almost the whole range. So the answer is **bounded, not estimated**:

| assumed correlation | false positives |
|---:|---:|
| -0.5 | 0.9% |
| 0.0 | 2.8% |
| +0.5 | 6.1% |
| +0.9 | 11.4% |
| +1.0 (perfectly redundant) | 16.7% |

Against 16.6% for `total_fg` alone. The two-metric rule is **stronger across the whole plausible
range and never weaker**, even in the worst case where the metrics are perfectly redundant and it
degenerates to the single-metric rule. It costs no extra fits, unlike a third seed.

**This is a corroborating filter, not a substitute objective.** Line score measures text-line
periodicity, not recovered ink, and
`reports/duplicate_coverage_inflates_the_objective.md` showed it fails to catch duplicated coverage.
It is being used here for its low seed variance, not as a measure of the thing being optimised.

## Limits

Four fits, one dataset, one ROI, one architecture. The parametric arm assumes approximate
log-normality of the seed distribution, which n=4 cannot test; the exact arm assumes nothing but
rests on three splits. Both assume a change alters the mean and not the spread itself, and a change
that also changed the seed sensitivity would not be described by this. The CV is a point estimate
from four fits, and every rate here scales with it: at half the noise these numbers improve
substantially, at double they get worse.

This describes the metric's behaviour under the measured noise. It does not observe villa's loop and
makes no claim about what it has accepted.

Reproduce: `scripts/analyse_two_seed_check_power.py`.

---

# Correction and strengthening, 2026-09-12

Re-checked after `reports/noise_floor_by_tier.md` found the noise estimate behind the power table was
from the wrong tier. **Half of this report was obsolete and the other half is stronger than it knew.**

## The power table above is obsolete for current villa

It was computed at the **inner** CV of 0.1086. Current villa's seed noise on `total_fg_pixels` is
**0.0125** — 8.7× quieter. Rerun at that noise:

| true effect | rule A @ 0.1086 | rule A @ 0.0125 |
|---:|---:|---:|
| 2% | 21.1% | **66.4%** |
| 3% | 23.6% | **86.1%** |
| 5% | 28.6% | **99.2%** |
| 10% | 43.7% | **100%** |

**On current code the two-seed check has excellent power.** The "it cannot see a 10% gain" half of
this criticism does not apply to the loop villa runs today, and should not be repeated.

## The false-positive half is not merely intact, it is exact and distribution-free

The acceptance rate under a true effect of zero is a **rank** statistic. If the change and baseline
runs are exchangeable under the null, the chance that all *k* change runs land above all *k* baseline
runs is exactly

> **1 / C(2k, k)**

| seeds per arm | false positives | simulated (300k) |
|---:|---:|---:|
| 2 | **1/6 = 16.67%** | 16.60% |
| 3 | **1/20 = 5.00%** | 4.98% |
| 4 | **1/70 = 1.43%** | 1.38% |

**This does not depend on the CV, the metric, the code version, or how good the fits get.** It is why
the 16.6% simulated at 0.1086 and the 16.7% simulated at 0.0125 agree: there was never any noise
dependence to find. A loop cannot fix this by fitting better.

That makes the finding sharper than first stated. The original framing invited "this matters because
the fits are noisy". The correct framing is the opposite: **it matters no matter how quiet the fits
get, and villa's fits just got 4× quieter without moving it at all.**

## The fix is one extra seed

Going from two seeds to three takes the false-positive rate from **1 in 6 to 1 in 20** — a
conventional 5% — at 1.5× the compute. On current code three seeds also detects a 3% effect 86% of
the time, so the extra seed costs little and buys both halves at once.

## What changed in what we would say outward

* **Drop:** "the check cannot detect realistic gains." False on current code.
* **Keep and sharpen:** "the check accepts 1 null in 6, exactly, for structural reasons no amount of
  fitting improves; three seeds makes it 1 in 20."
