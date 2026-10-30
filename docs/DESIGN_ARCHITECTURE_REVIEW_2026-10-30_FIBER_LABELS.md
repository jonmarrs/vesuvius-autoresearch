# Design and architecture review: fiber labels, October 30, 2026

Reviewed base: `62905f3a005deeda2f6909a49ca6cc567f4214e7`.
Scope: the fiber-label CLI, candidate identity/geometry, source provenance,
serialization, failure behavior, and skeleton voxelization. This is a focused
review, not a claim that every repository workflow is free of defects. The
training loop, checkpoints, live registered study, and pinned Villa submodule
were not changed.

## Reproduced problems and repairs

| Problem | Resulting change |
| --- | --- |
| Standalone `--help` failed with `ModuleNotFoundError: No module named 'tools'` because the script used a stale Villa import/path | Bootstrap the actual repository and `src` paths; use the existing vendored fiber package; import WebKnossos only for skeleton execution |
| CT reads clipped requested stops and allowed negative slicing | Validate exact source-local geometry, minimum axis lengths, numeric/finite values, and a requested voxel budget; never alter the requested window |
| Existing evidence was overwritten file by file, with no binding between label and candidate source | Require a fresh run, retain candidate metadata, stage and read back both TIFFs, record source/TIFF hashes, then publish the completed directory |
| Planning created output directories and probed/fell back between GPU and CPU | Planning validates TSV/settings only, writes nothing and probes no CUDA; explicit GPU requests fail if unusable |
| Skeleton bounds compared XYZ positions with ZYX dimensions, and integer truncation admitted negative fractions | Compare against reversed dimensions and test floating coordinates before conversion |
| Empty skeleton expansion produced nine false corner voxels for an all-zero `(9,10,11)` mask at radius 2 | Return an empty mask before the distance transform/filter |
| Skeleton mode queued every tree and retained completed whole-cube results | Submit at most one batch per worker, release consumed futures, and accumulate in place |
| Research roadmap still instructed filing the already submitted engineering entry | Link the verified submission and retain the separate research entry's unsubmitted status |

The added baseline regression run had 28 failures, including assertions for new
publication contracts. Those failures are not 28 independently discovered bugs.
The standalone import and empty-mask observations above were also reproduced
directly. Existing vesselness math and normalization were retained.

## Architecture and usability

The CLI keeps argument parsing and skeleton geometry in
`scripts/labeling/generate_fiber_labels.py`. Candidate parsing, bounded CT reads,
filter dispatch, provenance, and whole-run publication live in the adjacent
`fiber_candidates.py`. Both reuse the existing label publication and candidate
artifact helpers instead of adding another rename or JSON-writing framework.

The new contract deliberately retires appending labels into an existing evidence
tree. This avoids associating a newly ranked candidate with an earlier
candidate's predictions. The default output path is now `reports/fiber_labels_run`.
The [usage guide](FIBER_LABEL_GENERATION.md) explains migration, inputs, exit
statuses, plan scope, coordinate frames, and the limits of heuristic labels.

Source metadata is checked before execution; the captured TSV bytes are both
parsed and hashed. Before publishing, the TSV, filter source and all selected
source regions are rechecked. The entire run succeeds or no final directory is
published. This requires stable inputs and serialized writers, not a transactional
source snapshot. The requested voxel budget bounds the logical fragment, not
codec allocation, filter temporaries, or multiprocessing memory.

## Verification

Commands ran from the review worktree with cached project dependencies, CPU
thread counts of one, and CUDA hidden. The integration command was:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python -m pytest -q -rs \
  tests/test_fiber_label_generation.py tests/test_fiber_streaming_cli.py \
  tests/test_candidate_fiber_report_contracts.py tests/test_file_modes.py \
  tests/test_validation_suite_covers_the_loop.py
```

Captured final output: **214 passed in 25.05s**. The 45 new cases cover standalone
execution without `PYTHONPATH`, exact CPU filter/threshold parity, scalar TIFFs,
source geometry and mutation, aliasing, existing outputs, invalid settings,
serialization/filter failures, explicit GPU failure behavior, dry runs, and
skeleton coordinates/empty-mask/publication. GPU failure tests use stubs; they
do not establish native CUDA behavior. Skeleton publication tests stub the SDK
and voxelizer; coordinate and empty-mask tests exercise the actual functions.
A real two-worker process pool also voxelizes synthetic crossing trees and
preserves the horizontal, vertical and mixed labels. This does not validate
pickling or parsing of native SDK objects.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

Captured output: **8/11 passed, 3 skipped, 0 failed in 11.7s**. Skips were the
two unavailable training-data loaders and the unavailable batchgenerators-v2
augmentation entry point. These checks do not measure training or inference
quality.

A standalone CLI invocation, without `PYTHONPATH` and from a foreign working
directory, also processed a `(16,32,40)` crop from the public uint8 fiber CT
cube `s1_00497_01497_03997_256`. Both serialized outputs matched the existing
CPU filter and threshold exactly; the source digest and attributes matched.
The default threshold selected zero voxels in this crop. No accuracy or
threshold-quality claim follows. The
[public CT smoke record](../reports/evidence/fiber_label_public_ct_smoke_2026-10-30.json)
contains the exact command, source URL/hash, measured source hashes and TIFF
hashes; raw inputs/outputs remain local under `/workspace/shared/`.

Static quality checks and the final PR review are recorded in the PR's test
report. The full repository validation suite was not run. Native CUDA, actual
WebKnossos parsing/SDK multiprocessing, large fragments, power-loss durability,
concurrent writers, and label quality were not tested. The downstream ink/fiber
report still uses shape-only fiber alignment; it does not yet consume the new
fiber sidecar as a registration contract.
