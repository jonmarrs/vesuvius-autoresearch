# Design and architecture review — loop proposals, the validation read, and the lasagna warp

Date: 2026-10-13. Baseline: `4a8393b7` (main after the labeled-dataset review and the strict
preprocessing review). Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `run_autoresearch_loop.py` turns the bandit's choice into a cycle, what a cycle spends
before its result is known, and the lasagna flattening that `config.json` requests
(`_apply_lasagna_flattening` in `src/vesuvius_autoresearch/core/vesuvius_loader.py`). The owner's
decisions from finding 86 (`reports/loop_v2_constant_control.md`) are not taken here: lasagna stays
requested and unapplied, and the metric and noise tolerance are unchanged.

## What changed

The VRAM estimate filters values before the bandit samples, so a value it rejects is never
proposed. `train.py` reads one strict validation patch before training, so a run whose validation
cannot be read fails before training instead of after its budget. The lasagna uint8 warp refuses a CPU
patch with the real reason (villa's kernel takes CUDA tensors) and passes the kernel's 4-D grid;
finding 86's report carries the correction, because its "install a CUDA toolkit" option would not
have made the warp run.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **Finding 86's lasagna diagnosis named the wrong cause.** Every logged failure was the extension's JIT compile (no `nvcc`, `CUDA_HOME` unset), so the report offered "install a CUDA toolkit" as a way to make the warp run. It would not: `villa/lasagna/grid_sample_3d_u8_kernel.cu` checks that every input is a CUDA tensor and that the grid is `(D, H, W, 3)`. The loader reads patches on the CPU (`get_raw_patch` returns `torch.from_numpy(...)`) and passed a `(1, D, H, W, 3)` grid, so with a toolkit installed every patch would fail the kernel's checks instead. The test that covered this call stubbed the kernel with a CPU function that accepted anything. | A uint8 patch not on CUDA is refused before the extension is loaded, with that reason, as a counted `lasagna_warp_failed` warning in training and an error under strict reads (no change in what is computed: the warp never ran). The grid is 4-D. The stub now enforces the kernel's checks and runs only where CUDA is available; a CPU test asserts the refusal and that the kernel is never loaded. Correction added to `reports/loop_v2_constant_control.md`. |
| P2 | **A run whose validation could not be read still trained for its full budget.** Since the strict preprocessing review, a validation read that cannot apply a requested step fails, and `collect_validation_predictions` marks the sample incomplete, which blocks promotion. With `config.json`'s `use_lasagna: true` on uint8 volumes that is every patch, so every cycle that keeps lasagna on would train for 15 or 60 minutes and then be unscoreable. `train.py` already built the validation dataset first, so that an empty catalogue "fails in seconds, not after the training budget", but it read no patch. | `probe_validation_read` reads the protocol's first patch (the same index the measurement reads first) right after `build_validation_dataset`, before the model is built. Any failure there means the measurement could not be complete, so stopping costs nothing that could have counted. |
| P3 | **The VRAM gate ran after sampling.** `batch_size: 24` scores 2.00 against the 1.5 cap at the production structure (batch 4, 16 layers, `base_feat` 64), so it was always rejected, but only after the cycle had taken a cycle number, a slot in the 20-entry `recent_configs` window, and a 0.95 decay step for every active family, with no sprint-log entry. In the sprint logs since the 2026-06-09 pinning, 20 cycle numbers that are not every-10th (those were the removed GP baseline) are missing, and `batch_size_24` never appears. No GPU time was lost: the skip came before training. | `complexity_score(config)` is a function, and `active_tweaks` drops values whose config exceeds the cap. A value is only dropped if it also raises the estimate above the baseline's own, so a baseline already over the cap (an operator's config that runs) can still be tweaked on other axes instead of skipping every cycle. Exclusions are printed and written to the sprint log when they change. |

## Reviewed and sound

- The bandit's family weights (`template_weights`), the decay floor of 1.0, and the dedup
  fallback that accepts the last sample after ten duplicates: unchanged, and with the VRAM filter
  the fallback can no longer accept a value the cap rejects.
- The preflight smoke check exercises the model and augmentation on synthetic input on the CPU; it
  cannot see data reads, which is why the read check belongs in `train()`, where the real
  validation dataset exists.
- The float lasagna path (torch `grid_sample`, normalised coordinates, `align_corners=True`)
  samples the same coordinates as the uint8 path's absolute ones and runs on any device. They
  differ where a column's shift leaves the patch: the float path repeats the edge slice
  (`padding_mode="border"`), villa's kernel reads zeros.

## Architecture notes for the owner (not changed)

- **If lasagna is made to run,** the warp has to happen in the training process on the GPU (the
  data loader's workers read on the CPU), or on the CPU through the float path with the patch
  converted and rounded back to uint8 so the /255 normalisation still applies (and the edge
  padding chosen deliberately, since the two paths differ there). Either way
  inference must apply it too: `scripts/inference/predict.py`, `scripts/production_predict.py` and
  `scripts/inference/ensemble_predict.py` never flatten, so a model trained on warped patches would
  be served unwarped ones. No checkpoint is affected today, because the warp has never run.
- **Until that decision,** a loop restarted on this `config.json` crashes every cycle that keeps
  `use_lasagna: true`, now before training starts. Setting it to `false` (finding 86's second
  option) describes what every stored checkpoint was trained on.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff, mypy. The
baseline is a worktree of `4a8393b7` with `PYTHONPATH` set to its own `src/`, asserted before the
run; both trees run the full `scripts/run_validation_tests.py` list.

- New and changed tests: `tests/test_loop_lifecycle.py` (the reference config scores 1.0; values
  over the cap are never proposed; a baseline over the cap keeps its other axes),
  `tests/test_training_step_contracts.py` (the probe reads exactly the protocol's first index and
  names it on failure; `train()` probes before building the model),
  `tests/test_preprocessing_contracts.py` (the probe stops a strict lasagna config on the uint8
  fixture; lasagna failure and invalid-result cases now run the float warp, which can execute on
  the CPU), `tests/test_villa_modules.py` (the CPU refusal never loads the kernel; the CUDA-only
  contract test).
- Not verified here: the real villa kernel on a GPU, and a loop cycle on the GPU host.
