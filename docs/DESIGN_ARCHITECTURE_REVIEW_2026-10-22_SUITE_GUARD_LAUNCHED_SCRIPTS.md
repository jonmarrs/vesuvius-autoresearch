# Design and architecture review — the suite guard did not see scripts run by path

Date: 2026-10-22. Baseline: `dbe725f6` (main after #181).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `tests/test_validation_suite_covers_the_loop.py`, the guard that every test of code the loop runs is in
`scripts/run_validation_tests.py`'s VALIDATION_TESTS, and the scripts the loop's code runs.

Main has not moved since #181. There are no open pull requests. This round covers the 02:12 UTC firing.

## What changed

- **The guard saw only imports.**
  - It finds the loop's code by following import statements from a hand-kept list of entry points.
  - Two entry points also run scripts by path, in a subprocess, and the guard did not follow those:
    - the evidence chain (`run_villa_prize_evidence_chain.py`) runs `scripts/inference/launch_neural_tracing.py`
      for a candidate's tracing plan, when run with `--neural-tracing`;
    - `f1_noise_probe.py` runs `scripts/training/run_noise_probe.py`.
  - On the test side it counted a test only if the test imported loop code. A test that loads a script by path,
    with `spec_from_file_location` or a subprocess, did not count.
- **So one test file of code the loop runs was outside the standard suite: `tests/test_villa_baselines_launchers.py`.**
  - It tests `launch_neural_tracing.py`, which it loads by path and runs. It also tests the three training
    launchers the action matrix names.
  - Its own docstring records what being outside the suite cost:
    - every test in it failed on a path the June reorg moved;
    - one asserted a contract that had changed (318d6b85);
    - nothing reported either until `78638734` (2026-08-26) repaired "three months of red".
  - The noise probe's runner was already covered: its tests are in the suite.
- **The guard now covers both directions.**
  - The two launched scripts are entry points.
  - A test counts as testing loop code if it imports it or names its file (`loop_tests`).
  - `named_scripts` reads a file's string literals for either of these:
    - a repo-relative path;
    - a bare file name under `scripts/`, since the evidence chain builds its launcher's path from parts.

    It ignores glob patterns, names too long to be files, villa/, and paths that resolve outside the repository.
  - **A new test classifies every script the loop's code names by path.**
    - Each must be an entry point, if the code runs it. Otherwise it must be listed in `NAMED_NOT_RUN`, against the
      file that names it (`names_outside`). Thirteen are listed, named by five files:
      - the villa coverage report, the review manifest and the Volume Cartographer readiness report, which name
        viewers and tools;
      - the action matrix, which names the three training launchers and the villa-inference smoke;
      - the lasagna worklist, which writes the crop and structure-tensor commands for a person.
    - None of the five starts any process but `git`.
    - The list is keyed by naming file, so a file that starts to name one of these scripts is caught, even if
      another file already names it. A new launch of `launch_mutex.py` from the evidence chain fails the guard.
    - A pair no longer named fails it too.
  - With these, the guard asks for exactly one more file, `tests/test_villa_baselines_launchers.py`, which is now
    listed.
- **One of that file's tests asserted this machine's data.**
  - `test_launch_finetune_lejepa_uses_submittable_patch_and_finds_pretrain` required both of these, which are
    gitignored:
    - a LeJEPA checkpoint under `checkpoints/lejepa_foundation_v1*/`;
    - the labeled `local_data/PHercParis2Fr47/`.
  - The standard suite runs without data ("This suite uses a local Zarr fixture by default", README).
  - The test now checks each against the machine, with the launcher's own patterns:
    - a `*_final.pth` or `*_epoch*.pth` checkpoint;
    - a `surface_volume/` with `inklabels.png`.
  - It asserts that the marker:
    - finds each exactly when it is there;
    - names it as a blocker exactly when it is not;
    - is ready exactly when both are.
  - Where both are present, that is the old assertion. Where they are not, the test now checks the blockers
    instead of failing.
- **Tests of the guard** (+3). They run on a temporary repository, so they do not depend on what this checkout
  holds:
  - the classification;
  - `named_scripts` on several cases:
    - a repo path;
    - a path from parts;
    - a glob;
    - a missing name;
    - a villa file;
    - `..` and absolute paths outside the repository;
    - an over-long name;
  - the selection of tests and of named scripts.
- **Mutants.** Each of these fails a guard or launcher test, against a worktree without villa:
  - in the entry points and the suite list:
    - the two launched scripts dropped from the entry points;
    - the launcher tests unlisted;
  - in `named_scripts`:
    - bare file names ignored;
    - villa files counted;
    - paths outside the repository followed, or not resolved first;
    - any string ending in `.py` taken as a name;
    - an over-long name not caught;
  - in `NAMED_NOT_RUN`:
    - a named pair unlisted, or a stale one listed;
    - the evidence chain also launching `launch_mutex.py`;
  - in the selection:
    - only the entry points' files classified;
    - tests selected by imports alone;
  - in the LeJEPA launcher:
    - the checkpoint or volume blocker dropped;
    - `ready` always true.

## Verified, no change needed

- **No other test of the loop's code is outside the suite.**
  - With the change, the only file the guard asks for is the launcher tests.
  - Every test of the named-only scripts is already listed, apart from the launchers': the crop, structure-tensor,
    Volume Cartographer, villa-inference smoke and sheet-graph tests.
- **Every process start in the loop's code is accounted for.** It runs only:
  - `git` and `pgrep`;
  - `train.py`, `predict.py` and `train_with_new_augs.py`;
  - the noise probe's runner and the tracing launcher;
  - the handoff's literal step paths.

  `patch_catalog.py` and the villa loaders read villa files without running them.
- **Every test in `tests/`, with the locked packages, on main:** 4404 passed, 98 skipped and 1 xfailed, with 20
  failures and 19 errors. The causes are the ones `DESIGN_ARCHITECTURE_REVIEW_2026-10-21_LOOP_FAILURE_PATHS.md`
  tabled:
  - villa files absent from this sparse checkout, among them the launchers' `multi-task-3d-unet`;
  - villa's spiral modules;
  - gitignored local data: the `local_data/` patches and the LeJEPA checkpoint;
  - the owner's `spiral_out` fits;
  - `villa/.git` being a directory here;
  - the doc guard's villa paths.

  None comes from this repository's code. No test changed a tracked file.

## Observations for the owner (not changed)

- **The standard suite here gains one environmental failure.**
  - `test_launch_gp_winner_writes_baseline_marker` needs villa's `segmentation/models/multi-task-3d-unet`, which this
    container's sparse villa checkout lacks.
  - That makes ten villa-file failures here, with the nine already standing.
  - On a full villa checkout it should pass. This review could not run it there.
- **What the scan cannot see.**
  - It reads string literals. A launch through `-m` would go unseen, as would a path split inside a directory name
    (`"scripts" / "inference/x.py"`) or a name computed at run time. None of the loop's launches is built that way
    today.
  - Bare names are looked up under `scripts/` only. So two tests that read `detector/metrics.py` through path parts
    are not counted: `tests/test_metrics_contract_sync.py` and `tests/test_scrollgt_metrics_in_sync.py`.
    - Both are tripwires against a sibling ScrollGT checkout, and both are unlisted.
    - Here five of their seven tests skip.
    - Whether they belong in the loop's suite is the owner's call.
  - The scan also over-matches a little.
    - A bare `"config.py"` or `"__init__.py"` names the one file of that name under `scripts/`.
    - A test that only reads a loop script's text counts as testing it. Today that adds only
      `tests/test_noise_probe_v3_pooled_report.py`, which reads train.py's comments and is listed anyway.
- **The launcher tests generate runners under `scripts/`.**
  - `_finetune_lejepa_runner.py` is written on every suite run.
  - `_gp_winner_runner.py` is written only where villa's `multi-task-3d-unet` is present.
  - Both are ignored, and a test asserts it.

## Verification

- `pytest tests/test_validation_suite_covers_the_loop.py tests/test_villa_baselines_launchers.py`: 14 passed. The
  one failure is gp_winner, without `multi-task-3d-unet`.
  - The guard's 7 tests pass, 3 of them new.
  - Of the launcher tests, 7 pass.
  - On main the guard's 4 passed, and the launcher file failed gp_winner and the LeJEPA discovery.
- The mutants above each fail a test, in a worktree without villa: the guard's 7 pass there, and the launcher file
  fails 3 for want of villa.
- Ruff 0.9.10 `check` and `format` are clean on the three changed files, which were formatted before. `mypy` is
  clean on them.
- VAL148
- **Independent review** of the first commit (`5563038a`), in a worktree without villa or ScrollGT. It found
  nothing blocking.
  - **It confirmed:**
    - both launches;
    - that the launcher tests were outside the suite and invisible to the old guard;
    - that the thirteen are only named;
    - every process start in the loop's code;
    - the history claims, the mutant list and the gp_winner cause.
  - **Its should-fix finding:** the named-only list was one flat set, so a file starting to run a script another
    file already named would go unseen. A new launch of `launch_mutex.py` from the evidence chain passed. The list
    is now keyed by naming file.
  - **Its nits:**
    - the path shapes the scan misses, and the two metrics tripwires;
    - the over-matching;
    - guard tests that depended on this checkout's villa, or missed a dropped `resolve()`, a classification of the
      entry points' files only, or a selection by imports alone;
    - the opportunity plan credited with naming scripts it does not;
    - a LeJEPA skip looser than the launcher's checks, and all-or-nothing;
    - a crash on an over-long name;
    - three wordings in this doc: the LeJEPA data called villa's, the opt-in `--neural-tracing`, and the gp runner.
  - The guard tests now run on a temporary repository, and the LeJEPA test asserts both ways instead of skipping.
    The other nits are fixed above. The path shapes and the tripwires are recorded as observations.
