# Design and architecture review — the model the loop trains, and what its heads train on

Date: 2026-10-14. Baseline: `353fe865` (main after #60). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope:

- `src/vesuvius_autoresearch/core/model_wrappers.py`: `GenericMultiTaskWrapper` and the inference dispatcher;
- `train.build_model` and `build_vconfig`;
- the training step's auxiliary losses (fiber, QC, hallucination penalty, structure tensor);
- the loop's architecture-dependent tweak axes.

The production model is `resenc_unet`, a residual-encoder UNet in `GenericMultiTaskWrapper`, with
`multi_task_heads: true` since the 2026-07-11 promotion.

## What changed

- **Each model declares which auxiliary outputs are real heads, and only those are trained.** The declaration is
  a `task_heads` attribute, read through `model_wrappers.task_heads`:
  - the wrapper declares all three with `multi_task_heads` and none without;
  - `LeJEPAUNet` and `VesuviusNeuralTracingViT` declare none;
  - the TimeSformer declares fiber and QC;
  - the other models declare nothing, meaning all three outputs are real.

  The training step drops the undeclared outputs and skips the structure-tensor target when no ST head is
  trained. A wrapper asked for heads on a backbone without a volume output (resnet3d, i3d) now raises; before,
  it fell back to placeholders that were then trained as heads.
- **The loop proposes the fiber and ST loss weights and `target_fiber_source` only for heads that are
  trained.** The predicate `trains_head` mirrors the declarations, and a test checks them against each model
  class.
- **One ResEnc construction.** `model_wrappers.build_resenc_unet` builds the production model for both training
  and inference. A test requires `train.build_model` and `build_inference_model` to produce the same module (by
  `repr`) and the same state-dict shapes.
- **The `dropout` tweak is proposed only for `gated_unet`**, the one architecture it reaches.

The incumbent and `config.json` have heads, so cycles on the current baseline train exactly as before.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **Without multi-task heads, the fiber loss trained the ink logits toward the fiber target.** The wrapper without heads returned the backbone's own 5D output as "fiber", and its depth mean is exactly the ink logits. `train.py` applied `loss_fiber_bce * BCE(mean_z(fiber), target_fiber)` to it, so the ink map was supervised toward Frangi or Sobel-Z vesselness as well as ink. The QC placeholder is zeros, so `0.02 * hallucination_penalty` became `0.01 * mean(sigmoid(ink))`, a uniform push of every ink probability down. The module and class docs called these "zero-gradient constants". In the logged history (`sprint_logs/`, through 2026-07-11), 3,802 `resenc_unet` cycles trained this way, at fiber weights 0.1–0.3. Every `resenc_unet` production cycle before heads were promoted on 2026-07-11 was one of them, as is every later cycle that tweaks `multi_task_heads` to False. `LeJEPAUNet` and `VesuviusNeuralTracingViT` return the same placeholders for every architecture setting, and the TimeSformer returns zeros as ST. | The training step trains only the outputs a model declares as heads (`task_heads`), so a model without heads trains on the ink losses alone. The loop no longer proposes fiber/ST weights or the fiber target source where nothing trains them. Tests: the placeholder fiber equals the ink logits in its depth mean, and its BCE puts gradient into the backbone. Every model class's declaration is checked; the wrapper refuses heads without a volume output; the loop's predicate agrees with each declaration and with the built `resenc_unet`; and the head-weight axes are gated. |
| P3 | **The `dropout` tweak never reached the production model.** `config.dropout` is used only by `InkDetectorOptimized` (`gated_unet`). `resenc_unet` is built with `dropout_op=None`, and the TimeSformer fixes its own. With the architecture pinned to `resenc_unet`, the loop still proposed dropout 0.1, 0.2 and 0.0. The log has 162 such cycles on `resenc_unet` (2026-05-03 to 2026-07-11), and one was promoted on noise. | The template applies only when the architecture is `gated_unet`, like `ridge_sigma`'s gate on `use_ridges`. Tested for both architectures. |
| P3 | **Training and inference each held a copy of the ResEnc construction.** They agree today. Checkpoints load strictly by name and shape, so a later edit to a shape-free setting in one copy (nonlinearity, norm epsilon, dropout) would load cleanly and serve a different function from the one trained. | `build_resenc_unet` is the one construction. The parity test covers ridges on and off, with and without heads. |

## Review of the change, and what it changed

The first version, a check for the headless wrapper class (`has_task_heads`), was reviewed before the PR:

| Finding | Outcome |
| --- | --- |
| `LeJEPAUNet` and `VesuviusNeuralTracingViT` return the same placeholders, and a check for one class missed them. | Fixed: every model declares its heads. |
| The fix belongs in the models' contract, not in a class check in the training loop. | Done: the `task_heads` declarations. |
| `loss_fiber_bce`, `loss_st` and `target_fiber_source` become no-ops when no head trains them. | Gated in the loop (`trains_head`), like `dropout`. |
| Gating `dropout` gives the regularization family's whole weight to `multi_task_heads`, so it is proposed about twice as often. | Kept, and recorded below. A headless cycle is now a fair ink-only comparison, and the bandit reweights by results. |
| A wrapper with heads on a backbone without a 5D output fell back to placeholders while claiming heads. | Fixed: it raises. |
| A test assumed every other model has real heads. | Replaced by checks on each class's declaration. |
| Inference still exports a headless checkpoint's placeholder as a fiber map. | Recorded below; it is an inference-output change. |
| The structure-tensor target was computed for a model without an ST head. | Skipped. The loader's Frangi target is computed before the model is built, so it is left as is. |
| Loop comments said `resenc_unet` always has real ST heads and that the placeholders had no gradient. | Corrected; the 2026-05-17 note's claim that `resnet3d_decoder` returns a zero ST is also wrong (it has a real ST head) and is corrected. |
| `train.py` kept its own `ResidualEncoderUNet` import only for an availability check. | Removed; the shared builder's `ImportError` is re-raised with the same message. |

## Observations for the owner (not changed)

- **The 2026-07-11 promotion of `multi_task_heads: true` was confounded.** Adding heads also moved the fiber
  loss off the ink logits. Some of that gain may have come from ending the leak rather than from the heads. With
  the fix, a `multi_task_heads: false` cycle is a fair ink-only comparison.
- **The heads still feed the ink output during training.** With heads, the hallucination penalty
  `mean(sigmoid(ink) * (1 - sigmoid(qc)))` trains the ink logits against a QC head that the fiber target fits.
  This was noted in the 2026-10-13 inference review and is a training-objective choice.
- **`multi_task_heads` is now proposed about twice as often.** With `dropout` gated out, the regularization
  family's weight goes to its one remaining axis. Each such cycle drops the incumbent's head weights on its
  warm start.
- **Inference exports a headless checkpoint's placeholder as a fiber map.** It equals the ink probability map
  (noted in the 2026-10-04 volume review). The recipe could say there is no fiber head.
- **Pinned axes that would be no-ops if released.** `num_blocks` and `num_heads` do not reach `resenc_unet`,
  which uses two blocks per stage and no attention. They are pinned today; if they are ever unpinned they need
  the same gate as `dropout`.

## Reviewed and sound

- **`build_vconfig` and the inference `VesuviusConfig`** differ only in `batch_size`, which no model reads.
- **The wrapper's depth reduction** (mean of the 5D logits over Z) is the same in training, validation and
  inference, through the same module.
- **Warm starts across a `multi_task_heads` change** keep the backbone and drop or start the heads, through
  `load_shape_compatible_state` (2026-10-13 losses review).

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #60's head, whose tree is `353fe865`'s.

- Baseline: 42 failed, 2069 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2084 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 15 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files, and mypy on the loop and `model_wrappers.py`: clean.

New tests in `tests/test_task_heads.py`, now in `scripts/run_validation_tests.py`:

- the placeholder fiber is the ink logits, and its loss is not a constant;
- each model class declares its real heads;
- heads on a backbone without a volume output are refused;
- training and inference build the same `resenc_unet` (4 settings), and the loop agrees with its heads;
- the loop's predicate mirrors every architecture's declaration;
- dropout, the fiber and ST weights and the fiber target source are proposed only where they reach the model.

Not verified here: a training cycle on the GPU host.
