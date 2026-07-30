# Semantic fiber inference: `fiber_hz_vt` replaces classical vesselness

**Date:** 2026-07-29
**Result: the input-signal blocker is resolved.** Discrimination against hand-traced fibers goes
from **2.2x** (Hessian vesselness) to **14.2x** (published semantic model), with ROC-AUC **0.9525**.

## Why

`reports/fiber_tracer_first_result.md` established that the tracer itself works (exact on
synthetic tubes) but that classical vesselness on raw 7.91 um scroll CT separates fibers from
background by a mean ratio of only 2.2, so a tracer driven by it scored precision 0.026 against a
0.0126 base rate. The tracer cannot exceed its input's discrimination, so the fix had to be the
input. villa publishes a learned semantic fiber model for exactly this reason.

## What was loaded

`scrollprize/fiber_hz_vt` on Hugging Face (Apache-2.0):

| Property | Value |
| --- | --- |
| Trainer | `nnUNetTrainerMedialSurfaceRecall` (villa custom) |
| Plans | `nnUNetResEncUNetPlans_48G`, configuration `3d_fullres` |
| Dataset | `Dataset003_sk-fibers_hzvt-augmented-2`, 18 training cases |
| Classes | 4: background, vt-fiber, hz-fiber, intersection |
| Patch (plans) | 256 x 256 x 224 |
| Architecture | `ResidualEncoderUNet`, 7 stages, features 32..320 |
| Parameters | 141.5 M |
| Normalization | `ZScoreNormalization`, per image (`use_mask_for_norm: false`) |

Note the dataset name matches the local baseline directory
`reports/nnunetv2_baseline_Dataset003_sk-fibers_hzvt-augmented-2_...`, so this checkpoint
corresponds to work already touched in this repo.

## Implementation choice: build from `plans.json`, not `nnUNetPredictor`

`src/vesuvius_autoresearch/fibers/semantic.py` instantiates the architecture directly from the
shipped plans and loads `network_weights`. Three concrete reasons rather than preference:

1. The checkpoint's trainer, `nnUNetTrainerMedialSurfaceRecall`, is **not present in the installed
   `nnunetv2`** (it lives in villa's vendored copy under
   `villa/segmentation/models/arch/nnunet/...`), so `initialize_from_trained_model_folder` cannot
   resolve it.
2. `nnUNetPredictor` requires `nnUNet_results` / `nnUNet_preprocessed` environment variables,
   which is global state a library function should not demand.
3. The plans are sized for a **48 GB** GPU (patch 256x256x224). Building the network here allows
   overriding the patch size to fit the available 24 GB card.

Weight loading is deliberately strict: deep-supervision heads (`decoder.seg_layers.1..n`) are
expected to be unused at inference and are dropped, but **any other** missing or unexpected key
raises. A silently half-loaded network would still produce plausible-looking probabilities.

Everything affecting the numbers comes from the shipped configs: architecture and kwargs, patch
size, and the normalization scheme. Sliding-window inference uses nnUNet's Gaussian per-tile
importance map, without which tile seams appear as discontinuities that a tracer reads as fiber
endings. Normalization is applied once to the whole volume, not per tile, since per-tile
statistics would differ and reintroduce seams.

## Discrimination on a hand-traced cube

Cube `s1_00497_01497_03997_256` (256³, 7.91 um), scored against the shipped semantic label
(a rasterization of the 89 hand-traced NML skeletons). Base rate 0.0125.

| Metric | Hessian vesselness | **`fiber_hz_vt`** |
| --- | --- | --- |
| mean inside label | 0.0107 | **0.7597** |
| mean outside label | 0.0049 | **0.0536** |
| **ratio** | **2.20** | **14.17** |
| median inside | -- | **0.9900** |
| median outside | -- | **0.0003** |
| ROC-AUC | -- | **0.9525** |
| AP | -- | 0.2185 |
| AP-lift over base rate | -- | **17.48** |

The median separation (0.99 vs 0.0003) is the number that matters for tracing: inside a fiber the
model is confident, outside it is confidently negative.

**On the modest AP.** AP 0.2185 alongside ROC-AUC 0.9525 is not a contradiction and is not a
defect in the model. The ground truth is a ~1-voxel-wide *skeleton* rasterization (1.25% of
voxels), while the model predicts fibers at their **full thickness** (probability >= 0.5 covers
5.85% of voxels). Precision against a thin centreline is therefore capped by geometry, not by
model quality. This is exactly why the planned evaluation uses connectivity metrics between
centrelines with a tolerance, rather than voxel-wise precision.

## Cost

| | |
| --- | --- |
| Inference, 256³ cube, patch 128³, 27 tiles, no TTA | **6 s** |
| Peak GPU memory | **8.75 GB** (fits 24 GB comfortably) |

Patch 128³ was chosen because the network downsamples by 64x in z/y and 32x in x (strides
`[1,1,1]` then five `[2,2,2]` then `[2,2,1]`), so the patch must be divisible by 64 in z and y.

## Tracer driven by this field

Same 128³ sub-cube, ~24 ground-truth fibers, ~16,099 voxels of in-bounds traced length.
"Precision" is traced voxels landing on the shipped skeleton label; base rate 0.0125.

| Orientation from | Seed field | coverage | precision | n inst | median / max len | dominant stop |
| --- | --- | --- | --- | --- | --- | --- |
| raw CT (vesselness gate) | -- | 0.00 | **0.026** | 5-101 | 19 / 27 | low_response |
| raw CT | prob percentile | 0.129 | 0.225 | 113 | 17 / 38 | high_curvature |
| **prob field** | flat prob | **0.659** | 0.223 | 373 | 20 / **147** | collision |
| prob field | ridge of prob | 0.421 | 0.200 | 200 | 25 / 151 | high_curvature |
| prob field | ridge, strict | 0.272 | 0.215 | 104 | 34 / 151 | high_curvature |

Two findings from this:

1. **Computing orientation from the probability field rather than raw CT raised coverage 5x**
   (0.129 -> 0.659) at unchanged precision, and cut runtime. The weak-signal problem applied to
   *direction* as much as to magnitude: the Hessian of noisy CT gives noisy tangents, and walks
   were dying on `high_curvature`. The Hessian of a clean probability field does not.
2. **Over-splitting is now the limiting error**: 104-373 instances for ~24 true fibers, with
   `collision` dominant in the highest-coverage setting. Seeding on the ridge of the probability
   field instead of the flat field reduces the fragment count but costs coverage, which is the
   expected trade and the shape the abstention sweep is meant to expose.

## The precision number is metric-limited, not model-limited

Precision plateaus at ~0.20-0.22 across every configuration, which is suspicious in the useful
way: it indicates a ceiling imposed by the measurement rather than by the tracer. The ground truth
is a ~1-voxel-wide skeleton; a traced centreline sitting 1-2 voxels off the annotated centreline
inside the *same* fiber scores as a miss. Voxel-wise precision against a 1-voxel skeleton
systematically understates a centreline tracer.

**No configuration should be selected on this number.** The next step is the planned connectivity
evaluation: match traced fibers to ground-truth fibers with an explicit spatial tolerance, then
report expected run length with split and merge counts separately. That is the metric the
🙋 ask actually describes, and it is the one that can distinguish "off by one voxel" from
"followed the wrong fiber".

## Status

Input-signal blocker **resolved**. Orientation source identified as the second bottleneck and
fixed. Remaining work is the evaluation harness (plan step 3), which must land before any
configuration is chosen or any coverage/correctness curve is published.
