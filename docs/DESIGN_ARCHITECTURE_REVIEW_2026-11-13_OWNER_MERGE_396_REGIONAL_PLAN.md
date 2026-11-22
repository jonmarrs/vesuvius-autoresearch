# Design and architecture review — the owner's #396, the regional prediction plan

Date: 2026-11-13. Baseline: `30b9c46` (main after round #166's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 09:12 UTC firing on 2026-11-13. Main had not moved. **#396** is the last large merge that
earlier rounds left: a repository audit of twelve commits and about 90 files, merged on 11-11 at 19:03 UTC. It is
too large to review in one round at the depth this session can afford, so this round takes one slice of it, the
planning that the two regional prediction commands run before they load a model:
- `scripts/regional_prediction_artifacts.py` plans every output path and refuses one that would replace the CT
  source, a checkpoint or another output;
- `src/vesuvius_autoresearch/core/regional_resources.py` bounds the three blend arrays the predictors keep.

The last section lists what of #396 is still not reviewed.

## What changed

### Eight guards of the artifact plan are now tested (`tests/test_regional_artifact_plan.py`)

This round made 29 mutants: 21 of the artifact plan and 8 of the resource bound. #396's four regional test modules
killed 21, including all 8 of the resource bound. Eight new test functions (12 cases) kill the other 8. Each passes
on the code as merged and fails with its mutant.

#396's tests of the plan run a whole prediction command against stand-in models. The new tests build the plan alone,
on an OME group whose array is its level 0:
- **An output must be a nonempty local path.** A blank image or metadata path and an `s3://` address are refused.
- **The whole source is protected, not only the array the reader selects.** An output inside the OME group but
  outside its level 0 is refused. #396's test of this writes into a volume whose array is the volume itself, so
  the array's protection alone passed it.
- **An output directory that links into the source is refused.**
- **A source or a checkpoint named through a link is recorded as the real path**, and the real path is protected.
- **An output directory that is a regular file is refused**, and the file is left as it was.
- **Existing outputs keep their kinds.** The two arrays and the uncertainty mask may exist as directories. A
  directory where a file belongs is refused.

No code changed.

## Verified, no change needed

- **The plan covers the whole family of outputs.** It reserves the ten names `prediction_paths` lists for a stem,
  plus a custom image or metadata path when one is given, and checks them against the source, the selected array
  and every checkpoint in one call.
- **The image's file name is fixed before it is checked.** A name without a suffix gets Matplotlib's configured
  format, and the writers are told that format, so the file written is the file planned. #396's tests cover this,
  and each of its three mutants fails them.
- **The resource bound counts what the predictors keep.** Three float32 planes of the region are 12 bytes a pixel,
  against a default limit of 512 MiB. The bound admits exactly the limit. Its report says it is not a whole-process
  peak estimate. #396's tests kill all eight mutants of it.
- **Unrecordable checkpoint settings are refused** before anything is overwritten: a NaN and a value JSON cannot
  hold. #396's tests cover both.

## Observations for the owner (not changed)

- **Resolving the source and the checkpoints is not what refuses an alias.** With either `.resolve()` removed, an
  output that reaches the real volume or the real checkpoint is still refused, because `validate_plan_paths`
  compares real paths itself. The resolution only decides what the plan records. The new tests bind the recorded
  values.
- **The plan is tested through two commands and now alone.** `scripts/inference/predict.py` and
  `scripts/inference/ensemble_predict.py` are its only callers. This round did not review how they use it.

## Verification

- **The touched module.** `test_regional_artifact_plan.py` gives 60 passed, against 48 on `30b9c46`. With the other
  three regional modules that is 100 passed, against 88.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    changed test file.
  - Mypy is clean over the whole repository, with `--python-executable ./.venv/bin/python`.
- **The standard suite.** The 216 modules give the same 171 failing ids on `30b9c46` and on this branch.
- **The test modules outside the suite.** The 250 modules give the same 23 failing ids on `30b9c46` and on this
  branch.
- **The doc audit**, run alone, lists the same unresolved references as on `30b9c46`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

The baseline figures for `30b9c46` are round #166's runs of its branch head, whose tree is identical. The failing
ids are this container's: it has no villa checkout.

## A note on this round's work

- **This is one slice of #396.** Its other parts are not reviewed: the proofreader launcher, fiber and 3D ink label
  generation, the canvas publication changes, the placement and scroll-frame tools, the retired v3 launchers, the
  CPU workflow and its requirements file, the research-prerequisite markers, and the audit document itself.
- **Also still not reviewed:** the estimator and resampler of #390.
- **The mutants are a sample** of the two modules' checks. All four test modules passed here before the mutants
  were run.
