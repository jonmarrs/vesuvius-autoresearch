# Design and architecture review — re-scoring the incumbent beside a running loop

Date: 2026-10-15. Baseline: `7e4013a7` (main after #73). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `scripts/reevaluate_best_model.py --update-stored`. Since #73 it is the only script outside the loop and
`train.py` that writes `best_model.pt`. It is also the remedy every refusal names (`promotion.RESCORE_COMMAND`):
- the loop's "Not starting" and "Stopping before cycle";
- `train.py`'s "Promotion blocked" and its preflight check of the validation inputs.

## What changed

- **`--update-stored` refuses while work holds this checkout's lock**: the loop, the noise probe or (since #73)
  the augmentation ablation. It checks `loop_control.running_pid` on the working directory twice:
  - before loading the model, so no GPU time is spent;
  - again just before the write, because the watchdog can start the loop while a re-score runs.

  The refusal names the PID and gives the commands: `./stop.sh` (which also pauses the watchdog) and `./start.sh`.
- **It does not write over a change made while it ran.** It hashes `best_model.pt` before loading it. Before the
  write it hashes the file again, and if the hash differs it refuses. Without `--update-stored` nothing is written
  and nothing is checked.
- `docs/CHECKPOINT_ANALYSIS.md` and the script's docstring say so.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **A re-score made while the loop ran could undo a promotion, or skew a cycle's comparison.** `--update-stored` loads `best_model.pt`, scores it for minutes (up to 400 validation patches), and writes the loaded model back with new scores. Nothing checked for a running loop. The 2026-10-12 runbook stops the loop first, but `docs/CHECKPOINT_ANALYSIS.md`, the script's usage and the command `train.py` prints in a running loop's sprint log ("Promotion blocked: … re-score it with `…`") do not. Beside a running loop, three things can go wrong. A promotion during the re-score is written over with the old model; `config.json` and the promotion commit then describe a model that is gone. A re-score written mid-cycle changes the score the cycle's candidate is compared with after the cycle has read the old one. And if that cycle then fails, the settle (#69) takes the re-scored file for the run's model: it moves it aside and restores the old scores. This is the lost update #73 removed from the augmentation ablation. | Refused at the start and before the write while `running_pid` finds work holding the lock. Refused before the write if `best_model.pt`'s SHA-256 changed since it was loaded. Tests: a real lock owner in the working directory makes it refuse before any validation read, leaving the file unchanged; the loop starting during the re-score makes it refuse at the end, leaving the file unchanged; a promotion during the re-score is kept; a dry run beside the loop reads only. |

## Observations for the owner (not changed)

- **A dry run beside the loop shares the GPU with the cycle.** It writes nothing, so it is allowed. But its
  validation pass can push a cycle out of memory (counted as a crash, unrewarded) or take training steps from a
  cycle's fixed time budget. The runbooks stop the loop first.
- **A watchdog restart can make a re-score refuse.** While the loop is refusing to start (a stale incumbent), the
  watchdog restarts it every few minutes. Each restart holds the lock for the second or two it takes to check the
  incumbent and print "Not starting". A re-score that checks in that moment refuses; running `./stop.sh` first, as
  the refusal says, pauses the watchdog.
- **The guard covers this checkout only.** `running_pid` looks for the lock in the working directory, which is
  where the command reads `best_model.pt` and `config.json`. A loop in a sibling checkout has its own files.

## Reviewed and sound

- **The write is atomic** (`save_checkpoint_atomic`), and a failed or incomplete measurement writes nothing, as
  the existing contract tests check.
- **A re-score made with the loop stopped is kept.** A stop settles the cycle in flight first (#69), and the next
  start reads the re-scored file.
- **The remaining window** between the last check and the write is the second hash and the save: well under a
  second for the production checkpoint (41 MB).

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #73's head, whose tree is `7e4013a7`'s.

- Baseline: 42 failed, 2136 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2140 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as the
  baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the script: clean.

New tests in `tests/test_checkpoint_tool_contracts.py` (the first three fail on main; the fourth guards the dry run):
- `test_a_rescore_refuses_to_write_beside_this_checkouts_loop` (a real process holding `autoresearch.lock`);
- `test_a_rescore_does_not_write_over_a_change_made_while_it_ran` (the loop started; `best_model.pt` replaced);
- `test_a_dry_run_beside_the_loop_reads_only`.

Not verified here: a re-score on the GPU host.
