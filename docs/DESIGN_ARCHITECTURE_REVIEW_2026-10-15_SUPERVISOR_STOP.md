# Design and architecture review — stopping a supervised run twice

Date: 2026-10-15. Baseline: `3a29082e` (main after #77). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/process_supervisor.py`, which runs the loop's preflight, training and benchmark, the noise probe's
trials, the augmentation ablation's cells and the iterative pseudo-labeler's steps, each in a session of its own.
Also the stop paths that call it: the loop's `signal_handler`, and the `KeyboardInterrupt` handlers of the other
callers.

The loop relies on one guarantee of `stop()` (#69): once it returns, the run is dead, so nothing writes
`best_model.pt` after the loop settles it. `stop()` sends SIGTERM to the group, waits up to the grace period (5 s),
sends SIGKILL, and waits for the leader.

## What changed

- **A `stop()` re-entered while a stop is under way kills the group at once and waits for the leader.** This is
  what a signal handler calls during a stop already in progress: a second stop during the first one's grace period,
  or a stop during `run()`'s own clean-up after the leader exits. It used to return at once, with the group alive.
- **An interrupted `stop()` kills the group before the exception propagates.** The handler's `SystemExit`, or a
  `KeyboardInterrupt`, raised inside the grace-period wait used to skip the SIGKILL.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A second stop let a training run outlive the loop and replace `best_model.pt` after the settle.** The loop's handler calls `supervisor.stop()`, then settles the cycle and exits. A second SIGTERM or SIGINT during the first stop's grace period (`./stop.sh` twice, or Ctrl-C twice) re-entered the handler. Its `stop()` found nothing active (the first had cleared it), so it returned at once. The handler then settled with the run still alive, and its `SystemExit` unwound through the first stop's wait, past the SIGKILL. A run that ignores or outlasts SIGTERM then kept going unsupervised, and could replace `best_model.pt` after the settle, with no hold left to catch it: the #69 failure this design exists to prevent. Reproduced: a run that ignores SIGTERM for 3 s and then writes `best_model.pt`; two stops 0.5 s apart; the loop settled on the incumbent and exited, and the run wrote the file 3 s later. | `stop()` records the process it is stopping. A nested call kills that group and waits for its leader before returning, so the handler settles only after the run is dead. The outer stop kills the group if its wait is interrupted. The reproduction now settles and ends with the incumbent, and leaves no process. Test: two stops 0.3 s apart against a run that ignores SIGTERM and writes after 2 s; the run is dead when the handler settles, and nothing is written. Fails on main. |
| P3 | **A stop during `run()`'s clean-up left the run's survivors running.** After the leader exits, `run()` stops what is left of its group (DataLoader workers, a stray child), waiting up to the grace period. A stop in that window found nothing active, and its exit cut the clean-up short before the SIGKILL. A worker that ignores SIGTERM then outlived the loop, holding GPU memory into the next start. | The same: the nested stop kills the group, and so does the interrupted clean-up. Test: a leader exits leaving a worker that ignores SIGTERM; a stop during the clean-up; the worker is gone. Fails on main. |

The other callers benefit too. The noise probe and the ablation turn SIGTERM into `KeyboardInterrupt`, and
`run()` stops the group on the way out. A second signal during that stop now kills the group instead of skipping
the SIGKILL. The pseudo-labeler installs no SIGTERM handler: Ctrl-C reaches `run()`'s clean-up as a
`KeyboardInterrupt`, but a SIGTERM ends it at once and leaves its supervised step running in its own session (see
the observations).

## Observations for the owner (not changed)

- **A stop during `run()`'s clean-up still settles the cycle as failed**, although the run had ended. The deferral
  (#77) starts when `run()` returns, after the clean-up. The clean-up lasts as long as a survivor ignores SIGTERM, up
  to the grace period.
- **A signal between `Popen` returning and `run()` recording the process** finds nothing to stop, and that run would
  outlive the handler. The window is a few bytecodes. Closing it would need the signals blocked around `Popen`, and
  the child would inherit that mask.
- **`scripts/iterative_pseudo_labeling.py` does not handle SIGTERM.** A `kill` ends it without stopping its
  supervised step, which runs on in its own session. It is not registered in `autoresearch.lock`, so `./stop.sh`
  never targets it; turning SIGTERM into `KeyboardInterrupt`, as the probe does, would close this.
- **A process killed while in uninterruptible I/O** finishes that system call first. `best_model.pt` is written by
  `os.replace` from a complete temporary file, so this cannot produce a partial incumbent.

## Reviewed and sound

- **A single stop** behaves as before: SIGTERM to the group, the grace period, SIGKILL, and the leader reaped.
- **The nested wait is bounded.** If the interrupted outer wait holds the process's wait lock, the nested
  `wait(timeout)` times out instead of deadlocking; the SIGKILL has already been sent.
- **`run()`'s contract is unchanged**: a timeout raises `TimeoutExpired` after the group is stopped, and `active`
  is cleared on every exit.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #77's head, whose tree is `3a29082e`'s.

- Baseline: 42 failed, 2151 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2153 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on the supervisor: clean.

New tests in `tests/test_loop_lifecycle.py` (both fail on main; 3 of 3 repeated runs passed):
- `test_a_second_stop_kills_the_run_before_the_loop_settles`;
- `test_a_stop_during_the_runs_clean_up_still_kills_its_survivors`.

Not verified here: a double stop on the GPU host with a real training run.
