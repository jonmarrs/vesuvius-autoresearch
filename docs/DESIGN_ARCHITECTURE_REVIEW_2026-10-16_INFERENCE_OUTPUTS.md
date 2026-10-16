# Design and architecture review — what inference writes, and says it wrote

Date: 2026-10-16. Baseline: `6ca7cccd` (main after #87). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Follow-up: [PR #88 review fixes](PR88_REVIEW_FIXES_2026-10-16.md) records the
custom-sidecar invalidation and coherence-boundary corrections, with validation
against the reviewed head. The results below describe the original review.

Scope:
- the inference path: `scripts/inference/predict.py` (which the loop runs as its benchmark every fifth cycle) and
  `scripts/inference/ensemble_predict.py`;
- what they write, and the metadata that describes it;
- the optional fiber coherence score (`scripts/compute_fiber_coherence.py`).

## What changed

- **A model without a fiber head exports no fiber prediction.** `predict.py` and `ensemble_predict.py` ask each
  model which heads it trains (`model_wrappers.task_heads`).
  - A model without a fiber head returns its ink logits as "fiber". That was written as `_fiber.npy`, `.png` and
    `.zarr`, drawn as "Fiber Context", and summarised as `fiber_stats`: the ink map under the fiber prediction's
    name.
  - Now none of these is written, the figure's panel says "No fiber head", and the metadata records the heads
    (`task_heads`; `ensemble_task_heads` per member).
  - An ensemble exports a fiber prediction only when every member has the head.
  - `rank_scroll23_candidates.py` reads a prediction's `_fiber.npy` by name, and its mean weighs on the lasagna
    worklist's priority (`build_lasagna_fiber_worklist.py`). It now reads the file only when the prediction's
    metadata records fiber statistics, so a fiber file left by an earlier model of the same region does not count.
- **The metadata is removed before the arrays are written, and rewritten last.** Every run for one region writes the
  same names; the loop's benchmark always predicts one region. A run cut short after its arrays (the loop's 600 s
  timeout, a stop, an error in the figure) left the previous run's `_meta.json` describing them: the previous
  model's config and statistics.
- **The fiber coherence score works.**
  - `--compute_coherence` called `StructureTensorComputer.compute_st` and `.layout`, which villa's computer does not
    have. Every run failed, as a printed warning, and recorded `fiber_coherence: null`.
  - It now uses villa's `compute` and `eigendecompose`.
  - Its components are smoothed at three times the gradient scale. Unsmoothed, each pixel's tensor is one gradient's
    outer product, rank 1, so its anisotropy is 1 everywhere, noise included.
  - The fractional anisotropy is written for n eigenvalues, sqrt(n / (n − 1)) · |λ − λ̄| / |λ|. It is the usual
    formula for a 3-D block and |λ1 − λ2| / |λ| for the 2-D slice `predict.py` passes.
  - Villa is found from the checkout, not the working directory. A missing villa raises an `ImportError`, which
    predict reports. The module used to exit the whole process at import, after predict had written its outputs.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **A model without a fiber head exported its ink map as the fiber prediction.** With `multi_task_heads=False` (a value the loop's tweak templates can promote for `resenc_unet`), and for `lejepa_unet` and `neural_tracing_vit`, the wrapper returns the ink logits as fiber. `predict.py` wrote them as `_fiber.npy`, `_fiber.png` and `_fiber.zarr`, in the figure and in `fiber_stats`, so the benchmark and any evidence export named the ink map a fiber prediction. `validate_prize_artifact.py` would accept the fiber zarr, and the candidate ranking counted its mean as fiber. Today's incumbent has real heads. | Fiber outputs only for a model (and an ensemble whose members all) with a fiber head; the metadata records the heads; the ranking reads a fiber file only when the metadata records one. Tests: no fiber files, no fiber zarr path and empty fiber stats without the head (single and ensemble); a mixed ensemble exports none; with real ResEnc weights, the head decides; the ranking ignores an unrecorded fiber file. Fail on main. |
| P3 | **A benchmark cut short left the previous run's metadata beside its arrays.** The outputs reuse one name per region, and `_meta.json` is written last. A timeout, a stop or an error after the arrays left the new arrays with the old metadata. | The metadata is removed first. Test: a run that fails at the figure leaves its arrays and no metadata, not the stale file (single and ensemble). Fails on main. |
| P4 | **`--compute_coherence` never worked, and said so only as a warning.** Besides the missing methods, the formula ran on the unsmoothed tensor, where it is 1 everywhere. | Villa's API, smoothed. Tests: oriented stripes score above 0.95 and noise under 0.7; a 3-D block is accepted, other shapes refused; `predict.py --compute_coherence` records a number. Fail on main. |

## Review of the PR, and what it changed

The owner's commit `a496c740` fixed two findings of their own review
([PR #88 review fixes](PR88_REVIEW_FIXES_2026-10-16.md)):
- a custom `--metadata_out` left the region's default sidecar in place, still vouching for old fiber files;
- villa's zero padding gave a constant field coherence (0.59 for a constant 64 × 64 slice).

The independent review of the PR at that head found nothing blocking. It checked that reverting each fix fails its
tests, and that every model predict can build declares its heads. Its other findings:

| Finding | Outcome |
| --- | --- |
| No test protects the reflected halo. With `halo = 0` every coherence test passed: mean-centring alone keeps the constant and offset cases at 0. Without the halo, a slowly varying field is cut at the crop edge (`sin(0.1 x)` scored 0.91 in 2-D, 0.84 in 3-D, instead of 1.0). | Tested on that field, in 2-D and 3-D; fails with `halo = 0`. |
| A singleton axis was scored as an axis. A (1, H, W) block, the shape of predict's `_ink.zarr` and of the CLI's natural input, has a zero eigenvalue, so any texture scored at least about 0.71 (noise 0.76, against 0.36 as a slice). | Singleton axes are dropped, after the 2-D/3-D check, so a 4-D input is still refused. Fewer than two axes longer than one is refused. Tested. |
| The `1e-8` in FA's denominator made the score depend on intensity scale: unit noise 0.36, the same noise × 1e-4 0.001. | The centred field is divided by its standard deviation. Tested from × 1e-4 to × 1e3. |
| The ensemble asked for its members' heads after inference, so a member that declares none failed only after the whole region was predicted. | Asked right after loading. Tested: refused before the volume is opened. |
| `production_predict.py` wrote its zarr before its metadata, with no removal first. | It uses `invalidate_prediction_metadata`. Tested with a run stopped before the metadata. |
| `docs/VOLUME_INFERENCE.md` still said every regional run writes fiber maps, and described the ink-as-fiber output. | Updated. It now covers the heads in the metadata, the sidecar removal, and that with `--metadata_out` elsewhere the default sidecar is not rewritten. |
| Old fiber files stay beside a headless rerun. A VC3D user loading `*_fiber.zarr` gets the earlier model's map. | Stays as is. The metadata names the outputs a run wrote, and the ranker follows it. Deleting a directory the run did not write is a larger step than this PR's; recorded below. |
| The ranker cannot tell a pre-PR headless sidecar apart: its `fiber_stats` hold the ink map. | Stays as is. Such sidecars record no heads, so no check can tell them apart. |
| The CLI loads the whole level-0 array, now as float64 plus a padded copy. | Stays as is; recorded. |

## Observations for the owner (not changed)

- **The benchmark reads today's incumbent outside the band it was scored on.**
  - `predict.py` centres the window in the checkpoint's recorded `depth_band`, and in the volume when there is none,
    as the loop's comment says.
  - The incumbent records none in its config. Its re-score's band, `[1, 27]`, is only in `reevaluation` and in
    the protocol string (`seeded-sample-400-v2+z1-27`). So the benchmark reads at the volume's centre (z = 8 on
    Fr143) rather than the band's (z = 6).
  - A model trained under today's `config.json` records the band, so the next promotion ends this. Reading the
    re-score's band as well would end it now; which band the benchmark reads is the owner's call.
  - `BENCHMARK_URI` is a constant. It equals `config.json`'s `val_uri` today, as the comment says, but does not
    follow it.
- **Inference reads more leniently than validation.**
  - A failed ridge filter gives a zero channel with a warning (`FastVesuviusVolume`, `strict=False`), and an
    unknown CT dtype falls back to `/255`. Validation refuses both.
  - Neither the counts nor a strict mode reach the prediction's metadata.
- **A recorded `use_lasagna` is not applied at inference.** Only the re-score handles it. The loop pins it off, and
  the incumbent records false.
- **The fallbacks for a checkpoint missing shape-defining keys differ** between `predict.py` (patch 32,
  `base_feat` 128) and `ensemble_predict.py` (patch 64, 16 layers, `base_feat` 64); `checkpoint_tools` refuses such
  a checkpoint. Every current writer records them all.
- **A mixed-depth ensemble gives its shallower members the top slices** of the deepest member's window, not their
  own centred window. The metadata records one z.
- **Files the benchmark writes are tracked but never committed.** `reports/benchmark_v210_cycle*.png` and
  `reports/pred_10_*` are tracked. The loop commits only its promotion files.
- **A run's outputs that it does not rewrite stay beside it.** An uncertain-patch export, or a fiber file from an
  earlier model of the same region, keeps its name until overwritten. The metadata says which outputs this run
  wrote, and the ranking now follows it; a reader that lists the directory does not.
  - Nor does a VC3D user who loads `*_fiber.zarr`, as `launch_vc3d.py` suggests.
- **`compute_fiber_coherence.py --input` reads the whole level-0 array into memory**, as float64 and then a padded
  float32 copy.

## Reviewed and sound

- **Weights load strictly** in `predict.py`, `ensemble_predict.py` and `checkpoint_tools`, with every
  shape-defining setting taken from the checkpoint's own config. A ridge or heads mismatch fails loudly.
- **The loop's benchmark invocation**:
  - it runs from the repo root, after the incumbent is settled;
  - every argument it passes exists;
  - its supervisor stops the group on the timeout.
- **The blending window is strictly positive**, so a complete region has no uncovered pixel. The depth window and
  the ridge context match validation's read.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `981a8967` (#87), whose tree is `6ca7cccd`'s but for its review doc's result
  lines. It was 42 failed, 2194 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch, first run: 44 failed, 2199 passed, 15 skipped, 1 xfailed, 2 errors. The 2 extra failures were
  `test_prediction_uses_checkpoint_scale_for_both_exports_and_metadata`: its stub model declared no heads, which
  `task_heads` refuses. It now declares a fiber head, since it checks the fiber zarr.
- Branch, with the ranking fix (PR first head, `18063df1`): 42 failed, 2203 passed, 15 skipped, 1 xfailed,
  2 errors. The failures and errors are the same set as the baseline; the 9 extra passes are the new tests.
  `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- The owner's head (`a496c740`), run here: 42 failed, 2218 passed, 15 skipped, 1 xfailed, 2 errors. Same set; its
  15 new tests pass. Ruff and mypy, which its report could not run, are clean.
- After the PR review's fixes (`1837cc1c`): 42 failed, 2224 passed, 15 skipped, 1 xfailed, 2 errors. Same set; the 6
  extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped. The six new tests
  (`test_coherence_reads_slow_structure_to_the_crop_edge` in 2-D and 3-D, `test_coherence_drops_singleton_axes`,
  `test_coherence_does_not_depend_on_intensity_scale`, `test_ensemble_asks_its_members_heads_before_reading_volume`,
  `test_a_production_run_cut_short_leaves_no_previous_metadata`) each fail with their fix reverted. The affected
  modules with `test_task_heads` and `test_predict_checkpoint_loading`: 256 passed. The nine documentation guards:
  1 failed, 90 passed, 2 skipped, as on the baseline, with the same diagnostic (villa paths this checkout lacks).
- `tests/test_volume_inference_contracts.py`, `test_submission_contracts`, `test_production_predict` and
  `test_prize_readiness`: 212 passed.
- Ruff (check and format) and mypy on the four changed scripts: clean.

New tests in `tests/test_volume_inference_contracts.py` (each fails on main):
- `test_a_model_without_a_fiber_head_exports_no_fiber_prediction` (single, ensemble);
- `test_an_ensemble_exports_fiber_only_when_every_member_has_the_head`;
- `test_a_run_cut_short_leaves_no_metadata_from_the_previous_one` (single, ensemble);
- `test_fiber_coherence_tells_oriented_structure_from_noise`;
- `test_predict_records_the_fiber_coherence_it_is_asked_for`.

New test in `tests/test_prize_readiness.py`: `test_rank_scroll23_candidates_reads_the_fiber_map_its_prediction_wrote`
(written and not written; the second fails on main).

`test_real_resenc_weights_match_direct_model_probabilities` now expects no fiber output without real heads.

Not verified here: the loop's benchmark on the GPU host.
