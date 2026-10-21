# Design and architecture review — the commit hooks, the documented commands, and the standing failures

Date: 2026-10-21. Baseline: `363f4277` (main after #177).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: whether main still passes what the owner's commits run, and what the review rounds' "environmental" failures
are.

- **The hooks.** `.pre-commit-config.yaml` runs these on every commit:
  - ruff and ruff-format on staged files;
  - mypy on the whole repository (`mypy . --explicit-package-bases --namespace-packages`);
  - nine doc-guard tests.

  The review rounds commit from a cloud container that does not run the owner's hooks. A hook failure on main blocks
  every commit the owner makes that touches Python, as `bd3666fe` records.
- **The standing failures.** Every round has reported the standard suite as "2704 passed, with the same 42 failures
  and 2 errors, all environmental", and said so without testing it.

Main has not moved since #177. There are no open pull requests. This round covers the 18:13 UTC firing.

## What changed

No code. This document records what was checked, and two observations for the owner.

## Verified, no change needed

- **mypy, run as the hook runs it, reports 6 errors in 5 files. None of the files has changed since the owner's
  last clean run (`bd3666fe`, 2026-10-19).** The errors come from this container's tool versions:
  - **Four** are "Star unpack syntax: requires Python 3.11", on `x[(slice(None), *selection)]`:
    - in `scripts/training/mutex_data.py`, `scripts/compute_structure_tensors.py` and
      `scripts/evaluate_deformation_metric.py`;
    - the parenthesized tuple is valid on every Python 3, and all three files parse on this venv's 3.10;
    - mypy 2.4.0, installed here, misreads it.
  - **Two** are cv2 overload errors, in `repro/sota_data/register.py` and `tests/test_sota_register.py`. They come from
    OpenCV 5.0.0's stubs. The lockfile pins 4.13.0.92.
- **ruff** (0.9.10, as the hook pins it):
  - Outside the hook's exclusions, the only errors are long-standing lint in frozen files:
    - `repro/gp_winner/`'s five scripts: import order, `super()` arguments, and a list default that is only read;
    - an f-string without placeholders in `repro/sota_data/validate_render.py`;
    - import order in `v3_training/trainer.py`.
  - The hook checks only staged files, so these bite only when one is edited.
  - `repro/villa_preserved/` is excluded on purpose.
  - The 23 Python files the review rounds changed from #171 to #177 all pass `ruff check`, and all but one pass
    `ruff format --check`. The exception is `repro/gp_winner/prize_gate_eval.py`, which #175 edited without
    reformatting, since it was found unformatted. ruff-format will reformat it when the owner next stages it.
- **The doc guards.** 93 passed, 2 skipped and 1 failed. The failure is `test_live_documents_stay_clean`, which
  flags:
  - `villa/` paths absent from this checkout;
  - the untracked `models/detector/detector_epoch=7.ckpt`.

  None comes from a review document.
- **Every documented command line names flags its script defines.**
  - For each `scripts/…py` or `repro/…py` command in the tracked Markdown, every `--flag` was checked against the
    script. The review documents and `docs/superpowers/` plans were left out.
  - The nine apparent misses are all defined elsewhere:
    - `train.py`'s and `predict.py`'s flags are Tap fields;
    - `scan_dataset.py`'s are in `dataset_inspection.scan_main`;
    - the June report's `--out-u` is the interface `docs/SPATIAL_PARTITIONS_AND_INSPECTION.md` records as retired.
- **The standing failures are environmental, now shown rather than assumed.**
  - This container's venv lacks four packages the lockfile pins:
    - s3fs 2026.2.0;
    - numba 0.65.1;
    - tensorstore 0.1.78;
    - jsonschema 4.26.0.

    Installed at those versions into a separate directory, added after the venv's own packages, they change the
    standard suite:
    - before: 2704 passed, 42 failed, 2 errors and 21 skipped;
    - after: **2747 passed, 9 failed and 22 skipped**.

    The two errors were collection errors, each hiding a whole file's tests.
  - All nine remaining failures need villa files that this checkout does not have, though it is at the pinned
    `ccb43181`:
    - six in `tests/test_label_curation_contracts.py` need `villa/segmentation/vc_proofreader/extract_good_labels.py`;
    - three in `tests/test_geometry_handoff_contracts.py` need `villa/foundation/volume-registration/`.
  - So none of the 44 is a failure of this repository's code. Villa was not fetched to check the last nine.

## Observations for the owner (not changed)

- **The cloud environment is not the locked one.**
  - Of 243 packages in `uv.lock`, the venv lacks 123 and has 57 at other versions. Among the differences:
    - torch 2.14.1 for 2.9.1+cu128, since `download.pytorch.org` is denied;
    - OpenCV 5.0.0 for 4.13.0.92;
    - huggingface-hub 2.2.0 for 1.5.0.
  - The review rounds' suite runs are against that environment. 43 tests that pass with the locked packages did not
    run in it.
  - The environment's setup script runs at the start of each new session. A line there would let every round test
    them:

    ```
    uv pip install --python .venv/bin/python s3fs==2026.2.0 numba==0.65.1 tensorstore==0.1.78 jsonschema==4.26.0
    ```

    A full `uv sync --frozen` would also need the PyTorch index, which the network policy denies.
  - Which, if either, is the owner's call.
- **mypy is not pinned.**
  - It is neither in `uv.lock` nor in `pyproject.toml`'s dependencies, and the hook runs `uv run --no-sync mypy`, so
    each machine checks with whatever mypy it has.
  - mypy 2.4.0 rejects the four valid lines above. An upgrade to it would fail every commit until either:
    - those lines are written as `x[(slice(None),) + tuple(selection)]`; or
    - mypy is pinned.
  - The choice is the owner's.

## Verification

- `mypy . --explicit-package-bases --namespace-packages`: 6 errors in 5 files, as above.
- `ruff check .` and `ruff format --check .` with the pinned 0.9.10: as above.
- The nine doc-guard tests: 93 passed, 2 skipped, 1 failed, as above.
- **The standard suite on `363f4277`:**
  - as the rounds have run it: 2704 passed, 42 failed and 2 errors;
  - with the four locked packages: 2747 passed and 9 failed, all nine on missing villa files.
