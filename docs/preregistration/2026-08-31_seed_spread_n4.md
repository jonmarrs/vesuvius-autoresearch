# Pre-registration: the seed spread of `total_fg_pixels` over four fits

**Written 2026-08-31, before seeds 3 and 4 are fitted.** Two fits exist (`baseline01`, `seed02`);
seeds 3 and 4 have not been run.

## Why

`reports/objective_seed_noise_floor.md` reports 18.93% from **one** pair, and I flagged in it that a
single difference is a point estimate and not a distribution. It has since been used to judge
whether other results are real, so it needs to be an actual spread. Four fits give four values and
six pairwise differences.

## Method

Two further fits, identical to `baseline01` in every respect except `optimizer_random_seed` (3, 4).
Same dataset, same z-ROI 13056..18432, same 30,000 steps, same config overrides. Each is then
rendered and scored on windings w010..w019 with the settings used by every arm so far.

## Statistics to report, fixed now

* the four `total_fg_pixels` values, with `satisfied_area_fraction` beside each;
* **coefficient of variation** `CV = sd/mean` over the four, as the headline spread;
* all six pairwise `|dT|`, with min, median and max;
* the same for `overall_fg_fraction`, `line` and `column`.

No statistic will be selected after seeing the numbers. CV is the headline because it is scale free
and does not depend on which fit is called the reference, which the current 18.93% does.

## Predictions, fixed now

1. **`CV` between 0.04 and 0.15.** One observed pair at 18.93% implies a sizeable spread, but a
   single pair can easily be near the extreme of the distribution.
2. **`max |dT|` >= 0.10.** The observed pair should not turn out to be an outlier by a wide margin.
3. **The four fits are of indistinguishable quality**, `satisfied_area_fraction` within 0.01 of each
   other, as `baseline01` and `seed02` already are (0.8398, 0.8404). If a new seed lands far outside
   that, it is not a like-for-like member and must be reported separately rather than pooled.

## Consequences, fixed now

* If `CV <= 0.05`, then 18.93% was an unlucky pair, the floor for fit-to-fit comparison is smaller
  than reported, and `objective_seed_noise_floor.md` overstates it. The BAD-fit result at -59.5%
  would then clear the floor by considerably more than 3.1x.
* If `CV >= 0.10`, the objective is very noisy across seeds and any single-run gain below roughly
  `2 x CV` is uninterpretable. That is the number worth passing on, since `autoresearch.md` already
  prescribes a two-seed check without quantifying what it must beat.
* Either way, the same-fit arms (B, C, D, E) are untouched: seed spread does not apply to them, per
  `reports/pipeline_determinism_and_which_floor_applies.md`.

## Controls

Each new arm must render non-blank, its lasagna flatten must converge, and its `gap>=2` duplicate
coverage must be near 0%, confirming it is not duplicate-inflated.

## Limit

Four seeds is a small sample. A CV from n=4 has wide uncertainty, and it will be reported as an
estimate from four fits, never as "the" noise floor.
