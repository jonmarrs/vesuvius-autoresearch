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

Validation results are recorded in the pull request. Regression coverage includes
the reproduced failures; corrupt, shape-mismatched and non-scalar images; integer
range and path validation; source/output mutation before publication; replacement
and rollback failures; retained recovery data; destination permissions; unrelated
user files; manifest integrity; legacy layouts; and a fresh interpreter whose
import guard rejects Torch, Lightning, W&B and detector-package imports.

Existing conversion/reproduce, detector CLI/configuration/data, prediction and
evaluation tests are checked alongside the new failure cases. This is an
engineering integrity change. Synthetic fixtures do not establish scientific
label accuracy, physical alignment, improved ink quality or prize eligibility.

See [the preparation guide](DETECTOR_DATA_PREPARATION.md) for budgets, migration,
exit codes, source freshness and publication limits. Concurrent readers/writers
and power-loss recovery are outside this serialized file API's guarantee.
