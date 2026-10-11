# Pre-registration: how does villa PR #1934's automated fiber generator score against hand-traced fibers, in-sample and on cubes its models never saw?

**Written 2026-10-11, before the generator was run on any cube.** Chain `repro/fibers/run_afv_generator_chain.sh`;
analysis `scripts/afv_generator_analysis.py`; rasteriser `scripts/afv_to_labels.py` (`64cc8dd6`, tested). All on branch
`fiber-heldout-split`. Running the PR's code was approved by the user on 2026-10-11.

## The question

villa PR #1934 (Qualzz, open) adds `vesuvius.afv_spline_generator`. It predicts fibers in a CT zone with
`Qualzz20/afv_fiber_9um`, skeletonises them, fits splines, stitches them and writes an Automated Fiber Volume (`.afv`).
PR #1932 would feed such files to the spiral fit.

The author writes: "I don't know yet how useful this will by just guessing." The model card says: "No independent
test accuracy is claimed."

ScrollGT holds the only hand-traced fiber connectivity ground truth we know of. Since finding 82, it also has its in-sample
status measured. `afv_fiber_9um` was fine-tuned from `fiber_hz_vt`, which trained on all 11 ScrollGT targets. Its
fine-tuning scrolls are PHerc0125, 0175A, 0191, 0211, 0257, 0268, 0306B, 0358, 0800 and 1447, which include neither
Scroll 3 nor Scroll 5. So:
* the 11 ScrollGT targets are in-sample for its base model;
* the 10 held-out cubes of `2026-10-11_fiber_heldout_split.md` are held out for both its base and its fine-tune.

The result tells the author, and anyone weighing #1932, how the generator's fibers compare with hand tracing:
* how long it follows one fiber;
* how often one of its fibers covers two;
* how much fiber it finds;

each on data none of its models saw, and beside the same measures for connected components and our tracer.

## Entrant, fixed now

* **Code:** villa PR #1934 at head `2d8577ed2aaf6b2cd7a5a023bb824538cd20b0e0` (sparse clone,
  `spiral_out/afv_gen/pr1934`). It is installed editable without dependencies in an isolated Python 3.14 environment,
  `spiral_out/afv_gen/venv`, with torch 2.11.0+cu128 and PyPI `nnunetv2`. The package requires Python 3.14.
* **Model:** `Qualzz20/afv_fiber_9um` at Hugging Face revision `e189af7507d16d85d510c372e33d798fc509bb59`.
* **Settings: every default.**
  * threshold 60%, block 512, minimum length 100 voxels;
  * black distance 16, maximum join angle 45°;
  * no `--extend`, no `--mirror`.

  Device `cuda`, `--voxel-size 7.91`, which is outside the model's 8–10 µm range: the CLI warns, and the voxel size
  sets only reported lengths when `--extend` is off.
* **Input:** each cube's CT as a local Zarr array (`spiral_out/afv_gen/zarr/<cube>.zarr`, written from the same TIFF
  the targets use and read back identical), zone origin `0 0 0`, size the cube.
* **Identity check:** the analysis refuses any `.afv` whose `generator` metadata does not record this model revision
  and these settings.

## Scoring

* `scripts/afv_to_labels.py` rasterises each `.afv` as thin centrelines (nearest sample wins a voxel; ties to the lower
  id), dropping points outside the cube. The generator writes native voxels of the zone volume, so no transform is
  needed.
* ScrollGT `score_tracing`, fiber scoring version 2, tolerance 2.0.
* **Ground truth:**
  * in-sample: ScrollGT's targets with the current annotations (0.5.0, PR #2). The analysis requires each target's
    `ground_truth.nml` to name Dataset004.
  * held-out: the Dataset004 NMLs.
* **Comparators:**
  * in-sample: connected components and our tracer from the target's `meta.json`;
  * held-out: the same rows from the held-out study's `result.json`.

  Precision is reported but **not compared** with those mask-based labellings. A thin centreline and a full-thickness
  mask differ in precision by construction.

## Predictions, fixed now

1. **The generator follows a fiber further than our tracer:** raw ERL above the tracer's on at least 9 of the 11
   in-sample targets. Confidence moderate. Its fibers are smoothed chains of at least 100 voxels. The tracer's ERL is
   35–55 at 256³ and 41–53 at 512³.
2. **It finds less of the fiber than our tracer:** coverage below the tracer's on at least 9 of 11 in-sample targets.
   Confidence moderate. Chains are cut at every skeleton junction, and chains under 100 voxels are deleted. The tracer
   covers 56–68%.
3. **Connected components keeps the raw-ERL lead:** above the generator on all 8 in-sample 256³ targets. Confidence
   moderate.
4. **On the held-out Scroll-3 cubes the generator beats our tracer on merge-penalized ERL** on at least 6 of the
   eligible cubes (at least 75%). Both are out of sample there. Confidence low-moderate.
5. **The generator finds less fiber on Scroll 3 than in-sample:** its median coverage over the eligible Scroll-3 cubes
   is below its median over the three in-sample 512³ targets. Confidence low. The fine-tune's ten scrolls may
   generalise, and the scale mismatch applies on both sides.

**Descriptive, no prediction:** merges, splits, instance counts, and precision among thin entrants. The two held-out
Scroll-5 cubes are also described.

## Decision rule

| outcome | conclusion |
|---|---|
| a generator run fails or writes no complete `.afv` | that cube is reported as failed, not scored as zero; INCOMPLETE if any in-sample target fails |
| the held-out study's result is missing or not `OK` | P4 and P5 not evaluated |
| an `.afv`'s recorded model revision or settings differ | IDENTITY_FAILED, no verdict |
| otherwise | each prediction held or failed as registered; every row reported beside its comparators |

Whatever the outcome, nothing is posted to villa or added to ScrollGT without a separate decision by the user. Anything
posted to villa also falls under villa's posting limits (new items weekly, replies daily).

## What the result cannot do

* **In-sample rows are optimistic.** The base model trained on those cubes.
* **Scale.** The cubes are 7.91 µm, below the model's 8.64–9.36 µm training range. A user of Scroll 1, 3 or 5 at their
  public 7.91 µm resolution would run it that way, but resampling might score differently. That is not tested here.
* **Defaults only.** `--extend` (several times slower) and `--mirror` are not tested.
* **Ground truth vs product.** ScrollGT's ground truth covers every fiber in a cube. The generator deletes chains under
  100 voxels by design, so its coverage measures the default product, not the model's recall.
* **Scope of the comparison.** It ranks labellings on ScrollGT's metric; it does not say which is more useful to the
  spiral fit.

## Cost

GPU: about 21 runs at 0.5–1.5 minutes each, after the held-out chain releases the GPU. CPU scoring: a few minutes.
