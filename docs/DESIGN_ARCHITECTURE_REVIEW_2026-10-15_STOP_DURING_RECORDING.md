# Design and architecture review — a stop while the loop records a cycle

Date: 2026-10-15. Baseline: `b6010943` (main after #76). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what `run_autoresearch_loop.py` does when `./stop.sh` (SIGTERM) or Ctrl-C (SIGINT) arrives at each point of a
cycle. The handler is `signal_handler`; the stop's caller is `scripts/loop_control.py stop`, which waits 20 s for
the lock.

| A stop arriving | What happens | Since |
| --- | --- | --- |
| during the preflight, training or benchmark run | the supervisor kills the run's process group, the cycle in flight is settled as failed, the loop exits | #69 |
| between cycles | the loop exits | — |
| after the run, while the cycle is recorded | **the loop exited wherever it was** (this review) | — |

The third row covers, in order, from the settle to the cycle's stdout lines:
- `settle_incumbent`;
- the family decay (`save_history`);
- `config.json`'s promotion (`os.rename`);
- the promotion commit (`git add`, then `git commit` with the pre-commit hooks: seconds);
- the cycle's sprint-log entry.

## What changed

- **A stop while a cycle is recorded waits for it.** `STOP_DEFERRED` is set from the settle until the cycle's
  entry and stdout lines are written. A stop in that span is noted ("Stopping once this cycle is recorded") and
  handled when it ends. The loop then exits as before, before the benchmark or the next cycle.
- Outside that span the handler is unchanged: a stop during a run still kills it and settles the cycle.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A stop during a promotion's commit left the promotion half recorded.** The handler called `sys.exit` in the main thread wherever it was. During `commit_promotion` that is inside `communicate()` on `git add` or `git commit`. git itself, which `loop_control` does not signal, is left to finish or fail on its own, its output pipes closed. So a stop during `git add` left `config.json`, `best_model.pt` and `autoresearch_history.json` promoted and staged but never committed: the operator's next commit would take them in, which #70 prevents on a failed commit. A stop during `git commit` left the commit made, or aborted with the files staged, and the cycle without a sprint-log entry either way. A stop between the settle and `config.json`'s rename left the promoted model under the old config. A stop during an unpromoted cycle's recording lost its family decay or its entry. | `signal_handler` defers while `STOP_DEFERRED` is set; the cycle handles the stop once its recording is done. Tests: a stop during a promotion's commit lets the commit and the `(SUCCESS)` entry complete, with `config.json` the tried config and `best_model.pt` the promoted model, and then stops before a second cycle; a stop while an unpromoted cycle is recorded keeps its decay and its `(REVERTED)` entry. Both fail on main (no commit made, no entry). |

## Observations for the owner (not changed)

- **A hung commit delays a stop.** `_run_git` stops a git that runs over 300 s. `loop_control stop` waits 20 s, then
  reports that the loop did not stop and leaves the watchdog paused; the loop stops when the commit returns. A
  normal commit takes seconds.
- **A stop in the milliseconds between a run's end and its settle** still settles the cycle as failed, as since
  #69. That undoes a run that ended cleanly; the window is the reading of `run_result.json`.
- **A kill (SIGKILL) is not deferred**: nothing can be. During a commit it can leave git's `index.lock`, as any
  kill of git can.

## Reviewed and sound

- **The deferral cannot outlast its span.** No `continue`, `break` or `return` lies between the settle and the
  release, and `main()` clears the flag at start.
- **A stop during a run is not deferred**: the flag is set only after the run returns, so the supervisor still
  kills the run's process group at once.
- **The benchmark** (every fifth cycle, up to 600 s) runs after the release, under the supervisor, so a stop
  during it still ends it at once.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #76's head, whose tree is `b6010943`'s.

- Baseline: 42 failed, 2146 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2148 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py` (both fail on main):
- `test_a_stop_during_a_promotions_commit_waits_for_the_cycle_to_be_recorded`;
- `test_a_stop_while_a_cycle_is_recorded_keeps_its_entry`.

Not verified here: a stop on the GPU host during a real commit with its hooks.
