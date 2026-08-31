# Pre-registration: how much of the 18.9% is the fit, and how much is the pipeline?

**Written 2026-08-31, before the repeat run.**

## Why

`reports/objective_seed_noise_floor.md` measured 18.9% between two fits differing only in seed, and
that number is now load-bearing: it withdrew arms B and D. But it was measured end to end, so it
bundles two sources that have not been separated:

* **fit noise**, the thing I attributed it to;
* **pipeline noise**, from re-running render and score on identical input. The lasagna flatten is a
  GPU optimisation, flatboi and SLIM are iterative, and the scorer ensembles three nnU-Net folds.
  None of that is obviously bit-reproducible.

If the pipeline alone accounts for a large share, then "seed noise" is the wrong label and the
interpretation in that report needs changing.

## Arm

Re-run render and score on **the exact same baseline01 meshes already used**, w010..w019, same
settings, same wrapper, same scorer. Nothing about the input differs. Reference is the first run:
`total_fg_pixels` 240,088, `fg_fraction` 0.00897, line 0.438, column 0.232.

## Prediction, fixed now

**`|dT(repeat)| < 0.02`.** Same meshes and same model should give nearly the same answer; I expect
small non-determinism from the GPU flatten, not a large one.

## Decision rule

Let `dT = (total_fg(repeat) - 240,088) / 240,088`.

* **Pipeline effectively deterministic** if `|dT| < 0.02`. The 18.9% is then attributable to the
  fit, and `objective_seed_noise_floor.md` stands as written.
* **Pipeline contributes materially** if `0.02 <= |dT| < 0.10`. The 18.9% is a combined figure and
  that report must be amended to say so.
* **Pipeline dominates** if `|dT| >= 0.10`. Then the 18.9% is largely not about seeds at all, the
  report's framing is wrong, and arm E's +92.5% is measured on a far noisier instrument than I
  claimed. This is the outcome that costs most and is registered for that reason.

## Control

The repeat must render non-blank and its lasagna flatten must converge, as every arm so far has.

## Limit

One repeat gives one difference. Like the seed measurement it is a point estimate, not a spread.
