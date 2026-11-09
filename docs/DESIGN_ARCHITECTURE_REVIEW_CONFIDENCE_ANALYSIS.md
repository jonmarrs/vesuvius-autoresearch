# Confidence analysis: design and architecture review

Reviewed the registered confidence/reproducibility instrument, initially on
`e92cfb00`, then updated to main `79de90881360c217bac0993fe5d87b15e6150fb8`.
The changes repair measurement/reporting code; no original study artifacts were
available for a real-data re-analysis.

## Findings and repairs

- **Duplicate arms produced a positive verdict with no comparisons (P1).** A
  three-element list containing the same tag collapsed to one dictionary entry,
  exited the binning loop, then passed `len(significant) == len(results)` with
  both zero. The regression printed CONFIDENCE PREDICTS REPRODUCIBILITY without
  a single row. The CLI now requires exactly three distinct names and resolved
  directories, and the decision function requires all registered binnings.
- **Underpowered samples crashed or returned NaN (P2).** Sparse cohorts returned
  NaN and omitted fields used by the console formatter. They now produce finite
  JSON with null statistics, INDETERMINATE status/reason and exit 1. Missing or
  invalid inputs fail before replacing a report.
- **The declared re-score gate was unused (P1).** `INK_TOLERANCE` was defined but
  never applied. Version 2 validates original and re-scored single-strip metrics,
  paired mask pixel counts and the registered foreground-count tolerance. Reports
  retain the per-arm gate and hashes of the captured metrics used to apply it.
  The historical report's manually recorded comparison remains a separate record.
- **Background probabilities contaminated ink confidence (P2).** The old loader
  averaged every pixel in a 10×10 cell, then multiplied by the cell's ink count.
  The new reduction sums probabilities only at saved re-score ink pixels. It
  uses global strip column indices so tile/block boundaries cannot lose cells.
  A synthetic comparison explicitly differs from the old approximation.
- **Decision and p-value reporting overstated the evidence (P2).** Negative
  significance at one binning bypassed the all-three validity rule, and Monte
  Carlo p-values could be zero. Both effect directions now require all three
  binnings; partial/mixed support is BIN-DEPENDENT. Plus-one shuffle p-values
  replace zero estimates. Verdict text reports association without claiming that
  thresholding helps or ink is correct, and lack of detection is not called proof
  of no effect.
- **JSON output could replace inputs or truncate a prior report (P2).** Reports
  now reserve their destination against arm directories and declared files,
  including inode aliases, recheck before publication and use the shared atomic
  JSON writer with existing permissions retained. Observed source file states
  are checked before publication to reject ordinary concurrent changes.

The two initial regressions failed before repair (2 failed in 0.28s). No
historical numeric JSON was rewritten. The original registration is preserved
with a dated implementation-correction note, and the historical bin-level result
is explicitly marked as needing re-analysis before use as version-2 evidence.
The separate thresholding/matched-density follow-ups are not reclassified.

## Architecture and user workflow

`scripts/confidence_inputs.py` handles paired artifacts, exact reductions, count
gates and observed source states. The analysis script owns volume binning,
shuffle statistics, decision rules and CLI publication. Each arm is loaded once
for reuse across three binnings. Reports identify analysis version 2, statistic
kind, p-value method, input observations, gates, statuses and untested claims.
The original confidence tests and coordinate-helper tests now join the curated
suite, alongside the new analysis contracts. See
[the CLI and method guide](CONFIDENCE_REPRODUCIBILITY.md).

The required document checks exposed two unrelated pre-existing citations to a
local detector checkpoint not distributed in the repository. The two reports
now explicitly identify that path as historical; the reference audit adds exact
document/path exceptions, following its existing policy rather than increasing
a count allowance. Their measurement numbers are unchanged.

## Verification and limits

Python 3.10.21, NumPy 2.2.6, Torch 2.9.1+cpu, Villa pinned at
`ccb431818fa68059138f2c964ae299fc474ff116`.

- Affected curated selection after updating main: **108 passed in 26.50s**,
  across 7/195 modules. It covers the confidence decision/CLI, exact tiled
  reduction, count-gate boundaries, invalid/ambiguous inputs, source mutation,
  output aliases, atomic failures/modes, snapshots and test registration.
- Repository-wide Mypy passed **936 source files** against the review interpreter's
  installed dependencies. Ruff lint/format passed all six changed Python files.
- Document/claim guards: **138 passed, 1 skipped in 31.75s** after labeling the
  historical checkpoint citations. The live spiral corpus was unavailable.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 8.2s**. Local training
  data and an optional transform were unavailable; available imports/models and
  augmentations passed, including 288/288 checkpoint tensors. Exact commands
  and captured output are in the PR.

Tests use small synthetic artifacts and real NPY/PNG/TIFF/JSON I/O. No full
curated suite, original confidence-study re-run, full-strip memory/runtime
benchmark, CUDA workload or new scientific finding was produced. Large input
file states are observations, not cryptographic identities or an immutable
cross-file snapshot; inputs must stay stable and writers serialized. Header,
grid and block bounds are not RSS guarantees. The registered bin-label shuffle
does not by itself validate spatial exchangeability, independent seeds or
generalization beyond this ROI. Corrected code does not establish the historical
result under the corrected method.
