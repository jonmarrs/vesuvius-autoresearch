# Design and architecture review — the autoresearch loop's measurement

Date: 2026-10-12. Baseline: `b48543196aa8619c68996c7bec32de52d2722799` (main after the
cross-cutting review). Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what a loop cycle actually measures and what a promotion compares —
`run_autoresearch_loop.py`'s proposal and promotion path, and in
`scripts/training/train.py` the training sample, learning-rate schedule, the
validation that decides promotion, and the incumbent comparison, plus
`scripts/reevaluate_best_model.py`, the tool meant to keep the incumbent's stored
score comparable. The 2026-10-01 review covered the loop's process lifecycle
(locks, supervisor, stop/start, failed-exit promotion); no earlier review covered
these decisions.

## What changed

Promotion is now scored on a fixed, seeded validation sample spread over the whole
validation fragment, independent of `batch_size`, and recorded as protocol
`seeded-sample-400-v2`. An incumbent that is unreadable, lacks a finite `val_f1`, or
was scored under another protocol blocks promotion (and the loop will not start)
instead of being treated as absent. Checkpoints are written atomically. Training
and UA-MT batches are drawn in a seeded random order, fresh each run. The
learning-rate schedule follows the time budget instead of a 0.2 s/step estimate,
and `config.lr` is no longer overwritten with the batch-scaled value. The
every-10th-cycle GP-winner injection is removed. `reevaluate_best_model.py`
re-scores `val_f1` through the loop's own validation code. A patch catalogue with
no qualifying patch is refused instead of silently becoming patch (0, 0).

## Why

The loop's one decision — promote or revert — compared a candidate's F1 on one set
of patches with an incumbent's F1 from another, after training on the same small
strip every cycle at roughly half the intended learning rate. Its incumbent score
rests on 80 patches.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **The validation that decides promotion depended on `batch_size` and covered one strip.** It read the first 100 *batches* of an unshuffled loader: 400 patches at `batch_size` 4, 800 at 8, 1,600 at 16 (a swept axis), always the first entries of a raster-ordered catalogue, and dropped a whole batch when the batch held no ink. The stored incumbent records `requested_patches: 100, empty_target_patches: 80, usable_patches: 20` — its `val_f1` 0.468 comes from 20 batches × 4 = 80 patches. A `batch_size` candidate was scored on a different (superset) sample than the incumbent; in the latest sprint log (2026-07-11) the `batch_size_8` cycle scored 0.330 against 0.43–0.47 for the other thirteen scored cycles (the difference mixes the sample change with the tweak itself). | `scripts/training/promotion.py` defines protocol v2: 400 catalogue entries from a seeded permutation, scored per patch in any batch grouping; ink-free patches are dropped one at a time. `train.collect_validation_predictions` implements it with strict reads; a failed read marks the sample incomplete, which blocks promotion. Checkpoints and `run_result.json` record `val_protocol`. |
| P1 | **Every cycle trained on the same strip.** The training `DataLoader` had no sampler, and `__getitem__` is deterministic in the index, so each run read catalogue entries 0, 1, 2, … in raster order. A day-shift cycle reaches ~250 steps × batch 4 ≈ 1,000 of the 7,345-patch training catalogue; every warm-started cycle fine-tuned on those same ~1,000 patches in spatially adjacent batches. The UA-MT stream walked a 49,784-entry raster grid from (0, 0), so ~1,000 unlabeled patches cover only its first ~5 rows of patch origins (the top ~220 px) of an 8,181-px volume. `scripts/f1_noise_probe.py` describes the training loader as "unseeded", which was the intent. | `train.shuffled_loader`: a seeded random order; each pass after `StopIteration` is a fresh permutation. The seed is drawn per run (successive cycles see different patches) and recorded as `train_sampling_seed` in `run_result.json` and the checkpoint. |
| P1 | **The learning-rate schedule never left warmup.** It planned `max(1000, time_budget / 0.2)` steps with 12.5% warmup; production steps take 3.2–4.7 s. A 900 s cycle planned 4,500 steps (562 warmup) and ran ~250, ending at 0.445 × the configured peak and never annealing; a 3,600 s cycle ended at 0.467 ×. In the last 150 logged runs, 7 left warmup (mean 50% of warmup reached). Every candidate was scored at an un-annealed, still-rising LR, and the `lr` axis meant about half what it said. `config.lr` was also overwritten with the batch-scaled value, so checkpoints and `history.tsv` record e.g. 1.25e-4 for a configured 5e-4. | `train.budget_lr_factor`: warmup then cosine decay over the elapsed fraction of `time_budget`. The scaled peak is a local `peak_lr`; `config.lr` stays as configured. The step log now prints the LR. |
| P2 | **An unreadable incumbent let anything replace it.** If `best_model.pt` existed but failed to load, the comparison fell back to −∞ (any lift-positive candidate promotes), and the warm start in the same run had failed the same way, so the candidate was trained from random weights. Checkpoints were written in place by `torch.save`, so `stop.sh` or the supervisor's timeout during a save could produce exactly that file. Reproduced: a truncated `best_model.pt` with stored 0.47 and a 0.20 candidate → promoted. | `promotion.read_incumbent_val_f1` returns −∞ only when there is no file; otherwise an unreadable file, a missing/nonfinite `val_f1` or another protocol raises `IncumbentUnavailable`. `train.promotion_decision` fails closed on it and on an incomplete sample, and reports why (`promotion_blocked`, also written to the sprint log). The loop checks the incumbent before a shift and returns with the reason, so no GPU time is spent on cycles that cannot promote. `promotion.save_checkpoint_atomic` writes every checkpoint via a temporary file and `os.replace`. |
| P2 | **The cycle-10 "GP-winner baseline" could never run, and was unsafe if it had.** Every 10th cycle replaced the config with timesformer / patch 256 / defaults. The loop's own VRAM heuristic scores that 74.67 against a 1.5 cap, so it was always skipped (the 2026-07-11 log has no cycle 10). Had it run, it was promotable: a success would have renamed it over `config.json`, ending the pinned resenc_unet warm-start design. | Removed. Run-to-run calibration is `scripts/f1_noise_probe.py`. |
| P2 | **The re-baselining tool had drifted from the loop.** `reevaluate_best_model.py` exists to re-score the incumbent when validation changes, but it never computed `val_f1` (the deciding metric), forced `use_lasagna=False` (the production incumbent was trained and scored with lasagna), used `require_ink=True` (the loop uses False) and a different label-file preference. | It now builds the dataset with `train.build_validation_dataset`, scores with `train.collect_validation_predictions` and `train.pooled_segmentation_metrics`, uses the checkpoint's model and input settings with `config.json`'s validation fragment, and `--update-stored` writes `val_f1`, `ap_prevalence_lift`, `val_protocol` and the legacy numbers atomically. The existing checkpoint-tool contracts (saved settings, rejected bad ink, unchanged checkpoint on failure) still hold. |
| P3 | **A catalogue with no qualifying patch silently became patch (0, 0)** and was cached. In `run.log.old`, 203 runs initialised the validation set with 1 patch. | `VesuviusLabeledDataset` raises `ValueError` before caching. |

## Architecture and compatibility decisions

**Protocol, not bootstrap.** The previous rewire treated a checkpoint without
`val_f1` as −∞ so the first lift-positive cycle bootstrapped it. That lets a
candidate worse than the incumbent replace it once, and it cannot distinguish
"no incumbent" from "unreadable incumbent". The incumbent now carries the
protocol that scored it; anything else must be re-scored by the operator, which
measures the actual incumbent on the actual sample. The protocol constant lives in
`scripts/training/promotion.py`, which imports neither torch (lazily only) nor
training, so the loop can use it and `tests/test_loop_lifecycle.py`'s
import-isolation check still holds.

**Sample size.** 400 patches matches what v1 loaded at the production
`batch_size` 4, so evaluation cost is unchanged. v1 then kept 80 ink-containing
patches from one strip; v2 keeps the ink-containing patches of 400 spread over the
fragment. Ink-free patches are still excluded, as v1's "ink-containing patches"
message described; including them would change what F1 means and is a separate
decision.

**Per-run sampling seed.** A fixed training seed would again give every
warm-started cycle the same ~1,000 patches (spread out, but the same). The seed is
fresh per run and recorded; augmentation randomness was already unseeded, so runs
were not reproducible before either.

**Time-based schedule.** The budget is already enforced by elapsed time
(`total_training_time >= time_budget`), so the schedule now uses the same clock.
This changes training for every run: candidates now reach the configured peak LR
and anneal. Comparisons stay valid because promotion compares measured scores, and
the incumbent is re-scored under the new protocol.

**Reported-only metrics.** `val_bpb`, `avg_cc_diff` and the topology numbers are
now computed per patch rather than per batch (they no longer depend on
`batch_size`). They do not decide promotion.

**Deliberately unchanged.** `F1_NOISE_TOLERANCE` (3e-2) and `LIFT_MARGIN` stay;
the tolerance was measured under v1 and must be re-measured (below). The per-patch
jitter remains index-deterministic. The VRAM heuristic still always skips
`batch_size=24` (score 2.00); that costs a log line, not GPU time.

### Migration for the loop host

This change alters what the stored score means, so the loop refuses to start until
the incumbent is re-scored. The lock-file migration from the cross-cutting review
still applies.

```sh
./stop.sh
python3 scripts/loop_control.py status        # must report no running loop
git pull
uv run python scripts/reevaluate_best_model.py                  # dry run: compare
uv run python scripts/reevaluate_best_model.py --update-stored  # writes val_f1 + val_protocol
git add best_model.pt && git commit -m "Re-score best_model.pt under seeded-sample-400-v2"
uv run python scripts/f1_noise_probe.py       # re-measure run-to-run sigma
# update F1_NOISE_TOLERANCE in scripts/training/train.py if sigma moved
./start.sh
```

Until the re-score, `./start.sh` prints `Not starting: best_model.pt was scored under
validation protocol v1 (unrecorded) ...` and the watchdog reprints it.

## Remaining architecture observations (not changed)

- **Warm-start chaining confounds attribution.** Each candidate is the incumbent
  plus another budget of training with one tweak, compared with the incumbent's
  stored score. A tweak that does nothing still receives credit for the extra
  fine-tuning, and the family weights learn from that. A paired control (the
  unmodified config trained in the same cycle, or multi-seed means, as the
  `F1_NOISE_TOLERANCE` comment already suggests) is a design change for the owner.
- **The stored `avg_centerline_dice` is 1.349**, above any Dice's range. It is
  reported only, but `min_prize_centerline_dice` gates `submittable` on it; the
  metric's definition was not investigated here.
- **The 2026-06 12 h long-schedule study** ran through the same scheduler and
  loader: planned warmup 27,000 steps, ~12,000 steps run, final LR ~44% of the
  configured value, raster-ordered batches. A dated caveat was added to
  `reports/ink_detection_64px_window_study_2026-06.md`; the conclusion was not
  re-tested.
- If training is killed after `best_model.pt` is saved but before
  `run_result.json`, the loop counts a crash and does not promote `config.json`,
  so the two disagree. The window is the few statements between the two writes.

## Verification

Environment: CPython 3.10.20 venv with PyTorch 2.9.1 (CUDA build, no GPU visible),
NumPy, SciPy, pytest, Ruff 0.9.10 and mypy, the package installed editable, and
villa sparse-checked-out at the pin (`vesuvius/src/vesuvius`, `lasagna`,
`foundation/datasets/fibers-dataset`). No production data, no GPU. `$PY` is
`.venv/bin/python`.

### Reproductions on the baseline

Patch-catalogue order and loader reads, villa's `find_valid_patches` on a full mask
the size of the training fragment (8,181 × 6,330):

```text
catalogue size 12446 | y non-decreasing: True
train loader (no sampler), 250 steps x batch 4: indices 0 .. 999 | rows y<704 of 8181
validation, batch_size= 4: 400 patches, y<320
validation, batch_size= 8: 800 patches, y<576
validation, batch_size=16: 1600 patches, y<1088
```

Ten loop cycles with a fake supervisor and the tracked `config.json`:

```text
Cycle 10: Injecting FIXED GP-WINNER BASELINE for calibration...
Cycle 10: Skipping gp_winner_baseline (Complexity Score 74.67 > 1.5) to avoid OOM.
Cycle 11: Skipping batch_size_24 (Complexity Score 2.00 > 1.5) to avoid OOM.
```

The baseline step schedule at the logged step counts, and across `run.log.old`:

```text
day   (900s, 250 steps):  final LR = 0.445 x peak, warmup ends at step 562
night (3600s, 1050 steps): final LR = 0.467 x peak, warmup ends at step 2250
last 150 runs: past warmup=7, mean fraction=0.497899
```

The incumbent lookup (an exact replica of the baseline lines) against a
`best_model.pt` truncated mid-write:

```text
Warning: could not load best_model.pt for improvement comparison: RuntimeError
stored best was 0.47; candidate 0.20 (lift 1.5) promoted: True
```

The tracked incumbent's record:

```text
val_f1 0.46830821811402823, avg_centerline_dice 1.3493579958393833, config lr 0.000125 (config.json: 0.0005)
validation_diag: requested_patches 100, empty_target_patches 80, usable_patches 20, cc_samples 80
```

### End-to-end `train()` on CPU

`train.train()` with a tiny gated_unet (`base_feat` 8, patch 16, 8 layers,
`batch_size` 2, 8 s budget, UA-MT on), synthetic 60-patch catalogues, and `cuda`
mapped to CPU (`/tmp` harness, not committed). Baseline, then branch:

```text
Budget-Aware Scheduling: max_steps=1000, warmup_steps=125, scaled_lr=1.25e-04
CHECKPOINT config.lr 0.000125 | val_protocol None
TRAIN first reads [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
VAL reads 194 [0, 1, 2, 3, 4] ...
```

```text
Training sampling seed: 1713126192
Budget-time schedule: 12.5% warmup then cosine decay over 8.0s, peak_lr=1.25e-04
Step 0000 | Loss: 0.726489 | LR: 0.00e+00 | dt: 321ms | Remaining: 8s
Step 0010 | Loss: 0.727125 | LR: 1.03e-04 | dt: 271ms | Remaining: 5s
Step 0020 | Loss: 0.724027 | LR: 3.03e-05 | dt: 294ms | Remaining: 2s
Evaluating metrics on validation protocol seeded-sample-400-v2 (...)
CHECKPOINT config.lr 0.001 | val_protocol seeded-sample-400-v2
TRAIN first reads [54, 48, 23, 17, 2, 13, 12, 14, 41, 53, 59, 34]
VAL reads 60 [0, 1, 2, 3, 4] ...
```

Interpretation: on the baseline the 60-patch validation catalogue was read 194
times (100 batches of 2 with wrap-around, so patches counted repeatedly); on the
branch each sampled patch is read once, training order is random, the LR peaks
and decays within the budget, and the checkpoint keeps the configured `lr`.

The re-scoring path against the real tracked `best_model.pt` (model loaded by
`load_tool_checkpoint`, three synthetic inputs through
`collect_validation_predictions` with the validating probability function):

```text
settings: {'architecture': 'resenc_unet', 'patch_size': 64, 'num_layers': 16, 'base_feat': 64, 'num_blocks': 16, 'num_heads': 8, 'dropout': 0.0, 'use_ridges': True, 'multi_task_heads': True, 'ridge_sigma': 1.0}
diag: {'protocol': 'seeded-sample-400-v2', 'requested_patches': 3, 'empty_target_patches': 0, 'batch_errors': 0, 'usable_patches': 3, 'complete': True} | prob shape: (1, 1, 64, 64)
```

### Tests

```sh
OMP_NUM_THREADS=2 $PY -m pytest -q tests/test_autoresearch_measurement.py tests/test_loop_lifecycle.py tests/test_checkpoint_tool_contracts.py tests/test_vesuvius_loader.py tests/test_f1_improvement_criterion.py tests/test_improvement_criterion.py tests/test_pooled_seg_metrics.py tests/test_topology_threshold.py tests/test_prize_promotion_gates.py tests/test_disable_augmentation.py
```

```text
104 passed, 3 skipped, 3 warnings in 12.57s
```

The three skips are `tests/test_vesuvius_loader.py` cases that need a local
volume.

`tests/test_autoresearch_measurement.py` (new, 16 tests) covers the validation
sample's spread and batch-size independence, per-patch filtering, incomplete
samples, training-order coverage and fresh permutations, the time-based schedule,
every incumbent failure mode, interrupted saves, ten loop cycles without the
injection, the loop's refusal to start and the sprint-log record of a blocked
promotion. Failing-first for the loader fallback (source change stashed, test
kept):

```text
E       Failed: DID NOT RAISE ValueError
1 failed, 5 deselected in 1.92s
```

The other new tests exercise functions that did not exist on the baseline; the
reproductions above are their failing-first evidence.

### Standard validation, baseline versus branch

`scripts/run_validation_tests.py`'s list (now including the new test file and
`tests/test_vesuvius_loader.py`) with `--continue-on-collection-errors`, on a
worktree of the baseline and on the branch:

```text
baseline: 49 failed, 1832 passed, 7 skipped, 1 xfailed, 3 errors in 143.92s
branch:   47 failed, 1853 passed, 10 skipped, 1 xfailed, 3 errors in 130.67s
failing ids: baseline=52 branch=50
only failing on branch:
only failing on baseline:
FAILED tests/test_interpolation_drivers.py::test_direct_launch_freezes_all_helpers
FAILED tests/test_pseudo_handoff_contracts.py::test_sampler_is_actual_pinned_source_without_ml_bootstrap
```

Interpretation: nothing fails only on the branch. The two baseline-only failures
are artefacts of running the baseline worktree with the main checkout's venv
(corrected 2026-10-12 in the training-step review; this first said a `villa`
symlink was the cause): the editable install resolves `vesuvius_autoresearch` to
the main checkout's `src/`, and one test expects `.venv/bin/python` inside the
worktree. The same resolution means the baseline run imported the branch's
`src/vesuvius_autoresearch/core/vesuvius_loader.py`; the loader change's
failing-first evidence is the stashed-source run under "Tests". The 50 shared
failures and errors are environmental: `test_surface_render_contracts.py` (21),
`test_geometry_handoff_contracts.py` (14), `test_label_curation_contracts.py` (6),
`test_villa_metrics_integration.py` (4) and five others, from dependencies and
villa subtrees absent here. The extra passes and skips are the new tests. The
branch run preceded two edits with no behavioural effect (a docstring in
`train.py`, `itertools.islice` in a test helper); the targeted suite above was
rerun after them. This is not a substitute for the full suite.

### Documentation reference audit

```sh
$PY -m pytest -q tests/test_audit_doc_references.py
```

```text
1 failed, 8 passed in 15.09s
```

Interpretation: `test_live_documents_stay_clean` fails with output identical to the
baseline worktree's; every reported path is a villa directory outside this
review's sparse checkout (for example `villa/ink-detection` in
`docs/LAB_NOTEBOOK.md`). None comes from this change.

### Lint, formatting and typing

```sh
ruff check <changed Python files>
ruff format --check <changed Python files>
mypy run_autoresearch_loop.py scripts/reevaluate_best_model.py scripts/training/train.py src/vesuvius_autoresearch/core/vesuvius_loader.py scripts/training/promotion.py tests/test_autoresearch_measurement.py
```

```text
All checks passed!
9 files already formatted
git diff --check: clean
Found 4 errors in 2 files (checked 6 source files)
```

Interpretation: mypy reports the same four errors on the baseline and the branch
(two `torch.mean`/`torch.var` overloads in `train.py`, two list-item types in
`vesuvius_loader.py`); none is in changed code. The formatter's only change outside
new code removed two blank lines in `train.py`'s import block.

## Edge cases considered

- `batch_size` 1, 4, 8, 16 and 24 score identical patches and F1; a catalogue
  smaller than the sample; an empty catalogue; a failed read mid-sample.
- Incumbent absent, truncated, unrecorded protocol, another protocol, NaN or
  missing `val_f1`; a candidate within and beyond the tolerance; gates failing.
- A save interrupted after partial bytes; ten consecutive loop cycles; a loop
  start over an incomparable incumbent.

## What was NOT tested

- Any GPU run, the production data, the real lasagna/ridge inputs, or a real loop
  shift. The new protocol's noise and the new schedule's effect on F1 are unknown
  until `f1_noise_probe.py` and a shift run on the GPU host.
- `reevaluate_best_model.py` against the real `best_model.pt` and Fr143 (only
  against the existing synthetic checkpoint-tool fixtures, and the model-loading
  check above).
- `scripts/smoke_test.py` and the complete test suite with every dependency.

## Reviewer focus

That protocol v2 is the right sample (400 spread patches, ink-free patches
excluded), that refusing to start over a v1 incumbent is preferable to a one-off
bootstrap, and that a per-run training seed is acceptable for reproducibility.
On the GPU host: run the migration, then compare the re-scored incumbent's F1 with
0.468 and the new noise probe's sigma with 0.012.
