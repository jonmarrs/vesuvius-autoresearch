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

- **An explicit `--checkpoint` that resolves to nothing gave a `ready` marker.**
  - Villa's `resolve_checkpoint_path` (`neural_tracing/nets/models.py`) treats a bare name such as
    `extrap_displacement_latest` as a HuggingFace sentinel, and anything else as a path. The path can be a file, or a
    directory holding `ckpt_*.pth`.
  - The trace service loads the model lazily. So with a mistyped or moved path, the marker said `ready: true` and
    the service failed only at the first request that needed the model.
  - **Change:** the launcher now names a blocker when an explicit `--checkpoint` resolves to nothing:
    - a path-like name (one containing `/`, or ending in `.pt` or `.pth`) that does not exist;
    - a directory with no `ckpt_*.pth`.

    A bare name is taken as a sentinel. The launcher does not import villa, so a mistyped sentinel still passes; the
    docstring says so.
  - The evidence chain passes no `--checkpoint`, so its plans are unaffected.
- **Local discovery took the greatest name, not the newest file.**
  - `_find_neural_tracing_checkpoint` returned the first path of a reverse-sorted list.
  - Villa's trainer numbers each run's checkpoints, as `ckpt_000123`. So across two runs it took the run whose
    directory sorts last, not the newest checkpoint: `run_b/ckpt_000900.pth`, written first, over
    `run_a/ckpt_000100.pth`.
  - **Change:** it takes the newest by modification time. This is what `launch_finetune_lejepa.py` does, and what
    the action matrix does for the mutex launcher's runs.
  - Base precedence is kept: `checkpoints/neural_tracing` first, then `checkpoints/rowcol_cond`. So is the preference
    for a `.pth` over a `.pt`.
  - The repository has no local tracing checkpoint, so today the launcher still falls back to
    `extrap_displacement_latest`.
- **Tests** (`tests/test_villa_baselines_launchers.py`, +7, in the standard suite). They load the launcher in-process,
  with its project root and trace service moved to `tmp_path` and `sys.path` restored afterwards.
  - **The newest checkpoint is chosen:**
    - across two run directories whose names sort against their age;
    - with a newer `.pt` beside them, which loses to the `.pth`.
  - **Six explicit checkpoints, run through `main()`.**
    - A sentinel name, an existing file and a directory holding `ckpt_*.pth` give no blocker, and the marker is ready.
    - A missing `.pth`, a missing nested path and an empty directory each give exactly one blocker naming the
      problem, and the marker is not ready.
    - In every case the command passes the checkpoint through unchanged.
- **Mutants.** Each of these fails a new test:
  - the greatest name chosen, not the newest file;
  - a `.pt` ranked with `.pth` files;
  - the explicit checkpoint not checked;
  - a `.pth` name taken as a sentinel;
  - an empty directory accepted;
  - every missing path accepted.

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
  - With `allow_nan=False`, one non-finite metric would fail the run at its last step and lose the whole record.
  - #169 made the orientation-field driver's JSON strict because it is a published record. For `run_result.json`
    that trade is not worth it.

## Observations for the owner (not changed)

- **A mistyped sentinel name still gives a ready marker.**
  - Villa holds the sentinels in `_CHECKPOINT_SENTINELS`: `extrap_displacement_latest` and
    `copy_displacement_latest`.
  - Checking the name against them would mean importing villa's model module, with torch and huggingface_hub, into a
    launcher that otherwise needs neither.

## Verification

- `pytest tests/test_villa_baselines_launchers.py`: 14 passed, 7 of them new. The one failure is gp_winner, which
  needs villa's `multi-task-3d-unet`, absent from this sparse checkout, as on main.
- The mutants above were run in a scratch worktree. Each fails one or more of the new tests.
- Ruff 0.9.10 `check` and `format` are clean on both files, which were formatted before.
- VAL150
