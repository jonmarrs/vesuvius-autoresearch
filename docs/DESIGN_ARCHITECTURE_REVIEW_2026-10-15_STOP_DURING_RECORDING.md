# Design and architecture review — a stop while the loop records a cycle

Date: 2026-10-15. Baseline: `b6010943` (main after #76). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what `run_autoresearch_loop.py` does when `./stop.sh` (SIGTERM) or Ctrl-C (SIGINT) arrives at each point of a
cycle. The handler is `signal_handler`. A stop comes from `scripts/loop_control.py stop`, which signals the loop's
PID only and waits 20 s for the lock.

| A stop arriving | What happens | Since |
| --- | --- | --- |
| during the preflight or training run | the supervisor kills the run's process group, the cycle is settled as failed, the loop exits | #69 |
| during the benchmark (every fifth cycle) | the supervisor kills it; the cycle is already recorded; the loop exits | — |
| between cycles | the loop exits | — |
| after the run, while the cycle is recorded | **the loop exited wherever it was** (this review) | — |

The fourth row runs from the moment the run returns to the cycle's stdout lines. In order:
- reading `run_result.json` (or, on a crash, `run.log`);
- `settle_incumbent`;
- the family decay (`save_history`);
- `config.json`'s promotion (`os.rename`);
- the promotion commit (`git add`, then `git commit` with the pre-commit hooks: seconds);
- the cycle's sprint-log entry.

## What changed

- **A stop while a cycle is recorded waits for it.** `STOP_DEFERRED` is set when the run returns and cleared once
  the cycle's entry and stdout lines are written. A stop in that span is noted ("Stopping once this cycle is
  recorded"; a repeated stop, "Still recording this cycle") and handled when the span ends. The loop then exits as
  before, before the benchmark or the next cycle.
- **Outside that span the handler is unchanged.** A stop during a run still kills it at once, and the cycle is
  settled.
- **`_run_git` runs git in a process group of its own, and its waits are bounded.** On its 300 s timeout it sends
  SIGTERM to the group, git's hooks included, and SIGKILL 30 s later. It stops waiting for the output pipes 10 s
  after that. A terminal's Ctrl-C no longer reaches git or its hooks.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A stop while a cycle was recorded left it half recorded.** The handler raised `SystemExit` wherever the main thread was. During `commit_promotion` that is inside `communicate()` on `git add` or `git commit`. git itself, which `loop_control` does not signal, was left to finish or fail on its own, its output pipes closed. Reproduced with main's loop: a stop during a slow `git add` left `config.json`, `best_model.pt` and `autoresearch_history.json` staged but never committed, which the operator's next commit would take in (#70 prevents this for a failed commit). A stop during a hook that prints aborted the commit (SIGPIPE) with the files staged; during a silent hook the commit was made. Either way the cycle had no sprint-log entry. A stop between the run's clean exit and the settle settled the run as failed: its model moved aside and its rows removed. A stop during an unpromoted cycle's recording lost its family decay or its entry. | `signal_handler` defers while `STOP_DEFERRED` is set, from the run's end; the cycle handles the stop once it is recorded. Tests: a stop during a promotion's commit lets the commit and the `(SUCCESS)` entry complete, then stops before a second cycle; a stop just after a clean run keeps the promotion; a stop while an unpromoted cycle is recorded keeps its decay and its `(REVERTED)` entry; a real SIGTERM during a real commit with a printing hook is deferred and the commit is made. The first three fail on main. |
| P3 | **A hung git hook could hold the loop indefinitely.** On a timeout, `_run_git` signalled git's PID only. git's hooks run in the loop's process group, not git's, so a hook outlived git and kept the output pipes open, and the final `communicate()` had no timeout. Before this PR a stop still ended the loop there; with the deferral it would have waited behind it for good. | git runs in a session of its own; the timeout signals the whole group, and the last wait is bounded. Test: a hook that `exec`s a long `sleep` is ended within seconds and leaves no lock. (With the previous code the test hangs until killed.) |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The deferral turned `_run_git`'s unbounded wait (a hook holding the pipes) into a stop that never took effect. Reproduced with a hook running `sleep`. | Fixed: git's process group is signalled and every wait is bounded. Tested. |
| The span began at the settle, so a stop between a clean run's end and the settle still settled it as failed. That window includes the supervisor's clean-up of the run's group (up to 5 s if workers outlive the leader), not only reading the result. | Fixed: the span begins when the run returns. Tested. |
| A Ctrl-C in a foreground run also reached git and its hooks, which shared the loop's process group, and failed the commit. | Fixed by git's own session. Under `start.sh` and the watchdog there is no terminal. |
| The doc misstated the hung-commit bound, said a SIGKILL of the loop could leave `index.lock`, and said a stop during the benchmark settles the cycle. | Corrected below. |
| Test 2 could not observe the decay: the `lr` weight sat at its floor of 1. | It starts at 2.0 and is checked at 1.9. |
| The tests called the handler directly, never through a delivered signal. | A test sends a real SIGTERM during a real commit. |
| A repeated stop printed nothing. | It prints "Still recording this cycle". |
| `try/finally` around the span; `exit_description` for a git killed by a signal; cooperative cancellation. | Recorded below. |

## Observations for the owner (not changed)

- **A slow commit delays a stop.** Each git call is bounded: 300 s, then SIGTERM, then SIGKILL 30 s later, then
  10 s more for the pipes. A promotion makes two calls (three on a failed commit). `loop_control stop` waits 20 s,
  then reports that the loop did not stop and leaves the watchdog paused; the loop stops once the cycle is
  recorded. A normal commit takes seconds. Only a SIGKILL of git itself, at its timeout, leaves `.git/index.lock`.
- **SIGKILL of the loop cannot be deferred.** It kills the loop's PID only; git, now in its own group, runs on
  unsupervised to the same end a stop used to have.
- **An exception inside the span leaves `STOP_DEFERRED` set.** It also ends `main()`, and the process exits, so
  nothing reads the flag again; `main()` clears it at start. A `try/finally` would matter only to an in-process
  caller.
- **A stop during the supervisor's clean-up of a run** (before it returns) still raises inside
  `ProcessSupervisor.stop`'s wait, which can skip its SIGKILL step. That predates this PR.
- **A git killed by a signal** is reported as "exited -15"; `exit_description` would name the signal.
- **A follow-up design:** cooperative cancellation. The handler would kill the supervised group and set a flag, and
  the loop would record the stopped cycle and exit at checkpoints. Mid-run stops would then get a sprint-log entry
  too, and the settle could leave the handler.

## Reviewed and sound

- **The deferral cannot be skipped by control flow.** No `continue`, `break` or `return` lies in the span, and
  `main()` clears the flag at start.
- **The re-dispatch at the span's end** finds no supervised run and `CYCLE_HOLD` already cleared by the settle, so
  it only exits: no second settle, no benchmark.
- **A deferral flag, not a signal mask.** A blocked mask is inherited by children: git would then ignore the SIGTERM
  sent at its timeout and fall through to SIGKILL, leaving `index.lock`.
- **A stop during a run is not deferred**: the flag is set only after the supervisor returns.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #76's head, whose tree is `b6010943`'s.

- Baseline: 42 failed, 2146 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2151 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 5 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_a_stop_during_a_promotions_commit_waits_for_the_cycle_to_be_recorded` (fails on main);
- `test_a_stop_just_after_a_clean_run_does_not_discard_it` (fails on main and on this PR's first head);
- `test_a_stop_while_a_cycle_is_recorded_keeps_its_entry` (fails on main);
- `test_a_stop_delivered_during_a_real_commit_waits_for_it` (a real signal and a real commit);
- `test_a_hung_hook_does_not_hold_up_the_loop` (hangs with the previous `_run_git`).

Not verified here: a stop on the GPU host during a real commit with its installed hooks.
