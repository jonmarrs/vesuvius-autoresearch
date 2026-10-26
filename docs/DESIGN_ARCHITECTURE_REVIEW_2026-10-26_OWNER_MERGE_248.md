# Design and architecture review — the owner's #248 (the window test on the confirmation's own output)

Date: 2026-10-26. Baseline: `9cc6a26e` (main after the owner's #248).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 21:15 UTC firing. The 19:12 and 20:13 firings found main unmoved after #247.

#248 adds one test to `tests/test_loop_replicate_rule.py`. It writes a window's sprint log and run logs in the loop's
own formats, runs the registered confirmation's command on them, then runs `--window` on that output. Before, the
window test was tested only on confirmation outputs built by hand.

## What changed

Nothing. This record is the review.

## Verified, no change needed

- **The test runs the registered command.** Amendment 1 of `docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md`
  runs `scripts/loop_tweak_replication.py --registered --since 2026-10-25T16:00:00`. It passes the sprint logs as
  the glob `sprint_log_2026-10-2*.md`, and the run logs as `run.log.old run.log`. The test passes the same arguments,
  with the runs split across the two run logs as a rotation leaves them.
- **Its two cases are what they say.**
  - With 10 standing cycles, the window is cut at the 8th, the shift's 75th cycle. Before the cut it holds 66 other
    cycles, above the 60 required. The confirmation reads `CONFIRMED`, and the rule takes the standing tweak.
  - With 5 standing cycles, the confirmation gives `INCOMPLETE`, and the window test gives no reading and no
    promotion.
  - The shift starts at 15:45, so its first cycle starts before the window and is left out. The window's first
    cycle starts at 16:00:00, as the test asserts.
- **It catches a mismatch that no other test does.** Two edits to `scripts/loop_tweak_replication.py` were made and
  undone, with git restoring the registered script each time:
  - The verdict's reading written under another key fails this test and five of the confirmation's own tests.
  - The rows' start written as `2026-10-25 16:00:00`, with a space for the `T`, fails only this test, in both cases.
    The window test then refuses the output as starting before the window. The confirmation's tests do not pin the
    format.
- **Ruff** 0.9.10 `check` and `format`, and **mypy** with the pre-commit hook's flags, are clean on the test file.

## Verification

- **The replicate-rule and confirmation tests** give 48 passed.
- **The guard set**, with the replicate-rule, lifecycle and measurement tests, gives 576 passed and 6 skipped. The
  one failure is the standing `test_live_documents_stay_clean`, whose list is the same as on main.
- **No independent review this round.** #248 is one test.
