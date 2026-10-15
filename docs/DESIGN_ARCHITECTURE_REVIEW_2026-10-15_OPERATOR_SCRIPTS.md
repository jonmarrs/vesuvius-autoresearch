# Design and architecture review — operator scripts that act on the loop's checkout

Date: 2026-10-15. Baseline: `20d56885` (main after #71). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the scripts in `scripts/` that act on the same checkout as the running loop. They write `best_model.pt`,
`config.json` or the loop's logs, run git, or stop processes. They were found by searching for `pkill`,
`git commit`/`git push`, and writes to `best_model.pt`. The ones looked at:
- `transition_to_night_shift.py`
- `commit_divs.sh`
- `ablate_scroll_augmentations.py`, with its wrapper `train_with_new_augs.py`
- `reevaluate_best_model.py` and `f1_noise_probe.py`, which earlier reviews covered

## What changed

- **Two dead scripts are removed** (git history keeps them):
  - `scripts/transition_to_night_shift.py`
  - `scripts/commit_divs.sh`
- **The augmentation ablation runs its cells as experiment runs.**
  - Each cell sets `checkpoint_out`, so it writes none of the loop's files.
  - The `best_model.pt` backup and restore is gone; nothing writes the incumbent any more.
  - The harness refuses to start while this checkout's loop runs.
  - It clears `run_result.json` before each run.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **`transition_to_night_shift.py` would stop every loop and training run on the host.** It is from 2026-04-08, before the loop detected its shift itself. It rewrites `run_autoresearch_loop.py`'s source by string replacement (none of its patterns exist any more) and commits and pushes `main`. Then it runs `pkill -f run_autoresearch_loop.py` and `pkill -f train.py`, which match any such process on the machine: sibling checkouts' loops, manual training, the noise probe. Finally it starts a loop with a bare `&`, bypassing `start.sh`. Nothing references it. | Removed. |
| P3 | **`commit_divs.sh` would commit the operator's staged work under a data message, and push it.** It `git add`s eleven ~1 GB `local_data/` division datasets, then runs `git commit -m "Add 11x 1GB …"` and `git push` as separate commands. `local_data/` is ignored, so the adds fail, and the commit takes whatever else is staged. No such commit exists in history. Nothing references it. | Removed. |
| P2 | **The augmentation ablation trained in the loop's place, and could undo the loop's promotion.** `ablate_scroll_augmentations.py` runs each (condition, seed) through `train.train` with the main checkout's `config.json` and no `checkpoint_out`, with prize gates off. Each run is therefore a loop cycle as far as `train.py` knows: it writes `last_model.pt` and `history.tsv`, and on an "improvement" it writes `best_model.pt` and rows in `results.tsv` and `prize_readiness.tsv`. The harness copied a backup of `best_model.pt` back before each run and at the end, but the rows stayed. Its docstring asked for the loop to be stopped but nothing checked. Alongside a running loop, its final copy-back would put the old incumbent back over a promotion the loop had made and committed meanwhile, and the two would share `run_result.json`. | Each cell is an experiment run (`checkpoint_out` under `reports/ablation_logs/`, removed after its metrics are read). `train.save_cycle_checkpoints` then writes only that file and leaves every loop file alone. Every cell warm-starts from the same untouched incumbent, so the backup and restore are gone. The harness refuses to start while `loop_control.running_pid` finds this checkout's loop, and clears `run_result.json` before each run. Tests: two cells leave `best_model.pt` untouched, run as experiment runs, never see the stale result, and leave no checkpoint; with the loop running, the harness refuses and runs nothing. |

## Observations for the owner (not changed)

- **The ablation still reports `val_bpb`.** It was written in May, when `val_bpb` was the loop's metric. Promotion
  now uses `val_f1` with an AP-lift gate. `run_result.json` has both, so switching the summary is a small change,
  but it changes what the ablation measures.
- **`reevaluate_best_model.py --update-stored`** rewrites `best_model.pt` atomically. It is documented as run
  with the loop stopped, and since #69 a stop settles the cycle first, so a re-score made then is kept.
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
- the ablation leaves the loop's files alone (experiment runs, no stale result, no checkpoint left);
- the ablation will not run beside the loop.

Not verified here: an ablation on the GPU host.
