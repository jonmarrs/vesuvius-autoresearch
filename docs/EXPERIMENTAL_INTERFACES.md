# Experimental inference interfaces

The regional predictors use the maintained in-plane mirror implementation in
[`core.inference`](../src/vesuvius_autoresearch/core/inference.py). The fragment
detector has its own four-view option. Their recipes and checkpoint behavior
are unchanged by the optional interfaces described here.

| Interface | Scope |
| --- | --- |
| `GaussianBlender` | Maintained regional float32 blending window; finite, strictly positive, peak-normalized weights. |
| `VillaTTAWrapper` | Experimental scalar-field adapter to the pinned Villa implementation; no maintained prediction-command caller. |
| `VolumetricInkHead` | Untrained shape example with a single Conv3d head; no trained volumetric ink detector. |
| `resnet3d`, `i3d` | Retained historical training-only architecture names, requiring their optional Villa backbones. Inference reconstruction remains unavailable. |

## Gaussian weights

`core.villa_inference.GaussianBlender(patch_size, sigma=0.125)` requires a
positive integer patch edge and finite positive sigma, expressed as a fraction
of that edge. It rejects a window if float32 underflow makes any weight zero
or normalization would produce nonfinite values. Choose a larger sigma for an
unrepresentable window. Default-window arithmetic is preserved.

The window is cached per resolved device. CPU spellings share a cache entry;
an implicit `cuda` request resolves the current logical index, so changing the
current device cannot reuse another GPU's tensor. Valid-window checks run at
construction of each cached window. They add no per-tile validation step.
GPU execution and the cost of those checks were not measured here.

## Optional Villa TTA

Use an editable checkout with its pinned Villa submodule. The adapter reads
that source directly; an unrelated installed `vesuvius` package is not a
replacement. The upstream file remains unchanged.

```python
import torch
from vesuvius_autoresearch.core.villa_inference import VillaTTAWrapper

model = torch.nn.Conv2d(1, 1, kernel_size=1).eval()
wrapped = VillaTTAWrapper(model, tta_type="mirroring")
with torch.inference_mode():
    fields = wrapped(torch.zeros(2, 1, 16, 24))
```

Inputs must be nonempty `[B,C,H,W]` images or `[B,C,D,H,W]` volumes. Outputs
must preserve batch size and spatial rank. Batched mirroring requires the
same input/output spatial grid: Villa reshapes with the input grid, and equal
element counts alone cannot establish that geometry. Use `use_batched=False`
for coarser scalar fields. Sequential mirroring and axis-transpose paths retain
such grids when they align after deaugmentation. Shape checks do not prove
physical alignment or transform equivariance.

`tta_type="rotation"` retains the upstream axis-transpose views. It performs
no arbitrary-angle resampling. Raw model outputs are averaged as returned;
the adapter adds no sigmoid or probability calibration. Channels represent
independent scalar response fields. Directional vectors and structure-tensor
components need orientation-aware channel transforms outside this contract.

With `is_multi_task=True`, the default concatenator accepts three tensor heads
with matching batch and spatial grids/ranks. It returns one channel-concatenated
tensor; the wrapper does not split heads afterward. A custom concatenator can
handle another container and must return a compatible spatial tensor. Model
calls and concatenator timing retain the pinned implementation's order.

The project's ink plane, volumetric fiber response and global QC output have
different ranks. They are rejected here instead of being broadcast or silently
reinterpreted. Use the maintained regional multi-task path for that model
contract. The upstream batched/sequential choice and session-wide OOM fallback
are preserved. Callers remain responsible for evaluation and gradient modes.

## Volumetric shape demo and legacy names

```sh
uv run --no-sync python scripts/labeling/prototype_volumetric_ink.py --help
uv run --no-sync python scripts/labeling/prototype_volumetric_ink.py
```

Torch is required. Help parses before demo feature allocation. Execution uses
small random features and weights, prints shapes, and creates no dataset,
checkpoint or prediction artifact. The output is logits, not a normalized
three-dimensional probability distribution or an ink-quality measurement.

`VolumetricInkHead(in_channels, num_layers)` keeps its existing class and
`conv3d` parameter names. It requires positive integer sizes and a nonempty
`[B,C,Z,H,W]` tensor whose channels/depth match those declarations. Its output
is `[B,num_layers,H,W]`; convolution and gradients for valid inputs are
unchanged. It does not infer a depth band, project, interpolate or train.

`resnet3d` and `i3d` remain accepted training names and rejected inference names.
This preserves the existing architecture boundary. New inference reconstruction
or adoption of these experiments would require separate checkpoint/model and
scientific validation; this scope decision adds neither.
