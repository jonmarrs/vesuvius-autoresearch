# Design and architecture review — finding 93's analysis, and what its identity smoke shows

Date: 2026-10-20. Baseline: `da572b66` (main after #153).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #153 (finding 93):
- the registration (`docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md`);
- the chain (`repro/fibers/run_neural_tracer_seeding_chain.sh`);
- the analysis (`scripts/neural_tracer_seeding_analysis.py`), the report (`reports/neural_tracer_seeding.md`) and their
  tests.

Each was read against the registration, rule by rule.

## What changed

- **The analysis did not check that the identity smoke was the launcher's.**
  - The registration: "the launcher at the default smoothing (1.0) and `--tile-workers 0` … must reproduce finding
    91's `fibers.afv` … That shows the launcher changes nothing at the default."
  - `score()` compared the smoke's `fibers.afv` with finding 91's and nothing else. Villa's tracer is deterministic
    (the smoke itself shows it), so villa's tool alone, without the launcher, reproduces finding 91 too. The check
    could not tell whether the launcher had run, which is what the smoke is for.
  - The chain did run it through the launcher (its `trace` with `--smoothing 1.0`; the launcher forces
    `--tile-workers 0`). So the committed run's smoke is sound by construction. But `neural_tracer_seeding.json`
    recorded only that the `.afv` was identical.
  - **Change:** `smoke_check` also checks the smoke run's records, as every arm's runs are checked:
    - `run.json` against finding 91's settings, inputs, box, checkpoint and `tile_workers` of 0;
    - `seeding.json`, which only the launcher writes, at villa's smoothing of 1.0 and the Hessian's 1.5.

    `score()` records `launcher_problems` and `ok` with the smoke. The status is SMOKE_FAILED unless both the `.afv`
    and the records agree.
  - The committed result is unchanged and not re-scored here: the work directories are on the owner's machine.
  - The report test accepted only the smoke record as committed. A re-score would have failed it on the new keys, as
    finding 92's `sources` key did (the 2026-10-20 ridge-channel-scale review). It now checks the committed keys, and
    no launcher problems when they are recorded.
- **Tests** (`tests/test_neural_tracer_seeding_analysis.py`):
  - **`smoke_check`.** The launcher's smoke at the default passes. It fails, though the `.afv` is identical, in each
    of these cases:
    - without `seeding.json` (villa's tool alone);
    - with tile workers;
    - at arm A's smoothing;
    - at arm A's plane spacing;
    - on the 9.6 µm CT.

    A different `.afv` fails with clean records, and a missing run fails.
  - **`score()` end to end through `main()`**, with ScrollGT stubbed and no arm traced: INCOMPLETE with the
    launcher's smoke, SMOKE_FAILED with villa's tool alone.
  - Each of these mutants is caught:
    - the records ignored;
    - the smoke checked as arm B's run, or at smoothing r;
    - `seeding.json` assumed when absent;
    - a missing `run.json` passed;
    - `score()` gated on the `.afv` alone.

    With main's analysis, 7 tests fail.

## Verified, no change needed

- **The analysis implements the registration.**
  - A cube whose recorded seed dots differ from the probe's is MANIPULATION_FAILED and not scored.
  - A failed run is reported as failed, not scored as 0.
  - Fewer than 17 scored cubes in an arm leave its predictions unevaluated.
  - Any `run.json` or `seeding.json` off its arm gives IDENTITY_FAILED and no verdict.
  - P1 and P3 are medians of plain ratios over the scored cubes, with a native 0 refused, as #148 set for finding 92.
  - P2 counts Scroll-3 cubes where arm A beats ScrollGT's row for our tracer.
  - The four-way decision table maps as registered.
  - `score()` exits 1 unless OK.
- **The arms.**
  - The chain takes every flag from `args`, whose `repr` round-trips, so `run.json`'s floats equal the arm's exactly.
  - Arm A is scored as finding 92 (`scale_back`), arm B as finding 91. Both use ScrollGT scoring version 3 at
    tolerance 2.0.
- **The committed result.**
  - Status OK; 21 of 21 cubes scored in each arm.
  - No identity or manipulation problems; every run's seed dots equal the probe's.
  - All three predictions failed (0.67, 0 of 8, 0.88), so the registered reading is "the seeding scale is not the
    cause: the note stands".
  - `test_neural_tracer_seeding_report.py` recomputes every figure the report quotes from the JSON, the probe and
    finding 92's funnel: the group and ratio tables, the bullets and the run times.
- **The tracer is deterministic**, so arm A against finding 92's run (18 of 21 above it) compares settings, not draws.
- The report's and the pitch report's added sentences state the registered conclusion. The registration's predictions
  and decision rule are unchanged (pinned by hash).

## Observations for the owner (not changed)

- **P2's evaluability is tied to the arm's 17 rows, not to its Scroll-3 rows.**
  - With 17 or more rows but fewer than 6 Scroll-3 cubes scored, P2 reads False (6 of 8 cannot be reached), not
    unevaluated.
  - The registration does not say which; finding 92's had a Scroll-3 minimum of its own.
  - This run scored all 8.
- **The analysis now differs from the copy frozen in `seeding_run/`**, so the chain would refuse to resume there.
  That is harmless, since the run is complete. A re-score with the repository's copy adds the smoke's
  `launcher_problems` and `ok`.

## Verification

- `pytest` on the seeding analysis, seeding report, seeding launcher, pitch analysis, pitch report and filing-number
  tests: 100 passed, 4 skipped for want of the sibling checkouts.
- Ruff and ruff format are clean on the changed files, and mypy with `--warn-unused-ignores`, the tests included.
- The standard suite imports none of these modules.
