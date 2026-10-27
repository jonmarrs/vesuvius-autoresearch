# Design and architecture review — the owner's #250 (steps and ranking within a tweak)

Date: 2026-10-27. Baseline: `0221cbfe` (main after the owner's #250).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 03:12 UTC firing. The 22:14–02:12 firings found main unmoved after #249.

#250 regresses each measure's deviation from its tweak × epoch mean on the steps' deviation, over the 546 cycles
before the batchgeneratorsv2 window (`scripts/loop_steps_vs_ranking.py`, `reports/loop_steps_vs_ranking_2026-10-26.md`).
Within a tweak, cycles that train fewer steps score a higher ROC AUC and AP lift and the same val_f1. About a fifth of
batchgeneratorsv2's AUC gain is the size of its step deficit.

## What changed

- **The record's regeneration test failed on this machine.**
  - `test_the_record_regenerates_from_its_source` compared the regenerated JSON's bytes with the committed record.
  - Here 13 numbers differ in their last digits: slopes, intervals and the time-adjusted slopes. No reported
    figure changes.
  - The cause is OpenBLAS: it picks a dot-product kernel for the CPU, and the kernels sum in different orders.
  - With `OPENBLAS_CORETYPE=Haswell` or `Zen`, the script gives the committed record byte for byte. `SkylakeX`,
    the AVX-512 kernel, changes the same 13 numbers. The record is right; the test held it to one CPU family.
  - The test now compares the structure exactly and the floats to 1e-9. It still fails on a time-adjusted slope
    changed by one part in a million, a bin count off by one, or a permutation p off by 1e-4.
- **The time-adjusted slope depended on the runner's timezone.**
  - `deviations()` turned each start into hours with `datetime.timestamp()`. The starts are naive, so that reads
    them in the zone of the machine running the script.
  - UTC and America/Los_Angeles agree. A runner in Europe/London, whose clocks went back on 2026-10-25 inside the
    record, got different within-group hours. All three `with_hours` slopes then moved: val_f1 −0.0000468 →
    −0.0000463, for example. The rounded report figures did not change.
  - The hours are now the loop's wall clock read as such: the start minus 1970-01-01, the same on every machine.
    The loop's own clock (PDT) does not change inside the record, so wall-clock differences are elapsed time.
  - With the Haswell kernel, the fixed script gives the committed record's bytes in UTC, America/Los_Angeles and
    Europe/London.
  - A new test reads the record's deviations under UTC and under London's rules, given as a POSIX TZ string so no
    tz database is needed. It requires the hours to be equal, and fails against #250's script.

## Verified, no change needed

- **The report's tables and figures** are bound to the record by the owner's tests. The rest hold against the
  source record:
  - batchgeneratorsv2 averages 962 steps, against 1,261 for the other tweaks of the same step cost;
  - UAMT off averages 4,155 steps, 2,934 more than its epochs' other cycles;
  - batch 16 averages 627 steps, 634 fewer than the same-cost tweaks.
- **The learning rate follows the elapsed share of the time budget**, as the report says. `budget_lr_factor`
  takes `total_training_time / config.time_budget`.
- **The slope's degrees of freedom** are cycles − groups − 1, right for a within-group regression through the
  origin. The permutation shuffles the steps within each group, which leaves `x @ x` unchanged.
- **The bins hold all 454 deviations** (24 + 42 + 320 + 62 + 6).
- **`window_adjustment`** cuts the confirmation's rows at the 8th standing cycle, as its verdict does, and uses only
  the slopes fixed in the record (the owner's test).

## Observations for the owner (not changed)

- **`window_adjustment` has no command line.** The report says it reports at the readout, but `main()` takes only
  `--record`, so the readout will have to call it from Python on the confirmation's output and this record.
- **The fix assumes the loop's clock does not change inside a record.** That holds for this record, which ends
  2026-10-25. A record spanning 2026-11-01, when PDT ends, would need the loop's zone to turn wall-clock starts into
  elapsed hours.

## Verification

- **The test file** gives 10 passed. Against #250's script, the new timezone test fails.
- **The guard set**, with the steps-vs-ranking tests: to be filled in from the run.
- **Ruff** 0.9.10 `check` and `format`, and **mypy** with the pre-commit hook's flags, are clean on both files.
- **No independent review this round.** The change is one line of arithmetic and two tests.
