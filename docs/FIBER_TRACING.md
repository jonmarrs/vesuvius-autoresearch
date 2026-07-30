# Fiber tracing: a connectivity benchmark for papyrus fiber instances

Papyrus fibers physically define the U and V axes of a sheet, so tracing them helps both
flattening and surface segmentation. villa's 2026 open-problems post states the gap directly:
*"obtaining, either through direct tracing or through semantic/instance segmentation, a way to
identify and separate long fibers with the right connectivity"*, and asks for a tracer where
*"a tracer that confidently follows fewer fibers correctly is more useful than one that follows
more fibers with a higher error rate."*

This directory provides **the measurement layer for that problem**, plus a baseline tracer.

## The headline finding: coverage and precision cannot rank a fiber tracer

On a real hand-traced cube, five completely different instance labellings were scored:

| labelling | coverage | precision |
| --- | --- | --- |
| connected components | 0.960 | 0.229 |
| one instance for everything | 0.960 | 0.229 |
| one instance per voxel | 0.960 | 0.229 |
| 50 random instances | 0.960 | 0.229 |
| our tracer's mask | 0.960 | 0.229 |

They are identical, because coverage and precision depend on the **fiber mask**, not on the
**labelling**. A benchmark reporting them cannot tell a correct tracer from `numpy.random`.

What separates them is **expected run length** and the **merge count**:

| labelling | ERL | ERL (merge-penalized) | splits | merges |
| --- | --- | --- | --- | --- |
| *oracle (disclosed)* | *127.69* | *120.39* | *2* | *1* |
| one instance for everything | 111.49 | **0.00** | 21 | 21 |
| connected components | 110.66 | 22.47 | 24 | 11 |
| one instance per voxel | 0.96 | 0.96 | 3045 | 1 |
| 50 random instances | 0.99 | 0.00 | 2986 | 946 |

Note that raw ERL alone is also gameable: labelling everything as one instance scores 111.49,
near the oracle. **Both ERL and the merge penalty are required.**

## Metrics

Defined in `src/vesuvius_autoresearch/fibers/eval_trace.py`.

- **ERL**: walk each ground-truth fiber, split it into maximal contiguous stretches ("runs")
  assigned to one predicted instance, then take the length-weighted mean `sum(L^2)/sum(L)`
  (Januszewski et al.). It answers "pick a random point on a fiber: how far can I follow it
  before an error".
- **ERL merge-penalized**: every run belonging to an instance that spans two ground-truth fibers
  counts zero. The gap between the two ERLs *is* the merge cost.
- **Splits count runs, not distinct labels.** A fiber traced as two disconnected halves under one
  id is fragmented and is counted as such.
- **Merges are reported separately and never summed with splits.** A split fails to help; a merge
  actively corrupts the U/V parameterization fibers are wanted for.
- **Tolerance** (default 2.0 voxels). Ground truth is a ~1-voxel skeleton while any detector
  predicts full fiber thickness, so a centreline 1-2 voxels off is a correct trace. Label growth
  is nearest-label, never blanket dilation, so tolerance cannot itself merge neighbours. **Any
  number from this harness is meaningless without its tolerance**, so `tolerance` is part of
  every scorecard.

## Ground truth

The public `fiber-skeletons` dataset, `dl.ash2txt.org/datasets/fiber-skeletons/`. Cubes of 256³
or 512³ in which *every* papyrus fiber was hand-traced in WEBKNOSSOS, at 7.91 um.

Only the **`nml/` files** carry fiber identity and connectivity. The shipped `labelsTr/*.tif` are
semantic (`background`/`fiber`) and cannot support connectivity metrics. `skeleton_io.py` reads
NML into per-fiber graphs; the coordinate convention (NML writes `x,y,z`, volumes index `z,y,x`,
origin encoded in the filename as `z_y_x`) is pinned by a test asserting that in-bounds nodes
land on the shipped label at a rate of exactly 1.000.

Fibers are absent from both the open S3 bucket and the curated Hugging Face datasets; this legacy
server is the only source.

## Quickstart

```bash
# 1. get a cube (image + hand traces), ~35 MB
python -m vesuvius_autoresearch.fibers.bench_cli fetch --cube s1_00497_01497_03997_256

# 2. reproduce the published floors
python -m vesuvius_autoresearch.fibers.bench_cli floors --cube s1_00497_01497_03997_256

# 3. score YOUR instance labelling (.npy of int labels, 0 = background, cube-shaped)
python -m vesuvius_autoresearch.fibers.bench_cli score \
    --instances my_prediction.npy --cube s1_00497_01497_03997_256 --with-floors

# 4. run the baseline tracer end to end
python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00497_01497_03997_256
```

Steps 2-4 need the semantic model; see below. Step 3 does not, unless `--with-floors` is used.

## The semantic model

`semantic.py` runs villa's published `scrollprize/fiber_hz_vt` (Apache-2.0). Download
`plans.json`, `dataset.json` and `checkpoint_final.pth` into
`local_data/models/fiber_hz_vt/{,fold_0/}`.

The network is built directly from `plans.json` rather than via `nnUNetPredictor`, because the
checkpoint's trainer (`nnUNetTrainerMedialSurfaceRecall`) is a villa custom class absent from
released `nnunetv2`, because `nnUNetPredictor` requires global environment variables, and because
the published plans are sized for a 48 GB GPU. Inference runs in **6 s per 256³ cube at 8.75 GB
peak** with `--patch 128`.

Why a learned model at all: classical Hessian vesselness separates hand-traced fibers from
background by a mean ratio of only **2.2** on raw CT, and a tracer driven by it scores precision
0.026 against a 0.0126 base rate. `fiber_hz_vt` reaches a ratio of **14.2**, ROC-AUC **0.9525**.

## The baseline tracer

`trace.py`. Seeds on ridge-like voxels, follows the Hessian orientation field with sub-voxel
steps, and **abstains** rather than guessing: every walk records why it stopped
(`low_response`, `high_curvature`, `collision`, `invalid_direction`, `out_of_bounds`,
`max_length`). A traced fiber claims its neighbourhood so a second walk entering it stops rather
than merging in. `relink_fragments()` then joins collinear fragment endpoints across short gaps,
filling the gap geometry so the join is a real connection rather than a shared id.

Two implementation notes that cost real debugging time and are easy to repeat:

1. **Orientation must come from the probability field, not raw CT.** The Hessian of noisy CT gives
   noisy tangents and walks die on `high_curvature`; switching the orientation source raised
   coverage 5x (0.129 -> 0.659) at unchanged precision.
2. **`fiber_direction()` returns (z, y, x)** while the raw eigenvector from `hessian()` is
   (x, y, z), because that matrix indexes 0 <-> x. Walking a volume with an unreversed vector
   moves along the wrong axis, finds nothing, and looks plausible.

**Current standing: the tracer does not beat connected components on ERL.** It trades merges for
fragmentation and loses more than it gains. That is published here rather than hidden, and it is
the bar a new method should clear.

## Reproducing our numbers

```bash
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/ -q -k fiber   # 84 tests, CPU
python -m vesuvius_autoresearch.fibers.bench_cli floors --cube s1_00497_01497_03997_256
```

Reports: `reports/fiber_tracing_step0_gt_survey.md` (where the ground truth is),
`reports/fiber_orientation_validation.md` (the orientation primitive),
`reports/fiber_semantic_inference.md` (model discrimination),
`reports/fiber_connectivity_eval.md` (the metric, floors, and our negative result).
