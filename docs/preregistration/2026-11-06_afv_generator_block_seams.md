# Pre-registration: block seams in villa's automated fiber generator, and trimming the ends a block's border cuts

**Written 2026-11-06, before any held-out cube was run.** The script is `scripts/afv_generator_block_seams.py`, the villa
patch `repro/fibers/villa_fiber_generator_trim_cut_ends_7e6b82164.patch` (on villa main `7e6b82164`), both committed with
this file. Before this was pushed, the script ran once on one in-sample cube, `s1_00497_01497_03997_256`, from the
screen's cached fields: the gate passed and every row equals the screen's (2.4 minutes).

## The question

villa's `vesuvius.fiber_spline_generator` (PR #1934, merged 2026-11-01) is what VC3D runs for **Generate automated
fibers…**. It cuts a zone into blocks of `--block-size` voxels (512 by default), reads each with a 32-voxel margin,
fits splines per block, and stitches the blocks in a catalogue that "drops polylines duplicated by a neighbouring block,
chains polylines that overlap across a block face" (villa's documentation). Any zone larger than one block has block
faces. The question is how much fiber continuity the faces cost, and whether trimming the spline ends a block's border
cuts gives it back.

## Already seen, and not predicted here

An exploratory screen on the **eight in-sample 256³ ScrollGT cubes only**, each in 8 blocks of 128 against one block
(scratch, not committed). ERLpen at τ = 2 / τ = 4; `trim 16` is the patch as registered:

| cube | one block | same, main | real, main | real, trim 16 | merges τ2: one / real main / real trim 16 |
|---|---|---|---|---|---|
| s1_00497_01497_03997_256 | 7.71 / 39.91 | 6.78 / 32.50 | 6.53 / 27.01 | 7.16 / 34.90 | 8 / 14 / 13 |
| s1_00497_02497_02997_256 | 11.93 / 37.11 | 8.38 / 25.79 | 8.63 / 22.17 | 10.23 / 31.54 | 10 / 16 / 13 |
| s1_00997_02497_02997_256 | 11.70 / 45.24 | 7.83 / 28.79 | 5.98 / 22.57 | 10.15 / 37.19 | 10 / 16 / 11 |
| s1_08997_02997_02497_256 | 6.12 / 31.25 | 5.17 / 23.72 | 5.79 / 21.70 | 6.47 / 30.01 | 16 / 20 / 17 |
| s1_10997_02997_02997_256 | 17.47 / 79.76 | 13.25 / 59.67 | 14.50 / 49.58 | 17.11 / 72.11 | 5 / 7 / 7 |
| s5_03997_01497_03997_256 | 7.35 / 61.30 | 7.26 / 46.90 | 7.77 / 29.91 | 8.72 / 41.30 | 0 / 0 / 0 |
| s5_07997_02997_05497_256 | 12.54 / 66.55 | 9.17 / 43.25 | 7.47 / 30.95 | 11.41 / 42.15 | 4 / 2 / 3 |
| s5_14997_01497_01497_256 | 6.26 / 19.66 | 4.59 / 13.37 | 5.62 / 16.53 | 6.82 / 22.97 | 14 / 19 / 18 |

Medians over the eight: arm real at main reaches 0.838 (τ = 2) and 0.610 (τ = 4) of one block; with the trim, 0.954
and 0.862 (median gain +0.183 and +0.386, positive on 8 of 8 at both). Summed merges at τ = 2: one block 67, real main
94, real trim 16 82.

* **The defect.** On the same probability field cut into blocks (the stitching alone), the blocks write more fibers and
  more length for almost no coverage, and ERLpen falls. All the duplicated length lies within 32 voxels of a block
  face. With each block predicted from its own crop, as a multi-block zone is, it falls further.
* **The cause.** A block's splines bend over their last few voxels where its border cuts a fiber: within 2 voxels of
  an inner border they lie a median 1.6 voxels from the one-block spline of the same field, 0.33 at 2–4 voxels and
  about 0.17 beyond 6. The bent ends fail the catalogue's 15° endpoint test for overlaps (true overlaps of median
  0.15–0.27 voxels measured 15.3–19.5° at the ends and 0.6–4.4° eight voxels in), and the bent copies fail its strict
  duplicate test (at most 0.65 voxel), so the copies stay and make the remaining overlaps ambiguous.
* **The fix,** `trim_cut_ends` in the villa patch: at each end of a block's spline, drop the points within `CUT_END`
  voxels of a border of the block that the volume continues past, unless that end lies at the volume's own border.
  Trimming every point near the border instead split a fiber lying wholly inside a margin into two unjoinable copies,
  on a synthetic case. A stitcher-level test of the bent ends fails on villa main and passes with the patch.
* **`CUT_END = 16`, chosen on the screen:** the length with the best median real-arm gain at τ = 4, adding no
  merges. That rule was stated after 6, 12 and 16 had been seen and before 20 and 24 ran. Median gains (τ = 2 / τ = 4): 6 voxels +0.053 / +0.185,
  12 +0.111 / +0.320, 16 +0.183 / +0.386, 20 +0.076 / +0.248, 24 +0.011 / +0.063. Beyond 16 the two blocks' copies of
  a crossing fiber overlap by less than the catalogue's 24 voxels (64 − 2 × 20 = 24), and crossings break. Measuring the
  endpoint tangents inside the overlap instead (the other candidate) gained +0.017 / +0.034 and added merges; dropped.
* **What the trim removes, on arm real:** the median share of written length within 1.5 voxels of another fiber of the
  same family falls from 0.448 to 0.223. It is the margins' second copies, each block's prediction near its own border,
  more than broken crossings, that the gain comes from.

## Data

The eight **Scroll-3 512³** ScrollGT cubes (sibling checkout, v0.9.2, scoring version 3), at 7.91 µm, as finding 85
read them (`spiral_out/afv_gen/zarr`). None was used in the screen. Each is run as one 512 block and as 8 blocks of 256,
the nearest to villa's default these cubes allow.

## Method, fixed now

`scripts/afv_generator_block_seams.py run CUBE`, per cube, villa's defaults (model `Qualzz20/afv_fiber_9um` at
`e189af75`, threshold 60%, margin 32, no mirroring, no `--extend`, join angle 45°, minimum length 100, black distance
16), three arms, each with villa main's stitching (`main`) and with the patch (`patched`):

* **one:** one block (the reference);
* **real:** 8 blocks, each predicted from its own CT crop: **the decision arm**;
* **same:** 8 blocks cut from arm one's field (the stitching alone), reported.

Per arm and variant: ScrollGT `score_tracing` at τ = 2 and 4, written fibers and length, the share of written length
within 1.5 voxels of a different fiber of the same family, and each reference crossing of a mid plane (a one-block
`main` fiber with 40 voxels on both sides) as whole, broken or lost. **The gain:** patched ERLpen / main ERLpen − 1, arm
`real`, per cube. Device: CPU (about 3–4 hours per cube here, at nice 19, one cube at a time), unless the owner
approves the GPU; a cube's fields come from one device, and main and patched share every field.

## Gate, per cube; any failure means no verdict

1. The #1934 head's stitching and prediction modules are byte-identical to villa main's at the recorded commit, and
   the patched `stitch.py` differs from main's only by `CUT_END` and `trim_cut_ends` (`identity()`).
2. The model revision is `e189af75`.
3. Arm one gives identical rows for main and patched (one block has no inner border).

## Predictions

On the eight held-out cubes, arm real:

1. **P1 (moderate):** the gain at τ = 4 is positive on at least 6 of 8 cubes.
2. **P2 (moderate):** the median gain at τ = 4 is at least 0.10. Moderate, not high: one inner face per axis in a
   512³ cube puts half as much of the fiber within a margin as the screen's 256³ cubes in 128 blocks.
3. **P3 (moderate):** summed merges at τ = 2 rise by at most 5%.
4. **P4 (low; reported, not deciding):** the median gain at τ = 2 is at least 0.05.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| A gate check fails, or a cube is missing | No verdict. |
| P3 misses | `COSTS_MERGES`: the trim adds wrong connections; no proposal as it stands. |
| P3, P1 and P2 hold | `SUPPORTED`: a villa PR with the patch and this measurement, which is the owner's decision. |
| Otherwise | `NOT_SUPPORTED`: the defect, measured, may go to villa as an issue (the owner's decision); not the fix. |

## What it cannot say

* **Block 256, not 512.** villa's default block is 512; a 512³ cube allows one inner face per axis only at 256.
  Margin-zone duplication grows with face density, so the defect at 512 blocks is smaller per voxel of zone; the cut
  ends occur at every face whatever the block size.
* **7.91 µm**, finer than the model's 8.64–9.36 µm training pitch (as in finding 85).
* **One hand tracing per cube.**
