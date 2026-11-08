# Confidence-weighted ink training: design and architecture review

Reviewed the pseudo-label handoff to supervised ink loss at base
`e05587614cdec920cca4f9595833aa0e339c341d`. Reproductions use synthetic
tensors and temporary teacher/volume/PNG fixtures. No study data, incumbent
checkpoint, historical measurement or prize filing was changed.

## Findings and repairs

- **PNG ignore values still trained ink (P1).** The producer writes 0/128/255,
  while the loss only gave exact 0.5 zero confidence. PNG 128 decodes to
  128/255 and retained weight 1/255. Normalizing a sufficiently large ignored
  patch by its total weight cancels that factor: a 32×32 ignored target at
  logits 2.0 produced BCE 1.123006 and Dice 0.997490, with nonzero gradients.
  Confidence weighting now recognizes the encoded sentinel too. Matching
  post-augmentation targets have exactly zero contribution to ink BCE/Dice.
- **Fractional Dice confidence was squared (P2).** Multiplying both prediction
  and target by the weight made the intersection use weight squared, while its
  denominator used weight once. A four-pixel oracle expected loss 0.407404;
  the implementation gave 0.777772. Each weighted spatial sum now uses the
  confidence once.
- **Ignored samples diluted weighted Dice (P2).** An all-zero weight sample
  contributed zero loss but still counted in the batch mean. Adding one to a
  supervised sample halved loss from 0.333333 to 0.166667. Only nonempty
  weight maps now enter the weighted sample mean. An entirely ignored batch
  returns a differentiable zero.

The four baseline regressions failed before repair: ignored BCE, ignored Dice,
fractional weighting and empty-sample dilution. The original three confidence
tests passed, because they covered exact 0.5 and binary labels only.

## Architecture and compatibility

`scripts/training/ink_losses.py` isolates target shape checks, confidence weights,
soft Dice and the confidence-weighted BCE/Dice pair from trainer state. The
trainer calls that pair directly; its previous `compute_dice_loss` and
`confidence_weight` imports remain available to existing callers. Shape checks
refuse accidental cross-batch broadcasting. Half and bfloat16 weighted
calculations promote to float32 before reductions; the ignore sentinel is
recognized in its original dtype before promotion.

The unweighted branch retains its previous formula and sample mean. Binary
labels receive unit confidence. Source normalization, patch discovery, sampling,
augmentation settings, model architecture, inference and evaluation formulas
are unchanged. Confidence-weighted training intentionally changes for soft or
ignored targets. Future regular/periodic checkpoints and `run_result.json`
record `confidence_ink_recipe: confidence-ink-v2-png128-linear-dice` when
enabled, and null otherwise. Older artifacts remain historical records of the
previous recipe; they were not rewritten or rescored.

The handoff reports its revised residual-weight description, explicitly scopes
the exclusion to post-augmentation ink BCE/Dice, and records
`spatial_holdout_guaranteed: false`. This is a loss correction, not evidence of
an accuracy improvement or a self-training recommendation.

## Validation

Python 3.10.21 / Torch 2.9.1+cpu, with Villa pinned to
`ccb431818fa68059138f2c964ae299fc474ff116`. Focused loss, real teacher handoff
and training-step tests passed all 114 cases. Coverage includes zero ignored
gradients, invariance to ignored logits, a hand-computed weighted Dice oracle,
empty samples, binary controls, supported shapes, float16/bfloat16/float32/
float64 encodings, finite 256×256 low-precision reductions and periodic
checkpoint recipe records. The real teacher CLI publishes a temporary batch
whose PNG is then read through the actual training dataset.

The affected curated selection passed `202 passed, 2 warnings in 54.15s`
across 10/183 modules. Warnings concerned a third-party TimeSformer literal
comparison and CPU-only pinned-memory behavior. Exact commands/results are in
the PR. The required smoke check passed 8/11, with 3 skips and 0 failures: local
training URI/label checks and the optional batchgenerators transform were
unavailable. Scoped Mypy passed all six changed Python files; lint, formatting
and whitespace checks are recorded in the PR too.

## Limits

Weights are recomputed from the augmented target, not propagated as a separate
spatial mask. Mixup or interpolating augmentation can change an ignored value
into a soft supervised value. Topology losses, auxiliary heads, hallucination
penalties and consistency losses do not use these ink weights. Parameter
sharing, optimizer momentum and weight decay can still change parameters even
with zero direct BCE/Dice gradient. Use independently separated validation data;
this does not implement full spatial holdout exclusion.

No full training run, CUDA kernel/AMP validation, held-out accuracy benchmark or
full curated suite was run. CPU low-precision tests are mathematical checks,
not verification of RTX 4090 execution. The pipeline's independent holdout,
lineage and scientific evidence requirements still apply.

Usage: [pseudo-label training requirements](PSEUDO_LABEL_HANDOFF.md#training-requirements-and-ignore-encoding).
