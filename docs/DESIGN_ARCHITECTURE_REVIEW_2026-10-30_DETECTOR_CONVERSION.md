# Design and architecture review: detector data preparation

Reviewed main `8145ed9e` in an isolated CPU checkout on October 30, 2026 (Pacific
time). Scope: the raw-TIFF converter and the detector's conversion/reuse boundary.
No live research measurements, GPU jobs or study checkout were touched.

## Findings and fixes

1. **A failed rerun mixed generations.** Each file was atomic, but the fragment
   was not. Starting from two uint16 layers of 50000, replacing the first with
   1000 and removing the second left converted values `[3, 195]` after failure.
   Old labels and all required filenames could remain, so the reuse check passed.
   The converter now stages a whole fragment, verifies it, then publishes it with
   rollback. Rebuilds reject unrelated destination files rather than deleting them.
2. **Incorrect source types silently changed the signal.** A uint8 layer filled
   with 200 became entirely zero. Signed and floating inputs were also cast and
   scaled without a declared intensity contract. Only scalar uint16 layers are
   now accepted; the existing high-byte scale remains unchanged.
3. **Existence was mistaken for readiness.** Corrupt files, incorrect bit depth,
   inconsistent layer/label/mask shapes and edited outputs were considered
   converted. Reuse now decodes and checks selected images. New conversions bind
   source captures and output bytes in a completion manifest; present manifests
   are mandatory for reuse. Legacy fragments have explicitly weaker evidence.
4. **The caller imported conversion code by an ambient module name.** The detector
   appended a reproduction directory to `sys.path`, then imported
   `convert_fragment`. It now imports a lightweight packaged core implementation.
   The historical script is a thin CLI, including a no-write `--check`/`--dry-run`
   path that works without Torch and from another working directory.

The architecture keeps image validation, source capture, generation publication
and readiness checks together in `core/fragment_conversion.py`. The conversion
CLI and detector reuse boundary share it. No model, training recipe, metric,
checkpoint, historical result or Villa pin changed.

## Verification

Final validation: **221 passed in 107.84 seconds**, with no skips, using Python
3.10.21 and Torch 2.9.1 CPU, with CUDA hidden and numerical-library threads limited
to one. The 64 conversion cases also passed independently. Ruff check/format and
Mypy passed on all six changed Python files; local documentation links and
`git diff --check` passed. No GitHub CI runs were configured for the PR head.

The integration scope was `test_convert_fragment`,
`test_detector_conversion_contracts`, `test_detector_cli`, `test_detector_config`,
`test_detector_data`, `test_detector_contracts`, `test_detector_prediction_artifacts`,
`test_detector_eval`, `test_detector_measure`, `test_detector_metrics`,
`test_validation_suite_covers_the_loop` and `test_validation_runner` under `tests/`.

Regression coverage includes
the reproduced failures; corrupt, shape-mismatched and non-scalar images; integer
range and path validation; source/output mutation before publication; replacement
and rollback failures; retained recovery data; destination permissions; unrelated
user files; manifest integrity; legacy layouts; and a fresh interpreter whose
import guard rejects Torch, Lightning, W&B and detector-package imports.

Existing conversion/reproduce, detector CLI/configuration/data, prediction and
evaluation tests are checked alongside the new failure cases. This is an
engineering integrity change. Synthetic fixtures do not establish scientific
label accuracy, physical alignment, improved ink quality or prize eligibility.

The published PR's author review reproduced a cleanup error with read-only
fragment directories: replacement succeeded, but deleting the old backup raised
`PermissionError`. Cleanup now makes only disposable private workspace directories
owner-writable. Published modes and backups retained after rollback failure are
preserved. Staging and backup directories are siblings of the final destination:
cross-parent moves can themselves require write access to a read-only directory's
parent link. All three real read-only permission regressions failed before this fix.
An injected error immediately after a successful publication rename also checks
that a failed rollback retains the previous generation even when the complete
new destination exists. Cleanup is explicitly disabled for that recovery backup.

See [the preparation guide](DETECTOR_DATA_PREPARATION.md) for budgets, migration,
exit codes, source freshness and publication limits. Concurrent readers/writers
and power-loss recovery are outside this serialized file API's guarantee.
