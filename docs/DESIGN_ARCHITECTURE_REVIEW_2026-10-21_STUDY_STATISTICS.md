# Design and architecture review — the registered studies' shared statistics

Date: 2026-10-21. Baseline: `f67ed18b` (main after #175).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/analyse_gap_ink_arm.py`'s `welch` and `separation`. They were written for the gap study (4 baselines
against 3 gap fits). Seven later analyses import them:
- the second look, at 6 against 6;
- the exploratory gap contrast, on the gap study's own fits: up to 4 against 3;
- the patch bootstrap, the strip match, the anchor ablation and the current-villa same-winding study, each at
  3 against 3;
- the same-winding study, at 3 ablated fits against 6 baselines.

`FINDINGS.md` cites the patch-bootstrap tooling as "tested and reusable". No earlier review covered these files.

Main has not moved since #175. The owner's open PR #170 changes the octant-crop files and
`reports/tolerance4_rescore.md`, none of which this round touches. This round covers the 16:13 UTC firing.

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
    - Every report or finding that quotes the separation's 2.86% is about the gap study, at 4 against 3:
      `reports/gap_fix_ink_six_fits.md` and `reports/SPIRAL_FINDINGS_SUMMARY.md`, as its registration does.
    - The second look's 0.108%, in `reports/gap_fix_costs_ink_established.md` and `SPIRAL_FINDINGS_SUMMARY.md`, was
      printed by its own line, which was right.
    - None of the 3-against-3 or 3-against-6 verdicts reports complete separation.
    - In every one of these studies separation is printed as a confirmatory check only, and no verdict depends on it.
- **Tests** (`tests/test_analyse_gap_ink_arm.py`):
  - the message at each of the four sizes. Hard-coding 2.86% again fails three of them;
  - a fit tied with the other arm's extreme does not separate them. Nothing pinned that before.

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

  The claim rests on BOOTSTRAP against RANDOM. Contrasts with the baselines are printed as carrying no claim. Ink
  not significant with geometry significantly down falls to the last row, NULL; the registration's table has no row
  for that case.

## Observations for the owner (not changed)

- **The minimum detectable effect is computed for a z-test, and the studies run a Welch t-test at 3 fits per arm.**
  - `detectable_effect`, the studies' `mde` and `scripts/measure_noise_floor.py` all use
    (z₀.₉₇₅ + z₀.₈₀) · CV · √(1/n_a + 1/n_b), with z₀.₉₇₅ + z₀.₈₀ = 2.802.
    - The registrations quote that figure as the effect a null excludes. The patch bootstrap's says "80% power at
      alpha 0.05 needs about 9.6%".
    - `FINDINGS.md` says the patch-bootstrap and strip-match nulls show "no ink effect larger than ~10%", corrected on
      2026-09-12 to ~12% for the CV, "at three fits per arm".
  - The test the verdicts use is Welch's. At 3 against 3 it has at most 4 degrees of freedom: the committed
    verdicts' range from 2.35 to 4.00. Its power at that effect is well below 80%.
  - **Simulated**, with normal fits whose standard deviation in both arms is the CV times the control's mean, 40,000
    draws, seed 0:

    | arms | stated effect (CV 0.0514) | Welch's power there | effect with 80% Welch power |
    |---|---|---|---|
    | 3 vs 3 | 11.8% | 46% | 18.0% |
    | 4 vs 3 | 11.0% | 53% | 15.6% |
    | 3 vs 6 | 10.2% | 56% | 14.6% |
    | 6 vs 6 | 8.3% | 70% | 9.4% |

  - Under that model the power at the stated effect does not depend on the CV, since both scale with it.
  - If each arm's standard deviation is the CV times its own mean instead, 3 against 3 gives 50% power for a fall
    (16.7% needed for 80%) and 42% for a rise (20.0% needed). The conclusion is the same.
  - The independent review reproduced the table with 200,000 draws.
  - So a 3-against-3 null excludes effects of about 1.5 times the stated figure with 80% power, not the figure
    itself. For the patch bootstrap and the strip match that is about 18% rather than about 12%.
  - The formula is part of each registration, and `FINDINGS.md`'s sentence is the owner's. Whether to restate the
    bounds, with a t-based or simulated power, and whether to change `measure_noise_floor.py` for new studies, are
    the owner's calls.
- **`separation`'s percentage turns to scientific notation from 12 against 12.** No study is that large.
- **The separation message's "GAP" and "BASE" are positions.**
  - The patch bootstrap passes (RANDOM, BOOTSTRAP), so "all GAP below all BASE" there means every BOOTSTRAP fit below
    every RANDOM fit.
  - Naming the arms would change the registered studies' printouts, so it is left as is.

## Verification

- `pytest` on the tests of this module, of the seven studies that import it, of the verdict runner and of the stale-CV
  guard (nine files): 104 passed.
- Mutants caught:
  - 2.86% hard-coded again fails three of the four size cases;
  - a tie counted as separation fails the new tie case.
- Ruff 0.9.10 `check` and `format` are clean on both changed files, which were formatted before.
- **The standard suite** on the first commit (`12354eb2`) ran as on main: 2704 passed, with the same 42 failures and
  2 errors, all environmental. No test in it imports this module. The smoke test gave 9 of 11 passed and 2 skipped,
  as on main.
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - It confirmed:
    - 1/C(n_base + n_gap, n_gap) is the exact null probability, by enumerating every split at 4v3, 3v3, 6v3, 3v6,
      2v2 and 2v5, and by 2 million draws at 6v6;
    - the 4v3 output is byte-identical to before, over 20,000 random inputs with ties;
    - every caller passes its control first, at the sizes above, and no verdict reads separation;
    - no committed JSON carries the string, and none of the 3v3 or 3v6 studies separated;
    - the power table, with 200,000 draws;
    - the quotations of `FINDINGS.md` and the registration.
  - Its should-fix finding: this document listed `gap_fix_costs_ink_established.md` as quoting 2.86%. It quotes the
    second look's 0.108%.
  - Its nits:
    - seven later analyses, not six;
    - the exploratory contrast's sizes;
    - "about" 4 degrees of freedom, where 4 is the most;
    - the simulation's model, equal standard deviations rather than equal CVs;
    - the test count;
    - #170 also changes a report;
    - a comment that split a test case over five lines;
    - nothing pinned `separation`'s strictness;
    - the percentage's notation at large sizes.

  All are addressed above.
