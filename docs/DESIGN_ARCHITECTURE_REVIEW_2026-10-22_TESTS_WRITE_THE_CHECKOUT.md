# Design and architecture review — what the tests write into the checkout

Date: 2026-10-22. Baseline: `bed87b4e` (main after #182).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: every file the tests in `tests/` write inside the checkout. Rounds since 2026-10-16 have checked that no test
changes a tracked file. A test can also overwrite a gitignored file that the owner's own runs produced, and
`git status` does not show it.

Main has not moved since #182. There are no open pull requests. This round covers the 03:13 UTC firing.

## What changed

- **Measured.**
  - Every file under the checkout was recorded by path, size and mtime, apart from `.venv/`, `villa/`, `.git/`,
    `.claude/`, `__pycache__` and the tool caches.
  - Then all of `tests/` ran with the locked packages, and every file was recorded again.
  - Two files changed. No file was created or removed, and no tracked file changed.

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
  - **Change:** the script takes `--hist-dir`, which defaults to that directory as before. The test that runs villa's
    real skeleton metric points it at its own temporary directory, and checks that the histogram lands there.
  - With the change, the test file leaves the checkout's histogram untouched; its mtime was checked before and after.
  - **Mutants.** The test fails if the script ignores `--hist-dir`, either by hard-coding the old directory or by
    falling back to villa's default of the working directory.
- **The runner is by design.**
  - `launch_finetune_lejepa.py` writes its runner into `scripts/` on every run, and the runner is gitignored.
  - `test_a_generated_runner_names_its_launcher_and_stays_out_of_git` checks that it is ignored and untracked.
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-22_SUITE_GUARD_LAUNCHED_SCRIPTS.md` records it.

## Verified, no change needed

- **Every test in `tests/`, with the locked packages, on main:** 4408 passed, 98 skipped and 1 xfailed, with 19
  failures and 19 errors.
  - These are #182's 20 failures less the LeJEPA discovery test, which no longer depends on the machine's data.
  - Every one has the environmental cause the 2026-10-22 suite-guard review tabled.
- **The noise probe's temporary directories** are removed after each trial, in a `finally` (`f1_noise_probe.py`).
- **The loop's code has one silent broad `except`.** It is in `vesuvius_loader._cupy()`: a CUDA device query that
  fails leaves the ridge filter on the CPU. The CPU and GPU ridge channels are tested to agree, so nothing is lost
  silently.

## Observations for the owner (not changed)

- **`launch_neural_tracing.py` picks a local checkpoint by name, not age.**
  - `_find_neural_tracing_checkpoint` takes the last path in reverse-sorted order. Across two run directories it
    picks the later name, not the newer file.
  - Villa's own resolver, given a directory, takes its highest `ckpt_*.pth` iteration.
  - The repository has no local tracing checkpoint, so the launcher falls back to villa's
    `extrap_displacement_latest`.
- **An explicit `--checkpoint` that does not exist still gives a `ready` marker.** The trace service would fail only
  when it is first asked for a heatmap. The evidence chain does not pass `--checkpoint`.
- **Finding 95 is not yet in `FINDINGS.md` or the October draft.** The owner's finding commits update reports and
  tests, and the draft is folded in separately (`d32a9797` for finding 94).
- **`scripts/probe_skel_dist_validity.py`** also writes histograms to `outputs/skeleton_hists/`. No test runs it.

## Verification

- `pytest tests/test_evaluate_villa_metrics.py`: 4 passed. The checkout's histogram is unchanged.
- The two mutants were run in a scratch worktree, and the unmutated test passes there.
- Ruff 0.9.10 `check` and `format` are clean on both files, which were formatted before.
- VAL149
