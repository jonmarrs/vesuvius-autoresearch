# Design and architecture review — what `stop.sh` and `status` see

Date: 2026-10-15. Baseline: `bc01631d` (main after #81). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/loop_control.py` (behind `stop.sh`, `start.sh` and the watchdog), set against what the loop's start
checks since #81. #81 made the loop refuse to start beside a training run that no loop supervises: a run a killed
loop left going in its own session. Its review recorded that the operator's tools did not know about such runs, and
that the ablation's cell, the other supervised training script run in the checkout, was not looked for.

## What changed

- **The detection lives in `loop_control.unsupervised_runs(repo, supervisor=None)`**, shared by the loop's start,
  `status` and `stop`.
  - It covers the ablation's cell script (`scripts/train_with_new_augs.py`) as well as `train.py` (`RUN_SCRIPTS`).
  - It skips the runs of a live supervisor: those whose session leader is a child of the lock holder.
  - It tells a run a supervisor started (a session leader with a `config_temp*` config) from one started by hand.
- **`status` lists unsupervised runs**, with their age. Its exit code still reports only the lock holder, so the
  watchdog still starts the loop, whose start then refuses, or stops a loop's run past any cycle's timeout (#81).
- **`stop` stops the runs a killed loop or ablation left going**, by their group, after stopping the lock holder,
  and names a run started by hand without stopping it. If such a run does not end within the timeout, `stop`
  reports it and exits 2, with the watchdog paused.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **`stop.sh` reported nothing to stop while an orphaned run trained.** After a loop or ablation was killed without its handler, its run went on in a session of its own. `stop.sh` found no lock holder, printed "No autoresearch work running", and left the run training. That is the case where the operator most needs a stop: the run can still replace `best_model.pt` and write `run_result.json`. #81's message pointed to `kill -TERM -- -<PID>` instead. | `stop` stops such runs by their group and waits for them. Test: an orphaned loop run and an orphaned ablation cell are stopped (SIGTERM); a run started by hand is named and left alone; the watchdog is paused. Fails on main. |
| P3 | **An orphaned ablation cell was not looked for.** Its script is `scripts/train_with_new_augs.py`, which runs in the checkout and writes `run_result.json` there. A loop started beside it could read that file as its own run's result if its own run wrote none. | `RUN_SCRIPTS` includes it. The same test covers it. |
| — | **`status` did not show such runs.** | It lists them. Test: listed with no holder; a live loop's own run is not listed (its session leader is the holder's child). |
| P3 | **A loop's run was reported as two, one "started by hand" (review of this change).** A real run is `uv run python …`: uv leads the session and its python child carries the same arguments. `stop` named the child "not stopping: … (started by hand)", then stopped it with its group; the loop's start named it the same way. | A run's own processes (a listed run's children) are part of it. Test: a leader with a same-argument child is listed once, as a loop's run, and both end. Failed before. |
| P3 | **A run whose session leader had died was not seen (review of this change).** Reading the leader's `/proc` entry failed for uv killed alone, and the run was skipped; main's check saw it. | Listed, as not started by a supervisor. Test: the child of a killed leader is listed. Failed before. |

## Observations for the owner (not changed)

- **`status`'s exit code ignores unsupervised runs.** Exit 1 (nothing holds the lock) is what makes the watchdog
  start the loop. Reporting an orphan as running (exit 0) would stop the watchdog from starting it, and so the
  start from ever stopping a loop's run past its timeout. The loop's start makes that decision instead.
- **A run started by hand is never stopped by these tools.** It writes the same files, so the loop does not start
  beside it, but it is the operator's.
- **The noise probe's trials** run in their own directories and are never matched.

## Reviewed and sound

- **A live holder's runs are its own.** The loop's run is `uv` (session leader, child of the loop's Python process,
  which holds the lock) and its Python child; the ablation's cell is the same under the ablation. `status` and
  `stop` pass the holder's PID, and skip runs whose session leader it is the parent of.
- **`stop` stops the holder first.** Its handler kills its own run, so what is left afterwards is only what an
  earlier kill orphaned.
- **The loop's start** passes no supervisor: it holds the lock and has started nothing yet.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #81's head, whose tree is `bc01631d`'s.

- Baseline: 42 failed, 2170 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2172 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on `loop_control` and the loop: clean.

New tests in `tests/test_loop_lifecycle.py`:
- `test_stop_ends_what_a_killed_loop_or_ablation_left_running` (fails on main);
- `test_status_does_not_count_the_running_loops_own_run` (a guard for the new listing).
- `test_a_runs_python_child_is_that_run_not_one_started_by_hand` and
  `test_a_run_whose_session_leader_died_is_still_seen` (both failed before the review's fix).

Not verified here: `stop.sh` on the GPU host after a real kill.
