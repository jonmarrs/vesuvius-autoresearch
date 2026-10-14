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
  - `best_model.pt` as well on a promotion, written last.
- **One record goes to every file.** The three hand-copied payloads are one dict.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **Promoted candidates never reached `last_model.pt`, so the candidate snapshots left out the best of them.** `snapshot_loop_candidates.sh` copies `last_model.pt` as "each cycle's candidate", and finding 88's spread analysis scores those copies. A promoted cycle wrote only `best_model.pt`, so its candidate was never copied: the candidates that cleared the promotion bar were the ones a snapshot series lacked. A spread computed from such a series understates how far candidates range. Finding 88's pre-registered sample is not affected. Its 10 snapshots (2026-10-13, 15:58 to 18:24) are 16 minutes apart throughout; a promoted cycle would have left a gap of about 32. Also, `best_model.pt`'s hash (`d7da2776…`) is the same in the reports written before and after the window. | `save_cycle_checkpoints` writes `last_model.pt` on every cycle and then, on a promotion, `best_model.pt`. Test: the paths, in order, for a plain cycle, a promoted one, and an experiment run (its directory is created; nothing else is written). |
| P3 | **The three checkpoint payloads had drifted apart.** Each save spelled out its own 20-field dict. `last_model.pt` lacked `avg_mean_ap` (villa's mean AP), and `checkpoint_out` lacked `prize_gate_failures`, which says why an experiment would not have been promoted. Every field added since was added three times (`training_labels`, on 2026-10-14, was the latest). | One `checkpoint` dict, built once, is passed to every save. Test (on `train()`'s source): no direct `save_checkpoint_atomic` call is left, the one `save_cycle_checkpoints` call passes the record, the target and the promotion flag, and the record has `avg_mean_ap` and `prize_gate_failures`. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| `best_model.pt` was written before `last_model.pt`, widening the window in which a stopped run replaces the incumbent unrecorded; the doc's reason for the order (the loop's commit) did not hold. | Fixed: `last_model.pt` first, `best_model.pt` last. The pre-existing window is recorded below. |
| "No cycle was promoted or crashed" was too strong on crashes: a failed preflight writes no checkpoint and adds seconds to a gap. | Reworded to promotions, with the incumbent's hash as further evidence. |
| "The highest-scoring candidates" overstated it: promotion also needs the AP lift, the prize gates and a complete sample. | Now "the candidates that cleared the promotion bar". |
| The budget cited `config.json`; the loop sets it by shift. | Corrected. |
| The test did not check the call site or the record's fields. | An AST test on `train()` checks both. |
| `is_improvement and not ckpt_out` was computed twice. | Computed once (`promoted`). |
| `loop_candidate_spread.py` pairs a late hash with early scores. | Recorded below; that script is in open PRs. |

## Observations for the owner (not changed)

- **An experiment run reports `is_success`.** With `checkpoint_out` set, `run_result.json`'s `is_success` says
  whether the run would have been promoted, but nothing is promoted. Only experiment runs (by hand, or
  `scripts/f1_noise_probe.py`) set `checkpoint_out`; the loop never proposes it, and the probe does not read
  `is_success`.
- **`last_model.pt` holds the latest candidate only.** The snapshot script polls every 20 seconds. A cycle lasts
  at least the loop's training budget (900 seconds by day, 3600 by night), so a poll will not miss a write.
- **A run stopped after `best_model.pt` is replaced but before `run_result.json` is written changes the
  incumbent unrecorded.** The loop then counts a crash: it reverts `config.json` and commits nothing, but the
  next cycle warm-starts from, and is compared with, the new `best_model.pt`. The window covers the TSV rows,
  `os.sync` and the result file, a few seconds; the supervisor's timeout or `stop.sh` could land in it. This
  predates the PR; writing `best_model.pt` last keeps it from growing.
- **`scripts/loop_candidate_spread.py` reads `best_model.pt`'s hash at the end of its run** but scores the
  incumbent at the start, so a `--wait` run spanning a promotion would pair the new hash with the old scores.
  Promoted candidates now reach the snapshots, which makes such a run possible. The script is changed by open
  PRs #65 and #66, so it is left to them.

## Reviewed and sound

- **Saves are atomic** (`save_checkpoint_atomic`: a temporary file, then `os.replace`). The loop commits
  `best_model.pt` only after the run exits with a result, so the order of the saves matters only to a run stopped
  between them: `best_model.pt` last means such a run leaves the incumbent the loop still records.
- **An experiment run** leaves `best_model.pt`, `last_model.pt`, `history.tsv`, `results.tsv` and
  `prize_readiness.tsv` untouched, as before.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #67's head, whose tree is `a373d678`'s.

- Baseline: 42 failed, 2108 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: 42 failed, 2112 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped.
- Ruff (check and format) on the changed files: clean.

New tests in `tests/test_autoresearch_measurement.py`:
- `test_every_cycle_saves_its_candidate_and_a_promotion_the_incumbent` (three cases);
- `test_train_saves_one_record_through_save_cycle_checkpoints` (on `train()`'s source).

Not verified here: a training cycle on the GPU host. No test runs `train()` to its end; the call site is checked on
its source.
