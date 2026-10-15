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
  looks at the incumbent's hold, `unsupervised_runs()` reads `/proc` for interpreters (`python`, `uv`) working in
  this checkout with its `scripts/training/train.py` among their arguments, by path (relative or absolute). If it
  finds any, it prints "Not starting" with each PID, whether it is a loop's run, how long it has run, and how to
  stop it. The watchdog's next tick tries again, so the loop starts once the run has ended.
- **A loop's own run that has outlived any cycle's timeout is stopped.** The supervisor that enforced the run's
  timeout (budget + 300 s) died with the loop. A loop's run is recognisable: the session leader the supervisor
  started (`uv run python -u scripts/training/train.py --config config_temp.json`). Past the longest cycle's
  timeout (3,900 s), the start sends its group SIGTERM, as the supervisor would have. A run started by hand is
  never stopped.
- **A closed terminal stops the loop.** SIGHUP goes to the same handler as SIGTERM and SIGINT, unless it is ignored
  (`nohup`, as `start.sh` runs it). The handler first moves the loop's output from the closed terminal to
  `autoresearch.out`, where `start.sh` sends it. Unlike `stop.sh`, a hangup does not pause the watchdog.
- **`TRAIN_SCRIPT`** names the training script once, for the commands the loop builds and for the check.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A loop killed mid-run left the run going, and its restart ran a cycle beside it.** The run lives in a session of its own, so killing the loop does not end it, and its timeout died with the loop's supervisor: it trains to the end of its budget, or longer if it hangs. At its end it can replace `best_model.pt`, write `results.tsv` and `prize_readiness.tsv` rows, and write `run_result.json`. The watchdog restarts the loop within minutes. That start found the kill's `.best_model.pt.held` still the same file as `best_model.pt` (the run had not promoted yet), released it, and started a cycle. The two runs then shared the GPU and `run_result.json`, and the old run's promotion landed under the new cycle's hold, where a failed new cycle's settle would take it for its own run's model. | The start refuses while such a run is going, and stops a loop's own run past any cycle's timeout. When the run has ended, the hold is settled as before (#69). Tests: such a run (relative or absolute path) keeps the loop from starting and leaves the hold; one in another directory does not count; once the run is gone the loop starts and releases the unchanged hold; a loop's run past the timeout is stopped, and a run started by hand is not. Fails on main. |
| P3 | **A closed terminal killed a loop started in it at once.** Only SIGTERM and SIGINT had the handler, so a SIGHUP took the default action, and its run was left going as above. `start.sh` and the watchdog are not affected (`nohup`). | SIGHUP is handled like a stop unless ignored, with the output moved off the closed terminal first. Tests: the loop registers SIGHUP unless it is ignored; with a terminal whose writes fail, the handler stops the run and exits 0, and during a cycle's recording it defers, and the recording's output reaches `autoresearch.out`. Fail on main. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| After a hangup, the handler's first message to the closed terminal raised EIO, before it stopped the run or settled the cycle. Reproduced on a pty: the loop exited 1, leaving the hold. During a cycle's recording, the error broke the recording, for example by reporting a commit as failed while git went on. | Fixed: the handler moves the output to `autoresearch.out` first. Tested with a terminal whose writes fail, at rest and during recording. |
| Any process naming the script counted: `tail -f`, an editor or a pager open on `train.py` kept the loop from starting for as long as it was open, and the message said to kill it. A `python /abs/.../train.py` run was missed. | Only interpreters count, and the script is matched by resolved path. Both are tested. |
| The refusal had no bound, and the doc's "up to the cycle's timeout" was wrong: the timeout was the dead supervisor's. A run hung at its end (`wandb.finish()`) would keep the loop down. The doc also said the loop's runs could not be told from a hand-started one; they can, as session leaders. | A loop's own run past the longest cycle's timeout is stopped. The message gives each run's age and the group kill. The doc is corrected. Tested. |
| The message listed `uv` and its child as separate runs, and did not say the watchdog retries. | It names a loop's run, suggests `kill -TERM -- -<PID>` for its group (with the loader workers), and says the watchdog tries again. |
| The doc said "like `stop.sh`", which also pauses the watchdog; the benchmark writes `.npy` files besides its figure; a SIGKILLed ablation's cell is not seen. | Corrected or recorded below. |
| The test's second process started outside its `try`; a PID was checked as a substring; a `None` handler could not be restored. | Fixed. |

## Observations for the owner (not changed)

- **A run started by hand is only waited for.** It writes the same files a loop's run does, so the loop does not
  start beside it, and does not stop it either; the message says how.
- **An orphaned benchmark (`scripts/inference/predict.py`) is not looked for.** It writes a figure and two `.npy`
  arrays beside it, holds GPU memory, and its 600 s timeout also died with the loop.
- **An ablation killed with SIGKILL** releases its lock, and its cell (`scripts/train_with_new_augs.py`) runs on in
  the checkout and writes `run_result.json`. The check does not see it. `loop_control status` and `stop` do not
  report unsupervised runs either; the check could move there.
- **`python -m scripts.training.train`** is not recognised; nothing runs it that way.
- **Without `/proc`** (not a supported host) the check finds nothing, and the loop starts as before. A process of
  another user whose `/proc` entries cannot be read is skipped.

## Reviewed and sound

- **The order of the start-up checks**: the lock, the pause, then unsupervised runs, then the hold, then the
  incumbent. A run still going could still change `best_model.pt`, so the hold must not be judged before it ends.
- **The loop's own runs are never "unsupervised" while it runs**: the check is made once, at start, before the loop
  launches anything.
- **Runs of the noise probe** work in their own directories, and the ablation's cells run another script; neither
  matches. Both hold the lock anyway, so the loop cannot start beside them.
- **`uv run`** spawns its Python child rather than exec'ing it, and both show the script among their arguments, so
  both PIDs are listed; `uv` is the session leader. #74's spawned DataLoader workers do not show it.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #80's head, whose tree is `81b65726`'s.

- Baseline: 42 failed, 2163 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, first head: 42 failed, 2166 passed, 15 skipped, 1 xfailed, 2 errors.
- Branch, after the PR review's fixes: 42 failed, 2170 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 7 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py` (each fails on main, except the `nohup` guard):
- `test_the_loop_will_not_start_beside_a_training_run_it_does_not_supervise`;
- `test_an_editor_on_the_training_script_is_not_a_run` (fails on the first head);
- `test_a_loops_run_past_any_cycles_timeout_is_stopped`;
- `test_a_closed_terminal_stops_the_loop_like_stop_sh` (handled; ignored, which guards `nohup`);
- `test_a_hangup_moves_the_loops_output_off_the_closed_terminal` (at rest; during a cycle's recording).

Not verified here: a SIGKILL of the loop on the GPU host with a real run, and the watchdog's restart after it.
