# Design and architecture review — detector evaluation inputs

Baseline: `20aa0d87`. Scope: evaluation/measurement data consumption, report input
protection and prediction coverage at the scoring boundary.

## Findings and fixes

1. **Scoring decoded the CT stack twice.** After inference, both evaluation and
   measurement called the supervised volume loader to obtain annotations. The
   new `read_ink_label` reads labels alone, checks original dimensions and is also
   used by the existing supervised loader. Tiny real-file tests observe one CT
   decode per layer instead of two. No real-fragment speed or memory benchmark
   was performed.
2. **The scoring mask could differ from the inference mask.** Re-reading the
   fragment mask after inference could change the scoring sample. Both commands
   now retain `InferenceResult` and score against its captured fragment mask.
   A test changes the on-disk mask after capture and verifies that the original
   sample is scored. This does not snapshot CT layers, labels or model weights.
3. **Reports could overwrite their own CLI configuration.** When a configuration
   occupied a report filename, evaluation and measurement replaced it. Their
   preflight previously protected only the checkpoint. Shared input inventory
   now covers the configuration, selected converted fragment trees, CT layers,
   masks and discovered ink-label files. `reproduce` also checks configuration
   and selected converted inputs before conversion or training. The publisher
   rechecks input paths before replacing reports.
4. **Coverage information stopped at inference.** Successful scorecards and
   measurement rows now include valid/predicted/uncovered pixel counts and a
   coverage fraction. Measurement Markdown displays the latter two counts.
   `eval` and `measure` accept `--require-full-coverage`; a strict measurement
   retains successful targets and records uncovered targets as failures.
5. **Previous target arrays survived into the next inference.** Final review
   reproduced retained probability/mask/label references during measurement's
   next target. A per-target scoring function now returns only the compact metric
   row, releasing those arrays before the next load. A weak-reference regression
   verifies the lifetime; it does not measure allocator or device-cache behavior.

Data loading owns annotation shape checks; inference owns tiling and coverage;
the shared scoring boundary validates optional coverage and computes summaries;
the existing report publisher owns path checks and publication/rollback. The
scientific metric formula, threshold grid, blending and default denominator are
unchanged. Default scoring still includes uncovered zero-filled pixels.

The array-level evaluation API remains usable without coverage metadata, and
training keeps its existing combined volume/label loader. Test doubles now use
the documented original-size `InferenceResult` rather than obsolete padded plain
arrays. No historical report or research result was rewritten.

## Verification

- Five initial regressions failed against the old code: evaluation and
  measurement each decoded a CT layer twice; both CLI commands overwrote their
  configuration; reproduction reached conversion before detecting that collision.
- The new module passes **30 cases** for decode counts, captured masks, coverage
  counts and types, unchanged metric denominators, strict failures, partial
  measurement, early/late input aliases, changed annotation dimensions and target
  array lifetime. The added lifetime regression failed before its fix.
- Curated selection: **401 passed, 1 skipped** across **14/181 modules**. This
  includes both architecture training fixtures, checkpoint compatibility,
  prediction/report artifacts, conversion, metrics and validation-runner guards.
  The skipped patch-origin check requires the absent local validation fragment.
- An earlier overlapping detector selection passed **219 tests**; counts are
  not additive. The focused new module passed all 29 initial cases independently
  before the final lifetime regression was added.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. Skips are two absent training
  inputs and the unavailable legacy augmentation entry point. Scoped Ruff,
  formatting, Mypy and whitespace checks pass on eleven Python files.

Validation used Python 3.10.21 and Torch 2.9.1+cpu. The PR test report records
exact commands and captured output. Data/model fixtures were temporary and
synthetic; no live study checkout or real-fragment experiment was run.

## Limits

Coverage counts are producer observations, not independently verified accuracy.
The report checker checks serialized report integrity; it cannot reconstruct
full-resolution coverage from a thumbnail or the counts. A complete report means
every requested target was scored, not that every valid pixel was predicted.
Missing coverage metadata remains unknown.

Input-path checks do not hash or snapshot datasets/configurations/checkpoints or
lock writers. Keep sources and paths stable. Python array-level callers must
supply filesystem inputs when they need source-path protection; arrays alone do
not reveal filenames. Existing publication concurrency/recovery limits remain.

The full repository suite, GPU execution, full-fragment performance, Windows and
remote filesystems were not tested. No new model-quality or prize-eligibility
claim follows from these workflow changes. See the
[coverage and input contract](DETECTOR_REPORTS.md#coverage-and-scoring-inputs).
