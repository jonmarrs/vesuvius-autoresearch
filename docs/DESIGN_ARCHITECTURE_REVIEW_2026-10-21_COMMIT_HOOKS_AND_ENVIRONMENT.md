# Design and architecture review — the commit hooks, the documented commands, and the standing failures

Date: 2026-10-21. Baseline: `363f4277` (main after #177).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: whether main passes what the owner's commits run, whether the documented commands run, and what the review
rounds' standing failures are.

- **The hooks.** `.pre-commit-config.yaml` runs these on every commit:
  - ruff and ruff-format on staged files;
  - mypy on the whole repository (`mypy . --explicit-package-bases --namespace-packages`);
  - nine doc-guard tests.

  The review rounds commit from a cloud container that does not run the owner's hooks. A hook failure on main blocks
  every commit the owner makes that touches Python, as `bd3666fe` records.
- **Two earlier reviews** found most of the environment's gaps:
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-18_DEV_WORKTREE_STEPS.md` reported this container's six mypy errors, and that
    mypy is not in `uv.lock`.
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-20_BASELINE_AND_DEPENDENCIES.md` classified the suite's 44 failures and errors
    by cause: s3fs 22, numba 12, villa files 8, tensorstore 1 and jsonschema 1.

  This round fixes the first and measures the second.

Main has not moved since #177. There are no open pull requests. This round covers the 18:13 UTC firing.

## What changed

- **main now passes mypy as the hook runs it here** (mypy 2.4.0, which sees this venv's packages). It reported six
  errors in five files. None of the five has changed since the owner's last Python commit, so whatever mypy the
  owner's hook runs passes them.
  - **Four** were mypy 2.4.0's "star unpack requires Python 3.11" on `x[(slice(None), *selection)]`:
    - in `scripts/training/mutex_data.py` (twice), `scripts/compute_structure_tensors.py` and
      `scripts/evaluate_deformation_metric.py`;
    - the parenthesized tuple is valid from Python 3.5 on. The independent review found that mypy 2.3.1 and 1.20.2
      accept it, so this is a 2.4.0 regression;
    - each is now `x[(slice(None),) + tuple(selection)]`. `spatial_blocks` yields a tuple of slices, so the index
      is unchanged.
  - **Two** were cv2 overload errors in `repro/sota_data/register.py` and `tests/test_sota_register.py`.
    - numpy 2.2.6's stubs, the locked version, type `np.float32([...])` as a scalar `floating[_32Bit]`, not an
      array, and no cv2 overload takes that.
    - The independent review found the locked OpenCV 4.13.0.92 gives the same errors, under mypy 2.4.0, 2.3.1 and
      1.20.2, so they do not come from this venv's OpenCV 5.
    - Each is now `np.array([...], dtype=np.float32)`, the same array.
  - `mypy . --explicit-package-bases --namespace-packages` now reports no issues in 748 files.
  - The tests of the five files pass with the four packages below present. The two failures among them, in
    `tests/test_villa_baselines_launchers.py`, fail the same way on main.
- **`reports/local_proofreader_guide.md`** told the reader to run `scripts/inference/launch_proofreader.py`. The
  script has been `scripts/launch_proofreader.py` since May, and it takes the guide's `--volume` and `--predictions`.

## Verified, no change needed

- **ruff** (0.9.10, as the hook pins it):
  - **Lint.** Outside the hook's exclusions, `ruff check` fails only long-standing lint in frozen files:
    - `repro/gp_winner/`'s five scripts: import order, `super()` arguments, and a list default that is only read;
    - an f-string without placeholders in `repro/sota_data/validate_render.py`;
    - import order in `v3_training/trainer.py`.
  - **Formatting.** `ruff format --check` would reformat 23 files outside `repro/villa_preserved/`:
    - `repro/`: `gp_winner/prize_gate_eval.py`, `gp_winner/train_resenc.py`, six `sota_data/` scripts and
      `spiral_render/artifacts.py`;
    - `scripts/`: `analyse_control_sensitivity.py`, `analyse_samewinding_extension.py` and `check_villa_copy_tree.py`;
    - `src/vesuvius_autoresearch/detector/metrics.py`;
    - ten tests, among them `tests/test_audit_doc_references.py`, one of the doc guards.
  - The hook reformats a file the first time it is staged, and that commit then has to be made again.
  - `repro/villa_preserved/` is excluded on purpose.
  - The 23 Python files the review rounds changed from #171 to #177 all pass `ruff check`, and all but one pass
    `ruff format --check`. The exception is `prize_gate_eval.py`, which #175 edited without reformatting, since it
    was found unformatted.
- **The doc guards.** 93 passed, 2 skipped and 1 failed. The failure is `test_live_documents_stay_clean`, which
  flags:
  - `villa/` paths absent from this container's sparse villa checkout;
  - `models/detector/detector_epoch=7.ckpt`, which is gitignored and absent here.

  None comes from a review document.
- **The documented command lines, other than the proofreader guide's:**
  - In the tracked Markdown, every `--flag` in a `scripts/…py` or `repro/…py` command is defined by its script, or
    by a parser the script uses. That covers Tap fields in `train.py`, `predict.py` and `ensemble_predict.py`,
    `dataset_inspection.scan_main` for both scan scripts, and `production_predict.py`'s generated `--x`/`--y`/`--z`.
  - The June window-size report's `--out-u` and `--out-v` are the interface
    `docs/SPATIAL_PARTITIONS_AND_INSPECTION.md` records as retired.
  - Commands at old paths remain only in documents marked archived or dated:
    - `docs/VILLA_PRIZE_READINESS.md`, whose header says its scripts moved;
    - `docs/PROGRESS_PRIZE_SUBMISSION_2026-05.md`;
    - `reports/villa_autoresearch_prize_plan_2026-05-06.md`.
- **The standing failures, measured.**
  - The suite was run as the rounds run it: `pytest -q --continue-on-collection-errors -rfE` over
    `scripts/run_validation_tests.py`'s list. Results:

    | environment | passed | failed | errors | skipped | xfailed |
    |---|---:|---:|---:|---:|---:|
    | this venv | 2704 | 42 | 2 | 21 | 1 |
    | with the four locked packages, appended after the venv's own | 2747 | 9 | 0 | 22 | 1 |
    | with the locked set the setup line below installs, ahead of the venv's | 2747 | 9 | 0 | 22 | 1 |

  - The second and third rows fail the same nine tests. The third ran on this branch, with the changes above.
  - Of the 44:
    - 33 ran and failed on a missing module;
    - the two errors were collection errors in `tests/test_zarr_loading.py` and `tests/test_sota_gt_register.py`;
      those files hold 10 passes and a skip.
  - All nine remaining failures need villa files that this container's sparse checkout of the pinned `ccb43181`
    lacks:
    - six in `tests/test_label_curation_contracts.py` need `villa/segmentation/vc_proofreader/extract_good_labels.py`;
    - three in `tests/test_geometry_handoff_contracts.py` need `villa/foundation/volume-registration/`.
  - The 2026-10-20 review counted eight villa-file failures. With jsonschema present, the ninth, the zero-landmark
    transform test, reaches the missing `volume-registration` and fails there instead.
  - So none of the 44 is a failure of this repository's code. Villa was not fetched to check the nine.

## Observations for the owner (not changed)

- **The cloud environment is not the locked one.**
  - Of 243 packages in `uv.lock`, the venv lacks 123 and has 57 at other versions. Among the differences:
    - torch 2.14.1 for 2.9.1+cu128, since `download.pytorch.org` is denied;
    - OpenCV 5.0.0 for 4.13.0.92;
    - huggingface-hub 2.2.0 for 1.5.0.
  - The rounds' suite runs are against that environment.
  - The setup script runs at the start of each new session. A line there would install the four packages at the
    lock's versions, with their dependencies held to the lock:

    ```
    uv export --frozen --no-hashes --no-emit-project | grep -vE '^(-e|\./)|@ |^torch(vision|audio)?==' > /tmp/lock.txt
    uv pip install --python "$PWD/.venv/bin/python" -c /tmp/lock.txt s3fs numba tensorstore jsonschema
    ```

    - Torch is left out because the lock's CUDA build needs the PyTorch index, which is denied.
    - In a dry run against this venv, the second line installs 23 packages, among them the four at their locked
      versions. It moves nine others to their locked versions: fsspec 2026.9.0 to 2026.2.0, multidict 7.1.0 to
      6.7.1, aiohttp, and six more.
    - It assumes the setup script runs from the checkout's root.
  - Whether to add it is the owner's call.
- **mypy is not pinned.** The 2026-10-18 review noted this. It is in neither `uv.lock` nor `pyproject.toml`, and the
  hook runs whatever mypy the venv holds. The changes above make main pass mypy 2.4.0 with the venv's packages
  visible, and pinning one version would keep it from drifting.
- **`scripts/run_validation_tests.py` stops at a collection error.**
  - It runs plain `pytest -q`. Where a test file cannot import, as `tests/test_zarr_loading.py` cannot without
    tensorstore, the run stops with "Interrupted … errors during collection" and runs nothing.
  - The rounds add `--continue-on-collection-errors`.
  - In the locked environment nothing fails to import, so this only matters where the environment is incomplete.

## Verification

- `mypy . --explicit-package-bases --namespace-packages`: 6 errors on main, none on this branch.
- `pytest` over the tests of the five changed files, with the four packages: 241 passed, 1 xfailed, and the two
  launcher failures that main also has.
- `ruff check` and `ruff format --check` with the pinned 0.9.10, on the five changed files: clean.
- The doc guards, the suite runs and the dry run: as above.
- **Independent review** of the first commit, in a worktree without villa. It found:
  - **Blocking:** the cv2 errors were attributed to OpenCV 5, which the locked OpenCV disproved.
  - **Should-fix:**
    - the two earlier reviews went uncited, and the 8 against 9 was not reconciled;
    - the ruff account gave lint only;
    - the proofreader guide's moved script;
    - the suggested install line was not held to the lock: it would have downgraded fsspec and multidict and let the
      other dependencies float, and the overlay measured did not match it.
  - **Nits:**
    - which rounds reported 2704;
    - the xfail;
    - what the collection errors hid;
    - how the suite was run;
    - "3.5+";
    - the owner's last Python commit;
    - the sparse checkout;
    - the gitignored checkpoint;
    - the flag audit's coverage.

  All are addressed above.
