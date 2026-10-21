# Finding 95: cut to 256³, the 512³ cubes keep the neural tracer's tolerance-4 lead, so cube size as scored is not the 256³ deficit (2026-10-21)

The result of `docs/preregistration/2026-10-21_octant_crop.md`, registered at b5acd9bb before any octant was scored.
Finding 94 (`tolerance4_rescore.md`) found villa's neural fiber tracer ahead of our tracer at a 4-voxel tolerance on
all three in-sample 512³ cubes, and behind it on all eight in-sample 256³ ones. This test cuts the three 512³ cubes
into their eight 256³ octants. Both tracers' labellings, and the ground truth, are cropped to each octant. Both
tracers traced the whole cube, so only the scoring scale changes.

**Answer: cropping does not reverse it.** At tolerance 4 the neural tracer leads on 19 of the 24 octants, where the
rule asked for at least 16. By the registered rule, cube size as scored is not why the 256³ in-sample cubes trail at
tolerance 4.

## The run

* **Registered and run at b5acd9bb:** `scripts/octant_crop_rescore.py`, 00:29–01:06 PDT on 2026-10-21, at nice 19 with
  the loop running. CPU only.
* **Identity passed.** Each whole cube, scored by the same path at tolerance 4, reproduces finding 94's rows for both
  entrants. The status is `OK` (`octant_crop_rescore.json`).
* **The crop keeps ScrollGT's fibers.** Checked before registration: on all 24 octants it keeps the same fibers as
  ScrollGT's `in_bounds_mask`. An octant holds a median 132.5 ground-truth fibers.

## Results

| prediction | registered | result |
|---|---|---|
| P1: cropping does not reverse the lead | ahead of our tracer on ≥ 16 of 24 octants at tolerance 4 | **held:** 19 of 24 |

Merge-penalized ERL on the 24 octants, medians:

| tolerance | neural tracer | our tracer | ratio (range) | octants it leads |
|---|---:|---:|---:|---:|
| 4 | 45.28 | 38.67 | 1.08 (0.85–1.64) | 19 of 24 |
| 2 | 9.88 | 20.52 | 0.46 (0.37–0.63) | 0 of 24 |

* **The lead survives the crop at tolerance 4, a little narrower.** The ratio is a median 1.08 on the octants, against
  1.13 on the whole cubes. It leads on 7, 6 and 6 of each cube's 8 octants.
* **At tolerance 2 it trails on every octant**, as it trails on the whole cubes.

## What it means

* **For finding 91's "cube size" candidate:** a 256³ scoring window, by itself, does not turn the tolerance-4 lead into
  a deficit.
* **It is not the scroll alone either.** Three of the eight 256³ in-sample cubes are Scroll 5, the scroll of these
  512³ cubes. At tolerance 4 the neural tracer trails on all three (21.10 against 42.82, 24.30 against 56.52 and
  23.09 against 34.43), while it leads on most octants of the Scroll-5 512³ cubes.
* **What separates a real 256³ cube from an octant is that the tracer ran on it.** A 256³ run has a trace grid of 128
  voxels, and more of its traces are cut at the faces. The cubes' own content and annotation differ too. Testing the
  tracing context needs the GPU: run the tracer on the 24 octants as cubes, and score those runs beside these crops.
  That is the owner's call.

## What it does not say

* **Crops are not 256³ runs.** That is the point of the test, and its limit.
* **Three cubes, one scroll.** The octants are Scroll 5.
* **The octants of one cube are not independent.**
