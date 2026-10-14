# Design and architecture review — what an undone promotion leaves in the reports

Date: 2026-10-14. Baseline: `e401781b` (main after #70). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: a follow-up to the failed-cycles review (#69). A cycle whose run promoted and then failed is now undone: the
loop puts the previous `best_model.pt` back. This review looks at everything else a promotion writes. When
`train.py` promotes, it also appends a row to `results.tsv` and to `prize_readiness.tsv`, before it writes its
result. `generate_daily_report.py` and `plot_results.py` read `results.tsv`. `prize_readiness.tsv` is tracked in
git.

## What changed

- **Undoing a promotion also removes its rows.**
  - When the cycle begins, `hold_incumbent` records each promotion log's bytes (`_log_ends`). The logs gain a row
    per promotion, so they are small.
  - When the cycle is settled as failed after the run replaced `best_model.pt`, `settle_incumbent` puts each log
    back (`_undo_promotion_rows`):
    - a log that still begins with its old bytes is cut to them;
    - one the run created is removed;
    - one `append_tsv_row` rotated (moved aside for a new header) is moved back.
  - Any other change is left, and a log that cannot be restored is reported, not raised. The sprint log names the
    logs restored and the logs left.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A promotion the loop undid stayed in the reports.** After #69, a run that replaced `best_model.pt` and then failed has its model moved aside and the incumbent put back. But the rows that run appended to `results.tsv` and `prize_readiness.tsv` stayed. The daily report and the plots would show a promotion the incumbent does not reflect, and the tracked `prize_readiness.tsv` would carry it into the operator's next commit of it (the loop does not commit it). | `_undo_promotion_rows` restores each log to its bytes from before the run, judged by content. Tests: a failed promotion leaves `results.tsv` exactly as it was and removes a `prize_readiness.tsv` it created; a stop mid-cycle and a failed first incumbent remove their rows; a successful promotion keeps its row; a rotated log is moved back; a log rewritten with other content is left. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| A same inode did not mean the same file. A log deleted and recreated during the run (git does this when it updates a tracked file) can get its inode number back, and the cut then fell mid-row in the new content. | Fixed: content decides. A log is cut only if it still begins with its bytes from before the run. Tested. |
| A rotation left `results.tsv` (which the reports read) with the undone row while `prize_readiness.tsv` was cut. | Fixed: the rotated file is found by content and moved back. Tested. |
| After a kill, nothing undoes or mentions the rows. | The start message now says to remove that run's last row from the two logs. |
| An error while restoring a log, in the signal handler, could turn a stop into another cycle. | Fixed: reported per log, never raised. |
| The stop and first-incumbent paths did not check the logs. | Now checked. |
| The doc implied the loop commits `prize_readiness.tsv`, and the failed-cycles doc said both logs feed the reports. | Corrected: the operator commits it, and the reports read `results.tsv`. |

## Observations for the owner (not changed)

- **`history.tsv` keeps the failed run's row.** It records every run, promoted or not, and the run did complete
  validation before it failed.
- **External tracking (W&B) keeps the run.** It was logged as it happened.
- **A kill (not a stop) does not undo the rows.** The snapshot is in memory. The next start's message says to
  remove that run's last row from the two logs if it added one.

## Reviewed and sound

- **What a promotion writes** (train.py): `best_model.pt` (through `save_cycle_checkpoints`), then the
  `results.tsv` and `prize_readiness.tsv` rows, then `run_result.json`. `history.tsv` is written for every run,
  before any checkpoint.
- **The rows are tied to the replace.** They are written after `best_model.pt`, so a run that failed before
  replacing it wrote none, and nothing is cut.
- **A promotion the loop keeps** never loses its rows: the logs are restored only on the branch that moves the
  run's model aside, and each cycle's snapshot is taken after earlier promotions' rows were written.
- **A stop mid-cycle** goes through the same settle (#69), so its rows are cut too.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #70's head, whose tree is `e401781b`'s.

- Baseline: 42 failed, 2128 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: 42 failed, 2130 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 2 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

Tests in `tests/test_autoresearch_measurement.py`:
- the failed-promotion cases (four) now also check that `results.tsv` is as it was and that `prize_readiness.tsv`,
  created by the run, is gone; so do the stop and first-incumbent tests;
- a successful promotion keeps its row;
- a promotion log rotated during the run is moved back (new);
- a promotion log rewritten with other content during the run is left (new).

Not verified here: a cycle on the GPU host.
