# Design and architecture review: recorded experiment reporting

Reviewed baseline `1c2fa567` after the merged candidate ink/fiber report review.
This pass covers `scripts/plot_results.py`, `scripts/generate_daily_report.py`,
and the daily-report test: metric interpretation, source selection, chart/PDF
consistency, notebook design, input validation, provenance, and publication.

## What changed

Publish descriptive experiment charts and PDFs from bounded, captured inputs,
with exact source copies, verified provenance, immutable destinations, and an
isolated daily-report test.

## Why

The old reports ranked auxiliary loss as discoveries, mislabeled training rate
as inference throughput, combined unrelated cached charts and notebook content,
overwrote outputs, and included a test that overwrote/deleted workspace sources.

## Findings and repairs

| Priority | Verified problem | Repair |
|---|---|---|
| P1 | The daily-report test writes root `results.tsv` and notebook files, then deletes them regardless of whether they existed beforehand. | Replace setup/teardown with temporary-directory inputs and assert source preservation; include the safe test in standard validation. |
| P1 | Charts call loss a scientific optimization trajectory and hardware scatter a Pareto frontier; the PDF ranks discoveries by lowest loss. Training promotes threshold-swept F1 gated by AP lift, absent from the frozen TSV. | Label auxiliary recorded diagnostics, use unconnected observations, explicitly state comparability limits, and list recent rows chronologically. Keep training/evaluation and TSV schemas unchanged. |
| P1 | PDF reads the current TSV but embeds previously generated hardcoded charts and a lexicographically selected training image without checking their sources. | Render fresh charts from the same captured rows as the PDF; retire implicit legacy chart/sample consumption and preserve exact source bytes and hashes. |
| P1 | Charts write independently into fixed paths, and every same-day PDF overwrites the previous report. Failures leave partial output. | Stage and verify all outputs in one new source-disjoint directory, check source stability, and reuse the immutable directory publisher. |
| P2 | Notebook lookup uses the wrong root path and first section; actual dated sections are not reliably chronological. Unicode text fails with core Latin-1 fonts. | Read the actual docs path, select the greatest dated section, bound and label its intent/commentary excerpt, use bundled DejaVu fonts, and reject unsupported glyphs explicitly. |
| P2 | Missing TSV prints success; column widths, required numeric values, timestamp semantics, and input budgets are unchecked. Log loss/color scales break for a legitimate zero loss. | Fail clearly on invalid/empty/oversized inputs, require finite ranges and consistent clocks, retain source row identity, and use linear loss/color scales. |
| P2 | The throughput chart says inference throughput, although the writer computes training voxel-rate from steps and training duration; pyplot/seaborn change global plotting state. Ambient tight-crop settings can also change verified chart geometry. | Label the recorded training-rate proxy and render with independent headless figures and explicit canvas bounds without changing global style or managed figures. |

Initial regressions:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_experiment_report_contracts.py -q --no-header --tb=short
```

Captured: **6 failed, 9 warnings in 8.20s**. The failures reproduced missing-input
false success, the notebook path/selection defect, loss-ranked discoveries,
unsupported Unicode, scientific frontier wording, and same-day overwrite.
Tests ran in temporary working directories, so the original unsafe test was
never run against workspace sources.

An additional ambient-style regression was run before fixing explicit bounds:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_experiment_report_contracts.py -k rendering_preserves_global -q --no-header --tb=short
```

Captured: **1 failed, 1 passed, 76 deselected in 3.43s**. The tight-crop setting
changed PNG dimensions; explicit figure bounds now preserve the complete canvas
while leaving the caller's global setting unchanged.

## Architecture decisions

Keep input capture/validation in `scripts/experiment_report_data.py`; use one
chart renderer for standalone charts and PDFs. Each snapshot retains exact
bytes, a bounded read budget, a resolved path, and a source-stability check.
Parsed rows are immutable; timestamp sorting is stable and original timestamp
strings/TSV lines remain available. Extra TSV columns remain in the source copy
without being reinterpreted. No metric or schema migration is attempted.

Reuse the existing new-directory publisher and finite JSON writer. Source copies,
charts, PDF, and manifest are staged and verified together. The PDF consumes no
cached chart bundle and invokes no training/data producer. Each chart occupies
its own page so automatic page breaks cannot orphan chart headings. Intentional
CLI/output migration and operator limits are documented in
[Recorded experiment reports](EXPERIMENT_REPORTS.md).

## Verification

Focused regressions:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_experiment_report_contracts.py tests/test_daily_report.py -q --no-header --tb=short
```

Captured: **79 passed in 59.24s**. Input, metric/date, source copy/hash, Unicode,
recent-row selection, legacy-asset exclusion, outside-checkout CLI, failure
rollback, and global style/canvas contracts pass. Real PNG/SVG/PDF generation
and optional PDF text extraction ran successfully.

PDF design inspection:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/generate_daily_report.py --results /tmp/vesuvius-experiment-report-review/results.tsv --notebook docs/LAB_NOTEBOOK.md --out /tmp/vesuvius-experiment-report-review/bundle
pdfinfo /tmp/vesuvius-experiment-report-review/bundle/report.pdf
pdftotext /tmp/vesuvius-experiment-report-review/bundle/report.pdf /tmp/vesuvius-experiment-report-review/report.txt
pdftoppm -f 1 -l 1 -scale-to 1200 -png -singlefile /tmp/vesuvius-experiment-report-review/bundle/report.pdf /tmp/vesuvius-experiment-report-review/page1
pdftoppm -f 2 -l 2 -scale-to 1200 -png -singlefile /tmp/vesuvius-experiment-report-review/bundle/report.pdf /tmp/vesuvius-experiment-report-review/page2
pdftoppm -f 3 -l 3 -scale-to 1200 -png -singlefile /tmp/vesuvius-experiment-report-review/bundle/report.pdf /tmp/vesuvius-experiment-report-review/page3
pdftoppm -f 4 -l 4 -scale-to 1200 -png -singlefile /tmp/vesuvius-experiment-report-review/bundle/report.pdf /tmp/vesuvius-experiment-report-review/page4
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/generate_daily_report.py --results /tmp/vesuvius-experiment-report-review/results.tsv --notebook docs/LAB_NOTEBOOK.md --out /tmp/vesuvius-experiment-report-review/final-bundle
pdfinfo /tmp/vesuvius-experiment-report-review/final-bundle/report.pdf
```

Captured: both report commands published successfully; **4 A4 pages**, PDF 1.3,
with correct title/scope metadata. All four rasterized pages were visually
inspected. Seven synthetic rows exercise changed regimes, zero loss/rate, and
chronological selection; the real notebook selects **2026-08-07**, labels intent,
renders its punctuation, and explicitly truncates the excerpt. Table and chart
labels remain legible without clipping. The final bundle's seven artifact
hashes/sizes were checked, and both final PNGs are byte-identical to the visually
inspected PNGs. This is rendering evidence, not new experimental evidence.

Standard validation:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
```

Captured: **1340 passed, 3 skipped, 1 xfailed, 9 warnings in 170.53s (0:02:50)**.
All standard workflow checks, including the 79 report regressions, pass. Existing
optional checks and the upstream expected failure retain their conditions;
warnings concern data-loader pinning on CPU. The first standard run also passed
1339 tests before the additional ambient-style regression; the suite was rerun
after that fix to cover the final code.

Required smoke:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
```

Captured: **8/11 passed, 3 skipped, 0 failed in 10.0s**. Imports, architectures,
auxiliary heads, actual best-checkpoint loading (288/288 compatible tensors),
augmentations, and bandit templates pass. Two absent local-data fixtures and the
unavailable optional `batchgeneratorsv2` transform account for skips.

Documentation, claims, filing-number, and upstream-parity guards:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_filing_2026_10_numbers.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_soft_count_report_numbers.py -q --no-header --tb=short
```

Captured: **106 passed, 16 skipped in 25.09s**. Available guards pass; skips need
a missing sibling ScrollGT checkout or external render artifacts. Historical
experiments and reports were not rerun or regenerated.

Final reference/claim check after completing this report:

```bash
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
```

Captured: **16 passed in 4.42s**. The completed documentation's reference and
claim checks pass.

Typing:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
```

Captured: **Found 16 errors in 13 files (checked 627 source files)**. This remains
a failing repository check: missing YAML/requests stubs, OpenCV overloads,
augmentation slice types, loader tensor-list annotations, and training
tensor-list mean/variance calls. None are in changed files. A new constructor
typing diagnostic was fixed before the final check.

Lint, format, and whitespace:

```bash
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/experiment_report_data.py scripts/plot_results.py scripts/generate_daily_report.py tests/test_experiment_report_contracts.py tests/test_daily_report.py scripts/run_validation_tests.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/experiment_report_data.py scripts/plot_results.py scripts/generate_daily_report.py tests/test_experiment_report_contracts.py tests/test_daily_report.py scripts/run_validation_tests.py
git diff --check
```

Captured: **All checks passed!**, **6 files already formatted**, and no whitespace
diagnostics. Cached typing/lint tools ran offline; no dependency changes.

## Edge cases considered

Empty/malformed UTF-8/TSV; duplicate/empty/missing headers and wrong row widths;
unchanged configuration-last schema; bounded bytes/row counts; nonnumeric,
nonfinite, negative, zero, and out-of-range metrics; invalid dates and mixed
qualified/unqualified timestamps; normalization, source precision, tied rows;
unsorted/tied/undated/invalid notebook headings, explicit omission and truncation;
Greek/punctuation Unicode and unsupported glyphs; corrupt legacy images;
exact source/output hashes and source copies; existing files/directories,
source ancestors/aliases, valid/broken symlinks; second render/PDF/manifest
failures, source changes and appearing destinations; outside-checkout CLI
execution; global figure/style preservation; and same-day prior reports.

## What was NOT tested

GPU/training execution, full scrolls, historical experiment recomputation,
scientific metric quality, physical data registration, cross-regime
comparability, F1/AP promotion reconstruction, held-out lineage, or prize
eligibility. PDF visual inspection uses synthetic metrics with the real notebook,
not new experimental evidence. Optional PDF text assertions need `pdftotext`;
core rendering/provenance tests do not. Publication assumes serialized writers
and stable source paths; live-appending logs require an explicit stable copy.
Training/evaluation harnesses, historical reports, dependencies, and upstream
code are unchanged. Repository typing remains subject to its existing failures.

## Reviewer focus

Check the diagnostic scope and retirement of rankings, exact input snapshot
consistency across PDF/charts, timestamp/date selection rules, frozen-schema
compatibility, source-preserving tests, and complete immutable publication.
