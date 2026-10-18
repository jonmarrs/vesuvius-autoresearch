# Design and architecture review — the persistent loader workers, measured (#126)

Date: 2026-10-18. Baseline: `ad1549c0` (main after #126). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the owner's #126 (`6337fa29`). It measures #113's fix in the loop
(`reports/loader_epoch_boundary_measured_2026-10-18.md`, `reports/epoch_boundary_overhead_persistent.json`), and
adds `--since` and a list of run logs to `scripts/epoch_boundary_overhead.py`. The 2026-10-18 loader review
(`DESIGN_ARCHITECTURE_REVIEW_2026-10-18_LOADER_WORKERS.md`) had left this effect unmeasured.

## What changed

- **The report now says that its slope rests on one cycle.**
  - Nine of the shift's ten cycles crossed exactly 5 boundaries; only `use_uamt_False` crossed more (18). So the
    fitted 0.2 s per boundary is that one cycle's 101 s against the other nine's mean of 98.6 s, over 13
    boundaries. Without it, no slope can be fitted at all.
  - The SE of 0.6 is right for the model (recomputed: 0.58). But it assumes the model rather than measuring the
    spread at other pass counts.
  - The comparison at 5 boundaries rests on all nine cycles, and the report's answer stands on it: 97 s against
    185 s, with the same night's two old-code cycles at 182 and 185 s.
  - A dated bullet in "What it does not say" records this, and a test pins the boundary counts and the bullet.

## Verified, no change needed

- **The figures, recomputed from the JSON with the script's own `fit`:**
  - before: 84.3 s + 21.29 s per boundary, SE 1.21, residual SD 16.5, n = 72;
  - after: 97.6 s + 0.19 s, SE 0.58, residual SD 7.2, n = 10;
  - the 5-boundary medians, 185 s and 97 s (91–114, n = 9);
  - `use_uamt_False`: 17,020 steps at batch 8 is 18 boundaries; the old fit's 467.6 s; 101 s observed; val_f1
    0.2584, the shift's lowest;
  - the saving of 88 s against 106 s predicted, and 3,697 s against 3,785 s per cycle (2.4%).
- **`--since`.**
  - Each cycle's start is now a full date-time: the sprint log's date plus a clock that rolls past midnight
    (`_after`). So the 21:17:25 restart's cycles are kept and the two before it are not.
  - The two control rows, hand-assembled from the same command without `--since`, start before it, as the test
    checks.
- **`--run-log run.log.old run.log`.** Lines are concatenated in that order, so a run split by the 10 MB rotation
  is rejoined.
- **The killed-run pairing.** With `--since`, `crashed` narrows but `unscored` (run.log has no clock) does not. A
  mismatched count then pairs nothing, as the comment says, rather than pairing wrongly.

## Observations for the owner (not changed)

- **A second shift would give the slope more than one point.** The 15-minute day cycles cross about one boundary.
  Fitted with the 60-minute cycles, they would separate a per-boundary cost from a per-cycle one. The report says
  they were still running.
- **The 18 s gap between the 88 s saved and the 106 s predicted is unexplained.** The restart also brought in
  #112 and #115–#117, as the report says, and one shift cannot separate their costs from the loader's.
- **Carried from earlier reviews:** the resume marker is written once per run of restarts (#120's clock), and the
  catalogue is hard-coded.

## Verification

- `pytest tests/test_loader_epoch_boundary_measured_report.py tests/test_loader_epoch_boundary_report.py
  tests/test_epoch_boundary_overhead.py`: 25 passed (one new).
- The fits and SEs recomputed with `epoch_boundary_overhead.fit` and `residual_sd / √Sxx`.
- The standard suite: see the PR.
