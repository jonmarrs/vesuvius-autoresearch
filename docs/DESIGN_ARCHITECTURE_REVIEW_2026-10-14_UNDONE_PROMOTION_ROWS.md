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
  - When the cycle begins, `hold_incumbent` records each promotion log's file identity and length (`_log_ends`).
  - When the cycle is settled as failed after the run replaced `best_model.pt`, `settle_incumbent` cuts each log
    back to its earlier length (`_undo_promotion_rows`) and removes a log the run created.
  - A log rotated during the run is left as it is. (`append_tsv_row` moves a log whose header changed aside and
    starts a new one.) The sprint log names which logs were cut and which were left.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A promotion the loop undid stayed in the reports.** After #69, a run that replaced `best_model.pt` and then failed has its model moved aside and the incumbent put back. But the rows that run appended to `results.tsv` and `prize_readiness.tsv` stayed. The daily report and the plots would show a promotion the incumbent does not reflect, and the tracked `prize_readiness.tsv` would carry it into the next commit. | `_undo_promotion_rows` cuts each log to its length from before the run, if it is still the same file; a log the run created is removed. Tests: a failed promotion leaves `results.tsv` exactly as it was and removes a `prize_readiness.tsv` it created; a successful promotion keeps its row; a log rotated during the run is left. |

## Observations for the owner (not changed)

- **`history.tsv` keeps the failed run's row.** It records every run, promoted or not, and the run did complete
  validation before it failed.
- **External tracking (W&B) keeps the run.** It was logged as it happened.

## Reviewed and sound

- **What a promotion writes** (train.py): `best_model.pt` (through `save_cycle_checkpoints`), then the
  `results.tsv` and `prize_readiness.tsv` rows, then `run_result.json`. `history.tsv` is written for every run,
  before any checkpoint.
- **The rows are tied to the replace.** They are written after `best_model.pt`, so a run that failed before
  replacing it wrote none, and nothing is cut.
- **A stop mid-cycle** goes through the same settle (#69), so its rows are cut too.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #70's head, whose tree is `e401781b`'s.

- Baseline: 42 failed, 2128 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2129 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the extra pass is the new test. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop: clean.

Tests in `tests/test_autoresearch_measurement.py`:
- the failed-promotion cases (four) now also check that `results.tsv` is as it was and that `prize_readiness.tsv`,
  created by the run, is gone;
- a successful promotion keeps its row;
- a promotion log rotated during the run is left (new).

Not verified here: a cycle on the GPU host.
