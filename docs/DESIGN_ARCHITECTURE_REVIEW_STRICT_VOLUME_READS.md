# Design and architecture review — strict volume reads

Baseline: `1ea2fa15`. Scope: CT input validation and ridge preprocessing in the
regional single-model, ensemble and production inference commands, plus opt-in
strict reads in the Python volume and unlabeled-dataset APIs.

## Findings and changes

1. **Inference could publish substituted ridge features.** Its raw volume reader
   used the ridge helper's permissive default. All three commands completed and
   wrote outputs when a fixture solver failed and supplied zero ridge features.
   They now request strict reads. A working CPU ridge implementation remains a
   valid fallback from a failed GPU; complete feature failure raises before model
   execution and output replacement.
2. **The reader could guess an unsupported encoding or return a clipped read.**
   Opt-in strict reads validate nonempty Z/Y/X metadata, integer coordinates,
   positive in-bounds sizes, actual returned shape, supported CT types and finite
   float32-range values. Signed/other integer and boolean/complex storage is
   rejected instead of using the legacy `/255` guess. uint8/uint16 normalization,
   nonnative byte order and floating passthrough retain their conventions.
3. **Unlabeled consumers had no strict read policy.** `VesuviusS3Dataset` now
   accepts `strict_reads=True`, propagates it to the volume reader, validates
   complete finite floating samples and raises with source/sample context. A
   strict request for its unimplemented Lasagna path is refused before I/O.

Source checks are centralized in the raw volume reader and shared by normalized
and raw access. Ridge error policy remains in the existing shared helper; the
unlabeled adapter owns its sample shape and contextual exceptions. Inference
call sites explicitly choose strict policy. Default Python readers and existing
training callers keep their counted permissive fallbacks. Legacy serialized
volume/dataset states remain permissive; explicit strict volume flags survive
pickling. No model, tiling rule, loss or frozen training recipe was changed.

## Verification

- Three initial end-to-end regressions failed against the old code: the single,
  ensemble and production commands all published outputs after the mocked ridge
  solver failed. The fixes prevent model execution in those cases.
- The new module adds **56 cases**, covering all three commands, actual CT
  encodings, malformed backend responses, bounds, nonfinite/overflowing values,
  unsupported slicing, CPU ridge fallback, serialization, legacy defaults,
  strict/permissive unlabeled behavior and previous-output preservation.
- Final curated selection: **283 passed** across **7/182 modules**, including
  existing labeled dataset, production/regional inference and validation-runner
  contracts. Existing permissive calibration/fallback tests continue to pass.
- Scoped Ruff check/format, Mypy and whitespace checks pass on seven Python files.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. The skips require two absent
  training inputs and the unavailable legacy augmentation entry point.

Validation uses Python 3.10.21, Torch 2.9.1+cpu and the pinned Villa source at
`ccb431818fa68059138f2c964ae299fc474ff116`. The restarted environment required a
fresh CPU test environment and initialization of this worktree's pinned submodule.
All read/model fixtures are local, temporary and synthetic; GPU fallback is
simulated. Exact commands, smoke results and captured output are in the PR report.

## Limits

Strict reads do not verify source calibration, model accuracy, file generations
or independent evidence. Floating CT is not automatically rescaled to unit range.
A backend that conceals a failure behind plausible zero values cannot be
distinguished from real zero CT. Successful computation can legitimately return
zero ridge features. These checks enforce successful requested processing, not
a nonzero-feature threshold.

No remote/native backend or real GPU workflow, full-scroll performance/memory
benchmark or full repository test suite was run. Paths must remain stable; these
checks add no locks, checksums, snapshots or rollback across concurrent inputs.
Existing shard completeness and output publication contracts remain separate.
On a failed new attempt, an unchanged previous prediction is still a previous
result. No historical output was rewritten. See
[read failures and preprocessing](VOLUME_INFERENCE.md#read-failures-and-preprocessing).
