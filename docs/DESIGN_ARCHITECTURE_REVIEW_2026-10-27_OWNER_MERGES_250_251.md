# Design and architecture review — the owner's #250 (steps and ranking) and #251 (the incumbent's saved reference)

Date: 2026-10-27. Baseline: `f7b094a9` (main after the owner's #250 and #251).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12–06:13 UTC firings. The 22:14–02:12 firings found main unmoved after #249. #251 merged
while the review of #250 was under way, and this branch merges it.
- **#250** regresses each measure's deviation from its tweak × epoch mean on the steps' deviation. It uses the 546
  cycles before the batchgeneratorsv2 window (`scripts/loop_steps_vs_ranking.py`,
  `reports/loop_steps_vs_ranking_2026-10-26.md`).
  - Within a tweak, cycles that train fewer steps score a higher ROC AUC and AP lift, and the same val_f1.
  - About a fifth of batchgeneratorsv2's AUC gain is the size of its step deficit.
- **#251** reads the incumbent's ROC AUC and AP lift from the metadata saved in `best_model.pt`
  (`scripts/loop_incumbent_reference.py`, `reports/loop_incumbent_reference_2026-10-27.md`). It also:
  - refreshes the October readiness plan;
  - notes a Villa source check in the seed-heading draft;
  - makes #250's regeneration test tolerate floating-point roundoff.

## What changed

- **#250's time-adjusted slope depended on the runner's timezone.**
  - `deviations()` turned each start into hours with `datetime.timestamp()`. The starts are naive, so that reads
    them in the zone of the machine running the script.
  - UTC and America/Los_Angeles agree. A runner in Europe/London, whose clocks went back on 2026-10-25 inside the
    record, got different within-group hours. All three `with_hours` slopes then moved: val_f1 from −0.0000468 to
    −0.0000463, for example. The rounded report figures did not change.
  - The hours are now the loop's wall clock read as such: the start minus 1970-01-01, the same on every machine.
    The loop's own clock (PDT) does not change inside the record, so wall-clock differences are elapsed time.
  - With OpenBLAS's Haswell kernel, the fixed script gives the committed record's bytes in UTC,
    America/Los_Angeles and Europe/London.
  - A new test reads the record's deviations under UTC and under London's rules. The rules are given as a POSIX TZ
    string, so no tz database is needed. The test requires the hours to be equal, and fails against #250's script.
- **#251's new files failed the pre-commit checks.**
  - The mypy hook runs on the whole repository, and it stopped on `scripts/loop_incumbent_reference.py`: the
    NumPy 1.x fallback import redefined `scalar`. The fallback now carries `# type: ignore[no-redef]`. The locked
    NumPy, 2.2.6, takes the first import.
  - Ruff 0.9.10 flagged two things:
    - the script's import block (I001);
    - the regeneration test's `zip()` without `strict=` (B905). The lengths are asserted equal just before, so it
      is now `strict=True`.
  - `ruff format` also reformats the script and its test.
  - With these errors, the hook would have refused the next commit that touched any Python file.

## Verified, no change needed

- **#250's regeneration test.**
  - As #250 merged it, the test compared bytes and failed here. OpenBLAS picks its dot-product kernel for the CPU,
    and the kernels sum in different orders.
  - With `OPENBLAS_CORETYPE=Haswell` or `Zen`, the script gives the committed record byte for byte. `SkylakeX`, the
    AVX-512 kernel, changes the last digits of 13 numbers, and no reported figure moves.
  - #251 fixed the test independently: it compares floats to 1e-12, keeps the permutation p-values exact, and
    checks types. This branch takes #251's version and drops the 1e-9 comparison this round had first written.
- **#250's figures.** The owner's tests bind the report's tables to the record. The rest hold against the source
  record:
  - batchgeneratorsv2 averages 962 steps, against 1,261 for the other tweaks of the same step cost;
  - UAMT off averages 4,155 steps, 2,934 more than its epochs' other cycles;
  - batch 16 averages 627 steps, 634 fewer than the same-cost tweaks.
- **#250's method.**
  - The learning rate follows the elapsed share of the time budget, as the report says: `budget_lr_factor` takes
    `total_training_time / config.time_budget`.
  - The slope's degrees of freedom are cycles − groups − 1, right for a within-group regression through the origin.
  - The permutation shuffles the steps within each group, which leaves `x @ x` unchanged.
  - The bins hold all 454 deviations (24 + 42 + 320 + 62 + 6).
- **#251's figures match its record.**
  - **Means:** all 546 cycles score 0.267034, 0.577928 and 1.181224 (F1, AUC, AP lift). batchgeneratorsv2 scores
    0.271027, 0.589681 and 1.218496, and the other tweaks 0.266835, 0.577341 and 1.179361.
  - **AUC against the saved reference:** 385 cycles above, 159 below, 2 within the logs' rounding. For
    batchgeneratorsv2: 25 above and 1 below on AUC, all 26 above on F1, and 23 above and 3 below on AP lift.
  - **Mean differences for batchgeneratorsv2:** +0.015479 AUC and +0.005265 F1.
- **#251's script.**
  - **Regeneration:** the record regenerates byte for byte here from the tracked `best_model.pt`, because it does
    no BLAS arithmetic.
  - **Loading:** the checkpoint loads with `weights_only=True` and a scoped allowlist, so no model is built.
  - **Refusals:** it refuses window cycles, another incumbent, and an output that would replace an input.
  - **Rounding:** the half-widths of 0.00005 match the run log's four-decimal AUC and AP lift.
- **#251's plan update.** Its checkable claims hold: 25 of 26 batchgeneratorsv2 cycles above the saved AUC, and
  16:00 PDT is 23:00 UTC. The Villa-side claims (`39a8cf3a`, #2316) are outside this session's scope.

## Observations for the owner (not changed)

- **`window_adjustment` has no command line.** The report says it reports at the readout, but `main()` takes only
  `--record`. The readout will have to call it from Python on the confirmation's output and #250's record.
- **The timezone fix assumes the loop's clock does not change inside a record.** That holds for #250's record,
  which ends on 2026-10-25. A record that spans 2026-11-01, when PDT ends, would need the loop's zone to turn
  wall-clock starts into elapsed hours.

## Verification

- **#250's and #251's test files** give 21 passed. Against #250's script, the new timezone test fails.
- **The guard set**, with both test files: to be filled in from the run.
- **Ruff** 0.9.10 `check` and `format` are clean on the four changed Python files. So is **mypy**, with the
  pre-commit hook's flags, over the whole repository.
- **No independent review this round.** The changes are one line of arithmetic, a test, and lint and type fixes.
