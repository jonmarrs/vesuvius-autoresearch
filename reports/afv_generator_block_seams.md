Finding 106: trimming the spline ends a block border cuts raises the held-out ERLpen of villa's fiber generator by a median 13% at tolerance 4 and 7.1% at tolerance 2, with fewer merges (2026-11-07)

The result of `docs/preregistration/2026-11-06_afv_generator_block_seams.md`, registered at 40703acb (pushed 16:00:13
PST on 2026-11-06, 11 s before the first held-out cube started). It was amended at 6823af7a (pushed 19:14 PST), when
only the first cube's one-block arm had finished. The amendment changes the patch a villa PR would carry, not the patch
measured. On every cube here the zone is the whole volume, and there the two patches trim alike. The run took 16:00 PST
on 11-06 to 21:57 PST on 11-07 on the CPU at nice 19, one cube at a time, by
`repro/fibers/run_afv_generator_block_seams_chain.sh` from the registration's script. Inputs: villa main `7e6b82164`,
the #1934 head's prediction modules, model `Qualzz20/afv_fiber_9um` at `e189af75`, scored with ScrollGT c7b2f6f2
(v0.9.2, scoring version 3). Results: `reports/afv_generator_block_seams.json`, written once by the chain's verdict
step.

**Status OK; decision `SUPPORTED`.** By the registered rule, that means "a villa PR with the patch and this
measurement, which is the owner's decision." The gate passed on all eight cubes:
* the #1934 head's modules equal villa main's;
* the patched `stitch.py` adds only `CUT_END` and `trim_cut_ends`;
* the model is at `e189af75`;
* the one-block arm wrote the same fibers with and without the patch.

## What was tested

villa's automated fiber generator (`vesuvius.fiber_spline_generator`, VC3D's **Generate automated fibers…**) works in
three steps:
1. It cuts a zone into blocks.
2. It predicts each block's read region (the block plus a 32-voxel margin) and fits splines in it.
3. It stitches the blocks in a catalogue, which drops copies duplicated by a neighbouring block and chains copies that
   overlap across a face.

The defect is at a block's border. Where the border cuts a fiber, the block's spline bends over its last few voxels,
and the bent ends fail the stitcher's 15° endpoint test and its strict duplicate test. Both copies are then written.
The patch drops the points within 16 voxels of a border that another block reads past, at each cut end. The two copies
then meet straight, and they still overlap by 32 voxels, more than the stitcher's 24.

Eight Scroll-3 512³ cubes, none of them seen by the screen that set the patch, were run in three arms:
* **one:** one block, the reference;
* **real (deciding):** 8 blocks of 256, each predicted from its own crop;
* **same:** 8 blocks of 256 cut from the one-block arm's prediction, so it isolates the stitching.

The gain is patched ERLpen / main ERLpen − 1 on arm real.

## Result, the eight held-out cubes (arm real, main → patched)

| cube | ERLpen τ = 2 | ERLpen τ = 4 | merges τ = 2 | duplicated share | crossings whole/broken/lost |
|---|---|---|---|---|---|
| s3_00994_00494_01994_512 | 15.11 → 16.75 | 37.67 → 46.50 | 43 → 38 | 0.248 → 0.073 | 118/36/29 → 123/15/45 |
| s3_00994_01994_00494_512 | 15.37 → 16.44 | 33.30 → 38.15 | 56 → 53 | 0.217 → 0.095 | 96/38/28 → 108/15/39 |
| s3_00994_02494_01494_512 | 13.99 → 14.99 | 29.72 → 32.64 | 66 → 55 | 0.245 → 0.114 | 118/40/18 → 128/21/27 |
| s3_01994_01494_00994_512 | 13.84 → 15.30 | 33.18 → 40.27 | 12 → 8 | 0.286 → 0.150 | 82/8/18 → 73/10/25 |
| s3_01994_01994_01494_512 | 16.04 → 16.57 | 36.71 → 37.82 | 36 → 30 | 0.175 → 0.091 | 49/16/15 → 53/5/22 |
| s3_02994_02494_01994_512 | 23.31 → 27.76 | 51.89 → 60.70 | 53 → 52 | 0.293 → 0.166 | 175/73/26 → 202/30/42 |
| s3_03494_01494_00494_512 | 11.14 → 11.66 | 25.20 → 27.01 | 88 → 78 | 0.249 → 0.151 | 97/43/13 → 106/18/29 |
| s3_04494_00994_01494_512 | 13.19 → 13.72 | 32.59 → 36.20 | 85 → 72 | 0.235 → 0.086 | 118/25/25 → 91/28/49 |

The duplicated share is the share of written length within 1.5 voxels of a different written fiber of the same
family. A crossing is a place where a generated, unpatched one-block reference fiber crosses a mid-plane (a block face)
with at least 40 voxels of its arclength on each side. Its window is that ±40 voxels of the reference. Written fibers of
the same family, within 2 voxels, make the crossing:
* **whole** when one written fiber covers 95% of the window;
* **broken** when the written fibers together cover 80% of it;
* **lost** otherwise.

These diagnostics compare generated fibers. ERLpen and its coverage are scored separately against the hand-traced
skeleton.

* **P1, P2:** at tolerance 4, ERLpen rises on 8 of 8 cubes, by a median 0.128 (0.030 to 0.234). P1 needed 6 of 8,
  and P2 needed a median of 0.10. Both held.
* **P3:** summed merges went from 439 to 386 at tolerance 2 (−12.1%; P3 allowed +5%). At tolerance 4 they went from
  1,610 to 1,483.
* **P4 (reported):** at tolerance 2, ERLpen rises on all eight cubes as well, by a median 0.071 (0.033 to 0.191). P4
  asked for 0.05 and held.
* **Fibers written twice:** the median duplicated share falls from 0.246 to 0.104. The generator writes 5,236 fibers
  without the trim and 4,469 with it, against 4,055 from one block. Arm same falls from 0.162 to 0.027.
* **Against one block (not registered):** arm real, untrimmed, reaches 0.703 to 0.923 of one block's ERLpen at
  tolerance 4. With the trim it reaches 0.822 to 0.963. Arm same reaches 0.956 to 1.021 with the trim, so the
  stitching cost is all but gone. What still separates arm real from one block is predicting each block from its own crop,
  and the trim does not touch that. After the trim it costs a median 0.039 of one block's ERLpen (0.008 to 0.181).
  It is largest on s3_03494_01494_00494_512 (0.181) and s3_02994_02494_01994_512 (0.169).

## What it costs

* **Coverage, which is not a loss against one block.** The trim changes arm real's coverage at tolerance 4 by a median
  −0.0105. Untrimmed, the eight blocks covered a median +0.0152 more of the reference than one block (+0.0041 to
  +0.0218). That is because the two copies of a fiber come from two crops' predictions and miss the reference in
  different places. With the trim, arm real lands at one block's coverage, a median +0.0002 from it (−0.0050 to
  +0.0143). In arm same the copies come from one field: untrimmed coverage already matched one block (+0.0002), and the
  trim changes it by a median −0.0004. Precision at tolerance 4 rises from a median 0.8865 to 0.8939 (one block:
  0.9000).
* **Lost crossings.** At the mid-planes, lost crossings went from 172 to 278 of 1,304 in arm real, and from 47 to 66
  of 1,304 in arm same. In arm real, whole crossings went from 853 to 884 and broken ones from 279 to 142.
  A diagnosis run after the verdict, and not registered, followed them (`scripts/afv_generator_seam_diag.py`, reduced
  by `scripts/afv_generator_seam_diag_summary.py` to `reports/evidence/afv_generator_seam_diag_2026-11-07.json`). It
  rebuilt both stitchings of every cube and arm from the chain's cached fields. It reproduced every row's fibers
  written, written length and crossing counts. For each crossing whose kind changes, it asks whether a catalogue chain
  holds copies from two blocks, each covering at least 20% of the window. The changes run both ways. In arm real, 178
  crossings are better with the trim and 198 worse (arm same: 173 and 72):
  * **Better:** 176 of the 178 gain a join: copies that main left apart and the trimmed copies chain.
  * **A join lost:** in 63 of the 198, main chained the copies and the trimmed copies are not linked. The catalogue's
    reasons for the trimmed copies (a crossing can have several): the overlap is shorter than 24 voxels (29); one copy
    lies along the other, but the catalogue keeps both (28); an overlap candidate made ambiguous by another at the
    same end (27); the ends meet at more than 15° (11); a copy has less than 8 voxels beyond the overlap (10); the
    copies lie more than 3 voxels apart at an end (5); a gap candidate, not linked (2).
  * **Never chained:** in 125, the copies were chained in neither. A trimmed copy reaches at most 16 voxels past the
    face, not 32, and the best written fiber covers a median 0.733 of the window, against 0.969 without the trim. In
    60 of them, every copy from the other blocks is a chain shorter than `--min-length` (100 voxels), which `clean()`
    drops.
  * The other 10 were chained in both or only with the trim.

  Whole crossings fall on two cubes, s3_01994_01494_00994_512 (82 to 73) and s3_04494_00994_01494_512 (118 to 91). On
  s3_04494_00994_01494_512, 19 crossings lose a join, the most of any cube, and 11 gain one. On
  s3_01994_01494_00994_512, 5 lose one and 4 gain one. On the other six cubes, 11 to 46 gain a join and 2 to 10 lose
  one. ERLpen, evaluated separately against the hand tracing, rises on all eight.

## What it changes

* **For villa:** the registered rule makes this a villa PR, if the owner decides to propose it. It would carry the
  amended patch (`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch`) and this measurement. Three
  things stand before it:
  * **villa's open-PR limit:** three, and all three slots were taken on 11-06.
  * **villa's code-fix limit:** two a week, and both were used on 11-06.
  * **The November criteria, which ask that a fix bite in real use.** VC3D's dialog opens at a 512³ zone and 512
    blocks, which is one block, and there the patch changes nothing. It bites on any zone larger than one block along
    an axis. A real-use example at villa's defaults (a 1024³ zone at block 512, main against patched) would show how
    often. It needs no hand tracing for the written-twice share, and it takes minutes on the GPU (the owner's
    decision).
* **What the generator still loses at a border.** With the trim, arm same comes to about one block's ERLpen. Arm real stays
  a median 0.039 of it lower, and up to 0.181 lower. villa's CLI predicts each block on the block plus the same
  32-voxel margin the stitcher uses for overlap. So the region where neighbouring copies must match is predicted with
  the least context. Whether a wider prediction crop closes that gap is untested here.

## What it cannot say

* **Block 256, not villa's default 512.** A 512³ cube allows one inner face per axis only at 256. Per voxel of zone,
  the defect is smaller at 512 blocks, though the cut ends occur at every face whatever the block size.
* **7.91 µm**, finer than the model's 8.64–9.36 µm training pitch (as in finding 85).
* **One hand tracing per cube**, and eight cubes, all from Scroll 3.
* **The crossing counts and coverage were reported, not predicted.** The account of the lost crossings comes from a
  diagnosis run after the verdict, not from the registration.
* **The patch measured keeps ends at the volume's border only.** The amended patch (zone ± margin) is the one a villa
  PR would carry. On every cube here they are the same function; the amendment's tests check that, and this run does
  not.
