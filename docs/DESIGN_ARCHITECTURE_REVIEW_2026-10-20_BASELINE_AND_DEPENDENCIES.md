# Design and architecture review — the suite's standing failures, an undeclared dependency, and the GT offset's mean

Date: 2026-10-20. Baseline: `cb8033e3` (main after #161).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the standard suite's 42 failures and 2 errors, which every review since 2026-10-13 has compared against as
  environmental, re-checked by cause;
- the declared dependencies against what the code imports;
- `config.json` against `ExperimentConfig`;
- how `train.py` writes its checkpoints and result;
- the one problem left open by the last review in `scripts/neural_tracer_gt_offset.py`.

The owner's open #159, #160 and #162 are not touched, and neither is any file they change.

## What changed

- **`neural_tracer_gt_offset.mean_shift` refuses a missing axis.**
  - An entrant with no samples across an axis records `median_disp_perp_zyx` as None there. The mean of the two
    entrants then raised a bare `TypeError` from numpy.
  - It now raises a `ValueError` naming the entrant and its shifts, rather than averaging over one entrant. Which
    to do then is the owner's call.
  - Every cube has samples across every axis today, so the committed JSON is unchanged. Its test, which recomputes
    every cube's shift, passes.
- **Test** (`tests/test_neural_tracer_gt_offset.py`): an entrant with None on one axis is refused by name. With
  main's script it fails on the `TypeError`.

## Verified, no change needed

- **The standing failures are all environmental, by cause.** All 44 failures and errors in
  `scripts/run_validation_tests.py`'s list come from five causes:

  | cause | count |
  |---|---:|
  | `s3fs` not installed | 22 |
  | `numba` not installed (villa's `tifxyz`) | 12 |
  | villa's files absent (`vc_proofreader`, `volume-registration`) | 8 |
  | `tensorstore` not installed | 1 |
  | `jsonschema` not installed | 1 |

  - `s3fs` and `tensorstore` are declared in `pyproject.toml`, and `numba` and `jsonschema` are in `uv.lock`, so
    this container's virtual environment is incomplete. The repository is not broken.
  - The two bare `assert 1 == 0` failures are a missing villa registration tool and a missing villa proofreader
    script, each named in the captured output.
- **`config.json` sets every `ExperimentConfig` field, and has no key that is not one.** So no loop cycle takes a
  default silently.
- **Checkpoints are written atomically:** `promotion.save_atomically` writes a temporary file, then renames it.
- **`run_result.json`** is written last, and not atomically. The loop deletes it before each run, and records a
  non-zero exit, a missing file or an unreadable one as a crash. So neither a stale result nor a half-written one is
  read as the cycle's.
- **Ignored output.** The suite's figures go to the ignored `outputs/`, as `train.py` documents.

## Observations for the owner (not changed)

- **`jsonschema` is imported but not declared.**
  - `scripts/geometry_artifacts.py` imports it directly, to validate registration transforms against the pinned
    schema (`register_volumes.py`, `voxelize_predictions.py`).
  - It arrives only as a dependency of `nbformat`.
  - Declaring it (`"jsonschema>=4.26.0"`, the locked version) needs `uv lock` to regenerate `uv.lock`. That fails in
    this container, whose network policy denies `download.pytorch.org`, the index torch is locked from. Editing
    `pyproject.toml` without relocking would make `uv sync --locked` refuse. So it is left for a machine that can
    relock.

## Verification

- `pytest tests/test_neural_tracer_gt_offset.py`: 11 passed. With main's script, the new test fails.
- Ruff, ruff format and mypy with `--warn-unused-ignores` are clean on the changed files, the test included.
- The standard suite does not import the GT offset script.
