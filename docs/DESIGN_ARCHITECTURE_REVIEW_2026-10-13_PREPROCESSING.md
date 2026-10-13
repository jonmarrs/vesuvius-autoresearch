# Design and architecture review — preprocessing and native module boundaries

Date: 2026-10-13. Baseline: `73c9283e1e9d37481bea57b6540785d5baaba1b9`.
Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.

Scope: the recently revised loop and checkpoint-analysis workflows, their
strict sample boundary, requested preprocessing and lazy native module loading.
The earlier October 12 reviews already cover sampling, learning-rate scheduling,
UA-MT alignment, measured topology metrics and pinned source selection.

## What changed

Require requested preprocessing to succeed for strict labeled-dataset samples,
retain successful GPU ridge results on the CT tensor's device, and serialize
initialization of each pinned leaf module across concurrent callers. Add
regression coverage to standard validation and update the operator guide to
describe the current re-evaluation protocol.

## Why

Strict reads still allowed failed transforms to become scored samples, including
an explicit incumbent score update. A valid GPU ridge result was discarded due
to an undefined device attribute. Concurrent callers could observe a module
before its exports were initialized.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | `strict_reads=True` only guarded the outer read. Lasagna, ridge and Frangi helpers swallowed their own exceptions and returned unwarped patches or zero features. The real validation collector then reported `complete=True`; the re-evaluation update path overwrote a temporary incumbent's scores despite an unavailable warp. | Propagate requested preprocessing failures in strict mode with patch/backend context. Existing collector and re-evaluation guards now mark the sample incomplete and refuse score publication. Permissive reads retain fallbacks. |
| P2 | `_compute_ridges` moved GPU results to `self.device`, but the dataset defines no such attribute. A synthetic successful GPU result was computed twice: the attribute error forced CPU recomputation. | Transfer both backend results to the actual CT tensor's device; keep a valid GPU result and permit a valid CPU fallback. Validate feature shape and finite values. |
| P2 | `load_villa_leaf` registered a module in `sys.modules` before execution, then treated any registration as a completed cache entry. A concurrent caller immediately received the unfinished module; it could also retain that object after initialization failed and it was removed from the cache. | Lock each resolved module's cache lookup, registration, execution and failure cleanup. Waiting callers receive the completed module or retry after a failed initializer. Different modules have independent locks. |
| P3 | The checkpoint operator guide still described re-evaluation as a legacy-only metric path and counted batches, although the current implementation computes F1/AP/AUC on protocol v2 patches. | Describe the current protocol, stored-score migration, all-ink baseline, strict preprocessing and the still-open host/metric choices. |

## Architecture and compatibility decisions

The measurement boundary is **read source → run requested transforms → validate
the transformed sample → score**. Strict mode must not represent missing inputs
as a successful alternative configuration. A successful CPU implementation of
the requested ridge transform remains valid; unavailable GPU hardware alone
does not invalidate a sample. Only failure of both implementations blocks it.

Strict requests also reject warp/ridge contexts thinner than three slices and
invalid transform outputs. Warps must preserve tensor shape, dtype and device
and contain finite values; ridge arrays and Frangi targets must have the expected
shape and finite values. Default permissive behavior still returns unwarped
patches or zero features, with bounded warnings for computation failures.
Permissive thin-context behavior remains unchanged.

The fix is in the shared dataset rather than a second guard in each CLI. The
loop collector already counts dataset exceptions as incomplete samples, and
`reevaluate_best_model.py` already refuses updates from incomplete samples. Both
are exercised through their real control flow. No scoring formula, validation
sample, selection threshold or model reconstruction rule changes.

Leaf modules must be registered before execution for Python decorators such as
`dataclass`. Removing registration until execution ends would solve only one
race and break that import behavior. A per-module reentrant lock follows the
usual import initialization pattern while retaining private names, source-path
cache identity, failure cleanup and the existing refusal of non-leaf imports.
The small registry lock is held only to obtain a module lock, so a slow CUDA
extension initializer does not serialize unrelated leaf files. This is an
in-process thread guarantee; no process/fork or native compiler guarantee is
claimed.

### Operator implications

A strict measurement with `use_lasagna: true` now fails if the requested backend
cannot run, rather than reporting a score on an unwarped input. Resolve that
configuration/backend before re-scoring or updating an incumbent. Training
reads remain permissive, but the loop's final validation is strict and cannot
promote a score from a failed requested preprocessing step.

[Finding 86](../reports/loop_v2_constant_control.md) remains the recorded
scientific observation and open host/metric decision. This review does not
install a toolkit, alter the production config, choose a new selection metric,
update stored checkpoint scores, calibrate noise or launch the loop. Historical
measurements, scientific JSON and preregistrations were not regenerated.

## Verification

Commands run from the repository root in the existing Python 3.10 environment,
with CPU thread counts bounded. Process inspection found no active training,
loop, fit or renderer. Tests use temporary data and checkpoints.

### Baseline reproductions

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_preprocessing_contracts.py tests/test_villa_modules.py::test_concurrent_callers_wait_for_module_initialization -q --no-header --tb=short | tee /tmp/preprocessing-review-baseline.log
```

```text
8 failed, 4 passed in 11.98s
```

Interpretation: the initial regressions independently reproduce all three
runtime defects, including `complete=True` after a failed warp and a temporary
incumbent overwritten by re-evaluation. Existing permissive behavior and
successful CPU fallback pass. GPU selection is tested with synthetic CuPy
results, not GPU kernels; concurrency uses a deliberately paused Python leaf.

### Affected workflows

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_preprocessing_contracts.py tests/test_villa_modules.py tests/test_checkpoint_tool_contracts.py tests/test_autoresearch_measurement.py tests/test_training_step_contracts.py tests/test_vesuvius_loader.py -q --no-header --tb=short | tee /tmp/preprocessing-review-focused.log
```

```text
116 passed, 3 skipped, 2 warnings in 14.79s
```

Interpretation: strict failure and successful paths, permissive compatibility,
re-evaluation protection, model tools, loop measurements, training-step contracts
and native import contracts pass. Three external local-data tests skip. Two
warnings concern pinned-memory requests with no available accelerator.

### Standard validation suite

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py | tee /tmp/preprocessing-review-standard.log
```

```text
1945 passed, 11 skipped, 1 xfailed, 2 warnings in 246.68s (0:04:06)
```

Interpretation: the complete standard suite passes, including the new
preprocessing tests and the downstream inspection, labeling, inference and loop
contracts. Environment-dependent comparisons/data paths skip, and the existing
Mutex runtime blocker remains an expected failure. Warnings concern pinned
memory without an accelerator.

### Smoke check

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/preprocessing-review-smoke.log
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 12.6s ---
```

Interpretation: available smoke paths pass, including complete loading of the
incumbent's weights. Production training data and optional augmentation imports
are unavailable and skip.

### Lint, formatting and whitespace

```sh
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff check src/vesuvius_autoresearch/core/vesuvius_loader.py src/vesuvius_autoresearch/core/villa_modules.py scripts/run_validation_tests.py tests/test_preprocessing_contracts.py tests/test_villa_modules.py
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff format --check src/vesuvius_autoresearch/core/vesuvius_loader.py src/vesuvius_autoresearch/core/villa_modules.py scripts/run_validation_tests.py tests/test_preprocessing_contracts.py tests/test_villa_modules.py
git diff --check
```

```text
All checks passed!
5 files already formatted
```

Interpretation: all changed Python files pass lint and formatting; whitespace
checks have no diagnostics.

### Typing comparison

Created a baseline Python-source snapshot from the original commit. Two
pre-existing ignored runner files were copied into it so the check covers the
same local source scope as the working tree:

```sh
mkdir -p /tmp/preprocessing-review-type-baseline
git archive --format=tar 73c9283e1e9d37481bea57b6540785d5baaba1b9 -- '*.py' pyproject.toml | tar -x -C /tmp/preprocessing-review-type-baseline
cp -- scripts/_finetune_lejepa_runner.py scripts/_gp_winner_runner.py /tmp/preprocessing-review-type-baseline/scripts/
```

Baseline command, run from `/tmp/preprocessing-review-type-baseline`:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable /workspace/vesuvius-autoresearch/.venv/bin/python | tee /tmp/preprocessing-review-baseline-mypy.log
```

```text
Found 16 errors in 13 files (checked 662 source files)
```

Final command, run from the repository root:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python | tee /tmp/preprocessing-review-final-mypy.log
```

```text
Found 15 errors in 13 files (checked 663 source files)
```

Interpretation: comparison of the diagnostic lines finds zero introduced errors
and one removed error, the optional ridge tensor in the repaired dataset method.
All remaining diagnostics already occur on the baseline: missing stubs, OpenCV
overloads, augmentation indices, training list/tensor operations and the optional
tensor in the separate `FastVesuviusVolume` method at line 202. Mypy still exits
nonzero; no unrelated typing repair or dependency installation was performed.

### Final documentation guards and regression recheck

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_arm_tiers.py tests/test_audit_arm_coverage.py tests/test_analyse_flat_displacement.py tests/test_quotations_match_source.py tests/test_analyse_pooled_fit_only_floor.py tests/test_analyse_ink_maximum_offset.py tests/test_preprocessing_contracts.py -q --no-header --tb=short | tee /tmp/preprocessing-review-doc-guards.log
```

```text
111 passed, 1 skipped in 33.56s
```

Interpretation: the required documentation guards pass, and preprocessing
regressions still pass after a type-only test annotation adjustment. An external
tool/version comparison skips. The standard suite was not repeated for this
annotation/documentation-only adjustment.

## Edge cases considered

- Unavailable warp, failure of both ridge backends and failed Frangi computation.
- Malformed/nonfinite outputs and too-thin warp/ridge contexts in strict mode.
- A valid GPU result, valid CPU fallback and preserved permissive fallbacks.
- Incomplete validation refusing an explicit stored-score update, plus a
  successfully transformed sample that remains complete.
- Concurrent callers waiting for success, retrying after initialization failure,
  and loading a different file while another initializer is paused.

## What was NOT tested

- Real CUDA kernels, Lasagna extension compilation or GPU/CPU numerical parity.
- Production CT/model re-evaluation, measured score changes or actual training.
- Whole-process speed or memory; the two-call regression is a control-flow
  assertion, not a measured production speedup.
- Forking during module initialization, multi-process imports, external mutation
  of `sys.modules`, or source files changing during initialization.
- The scientific metric and host-migration choices recorded in finding 86.

## Reviewer focus

Check that strict mode cannot substitute a different input configuration after
failed preprocessing, that a working CPU ridge fallback remains accepted, and
that native module registration is never mistaken for completed initialization
by another caller. Verify the operator-facing description of the current
protocol and the separation from historical measurements and host decisions.
