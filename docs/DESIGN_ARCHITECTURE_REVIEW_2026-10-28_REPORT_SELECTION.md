# Experiment report design and architecture review — 2026-10-28

## Scope and evidence

Reviewed the captured-input reader, chart renderer, PDF generator, publication
helper, existing report contracts, and reporting guide against the tree of
remote main `ce8718ac2dfe0b973cb694c04815581078b74807` (PR #274).
The concrete changes concern report integrity and usability. This review does
not certify the entire research system or its scientific results.

Only synthetic experiment tables and a synthetic notebook were used. No live
study journals, result values, training processes, or GPU experiments were used.

## Finding: chart ticks depended on an unrelated global timezone

The input reader already normalized offset-qualified timestamps to UTC and
preserved unqualified timestamps as wall-clock labels with an unknown timezone.
The date locator and formatter nevertheless inherited Matplotlib's global
timezone. With `timezone=America/Los_Angeles`, the baseline renderer displayed
`05:00`, `05:30` for captured `12:00`, `12:30`, for both timestamp kinds. Its
axis still declared UTC or recorded local wall time. The displayed evidence and
its interpretation disagreed.

The chart now explicitly formats date coordinates in UTC. For unqualified
timestamps, this is a display convention that preserves the supplied clock
labels; the report continues to state that their timezone was not recorded.
The renderer does not mutate global Matplotlib settings. Regression tests
exercise the actual renderer inside a non-UTC global configuration.

## Feature: inspect recent appended records with an explicit selection

Both report commands and Python entry points now accept `--last-rows N` /
`last_rows=N`. The default remains the full table. A positive integer selects
up to N records from the end of the source. Selection occurs before timestamp
sorting, so a clock rollback or an out-of-order label does not select an older
append in preference to a newer one. It counts parsed TSV records, including
records with quoted multiline fields, rather than physical text lines.

Charts display the selection count. The PDF displays the source and selected
counts and tabulates at most five selected records by descending timestamp
label. No metric ranking, shift boundary, or scientific regime is inferred.
The guide describes this distinction explicitly.

## Architecture decisions

- Keep one captured `Results` object shared by chart and PDF generation. Apply
  selection in the reader after full-source validation, rather than implement
  a separate reader or filter in each output format.
- Retain byte and row budgets and validate every source record before selection.
  A small view cannot hide invalid earlier data or bypass input limits.
- Preserve the full source bytes, full-source SHA-256, raw timestamp labels, and
  physical source line identities. Changes outside the selection still abort
  publication through the existing source verification.
- Bump `report.json` to schema version 2. `source_row_count` counts the capture;
  `row_count` counts selected records. `selection` records the requested count,
  policy, and source line numbers. PNG/SVG metadata carries the same selection.
- Retain staged publication into a new directory, source/output separation,
  artifact hashes, and rollback on failures. This remains a stable-copy report
  API; it is not a concurrent live-log reader.

## Verification

Commands run from `/workspace/vesuvius-report-review` using the existing cached
environment; no dependencies were installed or credentials changed.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/vesuvius-report-mpl /tmp/vesuvius-review-env/bin/python -m pytest -q tests/test_report_time_and_selection.py tests/test_experiment_report_contracts.py tests/test_daily_report.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' /tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
/tmp/vesuvius-pr256-lint/bin/ruff check scripts/experiment_report_data.py scripts/plot_results.py scripts/generate_daily_report.py scripts/run_validation_tests.py tests/test_report_time_and_selection.py
/tmp/vesuvius-pr256-lint/bin/ruff format --check scripts/experiment_report_data.py scripts/plot_results.py scripts/generate_daily_report.py scripts/run_validation_tests.py tests/test_report_time_and_selection.py
PYTHONPATH=/tmp/vesuvius-pr256-types python3 -m mypy --follow-imports=skip --explicit-package-bases --namespace-packages --cache-dir /tmp/vesuvius-report-mypy scripts/experiment_report_data.py scripts/plot_results.py scripts/generate_daily_report.py scripts/run_validation_tests.py tests/test_report_time_and_selection.py
```

The focused report suite reported **106 passed** in 64.72 seconds. The smoke
test reported **8 passed, 3 skipped, 0 failed**. Skips concern two
data-loader checks without local training data and the optional bg2 augmentation
entry point. Fontconfig reported unwritable cache warnings, without test failures.
Ruff passed and found five files already formatted. Targeted mypy passed for five
files with imported implementations skipped; this is not a whole-project type check.

Synthetic integration checks cover source-order selection, offset ties, unknown
timezones, multiline records, oversized requests, invalid counts, full-input
validation and budgets, changes outside the selection, CLI invocation outside
the checkout, artifact hashes, and matching PDF/chart/manifest metadata. The new
test module is registered in the lightweight validation runner.

Visually inspected the first PDF page and both PNG charts from an eight-record
synthetic table selecting five records. The PDF with synthetic notebook has four
A4 pages; the first-page table and explanatory text fit, and selection banners
and clock labels are visible on the charts.

## Limits and follow-up

The frozen TSV still lacks promotion F1/AP fields and evaluation-regime identity;
recent-row selection cannot reconstruct these. Training, native GPU performance,
scientific eligibility, and live research deployment were not tested. Future
scientific comparisons need a separately designed metric/provenance migration.
Consumers that require `report.json` schema version 1 must explicitly support
version 2 before ingesting newly generated bundles. Historical bundles are not
rewritten.
