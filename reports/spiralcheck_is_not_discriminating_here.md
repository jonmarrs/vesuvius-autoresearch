# spiralcheck does not separate our configs or track ink; its one real signal is post hoc

**2026-09-24.** The result of `docs/preregistration/2026-09-24_spiralcheck_validation.md`, decided by
`scripts/analyse_spiralcheck_validation.py` (committed at `e42c2417` with its tests, before
spiralcheck ran on any study fit).

* Data: `reports/spiralcheck_validation/collected.json`.
* Verdict: `verdict.json`.
* Unregistered checks: `descriptive.json` and `common_bins.json`, same directory.
* Tool: spiralcheck v0.4.0 at `d1b50e29`, default thresholds, our `umbilicus.json`.

## Verdict: NOT DISCRIMINATING HERE

**Instrument gate: passed.** All 24 inputs (12 fits × 2 scopes) gave byte-identical `intrinsic`
blocks on their repeat run. Every fit loaded 120 windings (scope all) or 10 (scope scored).

**Q2, config separation, whole family (α 0.0125). Nothing separates.**

| metric | F(2, 9) | p | anchor10cov | nosamecur | curbase |
|---|---:|---:|---:|---:|---:|
| violated_bin_fraction | 2.84 | 0.111 | 0.00269 | 0.00310 | 0.00296 |
| collapsed_bin_fraction | 0.004 | 0.996 | 0.00880 | 0.00880 | 0.00878 |
| inflated_bin_fraction | 1.66 | 0.243 | 0.01046 | 0.01066 | 0.01033 |
| median_pitch (vx) | 2.25 | 0.162 | 18.105 | 18.121 | 18.134 |

**Q3, tracks ink within a config, scored windings w120–w129 (df 8, critical |r| 0.750). Nothing
tracks.**

| metric | r | p | r without `curbase_s6` (df 7) |
|---|---:|---:|---:|
| violated_bin_fraction | −0.17 | 0.64 | +0.29 |
| collapsed_bin_fraction | +0.13 | 0.72 | −0.08 |
| inflated_bin_fraction | −0.51 | 0.13 | −0.20 |
| median_pitch | +0.54 | 0.10 | +0.18 |

The two largest correlations come from one fit. `curbase_s6` has the highest ink of the twelve
(3,583,420, +21% above the mean of the other five in its group). It also has the largest outer pitch and the fewest
inflated gaps in its group. Without it, every |r| ≤ 0.29.

**Q1, seed noise, whole family (pooled within config, df 9).**

| metric | sd | CV | 3v3 difference detectable at 80% (approx.) |
|---|---:|---:|---:|
| violated_bin_fraction | 0.00022 | 7.4% | ~19% |
| collapsed_bin_fraction | 0.00039 | 4.4% | ~11% |
| inflated_bin_fraction | 0.00025 | 2.4% | ~6% |
| median_pitch | 0.019 vx | 0.11% | ~0.3% |

The last column is 2.56 × CV, which is (t₀.₉₇₅ + t₀.₈₀ at df 9) × √(2/3). This is the figure
spiralcheck's own validation could not give: its seed was held fixed. **Two fits of one config
routinely differ by ~10% in violations with nothing changed but the RNG.**

**Q4, agreement with villa's `satisfied_area_fraction` (descriptive).** None. The config-centred r
values are +0.19, −0.50, −0.22 and −0.39; all p ≥ 0.14. The two geometry measures do not agree
about which seed of a config is better.

**Predictions:**

* Q1 (all four vary between seeds, moderate): **hit.**
* Q2: withheld.
* Q3 (null on all four, moderate): **hit.** A predicted null that holds at n = 12 is weak evidence of
  skill; it is recorded, not claimed.

## Post hoc, not registered: the ablation *is* visible in the scored windings

Q1 on the scored scope reports an ANOVA F for each metric but no verdict. Two of those values are
large:

| scored scope | F(2, 9) | p | anchor10cov | nosamecur | curbase |
|---|---:|---:|---:|---:|---:|
| median_pitch (vx) | 25.5 | 0.0002 | 12.67 | 13.01 | 13.11 |
| inflated_bin_fraction | 17.9 | 0.0007 | 0.108 | 0.094 | 0.094 |

**For median_pitch the groups do not overlap.**

* All three anchor fits: 12.64–12.71 vx.
* The other nine: 12.93–13.25 vx.
* Dropping `curbase_s6` leaves F = 27.9.

These were read after the data, so they are a lead, not a finding. Two controls were run before
writing this section.

**1. Composition is ruled out.** The subset runs each derive their own z bins, so the medians could
be taken over different cells. We recomputed all 12 fits with fixed z edges shared across fits and
spiralcheck's own loader and umbilicus. Every one of the 4,320 (pair, z, θ) cells is valid in all 12
fits. On that common set the median gaps are:

* anchor10cov: 12.65–12.70 vx;
* the other nine: 12.96–13.24 vx.

The separation stands.

**2. The *mean* gap does not separate.** Mean gap on the common cells:

* anchor10cov: 16.16–16.21 vx;
* the other nine: 16.12–16.45 vx. `nosamecur_s2` is below every anchor fit.

The inflated-fraction separation also comes mostly from the threshold, not the data:

* spiralcheck sets the threshold at 2.5 × the fit's own median. The anchor fits have a lower median,
  so they get a lower threshold.
* At a fixed 32.5 vx, the fractions overlap: anchor 0.098–0.101 against 0.093–0.099.

**What this is, then.** Removing 40 of 50 absolute anchors changes the *shape* of the outer
inter-winding gap distribution. Its median falls ~3%. The mean, and so the total radial extent of the
ten windings, does not move beyond seed noise.

That is consistent with `reports/anchor_gate_verdict.md`. The gate measured the step between
per-winding median radii around the strip centroid and found spacing unchanged (0.3%, p = 0.32).
That is a central-tendency measure of the overall step, not of the gap distribution. The two are not
in contradiction.

The gate's quoted 26.4 vx is not reproduced here. The same estimator on these fits' scored windings
gives 13.8–16.1 vx, and it also does not separate the configs. The gate's number was computed on a
different fit set and strip definition. This was not chased further.

**Ink did not follow.**

* Anchor mean `total_fg_pixels`: 2,872,949. curbase mean: 3,069,469. That is −6.4%, inside the
  fit-only floor of 0.074 [0.051, 0.134].
* The registered anchor ablation was a null on reading (`reports/anchor_ablation_verdict.md`).

So this joins the pattern of `reports/no_lever_has_improved_reading.md` and
`reports/samewinding_verdict.md`: **a geometry change real enough to show up with no overlap, and no
detectable consequence for the ink.**

## What this means for spiralcheck, stated so its author could use it

* **Deterministic, fast (~4 s per family on CPU) and robust on real fits.** All 24 runs were clean.
* **Its whole-family fractions are dominated by seed noise at our scale.** They cannot tell apart
  configs that differ by removing 5,413 same-winding constraints, or 40 of 50 absolute anchors.
  Anyone comparing two fits with it should expect ~7% run-to-run movement in the violated fraction
  from the RNG alone.
* **Restricted to the windings that matter, its median pitch detected a manipulation that
  whole-family use missed.** Evaluating the scored region rather than the whole family is the
  practical recommendation. This rests on a post hoc result: one manipulation, one region.
* **Its inflated/collapsed thresholds are relative to each fit's own median.** Comparing two fits
  whose medians differ therefore mixes a threshold shift into the count. At a fixed threshold the
  anchor "inflation" difference disappears.
* **None of its metrics predicted ink within a config here.** A null at |r| < 0.75 does not show
  they are irrelevant to reading.

No outward post is made or proposed here. Any note to the author goes through the posting policy
(`villa-posting-rate-limit`) and needs the user's approval.

## Limits

* One region (s1 slice 13056–18432), twelve fits, one villa tier, one umbilicus.
* Default spiralcheck thresholds at one commit.
* spiralcheck measures consistency, not correctness: there is no positional ground truth here
  (`column-metric-line-closed`).
* The post hoc section was selected after the data, from four scored-scope ANOVAs. Its p values
  survive a Bonferroni over all eight ANOVAs (0.00625). That is not the same as having registered
  them.
