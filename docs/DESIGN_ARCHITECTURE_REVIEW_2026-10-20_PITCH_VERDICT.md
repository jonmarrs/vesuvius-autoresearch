# Design and architecture review — the pitch analysis's verdict against its registration

Date: 2026-10-20. Baseline: `db9924e6` (main after #146).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/neural_tracer_pitch_analysis.verdict`, which turns finding 92's rows into its predictions and its
reading. Finding 92 is new (#143), and the October filing draft cites it (#144). The verdict was compared, rule by rule,
with `docs/preregistration/2026-10-19_neural_tracer_training_pitch.md`. Finding 91's verdict
(`neural_tracer_analysis.verdict`) was read too; its four predictions are shares of cubes, as registered.

## What changed

- **The materiality rule was not the registered one.**
  - The registration: the published ScrollGT row moves materially if P3 fails (the median pitch-over-native ratio of
    merge-penalized ERL outside 0.85–1.15), or the comparison with our tracer flips on 2 or more cubes.
  - The code tested `|median log ratio| > log 1.15` instead of P3. That is symmetric in log space, so its lower edge
    was 1/1.15 = 0.87, not 0.85. A median between 0.85 and 0.87 passed P3 and still read as material.
  - It now uses P3's own result: material if P3 is false, or the flips are 2 or more.
- **A cube traced to nothing left the median.**
  - The median was over log ratios, and a cube whose pitch-matched score was 0 had no log, so it was dropped. The
    registration's median is over the 21 cubes' ratios, and a 0 is a ratio of 0: the largest drop there can be.
  - The median is now over the ratios themselves. Only a cube with no native score is left out, its ratio being
    undefined.
  - With an odd count this is the same median as before. With an even count it is the mean of the middle two ratios,
    not their geometric mean.
- **Tests** (`tests/test_neural_tracer_pitch_analysis.py`, 2 new):
  - a median of 0.86 with no flips reads as not material;
  - cubes traced to nothing count as ratios of 0.

  Both fail with main's code.

## The published result is unchanged

`reports/neural_tracer_pitch.json` has all 21 rows, none of them 0, and a median ratio of 0.63 with 8 flips. Both
rules read that as material, and the medians agree. `tests/test_neural_tracer_pitch_report.py`, which recomputes the
verdict from the committed rows, passes unchanged. The report and the draft state the registered rule.

## Verified, no change needed

- P1 (in-sample trails on at least 9 of 11), P2 (Scroll 3 leads on at least 6 of 8), and their minimum row counts
  match the registration.
- Flips are counted over every scored cube, as registered.
- `identity_problems` refuses a `run.json` that differs from the registered entrant in checkpoint, settings, box, CT
  or presence (tested against finding 91's own run).
- `scale_back` maps resampled voxels into the cube's frame by r = 9.6 / 7.91, the inverse of
  `resample_cube_pitch.resample` (tested).

## Observations for the owner (not changed)

- **The in-sample reading with a failed cube.** The registration reads "pitch is a material cause of the in-sample
  deficit" when the tracer "no longer trails our tracer on 3 or more in-sample cubes (P1 fails)". With all 11 rows
  those two agree. With 9 or 10 they do not: at 10 rows and 8 trailing, P1 fails, but only 2 have stopped trailing.
  The code follows the "3 or more". Which governs is the owner's call; this run had all 11.
- **The research and filing tests are outside the standard suite**, finding 91's and 92's included. They pass in
  this container in under a second.

## Verification

- `pytest tests/test_neural_tracer_pitch_analysis.py tests/test_neural_tracer_pitch_report.py`: 15 passed. With main's
  script, the 2 new tests fail.
- Ruff clean, the unused `math` import removed. Mypy clean on the changed files, the test included.
- The standard suite: see the PR.
