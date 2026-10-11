# Ensemble voting

There are two separate APIs:

- [Regional CT inference](VOLUME_INFERENCE.md) loads compatible checkpoints,
  computes QC-gated model probabilities and averages them in a recorded region.
- [SwarmVoter](../scripts/swarm_voter.py) is a PyTorch module for a normalized
  weighted mean of raw model tensors. It does not load checkpoints, choose
  regions, apply activations/gates or export evidence.

Averaging cannot guarantee accuracy or eliminate hallucinations. Models must
already share preprocessing, spatial frame and output meaning. Matching tensor
metadata alone does not establish that compatibility.

## Generic weighted mean

Given compatible models already loaded by the caller:

~~~python
import torch
from scripts.swarm_voter import SwarmVoter

voter = SwarmVoter([model_a, model_b], weights=[1, 3]).eval()
with torch.inference_mode():
    output = voter(batch)
~~~

Relative weights [1, 3] mean coefficients [0.25, 0.75], not an output scaled by
four. Omitting weights selects a uniform mean. Construction accepts 1..64
PyTorch modules in a list, tuple or ModuleList. Weights must be a list/tuple
with one finite nonnegative real number per model and at least one positive
value. Empty/mismatched vectors, booleans, strings, nonfinite/negative values
and nonzero values/positive ratios unrepresentable in float64 fail explicitly.
Rescaling before summing
supports large finite weights without overflowing their sum.

Zero-weight members are disabled and are never invoked; they do not define
the output structure. Each active member receives the same input and keyword
arguments once. Member failures propagate instead of being replaced by zeros
or omitted from the mean.

Active outputs must all be a tensor or all be a nonempty plain flat tuple of
tensors. Tuple head counts must match. Each corresponding head must have the
same shape, dtype and device, although different heads may have different
shapes. Supported outputs are nonempty dense real tensors in float16, bfloat16,
float32 or float64. Integer, boolean, complex, sparse, meta, nested, empty and
nonfinite outputs fail. Scalars are valid nonempty tensors.

Half/bfloat16 outputs accumulate in float32 before returning to their original
dtype; float32/float64 outputs accumulate at their own precision. The final
output is checked for finiteness. Arithmetic that cannot remain finite raises
an error instead of returning a corrupt mean. Voting accumulates members in
order without allocating a tensor stacked along a new model axis; autograd
can still retain each active member's activations during training.

The module averages raw tensors. A mean of logits is not a mean of probabilities,
and averaged QC/projection/structure-tensor heads are not automatically a valid
scientific decision rule. No sigmoid, calibration, confidence interval,
threshold, TTA or coordinate conversion is implied.

## Module and checkpoint behavior

The registered weights_tensor buffer is the sole weight state. The weights
property exposes an immutable tuple of the effective normalized coefficients;
there is no caller-owned list that can drift from the buffer. The buffer travels
with module state_dict/device/dtype conversion. A legacy unnormalized buffer is
interpreted as relative weights on forward.

Buffer shape/type/values and member count are revalidated before any active
member runs, including after state reload or mutation. Weights are fixed
coefficients, not trainable parameters. Module dtype conversion can round the
buffer; the weights property reflects its effective values. Gradients flow
through active model outputs, and disabled members receive no voting gradient.
Use eval/train and inference_mode/no_grad as appropriate; voting does not
silently change a caller's execution mode.

## First Title launcher status

[scripts/search_first_title.py](../scripts/search_first_title.py) does not
implement a title search. The former entry point slept in place of inference
and reported zero candidate regions for both present and missing local data.
Those messages were simulated output, not evidence that a region was scanned
or that ink/titles were absent.

Execution now exits 1 with an explicit unimplemented message and produces no
predictions, discovery images, measurements or history. The old scrolls and
batch-size options remain accepted only to give existing invocations the
scope explanation. Help exits zero and describes the retired simulation.

For actual regional predictions, use the CT inference guide with explicit
checkpoints and source coordinates. Human interpretation and independent
evaluation are still required for title/legibility claims. This utility review
did not establish a full-scroll search, detection performance or prize readiness.
