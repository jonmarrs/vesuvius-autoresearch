# Design and architecture review: Villa binary evaluation, October 30, 2026

Reviewed base: `114a3400a3b21d0cfe777d89c627cc776e12d041`.
Scope: the standalone paired-volume evaluator, its input/encoding contracts,
metric loading, resource controls and output publication. No training code,
checkpoint, live-study checkout, upstream metric formula or Villa pin changed.

## Reproduced findings

The baseline was run on newly created synthetic TIFF fixtures using the exact
metric sources at the repository's Villa pin,
`ccb431818fa68059138f2c964ae299fc474ff116`. The cached source bytes were checked
against their seven Git blob hashes. No real-model quality was measured.

- A `(3,4,5)` reference and `(2,4,5)` prediction were silently cropped to the
  smaller shape. The run completed instead of rejecting an invalid comparison.
- At threshold 0.8, Dice returned **1.0** while centerline Dice returned **0.0**
  for the same selected pair. Dice used the upstream default 0.5 on raw
  predictions while the other metrics used the requested threshold.
- Pointing `--out` at the prediction TIFF replaced that new fixture with JSON
  after evaluation. The production tool offered no output/source separation.
- Reference IDs were reduced to `gt > 0.5`, even when `--num_classes` requested
  multiclass evaluation. Thresholds, values, dimensions and materialization
  budgets were unchecked; a group could be converted incorrectly instead of
  selecting its explicit array `0`.
- Optional failures disappeared from a successful flat result, NaN could be
  written as JSON, imports could resolve an unrelated ambient `metrics` package,
  and import-time dependencies prevented independent help/planning.
- The pinned AP function can catch a backend exception and return zero after
  logging an error. That internal-error path now produces a failed metric,
  preserving the diagnostic instead of presenting zero as a measured score.

The destructive baseline reproduction touched only fresh test fixtures under
`/workspace/shared/villa-evaluation-baseline-2026-10-30/`. Its command/log and
observations remain there. Historical scorecards and research results were not
rewritten, and the reproduction's numbers are not a scientific result.

## Design and architecture

The command now performs **bounded binary evaluation**. Alignment and encoding
are explicit, full source shapes must agree, crops are exact, and all hard
metrics receive the same `>=` thresholded mask. Probability AP is the default;
legacy hard AP is an explicit option. Multiclass/ignore IDs fail rather than
being reinterpreted. The [usage guide](VILLA_BINARY_EVALUATION.md) documents the
deliberate output/flag migration and scientific limits.

`evaluation_artifacts.py` handles source headers, exact selections, binary and
probability encodings, bounded TIFF capture, semantic region hashes and source
rechecks. The CLI handles metric selection/adapters, statuses, rendering and
publication. Shared geometry, bounded source capture, private leaf-module import
and completed-directory publication helpers are reused.

Each run captures the exact selected upstream source files and the two local
adapter files. Modules load from fresh staged paths, preventing ambient imports,
stale source caches and skeleton-global reuse. Per-metric exceptions have an
explicit status, and nonfinite/empty results remain undefined. Inputs are copied
per metric to prevent cross-metric mutation. Only final published directories
constitute completed reports.

CPU is the default; optional CUDA requires an explicit device choice. Skeleton
evaluation is opt-in, disables module-local tracking, confines histograms to the
bundle and verifies their PNG contents/hashes. The pinned Kimimaro call's
all-CPU parallelism is capped to one worker through a module-local adapter,
without altering the shared package or source file. The setting is recorded.

The report includes readable Markdown and finite JSON with statuses, resource
and encoding settings, selected geometry, input/source hashes, runtime versions
and artifact hashes. Input/code/artifact changes and rendering failures abort
publication. Captures do not create a transactional snapshot across sources;
stable inputs and serialized writers remain necessary.

## Validation and limits

Final selected integration command:

```bash
VESUVIUS_EVAL_METRICS_ROOT=/workspace/shared/villa-evaluation-pin-ccb431818 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python -m pytest -q -rs \
  tests/test_evaluate_villa_metrics.py tests/test_villa_modules.py \
  tests/test_file_modes.py tests/test_validation_suite_covers_the_loop.py \
  tests/test_candidate_fiber_report_contracts.py
```

Captured result: **211 passed, 3 skipped in 87.06s**. The evaluator has 58 cases,
including three real pinned-source subprocess checks: Dice/centerline/components/AP
at thresholds 0.5 and 0.8, and skeleton distance with a verified PNG under the
one-worker adapter. The three skips are unrelated leaf-module tests: two require
the full Villa checkout, and one requires CUDA tensors. Actual metric sources
were supplied through the explicit verified source capture.

CPU smoke:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

Captured result: **8/11 passed, 3 skipped, 0 failed in 15.7s**. Skips were two
unavailable local training-data loaders and the unavailable batchgenerators-v2
augmentation entry point. Ruff check/format and Mypy pass for the four changed
Python files. Local Markdown links and whitespace checks pass; exact quality
commands are in the PR test report.

Adapter fixtures are explicitly separate from real-source tests. Exact-source
tests use `VESUVIUS_EVAL_METRICS_ROOT` pointing to a local capture with a source
manifest; they skip when it is not configured. The cached sources are public
Villa code, not substitute metric implementations. No dependencies or models
are downloaded by evaluation itself.

The full repository suite, native CUDA, real-model inference, registration,
annotation quality/coverage, held-out lineage, large-volume performance,
concurrent writers and power-loss durability were not tested. Scoring every
selected voxel does not establish that every reference zero is a known negative.
The pinned centerline formula and its known inflation routes remain unchanged.
Pixel/voxel/file budgets do not cap all third-party temporary allocations.
