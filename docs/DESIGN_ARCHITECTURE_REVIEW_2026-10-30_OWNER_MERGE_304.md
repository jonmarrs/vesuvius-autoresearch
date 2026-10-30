# Design and architecture review — the owner's #304 (Villa binary evaluation)

Date: 2026-10-30. Baseline: `0a5ecb83` (main after #304 and #306).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 22:12 UTC firing. #304 was merged at 21:15 UTC, while the previous round ran, and is reviewed
here on its own.
- **#304** rewrites `scripts/evaluate_villa_metrics.py` as a bounded binary evaluator.
  - The reference and prediction must have exactly the same shape; nothing is cropped implicitly.
  - Every hard metric gets the same `>=` thresholded mask.
  - The new `scripts/evaluation_artifacts.py` reads and rechecks the inputs.
  - Each report is published as a new directory with the captured metric sources.

No change was needed. This record is the round's only change.

## Verified, no change needed

- **The pinned metric sources run.**
  - #304's three real-source tests skip unless `VESUVIUS_EVAL_METRICS_ROOT` names a capture of the pinned files.
  - The Villa submodule here is at the pin, `ccb431818`. Its nine `segmentation/evaluation/metrics` files have the
    pinned tree's blob ids.
  - With a capture of the seven selectable metric files and a manifest, all 67 evaluator cases pass:
    - Dice, centerline Dice, components and AP at thresholds 0.5 and 0.8;
    - skeleton distance with its verified PNG under the one-worker adapter.
  - #304's integration command then gives 222 passed and 1 skipped (a CUDA-only test). Without the capture it
    gives 219 passed and 4 skipped, the same 223 cases as #304's recorded 220 and 3.
- **The input contract** (`scripts/evaluation_artifacts.py`).
  - TIFFs: the header is checked before reading. The values are decoded from the same captured bytes that are
    hashed, and the header is compared again on that capture.
  - Zarr: named and multiscale axes must be spatial z/y/x. The selected region is hashed, and its header and
    content are rechecked before publication.
  - The reference must be binary 0/1 or 0/255. The prediction encodings are explicit.
- **The metric calls** (`scripts/evaluate_villa_metrics.py`).
  - Each metric gets its own copy of the inputs.
  - Dice now gets the thresholded mask, so it agrees with the other hard metrics at any threshold.
  - AP uses probabilities unless `--ap-input binary` is given.
  - Pinned AP's logged internal error becomes `FAILED`, not a zero score.
  - Nonfinite results are `UNDEFINED`.
- **Order and publication.**
  - Execution requires `--aligned-inputs`.
  - The output must be disjoint from the inputs, the Villa root and the captured sources.
  - Inputs, sources, adapters and the skeleton PNG are rechecked before the report is published. Failures exit 1
    with no report.
- **Callers.**
  - No script, shell file or Makefile calls the evaluator; only its test does.
  - `docs/VILLA_DRAFT_centerline_dice_empty_slices.md`'s note still holds: the evaluator scores whole volumes
    through the pinned centerline file.

## Observations for the owner (not changed)

- **Exit 2 has two meanings.** It is argparse's exit for bad arguments, with nothing published, and also the exit
  for a published `PARTIAL` report. The guide says so. A caller can tell them apart only from stdout.
- **A centerline warning makes a run partial.** Predicted skeletons on reference-empty slices, or a score above
  one, mark centerline Dice `WARNING`. The report is then `PARTIAL` and exits 2, although every metric ran. The
  guide documents the statuses; callers should not read exit 2 as a failed measurement.
- **The Villa source is not checked against the pin.**
  - `--villa-root` is trusted as given, as the guide says.
  - The report records each captured source's SHA-256, not its Git blob id. Matching a report to a Villa commit
    needs that hash recomputed.
- **The pinned-source tests skip in a normal run.** The standard suite never sets `VESUVIUS_EVAL_METRICS_ROOT`, so
  the only tests that run the real pinned metric code are skipped there. A checkout whose submodule is at the pin
  already has the files; the capture above was built from it.

## Verification

- **The evaluator tests with the pinned capture:** 67 passed.
- **#304's integration command:** 222 passed and 1 skipped with the capture; 219 passed and 4 skipped without it.
- **The checks.** Ruff 0.9.10 `check` and `format` are clean on #304's Python files. Mypy is clean over the whole
  repository (848 files).
- **The standard suite** gives RESULT_SUITE.
- **The test modules outside the standard suite** give RESULT_OUTSIDE.
- **The doc audit** finds no new unresolved reference.
