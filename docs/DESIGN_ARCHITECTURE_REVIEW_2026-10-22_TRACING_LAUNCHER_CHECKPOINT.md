# Design and architecture review — the tracing launcher's checkpoint

Date: 2026-10-22. Baseline: `ebf1b89a` (main after #183).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/inference/launch_neural_tracing.py`.
- The evidence chain runs it for a candidate's tracing plan, with `--neural-tracing`.
- Since #182 it is one of the loop's entry points, and its tests are in the standard suite.
- `DESIGN_ARCHITECTURE_REVIEW_2026-10-22_TESTS_WRITE_THE_CHECKOUT.md` recorded two observations about how it chooses a
  checkpoint. This round fixes both.

Main has not moved since #183. There are no open pull requests. This round covers the 04:12, 05:12 and 06:14 UTC
firings.

## What changed

- **A checkpoint that resolves to nothing gave a `ready` marker.**
  - The trace service loads its model lazily, through villa's `resolve_checkpoint_path`
    (`neural_tracing/nets/models.py`). So with a mistyped or moved checkpoint, the marker said `ready: true` and the
    service failed only at the first request that needed the model.
  - **Change:** the launcher now resolves the checkpoint the way villa does, and names a blocker when it cannot load:
    - The text is stripped.
    - A name in villa's `_CHECKPOINT_SENTINELS` (`extrap_displacement_latest`, `copy_displacement_latest`) is a
      HuggingFace sentinel and is passed as it is. The launcher reads the names from the module's source with `ast`,
      because importing it needs torch.
    - Anything else is a path. It must be an existing file, or a directory holding `ckpt_*.pth` directly: villa does
      not look in subdirectories, or at a directory's other `.pth` files.
    - A missing path's blocker lists villa's sentinel names, so a mistyped sentinel shows the right one.
  - **The check covers the fallback too.** With no `--checkpoint` and no local checkpoint, the launcher passes
    `extrap_displacement_latest`. If villa renames it, the launch now blocks.
  - **A path is passed absolute,** so the printed command does not depend on the directory it is run from. A
    sentinel is passed by name.
  - The evidence chain passes no `--checkpoint`, so its plans are unaffected while villa keeps the fallback's name.
- **Local discovery took the greatest name, not the newest file.**
  - `_find_neural_tracing_checkpoint` returned the first path of a reverse-sorted list.
  - Villa's trainer numbers each run's checkpoints, as `ckpt_000123`. So across two runs it took the run whose
    directory sorts last, not the newest checkpoint: `run_b/ckpt_000900.pth`, written first, over
    `run_a/ckpt_000100.pth`.
  - **Change:** it takes the newest by modification time, and of equal times the greatest path. This is what
    `launch_finetune_lejepa.py` does, and what the action matrix does for the mutex launcher's runs.
  - Two orders are kept:
    - **base:** `checkpoints/neural_tracing` first, then `checkpoints/rowcol_cond`;
    - **suffix:** within a base, a `.pth` over a `.pt`.
  - The repository has no local tracing checkpoint, so today the launcher still falls back to
    `extrap_displacement_latest`.
- **A dead line is gone.** The launcher put `villa/vesuvius/src`, relative to the working directory, at the front of
  `sys.path` on import, and imported nothing from it. Loading it in-process left the entry behind.
- **Tests** (`tests/test_villa_baselines_launchers.py`, +19 cases in six functions, in the standard suite).
  - **The setup.** They load the launcher in-process, with its project root, trace service and villa model module
    moved to `tmp_path`.
    - The stand-in model module raises if imported, so the sentinel names are shown to be parsed.
    - Files whose age matters are written a second apart.
  - **Discovery:**
    - the newest checkpoint across two run directories whose names sort against their age;
    - a newer `.pt` beside them, which loses to the `.pth`;
    - a newer directory named like a checkpoint, which is skipped;
    - each base's precedence, even for an older `.pt`;
    - equal times.
  - **Fourteen explicit checkpoints, run through `main()`.**
    - **Ready:**
      - both sentinels, one with surrounding whitespace;
      - a file, by relative name, with whitespace, and by absolute path;
      - a directory holding `ckpt_*.pth`.
    - **Blocked:**
      - a missing `.pth`;
      - a missing nested path;
      - a bare `ckpt_000100`;
      - a mistyped sentinel;
      - three directories: one empty, one holding only `model.pth`, and one holding `ckpt_*.pth` only in a
        subdirectory;
      - blank text.
    - Each case checks what the command passes, the blocker and `ready`.
  - **Sentinels:**
    - A mistyped sentinel's blocker lists villa's names.
    - Without a readable model module, a sentinel becomes a path and is blocked.
    - The fallback blocks once villa's names no longer include it.
    - Villa's own model module holds the fallback's name. The test skips where the module is absent.
- **Mutants.** Each of these 19 fails a new test, in a worktree without villa:
  - **sentinels:**
    - not checked;
    - every bare name taken as one;
    - hard-coded;
    - read by importing the module;
  - **resolution:**
    - the text not stripped;
    - a relative path passed as given;
    - a directory searched recursively;
    - any `.pth` accepted in a directory;
    - an empty directory or a missing path accepted;
    - blank text not caught;
  - **reporting:**
    - the fallback not checked;
    - the blocker not reported;
  - **discovery:**
    - the greatest name chosen;
    - no tie-break;
    - the suffixes pooled;
    - the bases swapped or pooled;
    - directories counted.

## Verified, no change needed

- **The JSON the loop writes.**
  - Of the `json.dump` and `json.dumps` calls in the loop's code, 32 do not pass `allow_nan=False`.
  - Most write reports whose values are counts, paths and flags.
  - The one that can carry a non-finite metric is `train.py`'s `run_result.json`, written as the run's very last
    step.
    - The loop reads it with Python's `json`, which accepts `NaN`.
    - Promotion does not depend on that file's strictness:
      - `train.py` decides promotion before writing it, and refuses a non-finite `val_f1` or AP lift;
      - `promotion.py` refuses an incumbent whose `val_f1` is not finite.
  - **What #169 did.** It made the orientation-field report strict in two steps: it first wrote every non-finite
    number as `null`, then passed `allow_nan=False`.
  - `allow_nan=False` alone would fail the run at its last step on one non-finite metric, and lose the whole
    record. Writing `null` would change what the loop records. Neither is worth it for a file only the loop reads.

## Observations for the owner (not changed)

- **A checkpoint's base outranks its age.** An older `.pt` under `checkpoints/neural_tracing` is chosen over a newer
  `.pth` under `checkpoints/rowcol_cond`. This is the order the launcher had, and is now tested. Whether both bases
  should be searched together is the owner's call.
- **A request can name its own checkpoint.** The trace service's displacement-copy requests fall back to the
  service's checkpoint only when they carry none. The launcher checks only the one it starts the service with.

## Verification

- `pytest tests/test_villa_baselines_launchers.py`: 26 passed, 19 of them new. The one failure is gp_winner, which
  needs villa's `multi-task-3d-unet`, absent from this sparse checkout, as on main.
- `pytest tests/test_validation_suite_covers_the_loop.py`: 7 passed.
- **The mutants above** were run in a scratch worktree without villa. There the file gives 23 passed, 1 skipped, and
  the 3 failures it has without villa. Each mutant fails one or more new tests.
  - The tie-break mutant falls back to the order the directory lists its files in, so whether it is caught depends on
    the filesystem. It was caught here.
- Ruff 0.9.10 `check` and `format` are clean on both files, which were formatted before. `mypy` is clean on the
  launcher.
- **The standard suite** on the first commit (`3f48b15c`), with the locked-package overlay, gave 2783 passed, 22
  skipped and 1 xfailed, with the same ten environmental failures as main. The smoke test gave 9 of 11 passed and 2
  skipped, as on main.
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - **It confirmed:**
    - the launcher tests' results without villa;
    - that the tests write nothing outside their temporary directory;
    - that the evidence chain passes no `--checkpoint`;
    - that discovery's ordering matches the action matrix's choice of the mutex launcher's run.
  - **Its should-fix findings:**
    - every bare name was taken as a sentinel, though villa's names can be read without importing its module, so a
      mistyped sentinel or a bare `ckpt_000100` gave a ready marker;
    - a directory holding only `model.pth`, or `ckpt_*.pth` only in a subdirectory, was untested;
    - a relative path left the command depending on its working directory.
  - **Its nits:**
    - the reasoning given for #169;
    - discovery's base, suffix, file and tie rules untested;
    - ages a nanosecond apart;
    - the dead `sys.path` line.
  - All are addressed above.
