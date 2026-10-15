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

- **`start.sh` says when the loop it launches will not start a cycle.** If `loop_control.py status` lists a training run that no loop supervises, `start.sh` launches the loop as before. That keeps the loop's start, which stops a loop's run past any cycle's timeout. It then says that no cycle starts while that run goes on, and how to stop it.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **`start.sh` reported a start that did not happen.** Beside an orphaned or hand-started run, it printed the run (from `status`) and then "Autoresearch launcher started". The loop it launched refused at once ("Not starting", #81), and only `autoresearch.out` recorded that. An operator who had just run `start.sh` took the loop for running. The watchdog's `start.sh --watchdog` wrote the same to `watchdog.log` each tick. | After launching, `start.sh` adds a line saying that no cycle starts while the listed run goes on. It gives `./stop.sh` for a run a loop or ablation started, and says a run started by hand is the operator's to stop. Test: with a fake `uv`, `start.sh` beside an orphaned run says so, and without one it does not (fails on main). |

## Observations for the owner (not changed)

- **`recent_configs` is kept in two lengths.** The file holds the last 20 configs (`save_recent_configs`), but the
  loop's list in memory keeps every config of the run. So within a run, the dedup checks everything tried so far.
  After a restart it checks only the last 20. The list is reset when sampling runs out of new configs.
- **A syncing `uv run` in a dev worktree re-points the shared `.venv`.** `scripts/dev_worktree.sh` says so, warns
  that the loop's spawned loader workers would then import the worktree's code, and asks for `UV_NO_SYNC=1`.
  - That warning is broader than needed for a run already under way. This `.venv`'s editable install is a plain
    path entry (`__editable__.vesuvius_autoresearch-0.1.0.pth`), and a spawned worker takes its `sys.path` from the
    training process. So a run's workers import what the run itself imported.
  - Re-pointing reaches the processes started after it. The loop's own next `uv run` points the `.venv` back to the
    main checkout.
  - `UV_NO_SYNC=1` remains the right practice.
- **`start.sh` still launches the loop beside such a run.** That is so the loop's start can stop a loop's run past
  any cycle's timeout, and so the watchdog and a hand start behave alike.

## Reviewed and sound

- **The preflight (`train.py --smoke`)** builds the model and runs one forward and backward pass on a synthetic CPU
  batch. It builds no loader, so the loader workers neither slow it nor count against its 300 s timeout.
- **The runtime files.**
  - The process state is ignored and untracked, and `test_loop_runtime_state_is_never_tracked` holds it so: the lock,
    the pause flag, `autoresearch.out`, `watchdog.log`, `run.log`, `run_result.json`, `config_temp.json`,
    `results.tsv` and the sprint-log pointer.
  - `sprint_logs/`, `prize_readiness.tsv` and the benchmark figures are tracked on purpose, as project records.
- **Name and prefix checks** in the loop, `loop_control`, the trainer, promotion, the probe, the ablation and the
  re-score each compare text written to the same convention. For example, the preflight timeout's "preflight timed
  out" is the start of the failure text written a few lines above.
- **The watchdog** still starts the loop on `status`'s exit code alone; the new message is `start.sh`'s.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `8d44bb5c` (#84), whose tree is `a94e8832`'s but for its review doc's result
  lines. It was 42 failed, 2186 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental: no scroll data, no CUDA, no villa
  data files.
- Branch: 42 failed, 2187 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the extra pass is the new test. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- `bash -n start.sh`: clean. Ruff (check and format) on the test: clean.

New test in `tests/test_loop_lifecycle.py`:
- `test_start_sh_says_the_loop_will_not_start_beside_an_orphaned_run` (fails on main). It runs the real
  `start.sh` and `loop_control.py` in a temporary checkout, with a fake `uv` that launches nothing.

Not verified here: `start.sh` on the GPU host.
