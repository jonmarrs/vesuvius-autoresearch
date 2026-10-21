# Design and architecture review — the registered studies' shared statistics

Date: 2026-10-21. Baseline: `f67ed18b` (main after #175).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/analyse_gap_ink_arm.py`'s `welch` and `separation`. They were written for the gap study (4 baselines
against 3 gap fits). Six later analyses import them:
- the second look, at 6 against 6;
- the exploratory gap contrast, at any size of 2 or more;
- the patch bootstrap, the strip match, the anchor ablation and the current-villa same-winding study, each at
  3 against 3;
- the same-winding study, at 3 ablated fits against 6 baselines.

`FINDINGS.md` cites the patch-bootstrap tooling as "tested and reusable". No earlier review covered these files.

Main has not moved since #175. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches. This round covers the 16:13 UTC firing.

## What changed

- **`separation` printed the gap study's null probability for every study.**
  - It returned "p=2.86% one direction" whenever the arms separated completely. That is 1/C(7,3), the figure the
    gap study registered for 4 against 3.
  - At the other studies' sizes the probability of one complete separation in a named direction is:

    | arms | studies | probability | printed |
    |---|---|---|---|
    | 4 vs 3 | the gap study | 1/35 = 2.86% | 2.86% |
    | 3 vs 3 | the patch bootstrap, strip match, anchor ablation, same winding on current villa | 1/20 = 5% | 2.86% |
    | 3 vs 6 | the same-winding study | 1/84 = 1.19% | 2.86% |
    | 6 vs 6 | the second look | 1/924 = 0.108% | 2.86% |

  - At 3 against 3, a separation no stronger than 5% was printed as 2.86%.
  - The second look's own registration gives 0.108%, and its script prints that figure correctly on the same line.
    That line then gave two probabilities for one event.
  - **Change:** `separation` computes 1/C(n_base + n_gap, n_gap) from the fits it is given.
    - The gap study's output is unchanged, byte for byte.
    - The docstring gives the figure at each size and says callers pass their control first. The "GAP" and "BASE"
      in the message are positions, not arm names.
  - **No published figure was wrong.**
    - Every report or finding that quotes 2.86% is about the gap study, at 4 against 3:
      `reports/gap_fix_ink_six_fits.md`, `gap_fix_costs_ink_established.md` and `SPIRAL_FINDINGS_SUMMARY.md`.
    - None of the 3-against-3 or 3-against-6 verdicts reports complete separation.
    - In every one of these studies separation is printed as a confirmatory check only, and no verdict depends on it.
- **Test** (`tests/test_analyse_gap_ink_arm.py`): the message at each of the four sizes. Hard-coding 2.86% again
  fails three of them.

## Verified, no change needed

- **`welch`** is scipy's unequal-variance t-test.
  - Its interval uses the Welch–Satterthwaite degrees of freedom and the t quantile, relative to the control's mean.
  - Two constant arms are reported as degenerate rather than given a p-value.
- **`separation` is strict.** A fit tied with the other arm's extreme does not count as separated.
- **`analyse_patch_bootstrap.verdict`** is the decision table of `docs/preregistration/2026-09-03_patch_bootstrap.md`.
  The rows are, in order:
  - ink up and significant;
  - ink down and significant;
  - ink not significant with geometry up and significant, recorded as a FAILURE;
  - neither.

  The claim rests on BOOTSTRAP against RANDOM. Contrasts with the baselines are printed as carrying no claim.

## Observations for the owner (not changed)

- **The minimum detectable effect is computed for a z-test, and the studies run a Welch t-test at 3 fits per arm.**
  - `detectable_effect`, the studies' `mde` and `scripts/measure_noise_floor.py` all use
    (z₀.₉₇₅ + z₀.₈₀) · CV · √(1/n_a + 1/n_b), with z₀.₉₇₅ + z₀.₈₀ = 2.802.
    - The registrations quote that figure as the effect a null excludes. The patch bootstrap's says "80% power at
      alpha 0.05 needs about 9.6%".
    - `FINDINGS.md` says the patch-bootstrap and strip-match nulls show "no ink effect larger than ~10%", corrected on
      2026-09-12 to ~12% for the CV, "at three fits per arm".
  - The test the verdicts use is Welch's. At 3 against 3 it has about 4 degrees of freedom, so its power at that
    effect is well below 80%.
  - **Simulated**, with normal fits of equal CV in both arms, 40,000 draws, seed 0:

    | arms | stated effect (CV 0.0514) | Welch's power there | effect with 80% Welch power |
    |---|---|---|---|
    | 3 vs 3 | 11.8% | 46% | 18.0% |
    | 4 vs 3 | 11.0% | 53% | 15.6% |
    | 3 vs 6 | 10.2% | 56% | 14.6% |
    | 6 vs 6 | 8.3% | 70% | 9.4% |

  - The power at the stated effect does not depend on the CV, since both scale with it.
  - So a 3-against-3 null excludes effects of about 1.5 times the stated figure with 80% power, not the figure
    itself. For the patch bootstrap and the strip match that is about 18% rather than about 12%.
  - The formula is part of each registration, and `FINDINGS.md`'s sentence is the owner's. Whether to restate the
    bounds, with a t-based or simulated power, and whether to change `measure_noise_floor.py` for new studies, are
    the owner's calls.
- **The separation message's "GAP" and "BASE" are positions.**
  - The patch bootstrap passes (RANDOM, BOOTSTRAP), so "all GAP below all BASE" there means every BOOTSTRAP fit below
    every RANDOM fit.
  - Naming the arms would change the registered studies' printouts, so it is left as is.

## Verification

- `pytest` on the eleven test files that use `separation`, `welch` or this module: 179 passed and 1 skipped, with
  the four new cases.
- Ruff 0.9.10 `check` and `format` are clean on both changed files, which were formatted before.
