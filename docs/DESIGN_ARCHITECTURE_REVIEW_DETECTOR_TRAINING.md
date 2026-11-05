# Design and architecture review — detector training

Baseline: `ff0dc660`. Scope: fragment selection before supervised dataset
construction, training budget overrides, CLI controls and checkpoint records.

## Findings and changes

1. **Different fragment names could hide the same CT input.** The dataset builder
   rejected a validation ID present in the training list but accepted directory
   symlinks, file symlinks and hard links to training layers under another ID.
   Three synthetic regressions reproduced this acceptance. The builder now
   validates all selected names and checks CT file identities before decoding
   either fragment. Reuse across distinct selected fragments fails with the
   offending fragment names and paths. Repeated training IDs also fail, avoiding
   accidental sample reweighting.
2. **Invalid overrides reached expensive work.** `max_epochs=0` selected the
   configured full run through an `or` fallback; other invalid epoch or batch
   limits were passed down after dataset/model construction. Overrides now have
   explicit type/range checks before data reads and output-directory creation.
3. **Short runs lacked convenient CLI controls and accurate budget records.**
   `train` now accepts positive integer `--max-epochs` and `--limit-batches`.
   The latter caps both training and validation batches. The Python API retains
   positive fractional batch limits. Training uses a configuration copy with the
   effective epoch budget, and the shared checkpoint mixin records the attached
   trainer's epoch and batch limits as optional `detector_training` metadata.
   These are configured limits, not assertions that the run completed them.

The data boundary owns split checks; the trainer owns budget validation and
execution; argparse owns CLI usage errors; the checkpoint mixin records the
framework's effective limits for both model architectures. No model architecture,
loss, augmentation, tiling, optimizer schedule or evaluation formula changed.
Checkpoint input-configuration version 1 remains compatible; no new field was
added to the strict configuration schema.

## Verification

- Against the original code, all **three alias regressions failed**: synthetic
  training and validation datasets were accepted despite sharing CT layers.
- The new module adds **32 cases**, including aliases at different depth indices,
  duplicate IDs, invalid names, a missing late layer, a FIFO, disjoint symlinks,
  invalid overrides before work, valid budget forwarding and CLI parsing.
- The focused detector run passed **107 tests**, including existing data and CLI
  tests. The curated integration selection passed **272 tests** across **8/180
  modules**. These selections overlap; their counts must not be added together.
- Both TimeSformer and ResEnc underwent one-epoch, two-batch CPU fixture runs.
  Readback checks confirm effective epochs and trainer limits in the saved
  checkpoints while the caller's configuration stays unchanged. Existing
  checkpoint compatibility and report/prediction artifact tests also pass.
- CPU smoke: **8 passed, 3 skipped, 0 failed**. Skips are two absent data inputs
  and the unavailable legacy augmentation entry point. Ruff check/format,
  scoped Mypy and whitespace checks pass.

Validation used Python 3.10.21 and Torch 2.9.1+cpu. Exact commands and captured
results are in the PR test report. The synthetic training warnings concern CPU
pinning, small loader/logging intervals and nonempty checkpoint directories.
The three training test modules are now in the curated runner.

## Limits

File identity does not detect copied images, overlapping scan regions or shared
training ancestry. Identical contents stored in distinct files remain allowed.
The preflight does not hash or snapshot inputs, and paths must remain stable.
No claim about the independence of existing studies follows from these checks.

Batch limits bound training/validation iteration, not initial fragment decoding,
tiling memory or model size. Very small Python fractional limits can still
produce no usable batches. Development checkpoints are not full-recipe benchmark
measurements; use a separate output directory and inspect saved progress.

The full repository suite, GPU behavior, real-fragment training, Windows and
remote filesystems were not tested. No live study checkout, research measurement
or stored model was changed. See the [workflow guide](DETECTOR_WORKFLOW.md#training-inputs-and-development-budgets).
