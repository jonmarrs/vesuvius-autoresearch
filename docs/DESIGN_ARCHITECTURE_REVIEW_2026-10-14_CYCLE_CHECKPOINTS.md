# Design and architecture review — what a cycle saves of its model

Date: 2026-10-14. Baseline: `a373d678` (main after #67). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the end of `train.train`, which saves the cycle's model and record. Three paths:
- `best_model.pt`, the incumbent, on a promotion;
- `last_model.pt`, the cycle's candidate;
- `checkpoint_out`, for an experiment run that must leave the loop's files alone.

Also the tools that read these files: `scripts/snapshot_loop_candidates.sh` and `scripts/loop_candidate_spread.py`
(finding 88).

## What changed

- **`last_model.pt` is written every cycle, promoted or not.** `train.save_cycle_checkpoints` decides the paths:
  - `checkpoint_out` alone for an experiment run;
  - `last_model.pt` for every loop cycle;
  - `best_model.pt` as well on a promotion.
- **One record goes to every file.** The three hand-copied payloads are one dict.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Promoted candidates never reached `last_model.pt`, so the candidate snapshots left out the best of them.** `snapshot_loop_candidates.sh` copies `last_model.pt` as "each cycle's candidate", and finding 88's spread analysis scores those copies. A promoted cycle wrote only `best_model.pt`, so its candidate was never copied: the highest-scoring candidates were the ones a snapshot series lacked. A spread computed from such a series understates how far candidates range. Finding 88's pre-registered sample is not affected. Its 10 snapshots (2026-10-13, 15:58 to 18:24) are 16 minutes apart throughout, one per cycle, so no cycle in that window was promoted or crashed. | `save_cycle_checkpoints` writes `last_model.pt` on every cycle, after `best_model.pt` on a promotion. Test: the paths for a plain cycle, a promoted one, and an experiment run (its directory is created; nothing else is written). |
| P3 | **The three checkpoint payloads had drifted apart.** Each save spelled out its own 20-field dict. `last_model.pt` lacked `avg_mean_ap` (villa's mean AP), and `checkpoint_out` lacked `prize_gate_failures`, which says why an experiment would not have been promoted. Every field added since was added three times (`training_labels`, on 2026-10-14, was the latest). | One `checkpoint` dict, built once, is passed to every save. Test: every path receives the same record. |

## Observations for the owner (not changed)

- **An experiment run reports `is_success`.** With `checkpoint_out` set, `run_result.json`'s `is_success` says
  whether the run would have been promoted, but nothing is promoted. Only manual experiment runs set
  `checkpoint_out`; the loop never proposes it.
- **`last_model.pt` holds the latest candidate only.** The snapshot script polls every 20 seconds. A cycle is at
  least the 900-second budget, so a poll will not miss a write.

## Reviewed and sound

- **Saves are atomic** (`save_checkpoint_atomic`: a temporary file, then `os.replace`). A promotion's
  `best_model.pt` is written before `last_model.pt`, the `results.tsv` and `prize_readiness.tsv` rows and
  `run_result.json`, so the loop's commit after the run sees the promoted model.
- **An experiment run** leaves `best_model.pt`, `last_model.pt`, `history.tsv`, `results.tsv` and
  `prize_readiness.tsv` untouched, as before.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #67's head, whose tree is `a373d678`'s.

- Baseline: 42 failed, 2108 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2111 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 3 extra passes are the new test's cases. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files: clean.

New test, `tests/test_autoresearch_measurement.py::test_every_cycle_saves_its_candidate_and_a_promotion_the_incumbent`
(three cases).

Not verified here: a training cycle on the GPU host. No test runs `train()` to its end, so the call site is
checked by reading.
