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
  - It now raises a `ValueError` naming the cube, the entrant and its shifts, rather than averaging over one
    entrant. Which to do then is the owner's call. One cube refused stops the run, with no partial JSON.
  - Every cube has samples across every axis today, so the committed JSON is unchanged. Its test, which recomputes
    every cube's shift, passes.
- **Test** (`tests/test_neural_tracer_gt_offset.py`): either entrant with None on one axis is refused by name. With
  main's script it fails on the `TypeError`.
  - Each of these mutants is caught: one entrant checked and not the other (either way round), the names swapped,
    `all` for `any`, and `nanmean` over the entrant that has a value (independent review).

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
  - The two `assert 1 == 0` failures are a missing villa registration tool and a missing villa proofreader script.
    The first is bare and names the tool in its captured output; the second names the script in its message.
- **`config.json` sets every `ExperimentConfig` field, and has no key that is not one.** So no loop cycle takes a
  default silently.
- **Checkpoints are written atomically**: `last_model.pt`, `best_model.pt` and `--checkpoint_out` go through
  `promotion.save_checkpoint_atomic`, which writes a temporary file, then renames it. The step-curve snapshots
  (`eval_every_steps`, off by default) use a plain `torch.save`; nothing reads them back.
- **`run_result.json`** is written last, and not atomically. The loop deletes it before each run, and records a
  non-zero exit, a missing file or an unreadable one as a crash. So neither a stale result nor a half-written one is
  read as the cycle's.
- **Ignored output.** The suite's figures go to the ignored `outputs/`, as `train.py` documents.

## Observations for the owner (not changed)

- **Packages our code imports but `pyproject.toml` does not declare.** The independent review scanned the top-level
  imports of `scripts/`, `src/` and the root modules. It excluded villa, external checkouts on `sys.path`, guarded
  imports and tests.
  - **Two are in neither `pyproject.toml` nor `uv.lock`**, so `uv sync --locked` never installs them:
    - `transformers`: `scripts/measure_third_scroll.py`, `measure_segment_vintage.py` and
      `measure_fourth_reconstruction.py`;
    - `pynrrd` (`import nrrd`): `scripts/characterise_label_cubes.py`.

    These are research scripts. `boto3` is in neither too, but only `scripts/archive/` imports it.
  - **Nine arrive only as another package's dependency**, so dropping or changing that parent could remove them:
    - `jsonschema` (via `nbformat`): `scripts/geometry_artifacts.py`, for registration transforms (`register_volumes.py`,
      `voxelize_predictions.py`);
    - Pillow: `core/vesuvius_loader.py` and 46 more files;
    - tifffile: 29 files;
    - scikit-learn: `scripts/pixel_auc.py`, `detector/metrics.py`;
    - PyYAML: the GP-winner and LeJEPA launchers;
    - tqdm, fsspec, numcodecs: one script each;
    - timm: `vesuvius_model.py`.
  - **Declaring them needs `uv lock`** to regenerate `uv.lock`. That fails in this container, whose network policy
    denies `download.pytorch.org`, the index torch is locked from (PyPI answers). Editing `pyproject.toml` without
    relocking would make `uv sync --locked` refuse. So it is left for a machine that can relock, and which to declare
    is the owner's call.

## Verification

- `pytest tests/test_neural_tracer_gt_offset.py`: 12 passed. With main's script, the new tests fail.
- Ruff, ruff format and mypy with `--warn-unused-ignores` are clean on the changed files, the test included.
- The standard suite does not import the GT offset script. On the first commit (`9fdcdc5b`) it ran as on main:
  2672 passed, with the same 42 failures and 2 errors. The smoke test gave 9 of 11 passed and 2 skipped.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - each claim above, recounting the 44 by cause;
  - the 69 keys and 69 fields;
  - the loop's handling of `run_result.json`;
  - that `download.pytorch.org` is denied and PyPI is not.

  Its should-fix finding: the undeclared imports go beyond `jsonschema` (above). Its nits:
  - only one entrant was tested;
  - the error did not name the cube;
  - the checkpoint function's name;
  - the step-curve snapshots;
  - the "bare" assertions.

  All are addressed above.
