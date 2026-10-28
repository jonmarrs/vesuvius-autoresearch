# Candidate preprocessing content and resume review

Reviewed October 28, 2026 against public main
`416cbe4daf3f29ca0ad91348ce231a62c2012271` from a separate checkout. Scope:
crop/tensor publication, candidate reuse, checkpoint identity in CT evidence,
operator verification and report destinations. No live study measurements or
GPU computations were used.

## Findings and fixes

- Crop reuse inspected metadata but accepted changed source voxels, modified
  crop data and a deleted payload chunk. Tensor reuse similarly accepted a
  modified source crop, changed normals and a deleted chunk. Six regressions
  reproduced those cases with actual local Zarr arrays.
- CT evidence reuse checked only the checkpoint's path. A seventh regression
  replaced that file while keeping its path and observed a false reuse pass.
  Single prediction now loads a captured byte buffer and records its SHA-256.
  Reuse compares that digest with the requested checkpoint. Hashing and parsing
  the same captured bytes prevents a replacement during load from binding the
  wrong file to the output.
- Pipeline reports were published before input selection, allowing a report
  destination to replace an input table, checkpoint or artifact metadata.
  Existing shared path checks now run before report writes and include local
  inputs, masks, the research lock and selected artifact directories.

The seven content regressions failed on the unchanged implementation. Crop and
tensor contracts now use version 2. Their fingerprints bind dtype, shape and
decoded values in deterministic 64³ spatial blocks. Tensor output identity
covers all six tensor channels, all nine vector components and confidence.
The producers compare source content before and after generation and preserve
previous outputs if it changes or publication fails. Resume verifies stored
content and refuses corrupt codec payloads. Contract-1 artifacts need a fresh
build rather than receiving a retroactive trust marker.

The new `--verify-only` mode reads artifacts, reports their stage states and
runs no processing subprocess. A rebuilt crop also forces requested CT evidence
to refresh. The normal execution path and verification share the same matching
helpers, avoiding a separate definition of reusable data.

## Limits and resource decisions

Only the selected crop is compared against its source, so updates elsewhere
in a large CT volume leave that crop valid. Hashing requires CPU reads and
codec work on the candidate and tensor outputs. The Python spatial reads are
bounded, while underlying codecs can decode larger storage chunks. Initial
absent chunks still follow Zarr's fill-value semantics; the fingerprint binds
the content observed at creation, not independent CT completeness or quality.

CT evidence retains its local artifact-validation scope. The checkpoint digest
identifies the file actually loaded, while full inference inputs, external
context and training exposure remain separate audit responsibilities. A
checkpoint-sized byte buffer is used transiently on CPU. No scoring definition,
model parameter, GPU experiment or registration was changed by the review.
Directory publication still requires serialized readers/writers, and path
validation is a snapshot rather than a concurrency lock.

## Verification

Tests use real CPU Zarr arrays and synthetic model checkpoints. The upstream
tensor subprocess is a controlled fixture that produces the required array
schema; native Villa tensor kernels were not executed. The pinned runner file
was supplied only to satisfy existing source checks, from Villa gitlink
`ccb431818fa68059138f2c964ae299fc474ff116`, verified as Git blob
`531948c2a6a88596718bde8beb0325554ec41b3b`.

The cached Python 3.10 environment is `/tmp/vesuvius-review-env`. With
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CUDA_VISIBLE_DEVICES=''`:

```sh
/tmp/vesuvius-review-env/bin/python -m pytest -q -rs \
  tests/test_candidate_content_provenance.py tests/test_candidate_preprocessing_contracts.py \
  tests/test_crop_candidate_zarr.py tests/test_execute_lasagna_pipeline_resume.py \
  tests/test_predict_checkpoint_loading.py tests/test_volume_inference_contracts.py \
  tests/test_submission_contracts.py tests/test_validation_suite_covers_the_loop.py
# 308 passed, 17 skipped in 50.91 seconds

/tmp/vesuvius-review-env/bin/python scripts/smoke_test.py
# 8 passed, 3 skipped, 0 failed in 14.7 seconds
```

The 17 skipped checks require the unavailable Villa `nrrd` coherence dependency.
Smoke skips require real training data or Villa's augmentation import. Earlier
focused runs passed 75 and 202 checks after supplying the pinned source fixture.
Verification-only tests prohibit processing calls and compare artifact bytes
and mtimes before/after. Drift tests preserve prior outputs, codec corruption
fails closed, and a checkpoint replacement during loading retains the captured
file's digest. Report alias tests cover direct paths, symlinks and hard links.
The new tests are included in the standard validation list.

Ruff checks all eight changed Python files; targeted mypy checks the five
candidate helper, producer, pipeline and new test modules. The full repository
suite, real-scroll processing, native GPU kernels and deployment were not run.
