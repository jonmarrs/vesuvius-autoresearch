# Design and architecture review — re-scoring the incumbent beside a running loop

Date: 2026-10-15. Baseline: `7e4013a7` (main after #73). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/reevaluate_best_model.py --update-stored`. Since #73 it is the only script outside the loop and
`train.py` that writes `best_model.pt`. It is also the remedy most refusals name (`promotion.RESCORE_COMMAND`):
- the loop's "Not starting" and "Stopping before cycle" for a stale or other-input score;
- `train.py`'s "Promotion blocked" for the same, and its preflight check of the validation inputs.

## What changed

- **`--update-stored` holds this checkout's lock (`autoresearch.lock`) until it has written**, as the noise probe
  and the augmentation ablation do.
  - It refuses to start while other work holds the lock (the loop, the probe, the ablation), naming the holder's
    PID, or why it is unidentified. The refusal gives the commands: `./stop.sh`, which also pauses the watchdog,
    then `./start.sh`.
  - While it runs, neither the watchdog nor `start.sh` can start the loop.
  - `loop_control` names the script, so `status` reports it and `./stop.sh` stops it before it writes. SIGTERM is
    turned into an interrupt, so an interrupted save removes its temporary file.
- **It does not write over a change made while it ran.** The lock keeps the loop out, but not a writer that takes
  no lock: a `train.py` run by hand, a `git checkout`. It hashes `best_model.pt` (SHA-256) before loading, after
  loading and before the write, and refuses if the file changed.
- **It settles a hold left by a killed loop as the loop's start would.** If `.best_model.pt.held` is still
  `best_model.pt`, the hold is released. Otherwise it refuses with the loop's own message, so that the operator
  chooses which file to keep before the re-score replaces one (`run_autoresearch_loop.leftover_hold`).
- **A dry run** (no `--update-stored`) writes nothing and takes no lock.
- `docs/CHECKPOINT_ANALYSIS.md` and the script's docstring say so.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A re-score made while the loop ran could undo a promotion.** `--update-stored` loads `best_model.pt`, scores it for minutes (up to 400 validation patches), and writes the loaded model back with new scores. Nothing checked for a running loop. Of the documents, only the 2026-10-12 runbook stops the loop first; `docs/CHECKPOINT_ANALYSIS.md`, the script's usage and the refusals that name the command do not. And the watchdog restarts a loop that is down but not paused, so a loop could start during a re-score even when none ran at its start. A promotion in that time was written over with the old model; `config.json` and the promotion commit then describe a model that is gone. A re-score written during a cycle that then fails is taken by the settle (#69) for the run's model: it is moved aside and the old scores are restored. This is the lost update #73 removed from the augmentation ablation. | The re-score holds the lock from before it loads the model until after it writes. Tests: a real lock holder in the working directory makes it refuse before loading anything, and the file is unchanged; an unidentified holder is refused too; while it scores, another process cannot take the lock (what the loop's start does), and the lock and SIGTERM handler are restored afterwards; `loop_control` names a re-score holding the lock; a SIGTERM ends it before it writes. |
| P3 | **A change by a writer that takes no lock** was written over in the same way. | Refused if `best_model.pt`'s hash changed while it was loaded or scored. Tested for both. |
| P3 | **A re-score after a kill hid the choice from the loop.** After a kill (not a stop) mid-cycle, `.best_model.pt.held` remains. A re-score breaks its link to `best_model.pt`, so the loop's next start can no longer release the hold and refuses to start, although the run's model was the one re-scored. | `leftover_hold` is applied first: a hold that is still the incumbent is released; otherwise the re-score refuses with the loop's message. Tested for both. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The first version checked the lock at the start and again before the write, and refused at the end if the loop had started meanwhile, throwing away minutes of scoring. The common way to reach that was the remedy itself: while the loop refuses to start, each watchdog restart holds the lock for the seconds it takes to import torch, check the incumbent and print "Not starting". | The re-score takes the lock, so the watchdog cannot start the loop during it, and nothing is thrown away at the end. `running_pid` is called only before the lock is taken: it opens and closes the lock file, which would drop this process's lock. |
| An error from `running_pid` (an unidentified holder, a `PermissionError`) escaped as a bare traceback. | Reported as the refusal, naming why the holder is unidentified. Tested. |
| The doc said three of the four tests failed on main; all four did, one only because the attribute it patched did not exist there. | Restated below for the new tests. |
| The hash did not cover the bytes loaded. | Hashed again after loading. Tested. |
| A held lock whose PID is not visible (another PID namespace) counted as no loop. | The lock itself decides now. |
| A hold left by a killed loop turned a re-score into a refusal to start. | Settled as the loop's start would. Tested. |
| "The remedy every refusal names" overstated it, and a mid-cycle re-score does not change what a candidate is compared with (`train.py` reads the stored score at promotion time). | Corrected. |
| The real-lock tests need `/proc`; the refusal test did not check that no model was built. | Skipped without `/proc`; checked. |

## Observations for the owner (not changed)

- **A dry run beside the loop shares the GPU with the cycle.** It writes nothing, so it takes no lock. But its
  validation pass can push a cycle out of memory (counted as a crash, unrewarded) or take training steps from a
  cycle's fixed time budget. The runbooks stop the loop first.
- **A re-score started while the loop is down but not paused** holds the lock while it runs; the watchdog's next
  tick after it ends starts the loop on the re-scored incumbent. `./stop.sh` first, as the runbook does, keeps the
  loop stopped until `./start.sh`.
- **The guard covers this checkout only.** The lock is the one in the working directory, which is where the command
  reads `best_model.pt` and `config.json`. Run elsewhere, it creates an `autoresearch.lock` there.

## Reviewed and sound

- **The write is atomic** (`save_checkpoint_atomic`), and a failed or incomplete measurement writes nothing, as
  the existing contract tests check.
- **A re-score made with the loop stopped is kept.** A stop settles the cycle in flight first (#69), and the next
  start reads the re-scored file.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #73's head, whose tree is `7e4013a7`'s.

- Baseline: 42 failed, 2136 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2146 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 10 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the script: clean.

New tests in `tests/test_checkpoint_tool_contracts.py`. On main's script:
- six fail on the behaviour: it starts beside a lock holder, takes no lock, writes over a change made while
  loading or scoring, and neither releases nor respects a leftover hold;
- two fail only because the function they patch does not exist there (the unidentified holder, the dry run);
- the stop test was not run against main, where the SIGTERM would end the test process itself.

The tests:
- `test_a_rescore_will_not_start_beside_this_checkouts_loop` (a real process holding `autoresearch.lock`);
- `test_an_unidentified_lock_holder_is_refused_too`;
- `test_a_rescore_holds_the_checkout_lock_until_it_has_written`;
- `test_loop_control_names_a_rescore_so_stop_can_stop_it`;
- `test_a_stop_ends_a_rescore_before_it_writes`;
- `test_a_rescore_does_not_write_over_a_change_made_while_it_ran` (while loaded; while scored);
- `test_a_rescore_settles_a_hold_left_by_a_killed_loop_as_its_start_would` (the incumbent; another file);
- `test_a_dry_run_beside_the_loop_reads_only`.

Not verified here: a re-score on the GPU host.
