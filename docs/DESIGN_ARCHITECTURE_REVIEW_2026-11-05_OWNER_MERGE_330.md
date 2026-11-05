# Design and architecture review — the owner's #330

Date: 2026-11-05. Baseline: `0dbb1983` (main after #330).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 01:12 UTC firing.
- **#330 registers the two GPU studies** that #329 reviewed: the seed-heading confirmation (#328) and the refit-retry
  pilot (#326).
  - The owner approved both on 2026-11-03, before any trace. Each is amended in the open from #329's observations.
  - The predictions, thresholds and decision rules are as #329 left them.

Both scripts are now registered, so this round changes no study code. One test was added.

## What changed

- **The refit pilot's tolerance-4 baseline check had no test** (`tests/test_neural_tracer_refit_retry.py`).
  - The registration requires every baseline row to reproduce at both tolerances, or the status is BASELINE_DRIFT.
  - With the tolerance-4 comparison removed, all 34 tests passed: the existing case changes both rows alike.
  - The new test drifts only the tolerance-4 rows. It passes on the registered script and fails with that comparison
    removed.

## Verified, no change needed

- **The registered hashes.** `DATA_SHA256` holds the ten cubes of `CUBES`. Each NML hash equals the 11-02 evidence's
  (PR #326), and each image hash equals the checks record's, all 20 of them.
- **Where the hashes are checked.**
  - `nml_path` checks the NML, which `score` reads through `ground_truth`.
  - `cube_image` checks the image, which `fetch` and `presence` read.
  - A mismatch stops the command before any output.
- **The seed-heading zero baseline.**
  - A cube with zero `before` coverage or merge-penalized ERL is listed and left out of P1, P3, P4 and P5. P2 still
    applies to it.
  - The study is INCOMPLETE when no cube has a factor. The reading names the excluded cubes.
- **The refit baseline re-score.**
  - The 21 baseline runs are re-scored with the same scorer as the arms. `rows_match` requires every recorded field,
    exactly, after a JSON round trip.
  - BASELINE_DRIFT ranks after SMOKE_FAILED and before INCOMPLETE, and it makes no reading.
- **One result each.** Both `score` commands refuse an existing output before importing ScrollGT, and both record the
  ScrollGT commit.
- **Each new guard is reached.** Of 13 mutants (7 in the seed-heading script, 6 in the refit scorer), 12 fail a test
  as #330 committed it. The thirteenth is the tolerance-4 comparison above.
- **The cost figure.** "About 50 minutes" for the re-score is 11 cubes at 512³ × 265 s plus 10 at 256³ × 17 s,
  3,085 s.

## Observations for the owner (not changed: the scripts are registered)

- **A cube with no seed dots still stops `score`.** `skip_share` divides `no_heading` by `dots` for every cube before
  the zero-baseline filter, so a `before` run with no dots raises `ZeroDivisionError`. Such a run also has no
  coverage, which is the case the amendment meant to handle.
- **No loop-pausing wrapper is committed for either chain.** The seed-heading registration says a wrapper stops and
  restarts the loop "as the 10-28 re-run's wrapper did". `run_villa_seed_heading_rerun_paused.sh` checks for and runs
  only the re-run's own chain.
- **The image hash is of the release file.** The checks record hashes `imagesTr/<cube>_0000.tif`. `cube_image` reads
  `<cube>_image.tif` under the data directory, so the check passes only if that file is a byte copy. The fetch began
  before the registration commit, so its core comparisons may have read images without the check. `presence` applies
  it.
- **The NO_HIGH_SKIP_CUBE reading says "on any of the ten"** even when a zero-baseline cube is left out of P5. The
  appended note names the cube.

## Verification

- **The two studies' modules** give 60 passed, with the added test.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on #330's four Python files. Mypy is clean over the whole
  repository (880 files).
- **The standard suite** gives the same failures as round #144:
  - the 43 standing failures;
  - the 25 SDK cases that need `s3fs`;
  - the 2 modules that cannot be collected.
- **The 237 test modules outside the suite** give 2,241 passed, 80 skipped, 13 failed and 21 collection errors: the
  same failures as round #144.
- **The doc audit**, run alone, finds no new unresolved reference.
