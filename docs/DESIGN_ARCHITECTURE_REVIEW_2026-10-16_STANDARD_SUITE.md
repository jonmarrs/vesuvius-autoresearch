# Design and architecture review — what the standard suite runs

Date: 2026-10-16. Baseline: `8e2d4b9a` (main after #89). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the test suite that the owner's and these reviews' validation runs use, `scripts/run_validation_tests.py`'s
  `VALIDATION_TESTS`;
- the 213 of 285 test modules outside it, and why they fail where they fail.

## What changed

- **The standard suite runs every test of the loop's code.**
  - 28 test modules that import `train.py`, the loop, `loop_control`, the inference scripts, the core library or the
    evidence chain were outside `VALIDATION_TESTS`. They had been added after the list was last kept by hand.
  - Among them are the tests of the promotion criterion (`test_improvement_criterion`,
    `test_f1_improvement_criterion`), the prize gates (`test_prize_promotion_gates`), the Frangi target and its torch
    filter, the loader workers, the topology threshold, the scroll augmentations, and the evidence chain's reports.
  - So a change to any of these, validated against the list, was never tested. All 28 pass here; one skips for its
    checkpoint. Together they add about two minutes, most of it `test_loader_workers` (40 s).
- **A guard keeps it so.** `tests/test_validation_suite_covers_the_loop.py`, itself in the list:
  - reads each test module's imports;
  - fails, naming the modules, when one that imports the loop's code is not listed;
  - fails when the list names a missing file, or a module twice.

  A third test checks the guard against the ways the tests import that code (`import train`,
  `from scripts.training.train import …`, `from vesuvius_autoresearch.core… import …`, and so on).
- **`evaluate_villa_metrics.py` stops when villa's metrics do not import.**
  - It printed the error and went on, so it read both volumes and then failed on the first metric with a
    `NameError`.
  - It also found villa from the working directory, so run from elsewhere it took that path.
  - It now finds villa from its own checkout and exits with the import error.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **The standard suite left out 28 modules testing the loop's code**, among them the promotion criterion, the prize gates and the Frangi target. The list is kept by hand, and nothing checked it. | Listed, and guarded. The guard's first test fails on main, naming the 28. |
| P4 | `evaluate_villa_metrics.py` went on after a failed import, to a `NameError` after reading both volumes, and found villa from the working directory. | It exits on the import error, and finds villa from its checkout. Test (a shadowing `metrics` package that fails to import) fails on main. |

## The modules still outside the suite

They were run here (19 failed, 1384 passed, 76 skipped, 21 errors in 6 min 51 s). Every failure and error is
environmental:
- **villa's spiral-fitting modules are absent** (19, `test_spiral_*`, `test_tracer_*` and the like);
- **packages not installed here:** `s3fs` (5 errors), `wandb`, `cupy` (villa's metrics, so
  `test_evaluate_villa_metrics`'s first test);
- **missing data:**
  - `umbilicus.json` (4);
  - the LeJEPA checkpoint;
  - `test_probe_real_patch_scatter`'s patches;
  - `correlate_geometry_ink.py`'s data, which is under a host path (`/home/jon/…/spiral_out`);
- **villa as a directory, not a submodule:** `test_preflight_accepts_a_submodule`;
- **villa paths this checkout lacks:** `test_audit_doc_references`, the pre-commit guard.

The rest are research analyses and probes (`analyse_*`, `probe_*`, `audit_*`), the detector and fibers subsystems,
and the documentation guards that pre-commit runs on its own.

## Observations for the owner (not changed)

- **The guard is a floor.** It reads import statements only. A test that runs the loop's code as a subprocess, such
  as `test_villa_baselines_launchers` (the launchers the action matrix names), is not required, and is not added
  here. It fails twice here for the LeJEPA checkpoint and villa's GP-winner config.
- **`test_correlate_geometry_ink.py` runs its script on a host path** and fails where the data is absent, rather than
  skipping.
- **The validation runs these reviews record** describe the list as it stood. After this change their counts rise by
  the 28 modules' tests: "passed" here is not comparable with earlier reviews' figures.

## Reviewed and sound

- **Every module in the list exists, and none is listed twice** (now tested).
- **No module was outside the list because it fails.** The 28 all pass here, and the outside failures above are all
  environmental.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `e4032512` (#89), whose tree is `8e2d4b9a`'s but for its review doc's result
  lines. With the old list it was 42 failed, 2240 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors
  are environmental: no scroll data, no CUDA, no villa data files.
- Branch, with the enlarged list: 42 failed, 2371 passed, 19 skipped, 1 xfailed, 2 errors in 3 min 31 s (from
  2 min 37 s). The failures and errors are the same set as the baseline; the 131 extra passes and 4 extra skips are
  the 29 added modules' tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- The 28 modules, one by one: all pass (`test_load` skips: no LeJEPA checkpoint).
- The outside modules: 19 failed, 1384 passed, 76 skipped, 21 errors, all environmental (above).
- Ruff (check and format) on the changed files: clean.

New tests:
- `tests/test_validation_suite_covers_the_loop.py`:
  - `test_every_test_of_the_loops_code_is_in_the_standard_suite` (fails on main, naming the 28);
  - `test_the_standard_suite_names_only_existing_modules`;
  - `test_the_guard_sees_the_ways_tests_import_the_loops_code`.
- `tests/test_evaluate_villa_metrics.py`: `test_a_missing_villa_metric_stops_before_reading_the_volumes` (fails on
  main).

Not verified here: the enlarged suite on the GPU host.
