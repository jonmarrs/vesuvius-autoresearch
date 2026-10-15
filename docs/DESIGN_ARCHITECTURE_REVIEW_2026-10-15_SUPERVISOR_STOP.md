# Design and architecture review — stopping a supervised run twice

Date: 2026-10-15. Baseline: `3a29082e` (main after #77). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/process_supervisor.py`, which runs the loop's preflight, training and benchmark, the noise probe's
trials, the augmentation ablation's cells and the iterative pseudo-labeler's steps, each in a session of its own.
Also the stop paths that call it: the loop's `signal_handler`, and the `KeyboardInterrupt` handlers of the other
callers.

The loop relies on one guarantee of `stop()` (#69): once it returns, the run is dead, so nothing writes
`best_model.pt` after the loop settles it. `stop()` sends SIGTERM to the group, waits up to the grace period (5 s),
sends SIGKILL, and waits for the leader. The loop's leader is `uv`; `train.py` is its child, in the same group.

## What changed

- **A `stop()` re-entered while a stop is under way kills the group at once.** It SIGKILLs the group, reaps the
  leader, and waits (bounded) for the rest of the group to go. This is what a signal handler calls during a stop
  already in progress: a second stop during the first one's grace period, or a stop during `run()`'s own clean-up
  after the leader exits. It used to return at once, with the group alive.
- **An interrupted `stop()` kills the group before the exception propagates.** The handler's `SystemExit`, or a
  `KeyboardInterrupt`, raised inside the grace-period wait used to skip the SIGKILL.
- **Once SIGKILL is sent, `stop()` no longer raises `TimeoutExpired`** for a leader that is slow to be reaped.
- **The loop's handler handles a repeated stop by killing the run and returning.** The first handler settles once
  and exits.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A second stop let the run outlive the loop, and could let it replace `best_model.pt` after the settle.** The loop's handler calls `supervisor.stop()`, then settles the cycle and exits. A second SIGTERM or SIGINT during the first stop's grace period (`./stop.sh` twice, or Ctrl-C twice) re-entered the handler. Its `stop()` found nothing active (the first had cleared it), so it returned at once. The handler then settled with the run still alive, and its `SystemExit` unwound through the first stop's wait, past the SIGKILL. A group member that ignores or outlasts SIGTERM then kept going unsupervised and, if it writes `best_model.pt`, could replace it after the settle, with no hold left to catch it: the #69 failure this design exists to prevent. Reproduced: a run that ignores SIGTERM for 3 s and then writes `best_model.pt`; two stops 0.5 s apart; the loop settled on the incumbent and exited, and the run wrote the file 3 s later. Latent today: `train.py` installs no SIGTERM handler, so it dies on the first SIGTERM. | `stop()` records the process it is stopping. A nested call kills that group before returning, so the handler acts only after the run is dead. The outer stop kills the group if its wait is interrupted. The reproduction now ends with the incumbent and no process left. Test: two stops against a run that ignores SIGTERM and writes after 2 s; the run is dead when the handler acts, and nothing is written. Fails on main. |
| P3 | **A stop during `run()`'s clean-up left the run's survivors running.** After the leader exits, `run()` stops what is left of its group (DataLoader workers, a stray child), waiting up to the grace period. A stop in that window found nothing active, and its exit cut the clean-up short before the SIGKILL. A worker that ignores SIGTERM then outlived the loop, holding GPU memory into the next start. | The same: the nested stop kills the group, and so does the interrupted clean-up. Test: a leader exits leaving a worker that ignores SIGTERM; a stop lands during the clean-up (checked); the worker is gone. Fails on main. |
| P3 | **The same for the other callers.** The noise probe and the ablation turn SIGTERM into `KeyboardInterrupt` and call no `stop()` from the handler. A second interrupt landing inside `run()`'s stop skipped its SIGKILL. | The interrupted stop kills the group. Test: two interrupts, the second inside `stop()`; the leader that ignores SIGTERM is dead. Fails on main. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The interrupted-stop kill, the only part the other callers use, had no test: deleting it left every test passing. | Tested (two interrupts; the second lands inside `stop()`). |
| The doc called the window between `Popen` and `run()` recording the process "a few bytecodes". It runs from the fork, through the wait for the child's exec, to the assignment: milliseconds. | Corrected below. |
| `_kill` waited for the leader only, and the loop's leader is `uv`: `train.py` could still be exiting when the handler went on. | `_kill` also waits, bounded, until the group is gone. |
| The loop's settle was not re-entrant: a third signal during the nested handler's settle cut it short. | A repeated stop now only kills the run and returns; the first handler settles once. Test: a stop during the settle's row restore leaves the rows restored. Fails on the PR's first head. |
| `TimeoutExpired` from `stop()` (a leader not reaped in time) left `run()`, and the loop booked it as the training timeout and carried on, losing the stop. | Swallowed once SIGKILL is sent. |
| `stopping` was set after `active` was cleared. | Set first. Not a live bug: CPython runs no handler between the two stores. |
| A slow start could let the clean-up test pass on main; the tests' timers were not joined before SIGUSR1's default action was restored. | The test checks that the stop landed during the clean-up; the timers are joined. |
| The P2 rating assumed a reachable path; today's trainer dies on the first SIGTERM. | Rated P3, latent. |

## Observations for the owner (not changed)

- **A stop during `run()`'s clean-up still settles the cycle as failed**, although the run had ended. The deferral
  (#77) starts when `run()` returns, after the clean-up. The clean-up lasts as long as a survivor ignores SIGTERM, up
  to the grace period.
- **A signal between the fork inside `Popen` and `run()` recording the process** finds nothing to stop. The
  handler's `SystemExit` passes through `Popen.__init__`, which closes its pipes but does not kill the child, so that
  run would outlive the handler. The window runs through the wait for the child's exec: milliseconds. Closing it
  would need the signals blocked around `Popen`, and the child would inherit that mask.
- **`_kill`'s wait for the group counts zombies.** An orphan killed after its parent exited stays a zombie until
  init reaps it (about 1.7 s in this container), and `killpg(…, 0)` still finds it. The wait is bounded by the grace
  period (5 s), so a repeated stop may take that long to return.
- **`scripts/iterative_pseudo_labeling.py` does not handle SIGTERM.** A `kill` ends it without stopping its
  supervised step, which runs on in its own session. It is not registered in `autoresearch.lock`, so `./stop.sh`
  never targets it; turning SIGTERM into `KeyboardInterrupt`, as the probe does, would close this.
- **A process killed while in a system call** finishes that call first, and that call can be the `os.replace` of
  `best_model.pt` itself. `save_checkpoint_atomic` replaces it with a complete, fsynced temporary file, so this cannot
  produce a partial incumbent; it can only complete one replacement.

## Reviewed and sound

- **A single stop** behaves as before: SIGTERM to the group, the grace period, SIGKILL, and the leader reaped.
- **The nested wait is bounded.** If the interrupted outer wait holds the process's wait lock, the nested
  `wait(timeout)` times out instead of deadlocking; the SIGKILL has already been sent.
- **`run()`'s contract is unchanged**: a timeout raises `TimeoutExpired` after the group is stopped, and `active`
  and `stopping` are cleared on every exit, so a later `run()` works.
- **The #77 deferral** still re-dispatches a stop held during a cycle's recording as a first stop: it settles
  nothing (the cycle is recorded) and exits.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #77's head, whose tree is `3a29082e`'s.

- Baseline: 42 failed, 2151 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, first head: 42 failed, 2153 passed, 15 skipped, 1 xfailed, 2 errors.
- Branch, after the PR review's fixes: 42 failed, 2155 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) and mypy on the supervisor and the loop: clean.

New tests:
- in `tests/test_loop_lifecycle.py` (each fails on main; the module passed 4 of 4 repeated runs):
  - `test_a_second_stop_kills_the_run_before_the_loop_settles`;
  - `test_a_stop_during_the_runs_clean_up_still_kills_its_survivors`;
  - `test_a_second_interrupt_during_the_stop_kills_the_group`;
- in `tests/test_autoresearch_measurement.py`: `test_a_repeated_stop_does_not_cut_the_settle_short` (fails on main
  and on the first head).

Not verified here: a double stop on the GPU host with a real training run.
