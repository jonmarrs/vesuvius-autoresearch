# Design and architecture review — operator scripts that act on the loop's checkout

Date: 2026-10-15. Baseline: `20d56885` (main after #71). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the scripts in `scripts/` that act on the same checkout as the running loop. They write `best_model.pt`,
`config.json` or the loop's logs, run git, or stop processes. They were found by searching for `pkill`,
`git commit`/`git push`, and writes to `best_model.pt`. The ones looked at:
- `transition_to_night_shift.py`
- `commit_divs.sh`
- `update_script.py`
- `ablate_scroll_augmentations.py`, with its wrapper `train_with_new_augs.py`
- `reevaluate_best_model.py` and `f1_noise_probe.py`, which earlier reviews covered

## What changed

- **Three dead scripts are removed** (git history keeps them):
  - `scripts/transition_to_night_shift.py`
  - `scripts/commit_divs.sh`
  - `scripts/update_script.py`
- **The augmentation ablation runs its cells as experiment runs.**
  - Each cell sets `checkpoint_out`, so it writes none of the loop's files.
  - The `best_model.pt` backup and restore is gone; nothing writes the incumbent any more.
  - The harness holds this checkout's lock (`autoresearch.lock`) for the whole ablation, as the noise probe does.
    It refuses to start beside the loop, and neither the watchdog nor `start.sh` can start the loop under it.
    `loop_control` recognises it, so `./stop.sh` stops it; the cell in flight ends and the runs so far are written.
  - Each cell runs in its own process group (`ProcessSupervisor`), so a timeout ends the trainer, not just
    `uv run`.
  - It clears `run_result.json` before each run, and removes each run's checkpoints (with any `.step<N>.pt`).

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **`transition_to_night_shift.py` would stop every loop and training run on the host.** It is from 2026-04-08, before the loop detected its shift itself. It rewrites `run_autoresearch_loop.py`'s source by string replacement (none of its patterns exist any more) and commits and pushes `main`. Then it runs `pkill -f run_autoresearch_loop.py` and `pkill -f train.py`, which match any such process on the machine: sibling checkouts' loops, manual training, the noise probe. Finally it starts a loop with a bare `&`, bypassing `start.sh`. Nothing references it. | Removed. |
| P3 | **`commit_divs.sh` would commit the operator's staged work under a data message, and push it.** It `git add`s eleven ~1 GB `local_data/` division datasets, then runs `git commit -m "Add 11x 1GB …"` and `git push` as separate commands. `local_data/` is ignored, so the adds fail, and the commit takes whatever else is staged. No such commit exists in history. Nothing references it. | Removed. |
| P3 | **`update_script.py` rewrites `train.py` in the working directory by regex.** It is from 2026-03-24 and replaces `TrainConfig`, the data loaders and the summary with March's code. From the repository root it fails (no `train.py` there since the move to `scripts/training/`); run from `scripts/training/` it would overwrite the training code. Nothing references it. | Removed. |
| P2 | **The augmentation ablation trained in the loop's place, and could undo the loop's promotion.** `ablate_scroll_augmentations.py` runs each (condition, seed) through `train.train` with the main checkout's `config.json` and no `checkpoint_out`, with prize gates off. Each run is therefore a loop cycle as far as `train.py` knows: it writes `last_model.pt` and `history.tsv`, and on an "improvement" it writes `best_model.pt` and rows in `results.tsv` and `prize_readiness.tsv`. The harness copied a backup of `best_model.pt` back before each run and at the end, but the rows stayed. Its docstring asked for the loop to be stopped but nothing checked. Alongside a running loop, its final copy-back would put the old incumbent back over a promotion the loop had made and committed meanwhile, and the two would share `run_result.json`. | Each cell is an experiment run (`checkpoint_out` under `reports/ablation_logs/`, removed after its metrics are read). `train.save_cycle_checkpoints` then writes only that file and leaves every loop file alone. Every cell warm-starts from the same untouched incumbent, so the backup and restore are gone. The harness holds the checkout's lock for the whole ablation and clears `run_result.json` before each run. Tests: two cells run as experiment runs, each without the previous cell's result and under the lock, and leave no checkpoint or backup; beside a lock holder (the loop, or an unidentified process) the harness refuses and runs nothing. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The loop check was made once, at the start. The watchdog restarts a loop that is down but not paused (a shift's end, a crash), so it could start the loop mid-ablation. The two would then share the GPU, and each could delete or read the other's `run_result.json`. The loop could even promote `config.json` on a cell's `is_success`. | Fixed: the harness holds `autoresearch.lock` until it ends. `loop_control` names it, so `status` reports it and `./stop.sh` stops it (SIGTERM ends the cell in flight; the CSV keeps the runs so far). Tests: the lock is held during each cell and released at the end; a stop ends the ablation between cells. |
| A timed-out cell's trainer kept running: `subprocess.run`'s timeout killed only `uv run`. The trainer held the GPU through later cells and wrote its checkpoint and `run_result.json` after the harness had moved on. Reproduced with a launcher whose child sleeps. Predates the PR. | Fixed: cells run under `ProcessSupervisor`, which kills the whole group. Test: the launcher's child is gone after the timeout (with the old call it is still running). |
| With `eval_every_steps` above 0 a cell leaves `<run>.pt.step<N>.pt`, a full state dict each. Production has 0. | Removed with the cell's checkpoint. Tested. |
| A `PermissionError` from the lock check escaped as a traceback, and the message called a noise probe "the loop". | `OSError` is caught; the message says "autoresearch work" and names the PID, or why it is unidentified. Tested. |
| The test's "leaves `best_model.pt` untouched" also passed on the old script, whose restore wrote the same bytes. Nothing checked that `train()` writes the loop's logs only outside an experiment run, or that the result is cleared before every cell, not just the first. | The test now writes a result in every cell and checks the next cell starts without it. A source test checks that each of `train()`'s three `append_tsv_row` calls is under `not checkpoint_out` or `promoted`, and that `promoted` is `is_improvement and not ckpt_out`. |
| `scripts/update_script.py` is the same kind of dead source rewrite. | Removed. |
| `import shutil` was unused. | Removed. |
| Cells log to the loop's W&B project as `autoresearch_cycle` runs. | Recorded below. |

## Observations for the owner (not changed)

- **Ablation cells log to the loop's W&B project.** `config.json` has `use_wandb: true`, so each cell is logged as
  an `autoresearch_cycle` run; only its `checkpoint_out` tells it apart. As before this PR. Setting `use_wandb`
  off in `_build_condition_config`, or a run group, would separate them, but it changes what the ablation records.

- **The ablation still reports `val_bpb`.** It was written in May, when `val_bpb` was the loop's metric. Promotion
  now uses `val_f1` with an AP-lift gate. `run_result.json` has both, so switching the summary is a small change,
  but it changes what the ablation measures.
- **`reevaluate_best_model.py --update-stored`** rewrites `best_model.pt` atomically. The 2026-10-12 runbook
  runs it with the loop stopped, and since #69 a stop settles the cycle first, so a re-score made then is kept.
  Nothing checks that the loop is stopped; that is left to a review of its own.
- **`f1_noise_probe.py`** works in its own workspace copies (2026-10-13 repeatability review).

## Reviewed and sound

- **`train_with_new_augs.py`** only seeds, patches the scroll augmentations in and calls `train.train`. With
  `checkpoint_out` set by the harness, it inherits the experiment-run isolation.
- **No other script in `scripts/`** (outside `archive/`) stops processes, commits, pushes, or writes
  `best_model.pt`.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #71's head, whose tree is `20d56885`'s.

- Baseline: 42 failed, 2130 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2132 passed, 15 skipped, 1 xfailed, 2 errors. The failures, errors and skips are the same
  sets as the baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files: clean.

New tests in `tests/test_ablation_harness_isolation.py`, now in `scripts/run_validation_tests.py`:
- the ablation leaves the loop's files alone: experiment runs, no stale result, the lock held throughout, no
  checkpoint or backup left;
- the ablation will not run beside other work holding the lock (the loop, or an unidentified process);
- a stop ends the ablation between its cells, releases the lock and writes the runs so far;
- a timed-out cell ends its trainer too;
- `train()` writes the loop's logs only outside an experiment run (on its source).

Not verified here: an ablation on the GPU host.
