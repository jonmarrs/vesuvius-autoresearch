# Design and architecture review — what the tests write into the checkout

Date: 2026-10-22. Baseline: `bed87b4e` (main after #182).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: every file the tests in `tests/` write inside the checkout. Rounds since 2026-10-16 have checked that no test
changes a tracked file. A test can also overwrite a gitignored file that the owner's own runs produced, and
`git status` does not show it.

Main has not moved since #182. There are no open pull requests. This round covers the 03:13 UTC firing.

## What changed

- **Measured, in this container.**
  - Every file under the checkout was recorded by path, size and mtime, apart from `.venv/`, `villa/`, `.git/`,
    `.claude/`, `__pycache__` and the tool caches.
  - Then all of `tests/` ran with the locked packages, and every file was recorded again.
  - Two files changed. No file was created or removed, and no tracked file changed.
  - This container has a sparse villa checkout and no `local_data/`, so two more writes are not reached here (see
    below).

  | file | written by | |
  |---|---|---|
  | `outputs/skeleton_hists/skeleton_branch_length_hist_sample_1.png` | `tests/test_evaluate_villa_metrics.py` | fixed |
  | `scripts/_finetune_lejepa_runner.py` | `tests/test_villa_baselines_launchers.py` | by design |

- **The histogram replaced the loop's.**
  - `scripts/evaluate_villa_metrics.py` sends villa's skeleton histogram to the checkout's `outputs/skeleton_hists/`.
    `train.py` sends the loop's own histograms there.
  - So a test run in the main checkout replaced the first histogram of the loop's last validation with a synthetic
    one.
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-18_DEV_WORKTREE_STEPS.md` recorded this as an observation.
  - **Change:** the script takes `--hist_dir`, which defaults to that directory as before. The test that runs villa's
    real skeleton metric points it at its own temporary directory, and checks that the histogram lands there.
  - With the change, the test file leaves the checkout's histogram untouched; its mtime was checked before and after.
  - **Mutants.** The test fails if the script ignores `--hist_dir`, either by hard-coding the old directory or by
    falling back to villa's default of the working directory.
- **The runner is by design.**
  - `launch_finetune_lejepa.py` writes its runner into `scripts/` on every run, and the runner is gitignored.
  - `test_a_generated_runner_names_its_launcher_and_stays_out_of_git` checks that it is ignored and untracked.
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-22_SUITE_GUARD_LAUNCHED_SCRIPTS.md` records it.
- **Two writes this container cannot reach:**
  - `scripts/_gp_winner_runner.py`, by `test_launch_gp_winner_writes_baseline_marker`.
    - Its launcher writes the runner only once it finds villa's `segmentation/models/multi-task-3d-unet`, which
      this sparse checkout lacks.
    - Like the LeJEPA runner, it is gitignored, and a test asserts that.
  - `test_cache/valid_coords_villa_grid_*.npy`, by `tests/test_vesuvius_loader.py::test_labeled_dataset`.
    - The test builds a labeled dataset with no `cache_dir`, so it caches its patch coordinates in the loader's
      default, the checkout's `test_cache/`, which is also the loop's (`config.py`).
    - It skips here without `local_data/PHercParis2Fr47`.
    - The file's name carries the patch size (32), the masks' and labels' mtimes and the thresholds, so it sits
      beside the loop's caches and does not replace one.

## Verified, no change needed

- **Every test in `tests/`, with the locked packages, on main:** 4408 passed, 98 skipped and 1 xfailed, with 19
  failures and 19 errors.
  - These are #182's 20 failures less the LeJEPA discovery test, which no longer depends on the machine's data.
  - Every one has the environmental cause the 2026-10-22 suite-guard review tabled.
- **The noise probe's temporary directories** are removed after each trial, in a `finally` (`f1_noise_probe.py`).
- **The loop's code has one silent broad `except`.** It is in `vesuvius_loader._cupy()`: a CUDA device query that
  fails leaves the ridge filter on the CPU, the path every test without a GPU runs. A device whose query fails is
  not one CuPy could have used.

## Observations for the owner (not changed)

- **`launch_neural_tracing.py` picks a local checkpoint by name, not age.**
  - `_find_neural_tracing_checkpoint` returns the first path of the reverse-sorted list, the greatest name. Across
    two run directories it picks the later name, not the newer file.
  - Villa's own resolver, given a directory, takes its highest `ckpt_*.pth` iteration.
  - The repository has no local tracing checkpoint, so the launcher falls back to villa's
    `extrap_displacement_latest`.
- **An explicit `--checkpoint` that does not exist still gives a `ready` marker.** The trace service loads it
  lazily, so it would fail at the first request that needs the model. The evidence chain does not pass
  `--checkpoint`.
- **Finding 95 is not yet folded into the October draft.** The owner's finding commits update reports and tests,
  and the draft is folded in separately (`d32a9797` for finding 94).
- **`scripts/probe_skel_dist_validity.py`** also writes histograms to `outputs/skeleton_hists/`. No test runs it.

## Verification

- `pytest tests/test_evaluate_villa_metrics.py`: 4 passed. The checkout's histogram is unchanged.
- The two mutants were run in a scratch worktree, and the unmutated test passes there.
- Ruff 0.9.10 `check` and `format` are clean on both files, which were formatted before.
- **The standard suite** on the first commit, with the locked-package overlay, gave 2776 passed, 22 skipped and 1
  xfailed, with the same ten environmental failures as main. `test_evaluate_villa_metrics.py` is not in the
  standard suite. The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - **It confirmed:**
    - the default unchanged, and the histogram landing in `--hist_dir` when it is given, by running the script with
      villa's metrics read from this checkout;
    - the option reaching villa's `output_folder`;
    - both mutants;
    - the full-run numbers;
    - the noise probe's cleanup;
    - the single silent `except`;
    - the launcher observations.
  - **It re-measured the writes in its own worktree.** Only the LeJEPA runner was written there, because without
    villa the skeleton test stops at import.
  - **Its should-fix findings:**
    - the two-file claim held only in this container, missing the gp_winner runner and the loader's coordinate
      cache;
    - the CPU and GPU ridge channels are not tested to agree. Only vesselness is, and only on a GPU.
  - **Its nits:**
    - the reverse-sort wording;
    - the lazy load affects any request that needs the model, not only heatmaps;
    - `FINDINGS.md` numbers no findings;
    - the option's hyphen, where the parser's other two-word flags use `_`.
  - All are addressed above. The option is now `--hist_dir`.
