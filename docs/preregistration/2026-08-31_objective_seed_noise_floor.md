# Pre-registration: what is the seed-to-seed noise floor of `total_fg_pixels`?

**Written 2026-08-31, before the seed02 arm is rendered or scored.**

## Why this is a correction to my own work

`reports/duplicate_coverage_inflates_the_objective.md` reports duplicate arms at `dT` = +0.126
(B), +0.176 (D) and +0.925 (E) against one baseline, and `reports/objective_does_track_fit_quality.md`
reports -0.595 for a bad fit. **None of those has a noise floor under it.** I never measured how much
`total_fg_pixels` moves between two fits that are equally good, so I cannot presently say whether
+0.126 is a real effect or ordinary run-to-run spread. That is a missing control in work I have
already written up, and it should have been run first.

`seed02` is a second converged fit of the same dataset, same ROI, same 30,000 steps, differing only
in seed. Its satisfaction is statistically indistinguishable from baseline01: satisfied area 0.8404
against 0.8398, satisfied patches 0.6616 against 0.6542. Two fits this close in quality should score
close in ink if the objective is stable.

## Arm

Windings w010..w019 from `seed02`, identical render and scoring settings to every arm so far.
Reference is baseline01: `total_fg_pixels` 240,088, `fg_fraction` 0.00897, line 0.438, column 0.232.

## Prediction, fixed now

**`|dT(seed02)| < 0.05`.** Two fits of the same quality on the same data should differ by only a few
percent in recovered ink.

## What each outcome does to the existing reports

* **`|dT| < 0.05`**: the floor is small, arms B (+0.126) and D (+0.176) clear it by 2.5x to 3.5x and
  stand, E (+0.925) and the quality result (-0.595) stand comfortably.
* **`0.05 <= |dT| < 0.10`**: B and D are only about 1.3x to 1.8x the floor. They must be reported as
  **marginal**, and the duplicate-coverage claim then rests mainly on E.
* **`|dT| >= 0.10`**: **B and D are inside the noise and must be withdrawn as evidence.** The claim
  would rest on E alone, which is a single arm, and the report would need amending to say so.

I am registering the withdrawal branch explicitly because it is the outcome that costs me the most,
and it is the one I would otherwise be tempted to argue around.

## Controls

* the arm must render non-blank, p95 > 0;
* its lasagna flatten must converge;
* `gap>=2` overlap must be near 0%, confirming seed02 is not itself duplicate-inflated. Its full
  120-winding fit reads 0.10%, so the ten-winding subset should read at or near 0.00%.

## Limit

One seed pair gives one difference, not a distribution. A single `|dT|` is a point estimate of the
floor, not a confidence interval, and cannot be treated as one.
