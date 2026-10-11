# Design and architecture review — mesh preparation

Date: 2026-10-11. Baseline: 754cee75eebf89d17f5021197f1edbb31c8404b1.
Scope: stored Tifxyz grid sampling, complete artifact publication, the frozen
coarse-grid driver integration, and the legacy automatic flattening selector.
Verification uses synthetic surfaces and temporary directories, not new scroll
measurements.

## What changed

Validate and publish geometry-only sampled Tifxyz meshes with retained validity
and current metadata, and retire the unsupported automatic flattening selector.

## Why

Sampling could create partial or invalid meshes, lose exclusion masks, and carry
stale geometry metadata; automatic selection could treat malformed files as
quality evidence and name outputs that no longer existed.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | Sampling omitted mask.tif, so excluded positive-coordinate points could become valid again. | Intersect sampled masks and coordinate validity, publish a canonical mask, and write the full invalid sentinel at excluded points. |
| P1 | The automatic sweep accepted nonempty output files, used file size when quality scoring failed, and wrote its selected path after deleting that temporary directory. | Retire automatic selection with an explicit nonzero unsupported response; launch no producer or publish an optimum. |
| P2 | Negative/bool strides were accepted, fractional strides failed incidentally, and oversized strides produced a 1x1 grid. | Require a positive integral stride and retain at least a 2x2 grid. |
| P2 | Writes began before source shape, metadata and values were checked; missing components and read failures left a partial destination. | Validate first, then stage all writes and rename only after completion; preserve existing and late outputs. |
| P2 | Shape mismatch used assert; integer/complex/stacked coordinates, nonfinite values and invalid metadata/scales had no declared boundary. | Inspect TIFF headers and decoded-source budgets before reads; validate all coordinate/mask payloads and strict finite metadata. |
| P2 | Coarse meshes reused source UUID, dimensions, bbox, area and channel declarations even when grid/support or files changed. | Assign a derivative UUID, actual dimensions and valid-point bbox, retain source-only metadata/hashes under provenance, and declare auxiliary files untransferred. |
| P2 | The sweep sent OBJ input and --method to a pinned CLI requiring Tifxyz directories; its SLIM module path was stale. | Explain actual native options and separate direct native flattening from the unsupported automatic selector. |
| P2 | Scale division was described as guaranteeing the same rendered output size; odd dimensions can change canvas/center and edge coverage. | Document the exact index/scale relation and its limits, with independent alignment/coverage checks required. |
| P2 | The archived strategy described a robust FastLocalVolume-based selector and prize qualification without evidence. | Correct the historical implementation claim and link current supported scope. |

A synthetic 7x10 grid at stride 3 becomes 3x4. The old tool copied metadata
claiming a 10x7 grid and retained its old identity/area. A positive XYZ point
masked out at the origin previously lost its mask; the new output excludes
that point in both mask and sentinel coordinates. Valid sampled positions
remain exactly the original values.

The initial regression used controlled nonempty malformed producer outputs:
the old sweep printed an optimum and wrote a configuration pointing into an
already removed temporary directory. It did not exercise native flattening,
a quality measurement, or scientific results.

## Architecture and workflow decisions

The repository already separates model/data factories, detector/fiber workflows,
regional inference, artifact contracts, loop supervision and research drivers.
This pass reviews the geometry-preparation boundary, not the training selection
or scientific evaluation contract.

[The sampler](../scripts/subsample_mesh.py) remains standalone with the same
three positional arguments: [the coarse-grid driver](../repro/spiral_render/run_scorer_vs_labels_coarse.sh)
copies just this script into its frozen work directory. Importing repository
publication helpers would break that workflow unless its snapshot changed.
Local validation, fingerprinting and temporary-directory publication therefore
live in the utility; no dependency or native Villa file is added or changed.

The supported artifact is geometry plus validity, not a complete segment copy.
Existing XYZ values at retained valid points survive exactly. Masked values
become the conventional sentinel; labels, corrections and auxiliary channels
need separately validated resampling semantics. Provenance records their
source metadata without promoting it to output measurements or claiming copied
channels. New identity/dimensions/bbox describe the derivative.

Metadata scale is x/y; coordinate arrays are row/column. Dividing scale by
stride preserves the uncentered retained index relation, not every consumer's
canvas size or centered frame. No trailing edge points, interpolation,
registration, physical conversion, accuracy metric or reading-quality verdict
is invented.

The [pinned reader](../villa/vesuvius/src/vesuvius/tifxyz/reader.py) consumes the
actual published test mesh, mask and reversed internal scale order. Its z > 0
fallback is used when no source mask exists. The
[pinned native flattening CLI](../villa/volume-cartographer/apps/src/vc_flatten.cpp)
declares Tifxyz input, --iterations and --lscm-only; it has no --method.
No validated automatic quality-selection recipe is supplied by this wrapper.

[The retired selector](../scripts/automate_arap_flattening.py) accepts legacy
--input/--output so invocations receive a useful diagnostic, exits 1 and
touches no source, prior result, producer or configuration. Help remains usable.
Native flattening itself remains available for independent, reviewed use.

[The operator guide](MESH_PREPARATION.md) covers bounds, validity, provenance,
publication, frozen-copy execution, renderer-frame limits and migration.
Historical preregistrations, result artifacts, training/evaluation harnesses
and native Villa files are unchanged. No experiment was launched.

## Verification

All commands run from the repository root in the existing Python environment.
Process inspection found no active training, autonomous loop, fit or renderer.

### Reproduce before repair

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_mesh_preparation_contracts.py -q --no-header --tb=short
~~~

~~~text
14 failed in 5.47s
~~~

Interpretation: initial regressions reproduce unsafe strides, dropped validity,
stale metadata, partial outputs, source/output overlap and false selection of
temporary malformed producer artifacts.

### Focused final contracts

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_mesh_preparation_contracts.py -q --no-header --tb=short
~~~

~~~text
75 passed in 3.26s
~~~

Interpretation: geometry/scale/mask preservation, actual pinned-reader loading,
source/output/budget validation, provenance, failure cleanup and real CLI
subprocess/frozen-copy behavior pass. The corrupt-TIFF subprocess check also
caught a traceback-only failure; the explicit TIFF error diagnostic is repaired.

### Standard validation

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/run_validation_tests.py
~~~

~~~text
1743 passed, 4 skipped, 1 xfailed, 9 warnings in 236.58s (0:03:56)
~~~

Interpretation: the standard suite passes with all mesh-preparation contracts
included. Existing optional/CUDA skips and the expected failure remain;
warnings concern pinned-memory requests in CPU-only checkpoint checks.

### Smoke checks

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python scripts/smoke_test.py
~~~

~~~text
--- 8/11 passed, 3 skipped, 0 failed in 12.8s ---
~~~

Interpretation: available smoke paths pass, including all 288/288 checkpoint
keys; optional local training data and unavailable bg2 augmentation paths skip.

### Documentation and evidence guards

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py tests/test_withdrawn_claims_stay_withdrawn.py tests/test_interpolation_evidence.py tests/test_interpolation_drivers.py tests/test_quotations_match_source.py -q --no-header --tb=short
~~~

~~~text
53 passed in 21.61s
~~~

Interpretation: operator-reference, report-claim, withdrawn-claim and interpolation
evidence/driver guards pass with the documentation and utility changes.

Final document-reference/report-claim check:

~~~sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 MPLCONFIGDIR=/tmp/vesuvius-matplotlib .venv/bin/python -m pytest tests/test_audit_doc_references.py tests/test_audit_report_claims.py -q --no-header --tb=short
~~~

~~~text
16 passed
~~~

Interpretation: the final operator guide and review report pass reference and
frozen-report claim checks.

### Static checks

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff check scripts/subsample_mesh.py scripts/automate_arap_flattening.py scripts/run_validation_tests.py tests/test_mesh_preparation_contracts.py
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from ruff==0.9.10 ruff format --check scripts/subsample_mesh.py scripts/automate_arap_flattening.py scripts/run_validation_tests.py tests/test_mesh_preparation_contracts.py
git diff --check
~~~

~~~text
All checks passed!
4 files already formatted
~~~

Interpretation: changed Python files pass Ruff; whitespace checks emit no diagnostics.

~~~sh
UV_CACHE_DIR=/workspace/.cache/uv UV_TOOL_DIR=/workspace/.cache/uv-tools uv tool run --offline --from mypy==1.19.1 mypy . --explicit-package-bases --namespace-packages --python-executable .venv/bin/python
~~~

~~~text
Found 16 errors in 13 files (checked 639 source files)
~~~

Interpretation: mypy retains the same errors in unchanged files (missing YAML/
requests stubs, OpenCV overloads, augmentation indices, optional loader tensors,
and training list/tensor operations); no review file has a diagnostic.

## Edge cases considered

- Positive/nonintegral/bool/negative/oversized strides; stride one, odd dimensions
  and unequal x/y scale; integer NumPy API arguments.
- Missing, corrupt, mismatched, thin, stacked or unsupported coordinate planes;
  nonfinite/negative values and partial invalid sentinels, including dropped points.
- Explicit binary masks, source sentinel holes, z=0 with/without an explicit
  mask, all-invalid output, and usable points discarded by the stride.
- Duplicate/malformed/nonfinite/oversized metadata and invalid or native-float32
  unrepresentable scales; stale source bounds/area/channels/identity.
- Source component symlinks, existing outputs, broken aliases and ancestor/child
  overlap; source modification versus benign access-time changes.
- Source-point/decoded-byte bounds before payload decoding; serialization,
  disk-write and rename failures; a late destination published by another writer.
- CLI calls outside the checkout, a frozen standalone script copy, actual pinned
  reader integration, help and unsupported automatic-selection execution.

## What was NOT tested

- Native C++ flattening/rendering or GPU execution; no rebuilt native binary
  or new scroll data is needed for these utility checks.
- Full-scale memory/time behavior, adversarial TIFF decoder internals, crash/
  power-loss durability, concurrent writers or an atomic multi-file source
  snapshot. Limits bound decoded source planes, not total memory or elapsed time.
- Auxiliary label/UV/correction resampling, physical registration, full-resolution
  interpolation, rendered alignment, reading quality or prize eligibility.
- Re-execution of the preregistered coarse-grid scientific experiment or
  reinterpretation of its frozen results.
- A replacement automatic distortion/reading-quality selection metric.
- Training experiments or unrelated established mypy errors.

## Reviewer focus

Check validity and retained-coordinate semantics, x/y scales and odd-grid frame
limits, derivative metadata/provenance, complete publication and frozen-copy
compatibility, and the separation of native flattening from unsupported
automatic quality selection.
