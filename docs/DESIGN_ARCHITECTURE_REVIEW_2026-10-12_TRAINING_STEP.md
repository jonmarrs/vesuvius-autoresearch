# Design and architecture review — the training step and its reported metrics

Date: 2026-10-12. Baseline: `c01e42d9d566ca886877bac19bceb36a046b44fa` (main after the
autoresearch-loop review). Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what one training step in `scripts/training/train.py` optimises and what its
validation reports. That covers both augmentation modes (Albumentations and villa's
batchgeneratorsv2), `scroll_augmentations.py`, mixup/cutmix, the UA-MT
semi-supervised branch, the DINO-lite projection consistency, and the per-patch
metric wrappers (connected components, critical components, mAP, centerline Dice)
behind `submittable`. The previous review fixed what a cycle samples and compares;
no earlier review read the step itself.

## What changed

UA-MT's student and teacher now see the same augmented view. The
connected-component and critical-component wrappers pass villa the `[H, W, D]`
volume it requires, read the keys it returns, and let errors reach the caller's
counters instead of reporting 0. mAP is read under villa's key. A missing metric
reports NaN rather than 0. `aug_mode="batchgeneratorsv2"` raises when villa's
pipeline cannot be imported, and preflight runs the configured augmentation, so a
cycle fails in seconds instead of silently training with the other recipe. When
the pipeline runs, the five scroll augmentations it lacks are applied after it.
Per-batch fallbacks to Albumentations are counted in `run_result.json`. The
three TSV logs are appended through one helper that checks the file's header, and
the two tracked logs whose headers had fallen behind their rows were repaired.

## Why

Production enables UA-MT (`use_uamt: true`, promoted on 2026-07-11, cycle 9), and
its consistency loss rewarded predictions that ignore the image. Three of the
reported topology numbers were constants: two from errors read as perfect scores,
one from a key mismatch. And one of the loop's swept axes could change two
things, or nothing, while recording one.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **UA-MT compared misaligned images.** The student and teacher inputs came from two independent `apply_augmentations` calls, each with its own flips, ±180° rotation, affine and scroll warps, and the loss is a pixel-wise MSE between the two predictions. With the production config, the same asymmetric bar overlapped between the two views with IoU 0.00–0.20 across eight samples (pixel MSE 0.189, against 0 when aligned). A model that segments correctly in both views is penalised; the cheapest way to lower the loss is a prediction that ignores spatial structure. Weighted by `consistency_weight` (0.1), this term was in every production cycle since UA-MT was promoted. | `train.uamt_views`: one augmented view for both networks; the teacher's four stochastic passes keep their own input noise, as in UA-MT (Yu et al., 2019). |
| P2 | **Connected-component and critical-component metrics never ran.** `train.py` passes each patch as 2D `(H, W)`; villa's metrics require `[H, W, D]` and raise, and both wrappers caught every exception and returned 0. Critical components also read `critical_components_total`, a key villa never returns (it returns `_positive` and `_negative`). A single blob covering two strokes therefore scored a perfect 0. `avg_cc_diff` feeds the `max_prize_cc_diff` gate in `submittable`, so the gate could not fail; the incumbent records `avg_cc_diff` 0.0 over 80 samples with `cc_errors` 0. | Both wrappers pass `(H, W, 1)`, read villa's actual keys (critical = positive + negative), and raise; the validation loop counts each metric's failures under its own key (`cc_errors`, new `crit_errors`). Averages over no samples are NaN, which `evaluate_prize_gates` already treats as a failure. |
| P2 | **mAP was always 0.** Villa's `mean_ap` returns `{"ap_class_1", "mean_ap"}`; `train.py` read `mAP` with a default of 0.0, so every run reported `avg_mean_ap` 0.0 with `mean_ap_errors` 0. | Reads `mean_ap`; the fallback used when villa is absent raises (counted as `mean_ap_errors`) instead of returning 0. |
| P2 | **`aug_mode="batchgeneratorsv2"` could silently mean Albumentations.** When villa's `create_training_transforms` failed to import, the mode check fell through to Albumentations with no message. It needs `fft_conv_pytorch` (and `nrrd` through villa's package imports), neither of which is in `uv.lock`, so a fresh `uv sync` cannot build it; the GPU host evidently has them installed outside the lock, since `run.log.old` shows the pipeline running. Per-batch exceptions also fell back to Albumentations, with a warning only when `step % 100 == 0`: 210 such warnings are in `run.log.old` (June, an older pin; 0 of 400 samples failed at the current pin). The swept axis could therefore record batchgeneratorsv2 for a cycle trained with the other recipe. | `apply_augmentations` raises with the import error when the mode is requested but unavailable. `preflight_smoke` now runs the configured augmentation, so the loop logs PREFLIGHT FAILED in seconds. Fallbacks are counted (`augmentation_fallbacks` in `run_result.json`) and the first three are printed. |
| P2 | **batchgeneratorsv2 also switched off the scroll augmentations.** That path returned before `apply_scroll_specific_3d_augmentations`, so the `aug_scroll_*_p` settings production enables (squeeze, intensity drift, thick slice at 0.25) did nothing in that mode, except the four villa's pipeline adds itself. A cycle sampling `aug_mode` changed the base recipe *and* dropped those augmentations. | After villa's pipeline, the five augmentations it lacks (decohesion, warping, squeeze, z-dropout, intensity drift) are applied with their configured probabilities; the four it already covers (sheet compression, thick slice, Rician noise, blank rectangles) are not applied twice. |
| P3 | **Two tracked logs were mislabelled by their own headers.** `avg_mean_ap` was added to `history.tsv` rows and `avg_crit_comp` to `prize_readiness.tsv` rows in code, but a header is only written when the file is new, so the existing headers kept the old columns: 632 of 635 `history.tsv` rows and 14 of 31 `prize_readiness.tsv` rows have 12 fields under an 11-field header. Read by its header, `history.tsv`'s `train_loss` column holds mAP, `throughput_Mvps` holds the train loss, and so on to `config`, which holds peak VRAM. | `train.append_tsv_row` writes every row of `history.tsv`, `results.tsv` and `prize_readiness.tsv`; a file whose header differs from the current columns is moved aside to `<name>.until-<timestamp>.tsv` and a new one started. The tracked files were repaired: the header now lists the current columns, and the 3 and 17 rows written before the column existed carry an empty value for it. No value was changed. |

## Reviewed and sound

- `scroll_augmentations.py`: every geometric transform (warping, squeeze, thick
  slice) applies the same grid or interpolation to the image and to both labels;
  intensity transforms leave labels alone. Labels are clamped to [0, 1].
- `mixup_data` / `cutmix_data`: the partner batch is indexed (a copy) before the
  in-place write, and the same box is cut from image, ink and fiber.
- The Albumentations recipe registers `fiber` as an additional mask target, so
  flips, affine and dropout move both labels with the image.
- The DINO-lite consistency (`p1`, `p2`) uses a globally pooled projection, so
  comparing two differently augmented views is the intended invariance, not a
  misalignment.

## Architecture and compatibility decisions

**Teacher input.** UA-MT perturbs the teacher with noise, not with a second
geometric view; matching views by inverting each transform would need every
augmentation to be invertible, and the Albumentations and villa recipes are not.

**Failing metrics.** A metric that cannot be computed is now absent (NaN, counted
error), never a value. Gates already fail closed on NaN and on too few samples,
so a broken metric blocks `submittable` instead of passing it. With
`enforce_prize_gates: false` in production `config.json`, this changes what is
reported, not what is promoted.

**Reported numbers change meaning.** From this change on, `avg_cc_diff`,
`avg_crit_comp` and `avg_mean_ap` in `run_result.json`, checkpoints,
`history.tsv` and `prize_readiness.tsv` are measurements; earlier rows hold the
constants above and should not be compared with later ones.

**Lockfile.** `uv.lock` was not regenerated: resolving it needs the
`pytorch-cu128` index, which this review's network could not reach. The GPU host's
environment should be captured in the lock (adding `fft-conv-pytorch` and
`pynrrd`) by whoever can resolve it there.

## Remaining observations (not changed)

- **UA-MT's uncertainty weighting is a no-op at the production config.** With
  `dropout: 0.0`, the teacher's four passes differ only by 0.01 input noise.
  On the production checkpoint (CPU, random input), the per-pixel teacher variance
  was at most 1.7e-7, so `exp(-var)` was 1.000000 everywhere: the branch is a
  plain mean-teacher consistency. Its weighting also cannot fall below
  `exp(-0.25)` ≈ 0.78 for probabilities. Whether UA-MT should require dropout is
  a research decision.
- **The UA-MT promotion of 2026-07-11** (cycle 9, val_f1 0.468) is the current
  incumbent. `train.py`'s own noise note calls that gain 0.8 σ of the difference,
  and the loss it trained with is the misaligned one above. Re-testing
  `use_uamt` under the corrected loss and the v2 validation protocol is the
  meaningful comparison.
- **Villa's `centerline_dice` exceeds 1 on slices with no ground-truth skeleton**
  (the tolerance map is zero there, so every predicted pixel counts as a hit):
  two patches passed as slices, one ink-free, score 1.312; the ink patch alone
  scores 1.0. The loop now scores per patch and drops ink-free patches, so it no
  longer reaches this path (the incumbent's 1.349 came from the old per-batch
  scoring). `scripts/evaluate_villa_metrics.py` scores whole volumes and is still
  exposed; the fix belongs upstream in villa.
- **The DINO-lite projection is nearly degenerate**: `Linear(1, 128)` on the
  pooled ink logit followed by `LayerNorm`, so the consistency is about the mean
  logit only.

## Verification

Environment: CPython 3.10.20 venv with PyTorch 2.9.1 (no GPU visible), NumPy,
SciPy, Albumentations < 1.4, pytest, Ruff 0.9.10 and mypy; villa sparse-checked-out
at the pin with `vesuvius/src/vesuvius`, `lasagna`,
`foundation/datasets/fibers-dataset` and `segmentation/evaluation`; plus
`requests`, `pynrrd`, `SimpleITK` and `fft-conv-pytorch` so villa's training
transforms import. No production data. `$PY` is `.venv/bin/python`.

### Reproductions on the baseline

UA-MT views, production `config.json`, an asymmetric bar augmented twice as
`train()` did:

```text
aug_mode albumentations | use_uamt True | consistency_weight 0.1
per-sample IoU of the bar between student and teacher views: [0.06, 0.18, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]
pixel MSE student vs teacher views: 0.1894 | aligned control: 0.0
```

Metric wrappers called as `train.py` calls them (2D patches; two strokes against
one covering blob):

```text
blob     cc_diff=0 crit=0
perfect  cc_diff=0 crit=0
villa CC on 2D input raises: ValueError Label array must have shape [H, W, D] or [N, H, W, D].
villa crit on 2D input raises: ValueError not enough values to unpack (expected 3, got 2)
mean_ap as train.py passes {'ap_class_1': 1.0, 'mean_ap': 1.0}
```

With a trailing depth axis, villa reports the blob as 1 component off and the
perfect prediction as 0.

UA-MT teacher variance on the production checkpoint:

```text
config dropout: 0.0 | teacher prob range: 0.024 0.0731
teacher variance: max 1.68e-07 mean 1.74e-08 | exp(-var) min 1.000000
```

batchgeneratorsv2 at the current pin, production shapes (2 channels, 16 slices,
64 px), 400 samples:

```text
per-sample failures: 0/400 = 0.0%
```

### End-to-end `train()` on CPU

The harness from the previous review (tiny gated_unet, synthetic 60-patch
catalogues, UA-MT on, `cuda` mapped to CPU), baseline then branch:

```text
baseline: "avg_cc_diff": 0.0, "avg_crit_comp": 0.0, "avg_mean_ap": 0.0, ... "cc_errors": 0, "mean_ap_errors": 0
branch:   "avg_cc_diff": 3.216666666666667, "avg_crit_comp": 10.9, "avg_mean_ap": 0.5072120752071537, "augmentation_fallbacks": {"batchgeneratorsv2": 0}, ... "cc_errors": 0, "crit_errors": 0, "mean_ap_errors": 0
```

Interpretation: the same run reported three constants before and three
measurements after; the training path including the UA-MT branch runs end to end.

### Tests

New `tests/test_training_step_contracts.py` (11 tests). Failing-first with only
`train.py` reverted, before the three log tests were added:

```text
7 failed, 1 passed in 3.47s
```

The passing one checks villa's `mean_ap` key contract, which held on the baseline;
the end-to-end run above shows `train.py` now reads it. With the log tests added,
the file errors at collection on the baseline (the column constants it imports do
not exist there); the field counts below are their failing-first evidence.

### TSV logs

Field counts per line on the baseline (first line is the header):

```text
history.tsv:          4 lines with 11 fields, 632 with 12   (header: 11)
prize_readiness.tsv:  18 lines with 11 fields, 14 with 12   (header: 11)
```

After the repair, and from the CPU harness with promotion forced so all three
writers run inside `train()`:

```text
history.tsv:          636 lines with 12 fields
prize_readiness.tsv:  32 lines with 12 fields
harness history.tsv          header=12 fields: 12 x2
harness results.tsv          header=11 fields: 11 x2
harness prize_readiness.tsv  header=12 fields: 12 x2
```

```sh
OMP_NUM_THREADS=2 $PY -m pytest -q tests/test_training_step_contracts.py tests/test_disable_augmentation.py tests/test_scroll_specific_augmentations.py tests/test_autoresearch_measurement.py tests/test_loop_lifecycle.py tests/test_checkpoint_tool_contracts.py tests/test_topology_threshold.py tests/test_prize_promotion_gates.py tests/test_villa_metrics_integration.py tests/test_confidence_weighted_loss.py
```

```text
103 passed, 1 skipped, 3 warnings in 9.49s
```

### Smoke test

```sh
CUDA_VISIBLE_DEVICES="" $PY scripts/smoke_test.py
```

```text
--- 9/11 passed, 2 skipped, 0 failed in 6.2s ---
```

Interpretation: `augmentations_bg2` ran (villa's transforms import here); the two
skips need local fragment data.

### Standard validation, baseline versus branch

`scripts/run_validation_tests.py`'s list (now including the new test file) with
`--continue-on-collection-errors`, on a baseline worktree and on the branch:

```text
baseline: 45 failed, 1855 passed, 10 skipped, 1 xfailed, 2 errors in 131.10s
branch:   43 failed, 1868 passed, 10 skipped, 1 xfailed, 2 errors in 136.45s
failing ids: baseline=47 branch=45
only failing on branch:
only failing on baseline:
FAILED tests/test_interpolation_drivers.py::test_direct_launch_freezes_all_helpers
FAILED tests/test_pseudo_handoff_contracts.py::test_sampler_is_actual_pinned_source_without_ml_bootstrap
```

Interpretation: nothing fails only on the branch. The two baseline-only failures
come from running the worktree with the main checkout's venv: its editable
install resolves `vesuvius_autoresearch` to the main checkout's `src/`, and one
test expects `.venv/bin/python` inside the worktree. (The previous review blamed
a `villa` symlink; that explanation is corrected in its document.) This change
touches nothing under `src/`, so the comparison is otherwise like for like. The
45 shared failures are environmental: `test_surface_render_contracts.py` (21),
`test_geometry_handoff_contracts.py` (14), `test_label_curation_contracts.py` (6)
and four others. With villa's `segmentation/evaluation` now checked out,
`test_villa_metrics_integration.py` passes on both. Not a substitute for the full
suite.

### Lint, formatting and typing

```sh
ruff check scripts/training/train.py scripts/run_validation_tests.py tests/test_training_step_contracts.py
ruff format --check scripts/training/train.py scripts/run_validation_tests.py tests/test_training_step_contracts.py
git diff --check
mypy scripts/training/train.py tests/test_training_step_contracts.py
```

```text
All checks passed!
3 files already formatted
git diff --check: clean
mypy: the same two errors as the baseline (torch.mean / torch.var overloads in train.py)
```

## Edge cases considered

- UA-MT views with geometric scroll augmentations enabled; the teacher's noise
  passes unchanged.
- A metric that raises, a metric module that is absent, a perfect prediction, a
  merged prediction, no samples at all.
- batchgeneratorsv2 unavailable (preflight), available with each kind of scroll
  augmentation configured, and raising mid-run.
- A log with an older header, a log that matches, a row with the wrong number of
  values, and the two tracked logs against the columns `train.py` writes.

## What was NOT tested

- Any GPU run or production data; the effect of the corrected UA-MT loss on F1 is
  unmeasured.
- The GPU host's batchgeneratorsv2 environment (its packages are outside the lock).
- `scripts/evaluate_villa_metrics.py` was not changed.

## Reviewer focus

That feeding the teacher the student's view (noise-only perturbation) is the
UA-MT you intend, and that reporting NaN for an unmeasurable metric is preferable
to 0 for every consumer of `history.tsv` and `prize_readiness.tsv`. On the GPU
host: capture the environment in `uv.lock`, then re-test `use_uamt` against the
re-scored incumbent.
