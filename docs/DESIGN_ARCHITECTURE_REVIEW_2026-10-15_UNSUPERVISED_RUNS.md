# Design and architecture review — a training run the loop no longer supervises

Date: 2026-10-15. Baseline: `81b65726` (main after #80). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what is left behind when `run_autoresearch_loop.py` ends without its signal handler running, and what the
next start does about it. The loop runs each preflight and training run with `ProcessSupervisor`, in a session of
its own: Ctrl-C at a terminal does not reach the run, and `stop.sh` reaches it only through the handler. Today's
earlier reviews made every handled stop end the run (#69, #77, #78, #80). Two ways of ending remain unhandled:
- **SIGKILL**: `kill -9`, the kernel's out-of-memory killer, a supervisor that escalates;
- **SIGHUP**: the terminal closes, or an ssh session drops, when the loop was started in a terminal rather than by
  `start.sh` (which runs it under `nohup`, ignoring SIGHUP).

## What changed

- **The loop does not start beside a training run of this checkout that no loop supervises.** At start, before it
  looks at the incumbent's hold, `unsupervised_runs()` reads `/proc` for processes whose working directory is this
  checkout and whose arguments include `scripts/training/train.py`. If it finds any, it prints "Not starting", with
  their PIDs, the reason and what to do. The watchdog's next tick tries again, so the loop starts once the run has
  ended.
- **A closed terminal stops the loop like `stop.sh`.** SIGHUP goes to the same handler as SIGTERM and SIGINT, unless
  it is ignored (`nohup`, as `start.sh` runs it).
- **`TRAIN_SCRIPT`** names the training script once, for the commands the loop builds and for the check.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A loop killed mid-run left the run going, and its restart ran a cycle beside it.** The run lives in a session of its own, so killing the loop does not end it. It keeps training for up to the cycle's timeout (budget + 300 s), and at its end can replace `best_model.pt`, write `results.tsv` and `prize_readiness.tsv` rows, and write `run_result.json`. The watchdog restarts the loop within minutes. That start found the kill's `.best_model.pt.held` still the same file as `best_model.pt` (the run had not promoted yet), released it, and started a cycle. The two runs then shared the GPU and `run_result.json`, and the old run's promotion landed under the new cycle's hold, where the new cycle's settle could take it for its own run's model. | The start refuses while such a run is going. When it has ended, the hold is settled as before (#69): released if `best_model.pt` is unchanged, otherwise left to the operator. Test: a process that looks like the loop's training run (`scripts/training/train.py --config config_temp.json`, working directory the checkout) keeps the loop from starting and leaves the hold as it was; the same process in another directory does not count; once the run is gone the loop starts and releases the unchanged hold. Fails on main (a cycle is launched). |
| P3 | **A closed terminal killed a loop started in it at once.** Only SIGTERM and SIGINT had the handler, so a SIGHUP took the default action, and its run was left going as above. `start.sh` and the watchdog are not affected (`nohup`). | SIGHUP is handled like a stop unless it is ignored. Test: the loop registers SIGHUP when its disposition is the default, and leaves it alone when it is ignored. The first case fails on main. |

## Observations for the owner (not changed)

- **The check finds the run, but does not stop it.** The run belonged to a cycle that no loop will record. Stopping
  it automatically would be safe for the loop's own runs, but the check cannot tell those from a `train.py` the
  operator started by hand in the checkout, which writes the same files. Waiting is what the hold already does.
  `kill -TERM <PID>` ends it; train.py has no handler, so it stops at once.
- **An orphaned benchmark (`scripts/inference/predict.py`) is not looked for.** It writes only a report figure and
  ends within its 600 s timeout, but holds GPU memory until then.
- **Without `/proc`** (not a supported host) the check finds nothing, and the loop starts as before.
- **A process of another user** whose `/proc` entries cannot be read is skipped.

## Reviewed and sound

- **The order of the start-up checks**: the lock, the pause, then unsupervised runs, then the hold, then the
  incumbent. A run still going could still change `best_model.pt`, so the hold must not be judged before it ends.
- **The loop's own runs are never "unsupervised" while it runs**: the check is made once, at start, before the loop
  launches anything.
- **Runs of the noise probe** work in their own directories, and the ablation's cells run another script; neither
  matches. Both hold the lock anyway, so the loop cannot start beside them.
- **`uv run`** shows the script in both its own arguments and its Python child's. Both PIDs are listed, which is
  right: stopping either ends the run.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #80's head, whose tree is `81b65726`'s.

- Baseline: 42 failed, 2163 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2166 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 3 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_the_loop_will_not_start_beside_a_training_run_it_does_not_supervise` (fails on main);
- `test_a_closed_terminal_stops_the_loop_like_stop_sh` (handled: fails on main; ignored: guards `nohup`).

Not verified here: a SIGKILL of the loop on the GPU host with a real run, and the watchdog's restart after it.
