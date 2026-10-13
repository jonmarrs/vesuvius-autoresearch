# Design and architecture review — supervised losses, the update step, and which slices a patch shows

Date: 2026-10-13. Baseline: `43e73055` (main after the inference-consistency review). Villa pin:
`9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: what the 2026-10-12 training-step review left out of `scripts/training/train.py`:

- the supervised losses and their targets (ink BCE and Dice, label smoothing, confidence
  weighting, the Sobel-Z and Frangi fiber targets, the QC and structure-tensor terms);
- the backward pass and optimizer update;
- the warm start from `best_model.pt`;
- experiment tracking;
- which slices of the volume each training and validation patch shows the model, and where the
  loop's benchmark looks.

The owner's decisions from finding 86 (`reports/loop_v2_constant_control.md`) are not taken
here. The depth finding below is added to them.

## What changed

- **Update step.** It skips a step whose gradient is not finite instead of applying it, and checks
  that once per step instead of once per parameter tensor. `run_result.json` counts skipped steps
  (`skipped_updates`).
- **Benchmark depth.** The loop's every-5th-cycle benchmark predicts at the centre of the
  validation volume's depth instead of at slice 10.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1, owner decision | **Patches show the model a random depth, and most miss the inked surface.** `VesuviusLabeledDataset.__getitem__` draws each patch's read start uniformly over the whole depth (`z0 = rng.randint(0, z_range + 1)`), for training and for validation (seed 42). `patches.json` carries only `y` and `x`. The ink label is the 2D surface label either way. The project's own detector, the Grand Prize recipe that reached held-out pixel-AUC 0.711 on the same Fr47 to Fr143 split, reads only slices 17–42 (`detector/config.py`), and surface volumes are built around the segment surface at their middle layer. On a 65-slice volume (an assumption: the fragments' depth is not recorded here), with `num_layers` 16 plus the 8-slice context, 38% of validation windows contain slice 32 and 26% lie inside 17–42; training, with its 0–7 offset, gives the same fractions. So most patches ask the model to find ink in slices that do not show the inked surface, which is consistent with finding 86's near-constant incumbent (AUC 0.55). This is a hypothesis; it was not tested here. | **Not changed**, because it changes what validation measures: the stored incumbent score would no longer be comparable, and the loop would refuse to start until it is re-scored. Plan for the owner below. |
| P2 | **A non-finite gradient was applied.** AMP is off (`amp_enabled = False`), so `GradScaler` does not skip non-finite steps. A finite loss with a NaN or infinite gradient went through `clip_grad_norm_` (giving a NaN norm and NaN clip coefficient) into AdamW, which made every weight and moment NaN for the rest of the cycle. The cycle then could not be promoted, so the cost is a wasted cycle, not a bad incumbent. | `guarded_update` clips, checks the one returned norm, and either applies the step at the scheduled learning rate or zeroes the gradients and skips it, naming the offending tensors. Steps skipped for a non-finite loss (already zeroed) are counted with them in `skipped_updates`. Tests cover NaN and Inf: weights and optimizer state are untouched, and the next finite step applies. Disabling the skip fails them. |
| P3 | **Two GPU syncs per parameter tensor, every step.** The diagnostic loop ran `torch.isnan(grad).any()` and `torch.isnan(param).any()` on every named parameter after every backward pass, only to print. | Replaced by the single norm check above. Weights cannot turn non-finite without a non-finite step, which is now skipped. |
| P3 | **The benchmark looked below the band.** The loop predicted on the validation fragment at `--z 10`: slices 10–25 of a 65-slice volume, below the 17–42 band. | `centred_depth_start` reads the depth from the zarr metadata (`.zarray` or `0/.zarray`; the loop stays torch-free) and centres the incumbent's `num_layers` window: 24–39 on 65 slices. If the depth cannot be read, the benchmark is skipped with a message. |

### Plan for the depth finding

1. Confirm the fragments' depth and where their ink lies (for example, from `zarr.open(...)` shape
   and a per-slice mean of a labelled region).
2. Add `depth_band: [start, end)` to `ExperimentConfig`. Pass it to both labeled datasets as a read
   range widened by `DEPTH_MARGIN`, so validation's centred window lies inside the band.
3. Version the validation protocol with the band (for example `seeded-sample-400-v2+z17-43`), so
   that `read_incumbent_val_f1` refuses the old score.
4. Re-score the incumbent with `scripts/reevaluate_best_model.py --update-stored`, then restart.
   Finding 86's metric question should be re-read on the new protocol: the all-ink floor and the
   AUC may move.

## Reviewed and sound

- **Loss wiring.** The losses follow the model's output order: `(ink, fiber, qc, proj, st)` from
  the full call and `(ink, proj)` for the second view. Every output is sanitized before its loss.
- **Targets.** The structure-tensor target is computed from the same augmented CT the model sees.
  The Sobel-Z and Frangi fiber targets are min-max normalized per sample, and mixup and cutmix
  transform the input and both targets together.
- **Warm start.** Every shape-defining setting is compared, and only shape-compatible tensors load.
  A change of `multi_task_heads` keeps the backbone and starts or drops the heads.
- **Experiment tracking.** wandb falls back to offline mode when online init fails. With
  `use_wandb: false` every helper is a no-op.

## Observations (not changed)

- **Dice on ink-free patches.** Training patches can be ink-free (`require_ink` defaults to
  False; 80 of the 100 v1 validation patches were). On such a patch the per-sample soft Dice is
  about 1 whatever the prediction, with almost no gradient. It inflates the logged loss and dilutes
  the Dice gradient by the ink-free fraction.
- **AMP.** AMP is hard-disabled ("for NaN debugging"). This costs throughput in a fixed time
  budget; re-enabling it is now safer with `guarded_update`, but is a separate decision.
- **The "hallucination" penalty.** It uses the QC head, which predicts fiber density (see the
  inference-consistency review); the name says more than the term measures.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The
baseline is a worktree of `43e73055` with `PYTHONPATH` set to its own `src/`, asserted before the
run. Both trees run the full `scripts/run_validation_tests.py` list.

New tests:

- `tests/test_training_step_contracts.py`: a finite step is applied at the scheduled learning
  rate; NaN and Inf gradients are skipped with weights and optimizer state untouched, and the next
  step applies.
- `tests/test_loop_lifecycle.py`: the benchmark window is centred for both zarr layouts, and no
  window is given for missing or corrupt metadata.
- `tests/test_autoresearch_measurement.py`: the loop's benchmark runs at `--z 24` on a 65-slice
  volume.

Not verified here: real scroll data, the fragments' depth, and a GPU cycle.
