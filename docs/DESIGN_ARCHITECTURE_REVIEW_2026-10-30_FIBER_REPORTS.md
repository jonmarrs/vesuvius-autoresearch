# Design and architecture review: candidate fiber reports, October 30, 2026

Reviewed base: `2becf197ff7b82f6e58d96300e33af97590eb17d`.
Scope: the handoff from the bounded fiber-label producer into the descriptive
ink/fiber report. This focused review does not certify every repository workflow.
No live study, training run, checkpoint, Villa submodule, or GPU job was changed.

## Findings

1. The report ignored `fiber_labels_meta.json`. A same-shaped label TIFF from a
   different source window, a contradictory producer declaration, or a modified
   label file could still be counted as `INSPECTED`. Twelve new regressions
   failed against the baseline: eleven ignored contract/geometry/hash fields
   and one same-shaped label replacement. These are examples of the same
   missing producer/consumer check, not twelve independent bugs.
2. Standalone `--help` failed without pytest's `PYTHONPATH`, with
   `ModuleNotFoundError: No module named 'vesuvius_autoresearch'`. Bootstrap the
   current checkout's `src` as well as its repository root.
3. JSON and TIFF hashes were calculated separately from decoding. End-of-run
   rechecks cannot bind a transiently replaced file's measured contents to a
   different earlier hash. Capture bounded bytes once and use them for both
   hashing and parsing/decoding. Metadata now reuses `text_snapshot.Snapshot`;
   TIFF input is captured as bounded binary bytes before header validation and
   decompression. Original metadata paths are retained for rechecks, so a
   symlink retarget cannot leave the old target's hash standing in for the
   current input.
   A baseline check with a 42,394-byte TIFF decoded replacement pixels even
   though the original file was restored before the final recheck. The new
   regression exceeds the file handle's small read-ahead buffer and verifies
   decoding the original captured bytes instead.
4. The JSON boundary accepted an overflowing numeric token (`1e999` became
   infinity), while deeply nested JSON raised an uncaught `RecursionError`.
   Finite float parsing and a local nesting-error conversion now produce
   explicit invalid-metadata records. Initial and final input reads reject
   nonregular and oversized files rather than opening a replacement pipe or
   hashing an unbounded replacement.

## Architecture and experience

`scripts/fiber_label_metadata.py` validates only the supported producer contract,
source-local window, declared numeric settings and serialized label hash. It
does not read CT or run inference. Report discovery, array budgets, metrics,
failure records and paired publication remain in `cross_scroll_validation.py`.
The existing bounded text capture and label-publication helpers are reused.

The new `--require-fiber-metadata` option rejects missing provenance while the
default continues to inspect legacy arrays descriptively. Present contradictory
or unsupported metadata always fails. Metadata is captured before TIFF decoding,
preventing a sidecar that disappears during inspection from silently becoming
legacy evidence. A failed candidate stays visible and is excluded from metrics.

Per-candidate records and summary/group counts distinguish checked fiber
metadata, prediction/fiber sidecars agreeing with candidate geometry, and
physical registration. Physical registration and accuracy remain unverified.
The report preserves the producer CT digest as a declaration, without claiming
to have recomputed it. The Markdown table makes the provenance distinction
visible. Metric formulas, undefined ratios and equal-weight grouping are
unchanged. See [usage and limitations](CANDIDATE_INK_FIBER_REPORTS.md).

## Verification and limits

Final selected integration command:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python -m pytest -q -rs \
  tests/test_candidate_fiber_metadata.py tests/test_candidate_fiber_report_contracts.py \
  tests/test_fiber_label_generation.py tests/test_file_modes.py \
  tests/test_validation_suite_covers_the_loop.py
```

Captured result: **213 passed in 29.72s**, including 37 new regressions. The new tests
use the actual CPU label producer and actual TIFF/Zarr I/O, plus a standalone
strict report invocation with `PYTHONPATH` unset from a foreign working directory.
They include a transient TIFF rewrite during decoding, JSON rewrite after
capture, sidecar mutations/appearance, symlink retargeting, and FIFO rejection.

CPU smoke command:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

Captured result: **8/11 passed, 3 skipped, 0 failed in 27.1s**. The two
training-data loaders lacked their local inputs; the batchgenerators-v2
augmentation entry point was unavailable. Ruff check/format and Mypy pass for
the four changed Python files. Local links in the four changed Markdown files
and whitespace checks pass. Exact quality commands are in the PR test report.

No CT bytes are read by the report. It does not independently verify producer
CT or filter hashes, response TIFF contents, OME transforms, prediction depth
context, physical registration, model quality, held-out lineage or native CUDA.
No real model inference or training was run. The entire repository suite,
concurrent-writer safety, power-loss durability and large-volume performance
were not tested. Compressed-byte capture adds memory within the existing TIFF
byte budget; requested voxel/pixel bounds are not a hard RAM cap. Source files
must remain stable and writers serialized.
