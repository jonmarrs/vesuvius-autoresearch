# Design and architecture review — fiber miss diagnostic

Date: 2026-10-12. Baseline: `060585b62d06538a66947423b0c9583a7f307449`.
Scope: the recently merged finding-84 diagnostic, its evidence gates, current
CLI workflow, result publication, CPU artifact dependencies, process-readiness
test synchronization, independent regression coverage and historical report
reproducibility.

## What changed

Validate the fiber diagnostic's inputs and decision evidence, require the full
registered sample for a verdict, make data and output paths explicit, and add
local regression coverage to standard validation. Separate streaming file hashes
from checkpoint reconstruction and wait for actual loop-lock readiness in the
process fixture.

## Why

The diagnostic could issue a conclusion from an incomplete sample or NaN inputs,
count a virtual boundary point as a detection in an empty mask, and call recovery
of one cube recovery of both. Its CLI depended on one workstation and could
overwrite the committed scientific report.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | The method and default full-run description require all 21 targets, but eight Scroll-5 rows sufficed for a verdict; omitted trusted controls were never checked. | Declare the 21-target inventory, require every row for a full verdict and preflight every target and probability before computing. |
| P2 | Split metadata controlled which rows were trusted controls; incorrect splits could hide a control failure. | Match each cube's split to the registered inventory. |
| P2 | Floating comparisons accepted NaN at a coverage gate, and NaN at a threshold could produce `THRESHOLD_RESCUES`. | Validate finite fraction types/ranges and component consistency before gate or decision comparisons; invalid evidence emits no conclusion. |
| P2 | An all-background SciPy EDT measures a virtual point outside the array; two near-origin samples scored 100% covered by an empty mask. | Use infinite distance when the actual mask has no foreground, yielding zero coverage. |
| P2 | Invalid probabilities, malformed sample coordinates/lengths and zero in-bounds length entered calculations. | Validate 3D arrays, finite probabilities in [0, 1], boolean aligned masks, integer sample indices and positive measured length. |
| P2 | Perfect coverage wrote NaN for a soft-miss fraction whose denominator was zero. | Represent the undefined quantity as JSON null; refuse a full conclusion if that comparison is required. |
| P2 | If only one new cube reached the reference minimum, the script labeled both as rescued. | Require both for `THRESHOLD_RESCUES`, otherwise classify the one-cube case as `THRESHOLD_PARTIAL`; preserve P2's rule. |
| P2 | Data roots were absolute paths on another workstation; a default output replaced the committed result. | Require explicit ScrollGT/cache roots and a new JSON output outside all sources; reuse the existing staged new-file publisher. |
| P2 | Failed instrument/control results returned success, and JSON allowed non-finite numbers. | Return nonzero for failed gates, serialize strict JSON, retain finite failed-gate reports for inspection and never publish incomplete reads. |
| P2 | A module-wide skip disabled even dependency-free verdict tests when ScrollGT was absent. | Limit that skip to four external comparisons; add independent calculation, gate, inventory, CLI and publication regressions to standard validation. |
| P2 | CPU candidate reports and mask preparation imported the checkpoint exporter solely for SHA-256, loading PyTorch transitively; the broader suite hit a candidate CLI timeout. | Move the unchanged streaming hash function to a standard-library helper, use it directly in CPU callers and preserve the exporter's existing hash API. A subprocess guard verifies report/mask preparation with Torch imports forbidden. |
| P2 | A loop-process fixture treated file creation as readiness, although open creates the file before the child owns and populates the lock. | Poll the actual registered PID with a bounded startup wait, allowing the transient empty-PID state and stopping immediately if the child exits. |

## Architecture and compatibility decisions

The current workflow is **explicit source selection → complete workload
preflight → validated per-cube instruments → gated verdict → strict staged
publication**. `--cubes` is an explicit descriptive mode, with instrument status
and no full-sample conclusion. Duplicate selections and ambiguous probability
caches fail before computation. A cached import from a different ScrollGT
checkout is rejected rather than pairing one checkout's code with another's data.

The probability file is memory-mapped; validation, threshold/mask equality and
density counting use slabs. The distance transform still allocates a full-volume
distance array, and sample/shift lookups require additional memory. This change
does not assert a whole-process memory bound or production speedup.

The shared publication helper already enforces separate new paths and staged
completion. Reusing it keeps this research CLI consistent with the repository's
other artifact workflows. Writers must be serialized and source data must stay
stable. Recorded input roots are declarations, not content hashes or snapshots.

`scripts/artifact_hashes.py` owns streaming SHA-256 without a model runtime.
The exporter re-exports the same function for existing callers. Candidate
reports and mask partitioning use the lightweight import; dataset inspection
also imports the shared helper but still legitimately uses Torch for real
sample validation. Hash bytes, block size, return format and error behavior
are preserved. No model/inference API changes.

No dependency, native Villa implementation, training/evaluation harness,
registered thresholds or measured JSON artifact changes. The historical report
now identifies the original execution at `93115122` and links the current
contracts. Applying the repaired verdict to the saved 21 rows reproduces the
saved result exactly; this is not a recomputation of the real volume instruments.
The stricter full-sample guard and partial-rescue label are current tool repairs,
not retroactive changes to the preregistration or its predictions.

See [Fiber mask miss diagnostic](FIBER_MISS_DIAGNOSTIC.md) for invocation,
input/output contracts, migration and interpretation limits.

## Verification

Commands run from the repository root in the existing environment. Process
inspection found no active training, loop, fit or renderer before validation.

### Baseline regressions

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_fiber_diagnostic_contracts.py -q --no-header --tb=short | tee /tmp/fiber-diagnostic-baseline.log
```

Captured output from the initial regression set, before the repair:

```text
11 failed, 5 passed, 1 warning in 1.39s
```

Interpretation: the incomplete sample, NaN gate/decision, empty mask, invalid
probability, undefined denominator and partial-rescue defects were reproduced.
The committed test file adds further workflow checks after those initial cases.

### Final diagnostic checks

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_fiber_diagnostic_contracts.py tests/test_fiber_miss_diagnostic.py tests/test_fiber_miss_diagnostic_report.py -q --no-header --tb=short | tee /tmp/fiber-diagnostic-final-focused.log
```

```text
57 passed, 4 skipped in 21.64s
```

Interpretation: calculations, finite and complete evidence gates, all verdict
branches, saved-verdict compatibility, source selection, outside-checkout CLI,
immutable outputs, read/serialization failures, subset labeling and undefined
comparison behavior pass. The four direct ScrollGT equivalence tests skip
because the sibling checkout is absent.

### Broader-run failures and targeted follow-up

The initial broader run overlapped other validation and ended with:

```text
2 failed, 1861 passed, 8 skipped, 1 xfailed, 9 warnings in 940.94s (0:15:40)
```

The candidate-report CLI exceeded its 30-second subprocess timeout after
printing valid output. The loop fixture did not observe an owned lock within
its readiness check. Neither failure was in the diagnostic cases. The import
probe below reproduced the unnecessary checkpoint/PyTorch dependency:

```sh
.venv/bin/python - <<'PY'
import importlib.abc
import sys
class NoTorch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            raise ImportError('CPU report unnecessarily imports torch')
sys.meta_path.insert(0, NoTorch())
try:
    import scripts.cross_scroll_validation
except ImportError as exc:
    print(type(exc).__name__ + ': ' + str(exc))
    raise SystemExit(1)
PY
```

```text
ImportError: CPU report unnecessarily imports torch
```

After extracting the hash helper:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_artifact_hashes.py tests/test_candidate_fiber_report_contracts.py::test_cli_outside_checkout_returns_machine_readable_status tests/test_loop_lifecycle.py::test_stop_targets_lock_owner_with_unbuffered_python -q --no-header --tb=short | tee /tmp/fiber-diagnostic-dependency-recheck.log
```

```text
9 passed in 20.75s
```

Interpretation: hash equivalence across block boundaries, missing-file errors,
exporter API compatibility, CPU-only report/mask execution and both failed
checks pass. The subsequent loop-fixture change waits for actual PID readiness
and is covered by final standard validation. These timings are verification
observations, not a general performance benchmark.

### Final standard validation and remaining deadline limitation

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py | tee /tmp/fiber-diagnostic-final-standard.log
```

```text
1 failed, 1870 passed, 8 skipped, 1 xfailed, 9 warnings in 688.56s (0:11:28)
```

Interpretation: diagnostic, hashing, artifact, export and lifecycle cases pass
on the completed changes. One unchanged interpolation-driver test hit its
20-second subprocess timeout. The earlier candidate CLI and loop fixture
failures did not recur. Accelerator/data-dependent skips and the existing
expected failure remain; warnings concern pinned-memory use without an accelerator.

The interpolation-driver case was rechecked alone without changing its code or
timeout:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_interpolation_drivers.py::test_failed_selector_cannot_start_a_study_even_after_printing_eight_rows -q --no-header --tb=short | tee /tmp/fiber-diagnostic-driver-recheck.log
```

```text
1 passed in 8.35s
```

Interpretation: the selector-failure guard works on its isolated rerun. The
broader run retains a timeout limitation despite this isolated pass.

### Smoke check

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/fiber-diagnostic-smoke.log
```

Captured output excerpt:

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 25.9s ---
```

Interpretation: available smoke paths pass; unavailable training data and the
optional augmentation path skip.

### Final documentation and evidence guards

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_filing_2026_10_numbers.py tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_afv_generator_entrant_report.py -q --no-header --tb=short | tee /tmp/fiber-diagnostic-final-doc-guards.log
```

```text
30 passed, 3 skipped in 9.63s
```

Interpretation: documentation references and source-bound filing/report claims
pass. Three checks require absent sibling tool/version checkouts and skip.

### Lint, formatting, whitespace and typing

```sh
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff check scripts/artifact_hashes.py scripts/fiber_miss_diagnostic.py scripts/run_validation_tests.py scripts/export_for_production.py scripts/cross_scroll_validation.py scripts/dataset_inspection.py scripts/spatial_split_mask.py tests/test_artifact_hashes.py tests/test_fiber_miss_diagnostic.py tests/test_fiber_diagnostic_contracts.py tests/test_loop_lifecycle.py
/workspace/.cache/uv/archive-v0/ZbEljn70GB_GHxGK/ruff-0.9.10.data/scripts/ruff format --check scripts/artifact_hashes.py scripts/fiber_miss_diagnostic.py scripts/run_validation_tests.py scripts/export_for_production.py scripts/cross_scroll_validation.py scripts/dataset_inspection.py scripts/spatial_split_mask.py tests/test_artifact_hashes.py tests/test_fiber_miss_diagnostic.py tests/test_fiber_diagnostic_contracts.py tests/test_loop_lifecycle.py
git diff --check
```

```text
All checks passed!
11 files already formatted
```

Interpretation: every changed Python file passes Ruff and formatting checks;
whitespace has no diagnostics.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.cache/uv/archive-v0/iIym1u6_padgNlQe/bin/mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python | tee /tmp/fiber-diagnostic-final-mypy.log
```

```text
Found 16 errors in 13 files (checked 657 source files)
```

Interpretation: the established typing errors remain in unchanged files
(missing stubs, OpenCV overloads, augmentation indices, optional tensors and
training list/tensor operations). No changed file has a diagnostic.

### PR integration on the newer main branch

Before opening the PR, rebased the review onto
`21b91b1a9909d35aba5a10860a7181241a5b6144` and checked out its recorded Villa
pin, `9afddaf0fdc12efe088bab7b82534c4f9a79e536`. The base adds pinned native
module imports and updates renderer patch comparisons; it does not overlap the
review edits. The earlier verification above remains tied to the original
baseline. These additional checks cover the diagnostic and the newer base's
affected integration boundaries:

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_artifact_hashes.py tests/test_fiber_diagnostic_contracts.py tests/test_fiber_miss_diagnostic.py tests/test_fiber_miss_diagnostic_report.py tests/test_pinned_vesuvius.py tests/test_serial_folds_patch.py tests/test_check_villa_render_path.py tests/test_mesh_preparation_contracts.py tests/test_geometry_handoff_contracts.py tests/test_mutex_data_contracts.py -q --no-header --tb=short | tee /tmp/fiber-diagnostic-pr-integration.log
```

```text
311 passed, 7 skipped, 1 xfailed in 64.76s (0:01:04)
```

Interpretation: the repaired diagnostic and newer pinned-module, renderer,
geometry and Mutex contracts pass. External ScrollGT/history comparisons skip;
the existing Mutex runtime blocker remains an expected failure.

```sh
set -o pipefail
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py | tee /tmp/fiber-diagnostic-pr-smoke.log
```

```text
Loaded 288/288 compatible tensors from best_model.pt (skipped missing=0, shape=0).
SKIP: dataloader_3tuple_sobel — training URI / inklabels not present
SKIP: dataloader_frangi_target — training URI / inklabels not present
SKIP: augmentations_bg2 — create_training_transforms not available
--- 8/11 passed, 3 skipped, 0 failed in 18.9s ---
```

Interpretation: available smoke paths still pass on the newer base. Training
data and the optional augmentation path remain unavailable. The whole standard
suite and typing check were not repeated after this base integration; their
documented timeout and existing typing errors remain validation limitations.

## Edge cases considered

- Missing/extra cubes, all trusted controls, incorrect split labels, duplicates,
  ambiguous probability caches and already-imported code from another checkout.
- NaN/infinite/bool/out-of-range gate inputs, inconsistent component quantities,
  malformed sample shapes/types, negative or zero lengths and outside samples.
- Empty masks, complete coverage and undefined soft-miss comparisons; both,
  one or neither held-out cube reaching the reference minimum.
- Explicit full versus descriptive mode, failed gates and nonzero exit status,
  output/source overlap, existing artifacts, read errors and non-finite JSON.
- Streaming hashes across a block boundary, absent files, exporter API
  compatibility and CPU operations with Torch import forbidden.
- Lock-file creation before ownership/PID publication, transient invalid PID
  during child startup, a child that exits and a bounded readiness wait.

## What was NOT tested

- Recomputing the real volume instruments, loading the real ScrollGT targets
  or the four direct external scoring comparisons: the checkout/data are absent.
- New GPU/native Villa operations, training, model selection or a scientific
  experiment; the saved verdict check uses existing JSON evidence.
- Whole-process peak memory, production speedups, power-loss durability,
  concurrent publishers or an atomic snapshot of changing input files.
- Physical annotation/CT registration, underlying probability model identity
  or new prize eligibility/adoption claims.
- Repairs to the established unrelated repository typing errors or installation
  of missing stub/dependency packages.

## Reviewer focus

Check that full conclusions require every control and finite consistent evidence,
that undefined and partial-recovery cases remain explicit, and that failure
artifacts cannot look like successful measurements. Verify the CPU hash
dependency boundary and retained exporter API, source/output separation, and
the distinction between the original scientific result and current tool repairs.
