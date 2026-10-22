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
      for each candidate's tracing plan;
    - `f1_noise_probe.py` runs `scripts/training/run_noise_probe.py`.
  - On the test side it counted a test only if the test imported loop code. A test that loads a script by path,
    with `spec_from_file_location` or a subprocess, did not count.
- **So one test file of code the loop runs was outside the standard suite: `tests/test_villa_baselines_launchers.py`.**
  - It tests `launch_neural_tracing.py`, which it loads by path and runs. It also tests the three training
    launchers the action matrix names.
  - Its own docstring records what being outside the suite cost. Every test in it failed on a path the June reorg
    moved, and one asserted a contract that had changed (318d6b85). Nothing reported either until `78638734`
    (2026-08-26) repaired "three months of red".
  - The noise probe's runner was already covered: its tests are in the suite.
- **The guard now covers both directions.**
  - The two launched scripts are entry points.
  - A test counts as testing loop code if it imports it or names its file. `named_scripts` reads a file's string
    literals for a repo-relative path, or a bare file name under `scripts/`, since the evidence chain builds its
    launcher's path from parts. Glob patterns, villa/, and paths outside the repository are ignored.
  - **A new test classifies every script the loop's code names by path.** Each must be an entry point, if the code
    runs it, or listed in `NAMED_NOT_RUN`.
    - The thirteen listed are ones the code only describes or writes into a command for a person:
      - the villa coverage report, the opportunity plan, the review manifest and the Volume Cartographer
        readiness report name viewers and tools;
      - the action matrix names the three training launchers;
      - the lasagna worklist writes the crop and structure-tensor commands.
    - None of the files that name them runs anything but `git`.
    - A script the loop's code starts to run by path now fails the guard until it is classified. A stale entry
      fails it too.
  - With these, the guard asks for exactly one more file, `tests/test_villa_baselines_launchers.py`, which is now
    listed.
- **One of that file's tests asserted this machine's data.**
  - `test_launch_finetune_lejepa_uses_submittable_patch_and_finds_pretrain` required a LeJEPA checkpoint under
    `checkpoints/lejepa_foundation_v1*/` and `local_data/PHercParis2Fr47/`. Both are gitignored.
  - The standard suite runs without data ("This suite uses a local Zarr fixture by default", README).
  - The test now checks the patch, the submittability and the marker everywhere. It skips the discovery assertions
    when either is absent, saying why, as the neural-tracing test in the same file already skips on machine state.
  - Where both are present, it asserts exactly as before.
- **Tests of the guard** (+2): one for the classification, and a unit test of `named_scripts`. The unit test covers:
  - a repo path;
  - a path built from parts;
  - a glob pattern;
  - a missing name;
  - a villa file;
  - an existing file outside the repository.
- **Mutants.** Each of these fails a guard test:
  - the two launched scripts dropped from the entry points;
  - the launcher tests unlisted;
  - bare file names ignored;
  - villa files counted (in a checkout with villa, as here and on the owner's machine);
  - paths outside the repository followed;
  - a named script unlisted, or a stale one listed;
  - any string ending in `.py` taken as a name.

  One survives: the main test selecting tests by imports alone, with the launcher tests listed anyway. The guard
  cannot test its own selection.

## Verified, no change needed

- **No other test of the loop's code is outside the suite.** With the change, the only file the guard asks for is
  the launcher tests. Every test of the named-only scripts is already listed (the crop, structure-tensor, Volume
  Cartographer, villa-inference smoke and sheet-graph tests), apart from the launchers'.
- **Every test in `tests/`, with the locked packages, on main:** 4404 passed, 98 skipped and 1 xfailed, with 20
  failures and 19 errors. The causes are the ones `DESIGN_ARCHITECTURE_REVIEW_2026-10-21_LOOP_FAILURE_PATHS.md`
  tabled:
  - villa files absent from this sparse checkout (including the two launcher failures, `multi-task-3d-unet` and
    the LeJEPA data);
  - villa's spiral modules;
  - `local_data/` patches;
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
- **The guard reads literals.** A script launched under a name the code computes, from an f-string or a variable
  built at run time, would still go unseen. None of the loop's launches is built that way today.
- **The launcher tests generate two runners under `scripts/`**, `_gp_winner_runner.py` and
  `_finetune_lejepa_runner.py`. Both are ignored, and a test asserts it. They are now written on every suite run.

## Verification

- `pytest tests/test_validation_suite_covers_the_loop.py tests/test_villa_baselines_launchers.py`: the guard's 6
  pass (2 new). Of the launcher tests, 6 pass, 1 skips (the LeJEPA discovery, without data) and 1 fails (gp_winner,
  without `multi-task-3d-unet`). On main the guard's 4 passed, and the launcher file failed the same two tests.
- Ruff 0.9.10 `check` and `format` are clean on the three changed files, which were formatted before.
- VAL147
