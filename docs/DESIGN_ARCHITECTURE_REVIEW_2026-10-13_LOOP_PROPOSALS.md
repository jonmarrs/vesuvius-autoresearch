# Design and architecture review — loop proposals, crash streaks, the validation read, and the lasagna warp

Date: 2026-10-13. Baseline: `4a8393b7` (main after the labeled-dataset review and the strict
preprocessing review). Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how `run_autoresearch_loop.py` turns the bandit's choice into a cycle, what a cycle spends
before its result is known, what the loop does when cycles keep failing, and the lasagna
flattening that `config.json` requests (`_apply_lasagna_flattening` in
`src/vesuvius_autoresearch/core/vesuvius_loader.py`). The owner's decisions from finding 86
(`reports/loop_v2_constant_control.md`) are not taken here: lasagna stays requested and
unapplied, and the metric and noise tolerance are unchanged.

## What changed

- The VRAM estimate filters values before the bandit samples, so a value over the cap is never
  proposed.
- `train.py` reads one strict validation patch before it loads any training data, so a run whose
  validation cannot be read fails before training instead of after its budget.
- Five crashed cycles in a row pause the loop (`.loop_paused`) for the operator instead of letting
  the watchdog restart it into the same failure.
- The lasagna warp says which patches it cannot take, and why, before doing any work: uint8 on
  the CPU (villa's kernel takes CUDA tensors only) and int32 (uint16 volumes). The uint8 call now
  meets the kernel's contract (a 4-D grid and a contiguous volume).
- Finding 86's report carries a correction, because its "install a CUDA toolkit" option would not
  have made the warp run.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **Finding 86's lasagna diagnosis named the wrong cause.** Every logged failure was the extension's JIT compile (no `nvcc`, `CUDA_HOME` unset), so the report offered "install a CUDA toolkit" as a way to make the warp run. It would not: `villa/lasagna/grid_sample_3d_u8_kernel.cu` checks that every input is a CUDA tensor, that the volume is contiguous, and that the grid is `(D, H, W, 3)`. The loader reads patches on the CPU (`get_raw_patch` returns `torch.from_numpy(...)`) and passed a `(1, D, H, W, 3)` grid, so with a toolkit installed every patch would fail the kernel's checks instead. uint16 volumes (read as int32) failed too, in the surface estimate. The test of this call stubbed the kernel with a CPU function that accepted anything. | `_lasagna_unavailable_reason` refuses a uint8 patch that is not on CUDA, and any non-float integer patch, before the surface estimate and before the extension loads. Training counts the refusal as a `lasagna_warp_failed` warning; strict reads raise it. Nothing that was computed changes, because the warp never ran. The grid is 4-D and the volume is made contiguous. The stub enforces all of the kernel's checks: on CPU with the device refusal bypassed, and on CUDA where available. Correction added to `reports/loop_v2_constant_control.md`. |
| P2 | **The loop could crash-loop for a whole shift.** A crash does not change the bandit's weights, and the watchdog restarts a loop that returns. So a broken baseline, data path or host repeats until someone looks. On the 2026-04-24 night the logs record 4,704 crashed cycles in a row; 15 sprints since April have streaks of 50 or more. | `MAX_CONSECUTIVE_CRASHES = 5`: the loop writes the reason to the sprint log and stdout, creates `.loop_paused` (which the watchdog honours and `./start.sh` clears), and exits. A completed cycle resets the count. |
| P2 | **A run whose validation could not be read still trained for its full budget.** Since the strict preprocessing review, a validation read that cannot apply a requested step fails, and `collect_validation_predictions` marks the sample incomplete, which blocks promotion. With `config.json`'s `use_lasagna: true` on uint8 volumes, that is every patch, so every cycle that keeps lasagna on would train for 15 or 60 minutes and then be unscoreable. `train.py` built the validation dataset early so that an empty catalogue "fails in seconds, not after the training budget", but it read no patch. | `probe_validation_read` reads the protocol's first patch (the index the measurement reads first) at the top of `train()`, before the training and UA-MT loaders are built. A failure there means the measurement could not be complete, so stopping loses nothing that could have counted. |
| P3 | **The VRAM gate ran after sampling.** `batch_size: 24` scores 2.00 against the 1.5 cap at the production structure (batch 4, 16 layers, `base_feat` 64), so it was always rejected, but only after the cycle had taken a cycle number, a slot in the dedup list, and a 0.95 decay step for every active family, with no sprint-log entry. In the sprint logs since the 2026-06-09 pinning, 20 cycle numbers that are not every-10th (those were the removed GP baseline) are missing, and `batch_size_24` never appears. No GPU time was lost: the skip came before training. A baseline over the cap made every cycle a skip, with no sleep between them. | `complexity_score(config)` is a function. `tweak_proposals` scores each changed value once and keeps only those under the cap; the cap is read at call time. A baseline over the cap is offered only tweaks that bring it under; if there are none, the sprint ends with that reason. Exclusions are printed and written to the sprint log when they change. |

## Review of the PR, and what it changed

The first version was reviewed (code-review skill) before merging. Its findings, and what was
done:

| Finding | Outcome |
| --- | --- |
| On this `config.json`, the fast-failing probe turns lasagna cycles into a crash loop the bandit never penalises. | Fixed by the crash-streak pause above. The sprint logs show the loop already crash-looped for whole shifts, so the pause is not only about this config. |
| uint16 volumes (read as int32) cannot be warped either, but the docs said only uint8 could not. | Fixed: refused with that reason; documented. |
| The first version relaxed the cap to `max(cap, baseline score)`, so over-cap configs could launch while the log said nothing was excluded. | Fixed: the cap is hard again; an over-cap baseline is named in the log. |
| The device check ran after the surface estimate, wasting work on every refused patch. | Fixed: checked first; a test fails if the softmax runs. |
| The probe ran after the training loaders were built. | Fixed: it runs first in `train()`; the test checks it precedes `get_dataloader`. |
| `cap=VRAM_COMPLEXITY_CAP` was bound at definition while `main()` logs the global. | Fixed: resolved per call; tested. |
| The CPU suite lost coverage of the uint8 path after the device check, and the stub omitted the kernel's dtype, contiguity and `numel` checks. | Fixed: the full contract stub runs on CPU with the refusal bypassed; a non-contiguous patch is used, and removing `.contiguous()` fails the test. |
| Exclusions were scored twice per cycle. | Fixed: one pass returns both. |
| The kernel pads with zeros where the float path repeats the edge. | Already documented below and now in the docstring. No code change: the warp never runs. |
| Refuse at dataset construction instead of per patch. | Not changed. Per-patch refusal keeps one failure path, shared with ridges and Frangi (strict raises, training warns), and the check is now cheap. The probe surfaces it before training. |

## Reviewed and sound

- The bandit's family weights (`template_weights`), the decay floor of 1.0, and the dedup
  fallback that accepts the last sample after ten duplicates: unchanged. With the VRAM filter, the
  fallback can no longer accept a value over the cap.
- The preflight smoke check exercises the model and augmentation on synthetic input on the CPU. It
  cannot see data reads, which is why the read check belongs in `train()`, where the real
  validation dataset exists.
- The float lasagna path (torch `grid_sample`, normalised coordinates, `align_corners=True`)
  samples the same coordinates as the uint8 path's absolute ones and runs on any device. The two
  differ where a column's shift leaves the patch: the float path repeats the edge slice
  (`padding_mode="border"`), while villa's kernel reads zeros.

## Architecture notes for the owner (not changed)

- **If lasagna is made to run,** the warp has to happen in the training process on the GPU (the
  data loader's workers read on the CPU), or on the CPU through the float path. For the CPU route,
  the patch has to be converted, warped and rounded back to its integer type so normalisation
  still applies, and the edge padding chosen deliberately, since the two paths differ there.
  Either way, inference must apply it too: `scripts/inference/predict.py`,
  `scripts/production_predict.py` and `scripts/inference/ensemble_predict.py` never flatten, so a
  model trained on warped patches would be served unwarped ones. No checkpoint is affected today,
  because the warp has never run.
- **Until that decision,** a loop restarted on this `config.json` crashes, before training, every
  cycle that keeps `use_lasagna: true`, and after five in a row it pauses itself. Setting
  `use_lasagna` to `false` (finding 86's second option) makes the config describe what every
  stored checkpoint was trained on.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The
baseline is a worktree of `4a8393b7` with `PYTHONPATH` set to its own `src/`, asserted before the
run. Both trees run the full `scripts/run_validation_tests.py` list.

New and changed tests:

- `tests/test_loop_lifecycle.py`: the reference config scores 1.0; values over the cap are never
  proposed; an over-cap baseline gets only tweaks that bring it under; the cap is read per call.
- `tests/test_autoresearch_measurement.py`: five crashes in a row pause the loop; a completed
  cycle resets the streak.
- `tests/test_training_step_contracts.py`: the probe reads exactly the protocol's first index and
  names it on failure; `train()` probes before loading training data.
- `tests/test_preprocessing_contracts.py`: the probe stops a strict lasagna config on the uint8
  fixture; the lasagna failure and invalid-result cases run the float warp, which can execute on
  the CPU.
- `tests/test_villa_modules.py`: refused patches never reach the surface estimate or the kernel;
  the contract stub runs on CPU and on CUDA.

Not verified here: the real villa kernel on a GPU, and a loop cycle on the GPU host.
