# Design and architecture review — what a failed cycle leaves behind, and what it records

Date: 2026-10-14. Baseline: `07e28cae` (main after #68). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `run_autoresearch_loop.py` handles a cycle that does not end cleanly:
- the preflight;
- the supervised training run and its timeout (budget + 300 s);
- the exit code and `run_result.json`;
- the sprint-log entry;
- the incumbent `best_model.pt`, which `train.py` replaces itself when it promotes;
- `scripts/wandb_tracking.py`, whose `finish_run` is the one step `train.py` takes after writing its result.

## What changed

- **A failed cycle promotes neither the config nor the model.** The loop hard-links `best_model.pt` before each run
  (`hold_incumbent`). If the cycle fails after the run replaced it (`settle_incumbent`), the run's model is moved
  to `best_model.pt.failed-run-<time>` and the held incumbent is put back. A stop (`stop.sh`, SIGTERM) settles the
  cycle in flight the same way. A hold found at start means a kill or power loss: it is released if
  `best_model.pt` is unchanged; otherwise the loop does not start, and says how to keep either file.
- **The sprint log names the failure.** "Training crashed (Unknown error)" is replaced by the reason, one of:
  - preflight exited with code N (or was killed by a signal, named), or timed out;
  - killed at the N s timeout;
  - exited with code N (or was killed by a signal), or wrote no `run_result.json`;
  - could not be run;
  - `run_result.json` unreadable;

  with "after writing run_result.json" when that applies, and the run log's last line (for a failed preflight,
  its own last line, taken before the loop's marker).
- **A W&B error at the end of a run no longer fails it.** `wandb_tracking.finish_run` reports an exception from
  `wandb.finish()` instead of raising it, as its module promises for tracking hiccups.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A cycle that failed after promoting left an incumbent nothing recorded.** Since 2026-10-01 a promotion requires a clean exit as well as a result: the loop then reverts `config.json` and commits nothing. But `train.py` replaces `best_model.pt` before it writes `run_result.json` and exits. Any failure after that point left the new model in place while every record said the cycle crashed: `wandb.finish()` (production has `use_wandb: true`, online, and it runs after the result), an error in interpreter teardown, the supervisor's timeout, or `stop.sh`. The next cycle would warm-start from that model and be compared with it, and its config would be the reverted one. | `hold_incumbent` hard-links the incumbent before the run. `train.py` promotes by `os.replace`, so the link keeps the old file at no copy cost. `settle_incumbent` puts it back when the cycle failed and the incumbent's file changed, keeping the run's model aside, and releases the hold otherwise. The signal handler settles the cycle in flight on a stop. Tests: four failed promotions (exit 1 after the result; killed by SIGKILL; the timeout after the result; the timeout before it) leave the incumbent, keep the run's model aside and leave `config.json` unchanged; a promotion keeps its model and releases the hold; a stop mid-cycle settles, and a re-score made while stopped is kept at the next start; a failed run that wrote the first incumbent leaves none; without a hard link the cycle runs unheld. |
| P3 | **The sprint log could not say why a cycle failed.** Every failure that was not out-of-memory was written as "Training crashed (Unknown error)". The diagnostic tail went only to stdout (`autoresearch.out`, which is not kept with the logs). From 2026-06-29 to 2026-07-07, 264 cycles were killed at the loop's timeout and none was scored. The sprint logs show it only in the spacing of their timestamps: 20 minutes by day (the 1,200 s timeout plus the preflight) and 65 by night (3,900 s). | Each failure path sets a reason, written as `Training crashed (<reason>)`, with the run log's last line. Tests: a failed preflight is named; each failed promotion above is named, with the log's last line. |
| P3 | **A tracking error at the end of a run failed the run.** `finish_run` called `wandb.finish()` unguarded, after `run_result.json`. An exception there gave a non-zero exit, so the loop discarded a scored result, and with it any promotion. | Reported and swallowed. Test: an exception from `wandb.finish` is printed, not raised. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| A stop (`stop.sh`) almost always lands mid-cycle, and the handler exited without settling. The next start then took any later change to `best_model.pt` (a re-score made while stopped, a checkout) for the run's model, reverted it, and called it a failed run. | Fixed: the signal handler settles the cycle in flight. A hold found at start (a kill or power loss) is released if nothing changed; otherwise the loop does not start and gives both commands. Tested. |
| For a failed preflight, the "last log line" was the loop's own marker. | Fixed: taken before the marker. Tested. |
| An undone promotion keeps its rows in `results.tsv` and `prize_readiness.tsv`. | Recorded below. |
| A hold that vanished mid-cycle made the settle raise. | Fixed: it is reported and the cycle is left unsettled. |
| The no-incumbent and no-hard-link branches were untested. | Tested. |
| Two failed runs settled in one second would share an aside name. | Fixed: a counter is added. |
| A negative return code read as "exited with code -9". | Named: "was killed by SIGKILL". |
| The doc said "the supervisor's timeout" for June and July, before the supervisor existed. | Now "the loop's timeout". |

## Observations for the owner (not changed)

- **The cause of the 2026-06-29 to 2026-07-07 timeouts is not in the repository.** The run logs are on the host.
  With the reasons now recorded, a recurrence will name itself.
- **A run that fails after writing its result now loses its promotion.** It no longer half-promotes; the model is
  kept as `best_model.pt.failed-run-<time>`. Trusting a result written before a failed exit would be the other
  consistent choice, but the 2026-10-01 review chose a clean exit, and this keeps that rule. A W&B error no longer
  fails the run, but a hang in `wandb.finish()` still meets the timeout.
- **The hold needs hard links.** Where the filesystem refuses one, the loop prints a warning and runs that cycle
  without the hold, as before.
- **A manual change to `best_model.pt` during a cycle that then fails is moved aside like the run's model.**
  Re-scoring is done with the loop stopped; a stop settles the cycle first, so a re-score made then is kept.
- **An undone promotion keeps its rows.** `train.py` appends to `results.tsv` and `prize_readiness.tsv` when it
  promotes, before it writes its result, so a run that then fails leaves rows for a promotion the loop undid. The
  daily report and the plots read those files. (Fixed by #71:
  `DESIGN_ARCHITECTURE_REVIEW_2026-10-14_UNDONE_PROMOTION_ROWS.md`.)
- **A kill (not a stop) during a run that writes the first incumbent is not caught.** With no incumbent there is
  nothing to hold, so the next start sees no hold. A stop settles it.

## Reviewed and sound

- **`run_result.json` is deleted before each run** (since 2026-04-14) and written as `train.py`'s last step, so
  its presence means this run reached its end.
- **On a timeout, the supervisor kills the run's process group before returning**, so nothing writes
  `best_model.pt` after the loop settles it.
- **A promoted cycle's commit** comes after the settle, which has released the hold, and adds only the files it
  names.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #68's head, whose tree is `07e28cae`'s.

- Baseline: 42 failed, 2112 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: 42 failed, 2124 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 12 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

New tests in `tests/test_autoresearch_measurement.py` (the promotion test guards the success path; the others fail
on main):
- a run that fails after promoting leaves the incumbent (exit 1 after the result; killed by SIGKILL; the timeout
  after the result; the timeout before it);
- a promotion keeps its model and releases the hold;
- a failed preflight is named in the sprint log, with its own last line;
- a stop mid-cycle settles the run, and a re-score made while stopped is kept;
- a hold left by a killed loop is the operator's call (the loop does not start and changes nothing);
- a hold of an unchanged incumbent is released;
- a failed run that wrote the first incumbent leaves none;
- without a hard link the cycle runs unheld;
- a tracking error at the end of a run is not a failed run.

`tests/test_loop_lifecycle.py` lists `.best_model.pt.held` with the loop's runtime state, which git must ignore.

Not verified here: a cycle on the GPU host, and hard links on its filesystem.
