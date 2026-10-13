# Design and architecture review — is inference serving what training validated?

Date: 2026-10-13. Baseline: `b617897f` (main after the loop-proposals review). Villa pin:
`9afddaf0fdc12efe088bab7b82534c4f9a79e536`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the inference paths that turn a checkpoint into ink maps, compared input by input and
output by output with what training validates:

- `scripts/inference/predict.py`, `scripts/inference/ensemble_predict.py` and
  `scripts/production_predict.py`, through `src/vesuvius_autoresearch/core/inference.py`;
- the active-learning sampler (`scripts/active_learning_sampler.py`);
- the checkpoint tools (`src/vesuvius_autoresearch/core/checkpoint_tools.py`).

Measurements use the stored incumbent, `best_model.pt` (resenc_unet with real multitask heads,
`multi_task_heads: true`, ridges on, `target_fiber_source: frangi`). This container has no scroll
data, so the forward passes use synthetic CT.

## What changed

- **QC gate removed.** The regional and ensemble commands serve `sigmoid(ink)`, the quantity
  training validates (`val_f1` and its threshold) and `production_predict` already exported. They
  no longer multiply it by `sigmoid(qc / 0.1)`.
- **Sampler ranking.** The active-learning sampler ranks patches by prediction entropy alone.
- **Shared depth context.** Every inference path, and the sampler, computes the ridge channel with
  training's depth context. `DEPTH_MARGIN` in `core/inference.py` is now the one definition, used
  by training, validation, the checkpoint tools and inference.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **The regional and ensemble ink maps of the production checkpoint were blank.** `multitask_probabilities` multiplied ink by `sigmoid(qc / 0.1)`, a "QC gate". Training does not learn a quality score. It fits the QC head to the patch's mean fiber target (`loss_qc`, BCE against `target_fiber.mean()`), and the Frangi target's patch mean is small, so the head's logit is negative. Across a grid of plausible pooled inputs (mean CT 0.1–0.9, mean ridge 0–0.6, mean ink logit −6 to 3), the incumbent's QC logit stays between −5.27 and −0.23. The gate is therefore at most 0.09, with a median of 1.6e-5. A forward pass on three synthetic patches gave a gate of about 3e-12: served ink at most 5e-13, every exported uint8 pixel 0 (18–26/255 ungated). The overlay panel auto-scales its colormap, which hides this; the PNG and OME-Zarr exports, the ensemble, and the loop's every-5th-cycle benchmark do not. The 2026-10-04 volume review kept the gate on the assumption of placeholder heads (constant 0.5 gate); the incumbent has had real heads since at least the 2026-07-11 `multi_task_heads_True` promotion. | `prob_ink = sigmoid(ink)`. The recorded recipe says so, and the docs say that regional outputs from before 2026-10-13 are not comparable. QC logits are no longer requested, so a broken QC head cannot abort a region. The Scroll 2/3 candidate ranker gives a prediction bonus only to maps recorded as `sigmoid(ink)`; gated or unrecorded maps are on another scale. A regression test serves the same ink for QC logits of −5, 0, 5 and +∞; restoring the gate fails it. |
| P2 | **The active-learning sampler treated the QC head as confidence.** Its score was `0.7 * entropy + 0.3 * (1 - sigmoid(qc))`, documented as "the model's own estimate of quality". With a real head, that term ranks patches with little predicted fiber as uncertain, whatever the ink prediction. | The score is the mean prediction entropy. The sampler no longer requests QC. A test gives identical ink and very different QC per patch and requires equal scores. |
| P3 | **The ridge channel was computed over a different block at inference.** Training reads `num_layers + 8` slices, computes ridges over all of them, then takes `num_layers` (validation: the centre; training: offsets 0–7). All three inference commands read exactly `num_layers` slices, and so did the active-learning sampler (unlike the AUC and pseudo-label tools, which read the buffer). The ridge filter min-max normalizes its whole block (`fibers.detection.hessian`). On sheet-like synthetic CT the window's edge slices differ by 88% and its centre by 3%; on smooth noise every slice differs. For this incumbent the effect on ink is at most 0.1% (correlation 1.000): its ridge values are around 1e-5 to 1e-3, and it barely uses the channel. | `read_model_block` reads `depth_window(z, num_layers, depth)` (validation's centred context, shifted inside the volume at its ends), computes ridges over it, and crops the window. CT-only reads are unchanged. For ridge models the sampler reads the buffer and crops it with `centre_window`, which also centres a shallower read from a volume without room for the full context. The recorded recipes carry `ridge_depth_context`. The probes, AUC and pseudo-label tools use `DEPTH_MARGIN` instead of literals. A test builds a real labeled dataset and a `FastVesuviusVolume` over the same zarr: the served input equals validation's input, and the window-only read does not. |

## Review of the PR, and what it changed

The first version was reviewed (code-review skill) before merging. Its findings, and what was
done:

| Finding | Outcome |
| --- | --- |
| The sampler required exactly `num_layers + 8` slices, so a volume less than 8 slices deeper than the model failed, and CT-only models read context they do not use. | Fixed: context only for ridge models, and `centre_window` crops whatever depth was read. Tested with an 18-slice read for a 16-layer model. |
| The candidate ranker scored gated (pre-2026-10-13) and ungated maps on one scale. | Fixed: only maps recorded as `sigmoid(ink)` earn a prediction bonus. Tested for gated and unrecorded maps. |
| `depth_window` gives offset 8 for a volume's last window; training samples 0–7, while the docstring said "as training's sampled offsets do". | Docstring corrected. The read is kept: the last window has no in-distribution placement. |
| Overlay titles still said "Gated". | Fixed. |
| QC logits were still requested and checked, so a broken, unused head aborted inference. | Fixed: not requested. A test with an infinite QC logit passes. |
| The recipes did not record the ridge depth context; the sampler's queue did not say how it scores. | Fixed: `ridge_depth_context` in every recipe, plus the sampler's score definition. |
| The overlay's one-slice read ran the ridge filter on a ridge volume and counted a spurious `ridge_fallback`. | Fixed: the overlay reads CT only (`get_raw_patch`). A test fails on the old read. |
| `DEPTH_MARGIN` was "the one definition" while five tools still hard-coded `+ 8` and `4 : 4 +`. | Fixed: they use the constant. |
| The context rule is implemented twice (`read_model_block` and the sampler's buffered read). | Narrowed: both are in `core/inference.py` (`depth_window` and `centre_window`). The sampler's dataset decides where its reads start, so it can only crop. |
| The default proofreader export now flags most of a region for this incumbent (probabilities near 0.05 have high entropy). | Not changed: that is the model's uncertainty. The previous empty export came from the gate. The threshold is a separate choice. |

## Reviewed and sound

- **Intensity scale.** Training's labeled dataset and inference's `FastVesuviusVolume` both
  normalize uint8 by 255 (uint16 by 65535) before computing ridges, with the checkpoint's
  `ridge_sigma`.
- **Patch extent.** Every inference path reads one `patch_size` tile at a time, so the ridge
  filter's in-plane extent matches training.
- **Production ink.** `production_predict` exported `sigmoid(ink)` throughout. Re-evaluation and
  the loop's constant control score through `collect_validation_predictions`, which crops the
  buffered read.

## Observations (not changed)

- **QC in the training loss.** `hallucination_penalty = mean(sigmoid(ink) * (1 - sigmoid(qc)))`
  pushes ink down where predicted fiber density is low, under a "hallucination" name. It is a
  training-objective choice (weight 0.02), left as is; the name says more than the head measures.
- **Ridge scale.** The incumbent's ridge channel is small next to CT intensities in [0, 1], which
  is consistent with the model ignoring it. Whether to rescale it is a modelling question.
- **Ensemble depth.** Ridge-enabled ensemble members must still share `num_layers`; that check
  predates this review and stays.
- **Shallow validation volumes.** `collect_validation_predictions` crops `[4, 4 + num_layers)`
  from a read that the dataset caps at the volume's depth. A volume less than 8 slices deeper than
  the model would give it fewer slices than it expects. The production fragments are deep enough;
  the validation crop is unchanged here.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The
baseline is a worktree of `b617897f` with `PYTHONPATH` set to its own `src/`, asserted before the
run. Both trees run the full `scripts/run_validation_tests.py` list.

New and changed tests:

- `tests/test_volume_inference_contracts.py`:
  - QC logits (including +∞) do not scale served ink;
  - `depth_window` and `centre_window` cases;
  - the served ridge input equals validation's;
  - inference ridges see the depth context, and the overlay counts no ridge fallback.

  Two pinned values change because the gate is gone: 0.25 becomes 0.5 for zero logits, and
  expected probabilities are `sigmoid(ink)`.
- `tests/test_prize_readiness.py`: gated or unrecorded maps earn no ranking bonus.
- `tests/test_active_learning.py`: QC does not change the ranking; with settings, the model sees
  the centre of the buffered read; a volume shallower than the context still samples.
- `tests/test_checkpoint_tool_contracts.py`: the sampler is no longer required to reject a
  non-finite QC head, because it no longer reads one.

Not verified here: real scroll data, and the GPU host's inference on it.
