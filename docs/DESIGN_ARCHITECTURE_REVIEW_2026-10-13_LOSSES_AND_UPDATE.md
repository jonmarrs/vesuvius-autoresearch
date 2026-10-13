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
- **Benchmark depth.** `predict.py` centres its window in the volume's depth when `--z` is
  omitted, and the loop's every-5th-cycle benchmark now omits it instead of passing slice 10.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1, owner decision | **Patches show the model a random depth, and most miss the inked surface.** `VesuviusLabeledDataset.__getitem__` draws each patch's read start uniformly over the whole depth (`z0 = rng.randint(0, z_range + 1)`), for training and for validation (seed 42). `patches.json` carries only `y` and `x`. The ink label is the 2D surface label either way. The project's own detector, the Grand Prize recipe that reached held-out pixel-AUC 0.711 on the same Fr47 to Fr143 split, reads only slices 17–42 (`detector/config.py`), and surface volumes are built around the segment surface at their middle layer. On a 65-slice volume (an assumption: the fragments' depth is not recorded here), with `num_layers` 16 plus the 8-slice context, 38% of validation windows contain slice 32 and 26% lie inside 17–42; training, with its 0–7 offset, gives the same fractions. So most patches ask the model to find ink in slices that do not show the inked surface, which is consistent with finding 86's near-constant incumbent (AUC 0.55). This is a hypothesis; it was not tested here. | **Not changed**, because it changes what validation measures: the stored incumbent score would no longer be comparable, and the loop would refuse to start until it is re-scored. Plan for the owner below. |
| P2 | **A non-finite gradient was applied.** AMP is off (`amp_enabled = False`), so `GradScaler` does not skip non-finite steps. A finite loss with a NaN or infinite gradient went through `clip_grad_norm_` into AdamW. A NaN gives a NaN norm and coefficient, so every gradient becomes NaN; an infinity gives an infinite norm and a zero coefficient, so that tensor becomes NaN (inf × 0). Either way AdamW then made weights and moments NaN for the rest of the cycle. The cycle then could not be promoted, so the cost is a wasted cycle, not a bad incumbent. | `guarded_update` checks the gradient norm before clipping. It either clips and applies the step at the scheduled learning rate, or zeroes the gradients and skips it. A skip names the non-finite tensors and the step, or says that finite gradients overflowed the norm. A step with a non-finite or exploding (> 1e6) loss now skips the backward and the update outright. It no longer runs a dummy zero-loss backward, which with AMP on would have made `GradScaler` assert. It is also left out of the smoothed training loss. Both kinds are counted in `skipped_updates`, which `run_result.json` records and the sprint log shows. Tests cover NaN and Inf with AMP off and on: weights and optimizer state are untouched, only the culprit is named, and the next finite step applies. Disabling the skip fails them. |
| P3 | **Two GPU syncs per parameter tensor, every step.** The diagnostic loop ran `torch.isnan(grad).any()` and `torch.isnan(param).any()` on every named parameter after every backward pass, only to print. | Replaced by the single norm check above. Weights cannot turn non-finite without a non-finite step, which is now skipped, so the UA-MT teacher update's per-tensor check (one sync per tensor per step) is dropped too. |
| P3 | **The benchmark looked below the band.** The loop predicted on the validation fragment at `--z 10`: slices 10–25 of a 65-slice volume, below the 17–42 band. | `predict.py` centres the window when `--z` is omitted, from the volume it opens and the checkpoint's `num_layers` (24–39 on 65 slices). The loop's benchmark omits `--z`. |

### Plan for the depth finding

**Implemented 2026-10-13, at the owner's request**, as steps 2 and 3 below, with `config.json` set
to `depth_band: [17, 43]`, the band the project's detector reads from these fragments.
Steps 1 and 4 need the GPU host; see "Restarting the loop" below.

1. Confirm the fragments' depth and where their ink lies (for example, from `zarr.open(...)` shape
   and a per-slice mean of a labelled region).
2. Add `depth_band: [start, end)` to `ExperimentConfig`. Pass it to both labeled datasets as a read
   range widened by `DEPTH_MARGIN`, so validation's centred window lies inside the band.
3. Version the validation protocol with the band (for example `seeded-sample-400-v2+z17-43`), so
   that `read_incumbent_val_f1` refuses the old score.
4. Re-score the incumbent with `scripts/reevaluate_best_model.py --update-stored`, then restart.
   Finding 86's metric question should be re-read on the new protocol: the all-ink floor and the
   AUC may move.

### The implementation

- **`ExperimentConfig.depth_band`.** `[start, end)` or None (the whole depth, as before). It is
  validated, and must hold `num_layers` plus the context: the band widened by `DEPTH_MARGIN` and
  clamped at slice 0 has to hold a read of `num_layers + 8` slices.
- **`VesuviusLabeledDataset(depth_band=..., depth_margin=...)`.** It refuses a band outside the
  volume. Reads are drawn from the band widened by the margin, clamped to the volume, so only the
  context, never the band, is clipped. Without a band the draw is the same call as before, so
  protocol v2's sample does not move (tested against the old formula).
- **Training and validation datasets.** `train.py` passes the band with `DEPTH_MARGIN`, so
  validation's centred window lies inside the band. Training's depth jitter reaches up to 4 slices
  before and 3 after it.
- **`promotion.validation_protocol(depth_band)`.** It returns `seeded-sample-400-v2+z17-43`.
  `train.py` records it in every checkpoint and run result. `read_incumbent_val_f1` and
  `promotion_decision` now require a protocol. Promotion, the loop's startup check,
  `reevaluate_best_model.py` and `loop_v2_constant_control.py` all use `config.json`'s band.
  The re-score records the band it scored in `reevaluation.depth_band`.
- **Tools.** The AUC, pseudo-label and active-learning tools read inside the band the checkpoint
  was trained on. The pseudo-labels matter most, because they are trained on again. The topology
  diagnostic uses `config.json`'s band, like validation. The UA-MT unlabeled stream still reads
  the whole depth of its own volumes.
- **`predict.py`.** Without `--z`, it centres the window in the checkpoint's band when that band
  lies inside the volume, otherwise in the volume, and clamps the result.

### Restarting the loop

The loop now refuses to start ("Not starting: … scored under validation protocol
seeded-sample-400-v2, not seeded-sample-400-v2+z17-43"). On the GPU host:

1. Check the fragments' depth: a fragment shallower than 43 slices makes the dataset refuse to
   build, because the band would lie outside it. `uv run python -c "import zarr; print(zarr.open('local_data/PHercParis2Fr47/surface_volume.zarr'))"`.
2. **Decide lasagna first.** `reevaluate_best_model.py` scores the incumbent with its recorded
   `use_lasagna: true`. Strict validation refuses that warp on these uint8 volumes, so the re-score
   stops as incomplete. This was already true before the band; the band only makes the re-score
   mandatory.
3. `uv run python scripts/reevaluate_best_model.py --update-stored`, then `./start.sh`.

## Review of the depth-band PR, and what it changed

| Finding | Outcome |
| --- | --- |
| `predict.py` centred on the band for any volume, failing on shallower ones and reading the wrong slices on deeper ones. | Fixed: the band is used only when it lies inside the volume, and `z` is clamped. Tested with a band outside a 6-slice volume. |
| A band starting below the margin could pass config validation and then be refused by the dataset on every cycle. | Fixed: the config checks that the widened read fits. Tested with `[0, 16]` and `[3, 19]`. |
| `protocol` defaulted to the whole-depth protocol, so a forgotten argument failed open. | Fixed: `read_incumbent_val_f1` and `promotion_decision` require it. |
| `loop_v2_constant_control.py` did not pass the protocol to the collector. | Fixed. |
| The AUC, pseudo-label, sampler and topology tools ignored the band. | Fixed: they read the band (above). |
| The read range's end was clamped silently while the protocol named the band. | Fixed: a band past the volume is refused; only the margin is clamped. |
| The re-score did not record which slices it scored. | Fixed: `reevaluation.depth_band`. |
| An invalid `config.json` crashed the loop's startup with a traceback. | Fixed: "Not starting: …" (tested). |
| Comments on the benchmark, the `--z` default and the band field were stale or wrong. | Fixed. |
| Four copies of the config-loading expression. | Fixed: `load_current_config()`. |
| A tweak could pair a larger `num_layers` with a band too narrow for it. | Not changed: `num_layers` is pinned. Such a config fails `ExperimentConfig`'s check at preflight in seconds, with the band message. |

## Review of the PR, and what it changed

The first version was reviewed (code-review skill) before merging:

| Finding | Outcome |
| --- | --- |
| The norm was checked after `clip_grad_norm_`, which spreads a NaN into every gradient, so the warning named every tensor. | Fixed: checked before clipping; only the culprit is named (tested). |
| With AMP on, the bad-loss branch's dummy zero-loss backward reached `scaler.step` with no inf checks and would assert. | Fixed: that branch skips the backward and the update; tested with an enabled scaler. |
| The loop centred the benchmark with `config.json`'s `num_layers`, while `predict.py` uses the checkpoint's; it also re-implemented the loader's zarr path rules, for zarr v2 only. | Fixed: `predict.py` centres the window itself, and the loop helper is gone. |
| A skipped step's dummy loss of 0 pulled the smoothed training loss toward zero. | Fixed: skipped steps report NaN and leave the smoothed loss alone. |
| Finite gradients whose norm overflows were reported as "non-finite in 0 tensors". | Fixed: reported as an overflow; tested. |
| Skips were visible only in `run_result.json`, which the next cycle deletes. | Fixed: the sprint log shows them. |
| `skipped_updates` also counts > 1e6 losses, which the comments did not say. | Comments corrected. |
| The warning lost the step number. | Added. |
| The UA-MT teacher update kept a per-tensor sync. | Removed, with the reason. |
| The benchmark's config and metadata were read every cycle. | Gone with the loop helper. |
| This document described the Inf case wrongly. | Corrected above. |

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

- `tests/test_training_step_contracts.py`, with AMP off and on:
  - a finite step is applied at the scheduled learning rate;
  - NaN and Inf gradients are skipped with weights and optimizer state untouched, only the culprit
    is named, and the next step applies;
  - an overflowing norm is named as such;
  - a step with no gradients leaves the scaler usable.
- `tests/test_volume_inference_contracts.py`: without `--z`, the window is centred in the volume's
  depth.
- `tests/test_autoresearch_measurement.py`: the loop's benchmark leaves the depth to `predict.py`,
  and skipped updates reach the sprint log.

Not verified here: real scroll data, the fragments' depth, and a GPU cycle.
