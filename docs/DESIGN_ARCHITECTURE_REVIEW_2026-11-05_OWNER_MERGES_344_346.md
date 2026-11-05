# Design and architecture review — the owner's #344 and #346

Date: 2026-11-05. Baseline: `11943900` (main after #346).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 07:13 UTC firing.
- **#344 reserves the detector's prediction output before inference.** It merged after round #148's firing and was
  left for this round.
  - `write_prediction` creates the output directory first and opens a private `.prediction-` staging file. Then it
    calls the inference producer once.
  - It checks the output's paths three times: before inference, after inference and before publication.
- **#346 includes nested WEBKNOSSOS groups in skeleton labels.** `generate_fiber_labels.py` used to enumerate the
  root trees and one level of groups. It now uses the SDK's `flattened_trees()`, and the label metadata records
  `tree_traversal: "recursive"`.

This round changes no library or script code. It adds one test for #344's after-inference path check.

## What changed

- **#344's check after inference had no test** (`tests/test_detector_prediction_artifacts.py`).
  - The workflow doc says the CLI "checks paths before inference, after inference and again before publication".
  - With the post-inference `validate_output` removed, all 404 detector tests passed. The check before publication
    still refuses the same aliases, so only the work done before refusing changed.
  - The new test makes the output a symlink to the checkpoint while the model runs. It checks:
    - the write fails;
    - nothing is serialized;
    - the checkpoint is intact;
    - no staging file is left.
  - It passes as merged and fails with the post-inference check removed.

## Verified, no change needed

- **#344's ordering is pinned.** Mutants of `write_prediction`:
  - calling the producer before the staging file fails 7 detector tests;
  - restoring the output-named staging prefix fails 10 of the prediction and CLI tests;
  - dropping the returned result fails 16 of them.
- **#344's staging file is not mistaken for a prediction.** It has no extension, so nothing globbing `*.npy` or
  `*.npz` picks it up. A producer that raises leaves no staging file, which the existing tests check.
- **#346 with the real SDK.**
  - The SDK tests skip in this environment because `webknossos` is not installed. I installed the locked version,
    3.4.1, into a scratch overlay; its numpy and scipy matched the venv's.
  - With it, all 57 tests in `test_fiber_label_generation.py` pass.
  - With the old root-plus-one-level loop restored, 8 fail. They include the deep-nesting and mixed-group cases.
- **No other skeleton enumeration has the old shape.** `generate_fiber_labels.py` is the only place in `src/`,
  `scripts/`, `repro/` or `tests/` that walks SDK skeleton trees. The fiber benchmark's NML reader parses the XML
  itself.

## Observations for the owner (not changed)

- **Labels generated before #346 may be incomplete, and nothing marks them.**
  - Their `labels_meta.json` has no `tree_traversal` field. #346's doc says to regenerate affected runs into a new
    output directory.
  - No reader in this repository checks the field, so an old directory would be read as complete.
- **#346 was checked with the non-Windows lock only.** `uv.lock` pins `webknossos` 2.5.0 on Windows.
  `flattened_trees()` was not checked there.
- **#344's staging file can outlive a killed process.** It is opened before inference, so a run killed during
  inference leaves a `.prediction-*` file in the output directory. Before #344 it was opened only after inference.
  Nothing reads it.

## Verification

- **The touched modules**, `test_detector_prediction_artifacts`, `test_detector_cli` and `test_fiber_label_generation`,
  pass. The SDK cases ran with the locked SDK as above.
- **Ruff and mypy.**
- **The standard suite.**
- **The test modules outside the suite.**
- **The doc audit**, run alone.

A note on this round's own work: my first mutation runs left out a private `--basetemp`. The detector tests' temporary
directories, 2.4 GB under `/tmp/pytest-of-root`, then filled the disk, together with the 621 MB SDK overlay. I
stopped the run, restored `prediction.py` from git and deleted both. Every later run used a private base temp.
