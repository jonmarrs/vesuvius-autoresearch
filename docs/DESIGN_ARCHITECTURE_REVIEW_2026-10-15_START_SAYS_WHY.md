# Design and architecture review — what `start.sh` says beside an orphaned run

Date: 2026-10-15. Baseline: `a94e8832` (main after #84). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the operator's launchers (`start.sh`, `stop.sh`, the watchdog) after today's start refusals (#81 to #83);
- the loop's tweak sampling and its record of recent configs;
- the preflight against the spawned loader workers (#74);
- which runtime files git tracks;
- the dev-worktree helper;
- a scan for name and prefix checks that can never match, the kind of bug #84 fixed.

## What changed

- **`start.sh` says when the loop it launches will not start a cycle.** If `loop_control.py status` lists a training
  run that no loop supervises, `start.sh` still launches the loop. Its start stops a supervised run past any cycle's
  timeout, and the watchdog and a hand start then behave alike. `start.sh` then says that:
  - the loop it launched exits without starting a cycle while such a run goes on, and `autoresearch.out` says why;
  - once the runs end, the watchdog, if installed, starts the loop on its next tick; otherwise run `./start.sh`
    again;
  - `./stop.sh` stops the runs a loop or ablation started but pauses the watchdog, so run `./start.sh` after it;
  - a run started by hand is stopped with `kill -TERM <PID>`.
- **`start.sh` keeps its exit codes.** It exits 1 while work is running and passes on any other code from `status`.
  It now captures `status`'s output to look for such runs, and prints it as before. A test now covers both codes.
- **`watchdog.log` and `run.log` are in the runtime-state test** (`LOOP_RUNTIME_STATE`), beside the lock and the
  other process state. Both were already ignored, by `.gitignore` alone.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **`start.sh` reported a start that did not happen.** Beside an orphaned or hand-started run, it printed the run (from `status`) and then "Autoresearch launcher started". The loop it launched refused at once ("Not starting", #81), and only `autoresearch.out` recorded that. An operator who had just run `start.sh` took the loop for running. The watchdog's `start.sh --watchdog` wrote the same to `watchdog.log` each tick. | `start.sh` says the launched loop exits without a cycle, why, and what to do. Tests: with a fake `uv`, `start.sh` beside an orphaned run says so, and alone it does not (fails on main). With work running it exits 1, and with a lock `status` cannot read it exits 2, launching nothing either way. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The first message ("It will not start a cycle while the run above goes on … The watchdog tries again on its next tick") read as if the loop waits. It exits. On a host without the watchdog's cron entry, nothing starts it later. After `./stop.sh`, which it offered, the watchdog is paused. A supervised run past the timeout has already been stopped by the loop's start. "The run above" stayed singular for several runs. | Reworded, as above. |
| The doc said the runtime-state test holds `watchdog.log`, `run.log` and `results.tsv`; it held none of them. `results.tsv` is a promotion log, not process state. | `watchdog.log` and `run.log` are added to the test. `results.tsv` is recorded below. |
| The doc left out `recent_configs.json`, a tracked file the loop rewrites every cycle. | Recorded below. |
| The exit codes `start.sh` passes on had no test. | Tested. |
| Smaller wording: what "runs out of new configs" means; "a loop's run" where the code stops any supervised run. | Corrected. |

## Observations for the owner (not changed)

- **`recent_configs.json` is tracked, and the loop rewrites it every cycle.**
  - `commit_promotion` commits only `PROMOTION_FILES` (`config.json`, `best_model.pt`, the history), so on the host
    the file always shows as modified. It was last committed on 2026-07-11.
  - A `git checkout -- .`, `git stash` or `git restore .` (which `.gitignore` warns about for the lock) resets the
    loop's dedup memory to that July list.
  - Untracking and ignoring it would make it process state like the others.
- **`recent_configs` is kept in two lengths.** The file holds the last 20 configs, but the list in memory keeps
  every config tried since the loop process started. So the dedup checks everything this process tried, and after a
  restart only the last 20. The list is reset to the current config when 10 samples in a row are all recent.
- **`results.tsv` is ignored, but its sibling promotion log `prize_readiness.tsv` is tracked.** `.gitignore`'s own
  comment ("keep canonical best_model.pt and results.tsv tracked/visible", line 38) says otherwise.
- **A syncing `uv run` in a dev worktree re-points the shared `.venv`.** `scripts/dev_worktree.sh` says so, warns
  that the loop's spawned loader workers would then import the worktree's code, and asks for `UV_NO_SYNC=1`.
  - That warning is broader than needed for a run already under way. This `.venv`'s editable install is a plain
    path entry (`__editable__.vesuvius_autoresearch-0.1.0.pth`), and a spawned worker takes its `sys.path` from the
    training process. So a run's workers import what the run itself imported.
  - Re-pointing reaches the processes started after it. The loop's own next `uv run` points the `.venv` back to the
    main checkout.
  - `UV_NO_SYNC=1` remains the right practice. The reviewer reproduced all of this with a toy project.
- **If the run ends between `status` and the loop's own check,** the loop starts normally although `start.sh` said
  it would not. The window is the `uv run` start-up.

## Reviewed and sound

- **The preflight (`train.py --smoke`)** builds the model and runs one forward and backward pass on a synthetic CPU
  batch. It builds no loader, so the loader workers neither slow it nor count against its 300 s timeout.
- **The runtime files.**
  - `test_loop_runtime_state_is_never_tracked` keeps these untracked and ignored: the lock, the hold
    (`.best_model.pt.held`), the sprint-log pointer, the pause flag, `autoresearch.out`, `watchdog.log`, `run.log`,
    `config_temp.json` and `run_result.json`.
  - `sprint_logs/`, `prize_readiness.tsv` and the benchmark figures are tracked as project records.
- **Name and prefix checks** in the loop, `loop_control`, the trainer, promotion, the probe, the ablation and the
  re-score each compare text written to the same convention. For example, the preflight timeout's "preflight timed
  out" is the start of the failure text written a few lines above.
- **The watchdog** still starts the loop on `status`'s exit code alone; the new message is `start.sh`'s.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `8d44bb5c` (#84), whose tree is `a94e8832`'s but for its review doc's result
  lines. It was 42 failed, 2186 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch, first head: 42 failed, 2187 passed, 15 skipped, 1 xfailed, 2 errors. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Branch, after the PR review's fixes: REVIEW_RESULT
- `bash -n start.sh`: clean. Ruff (check and format) on the test: clean.

New tests in `tests/test_loop_lifecycle.py`, which run the real `start.sh` and `loop_control.py` in a temporary
checkout with a fake `uv` that launches nothing:
- `test_start_sh_says_the_loop_will_not_start_beside_an_orphaned_run` (fails on main);
- `test_start_sh_keeps_its_exit_codes` (work running, an unreadable lock; passes on main too, as a guard).

Not verified here: `start.sh` on the GPU host.
