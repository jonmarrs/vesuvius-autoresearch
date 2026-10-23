# Design and architecture review — the tests outside the standard suite, after #196 to #210

Date: 2026-10-23. Baseline: `28193e17` (main after #210).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:13 UTC firing. Main has not moved since #210. The owner's #206 and #207 are
open and unmerged, so they are not reviewed here.

## Why this check

Since round 92 last ran all of `tests/`, the owner and this series have merged a run of PRs. The
standard suite (`scripts/run_validation_tests.py`) ran on every one, but it lists only the tests of
the loop's code. Each round that added a test outside it (round 106's plane-spacing harness, round
108's retry probe and fiber record, round 111's survey) ran only its own files. A merge could have
broken one of the other 200 without anyone running it.

## What was found

- **Nothing new.** The 212 test files outside the standard suite give 1,819 passed, 76 skipped,
  9 failed and 19 errors, run with the locked-package overlay.
  - Every one of the 28 failures and errors was already failing in round 92's run of all of
    `tests/`.
  - **26** need villa's spiral-fitting modules, which this container does not have: the
    `test_probe_*` family, 21 files.
  - **2** are `test_preflight_accepts_a_submodule.py`, which needs a villa submodule checkout.
- **No change is made.** There is nothing a merge broke to fix.

## Verification

- `comm -23` of this run's failure list against round 92's is empty.
- **The standard suite** on the same main, from round 112: 2813 passed, 22 skipped and 1 xfailed, with
  main's ten environmental failures.
