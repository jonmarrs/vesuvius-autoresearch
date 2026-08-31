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

---

## Addendum 3, 2026-08-31: comparability controls, recorded before any seed 3 or 4 score exists

Seed 4 is still fitting and neither new arm has been rendered. These are checks on whether the four
arms are measurable against each other at all, which is worth recording now rather than after the
numbers land.

**The render and scoring tooling is byte-identical across all four arms.** Seeds 1 and 2 were
rendered with `spiral-fitting` extracted at villa `5479453a`. The pin has since advanced to
`c935851c3`, so this was checked rather than assumed:

```
render_ink.py        identical
get_ink_metrics.py   identical
tifxyz.py            identical
```

The three intervening upstream commits touch only volume-cartographer C++ and the fiber-merge and
vc-sync scripts, none of which is on the render path. Seeds 3 and 4 are nonetheless extracted from
`5479453a` explicitly, so comparability does not depend on that having been true. The container
binaries are unchanged: `vc-render:local` pins `VILLA_SHA=5479453a` and its VC tools come from the
frozen 2026-05-13 published image.

**Seed 3 clears both pre-registered controls.**

| control | seed03 | reference | verdict |
|---|---|---|---|
| quality gate, satisfied area within 0.01 | 0.8382 | 0.8398, 0.8404 | within band, pools |
| not duplicate-inflated, gap>=2 overlap | 0.00% (1 cell) | baseline 0.00% | clean |
| comparable surface | 206,847 cells | 206,321, 206,838 | within 0.3% |

Seed 4 gets the same three checks before it is pooled, and is excluded if it fails any of them.
