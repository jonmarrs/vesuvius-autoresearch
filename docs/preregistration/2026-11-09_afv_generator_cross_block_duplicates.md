# Pre-registration: suppressing a block's copy of a fiber another block also fitted, on top of the seam trim

**Written 2026-11-09, before the change was run on any held-out cube.** The script is
`scripts/afv_generator_cross_block_duplicates.py`, committed with this file. The change it tests is
`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`. It sits on top of the seam trim (findings
106 and 107) and applies to villa main `c3d9da6fe`, whose generator equals `7e6b82164`'s.

## The question

With the seam trim, finding 107's 1024³ zone at villa's default block size still writes 0.052 of its fiber length
beside a same-family copy. Run as one block, finding 106's cubes wrote at most 0.0002.
* **Is the rest a second defect, and does suppressing it help?** The catalogue suppresses a source from another
  block only when `strict_duplicate` matches it: full containment within a median 0.20 voxel (p90 0.40, max 0.65).
  Its own `compare()` also classifies looser containments, within a median 1.5 voxels, as duplicates. A comment in
  `_compare_pair` keeps those unsuppressed, so that adjacent fibres survive.
* **The change:** for sources of different blocks, a copy that `compare()` classifies as a duplicate (`contained`
  `A` or `both`, the shorter copy) is suppressed, as a strict duplicate is.
  * The bounding-box gate is the shorter copy inside the longer one's box ± `MAX_P90` (3 voxels). That loses nothing:
    `compare()`'s duplicate already requires every sample of the shorter copy within 3 voxels of the longer one.
  * Sources of one block are still never compared this way.

## Already seen, and not predicted here

* **Where the rest lies (finding 107's zone; exploratory, no ground truth).** With the trim:
  * 99.9% of the doubled length lies within 32 voxels of an inner block face. Beyond 32 voxels the share is 0.0001.
  * Within 16 voxels of a face, 35–43% of the length is doubled.
  * The doubled samples' nearest same-family neighbour lies a median 0.33 voxel away (0.5-voxel sampling), at a
    median 3.5°. 88% of them run along the face rather than across it.
* **Why the catalogue keeps them (villa's own tests on the zone's written fibers).**
  * 239 pairs share at least 4 voxels of doubled length.
  * None passes `strict_duplicate`. The median above 0.20 fails 90 pairs (most of the doubled length); the bounding
    box fails 140.
  * `compare()` classifies 112 of the pairs as duplicates and 32 as overlaps.
  * The zone is centred on the held-out cube `s3_04494_00994_01494_512`, so that cube is reported apart as well
    (below).
* **The dev screen: the 11-06 screen's eight in-sample cubes (Scrolls 1 and 5, 256³ in blocks of 128), from their
  cached fields.** None of them is held out.
  * The harness reproduced the 11-06 screen's base and trim rows exactly (16 of 16).
  * The patch's own form gave rows identical to an ungated version on all eight.
  * Against the trim alone, merge-penalized ERL rose on all eight: a median +17.2% at τ = 4 (+3.1% to +41.4%) and
    +6.0% at τ = 2 (+1.9% to +22.4%).
  * Summed merges went 82 → 79 at τ = 2 and 166 → 164 at τ = 4. The median duplicated share fell 0.223 → 0.070.
  * Of the face crossings, whole ones rose 248 → 291, broken fell 65 → 34 and lost fell 45 → 33.
  * Coverage at τ = 4 rose on all eight (median +0.7%). At τ = 2 the median was −0.2% (4 of 8 up).
* **The smoke before this was pushed:** `run --variants trim` on `s3_00994_00494_01994_512`. It is the trim alone, so it
  sees nothing of the change.
  * The gate passed, and the row equals finding 106's `real/patched` row exactly: ERLpen 16.75 at τ = 2 and 46.50 at
    τ = 4, merges 38, duplicated share 0.073, crossings 123 / 15 / 45.
  * It took about 6 minutes, so the run takes about 2 hours on the CPU.

## Data

* **Deciding:** finding 106's eight held-out Scroll-3 cubes, `afv_generator_block_seams.HELD_OUT`, from finding 106's
  cached per-block fields. That is arm real: 8 blocks of 256 on each 512³ cube, each predicted from its own crop with
  the 32-voxel margin.
  * The cubes' hand tracings scored the trim in finding 106, but nothing of this change has been run on them.
  * The change's rule was set from villa's code and the zone's doubling above, not from any held-out score.
* **Reported, not deciding:**
  * the seven cubes without `s3_04494_00994_01494_512`;
  * finding 107's 1024³ zone at block 512, from its cached fields: the zone's duplicated share and that cube's
    scores, trim against trim and change.

## Method, fixed now

`run` per cube, then `zone`, then `verdict`, with villa's defaults as in findings 106 and 107: threshold 60%, margin
32, join angle 45°, minimum length 100, black distance 16, model `Qualzz20/afv_fiber_9um` at `e189af75` (its fields
are finding 106's and 107's).
* **The two arms:**
  * `trim`: the amended seam trim, with the zone's read box the cube.
  * `trim+dup`: the trim plus the change. The `Stitcher` builds its catalogue from the patched `catalog.py`.
* **Scoring, as finding 106 scored:**
  * ScrollGT `score_tracing` at τ = 2 and 4 against the hand tracing;
  * the duplicated share;
  * the face crossings of the cube's one-block fibers (finding 106's `one_main_fibers.npz`).

The gain is the ERLpen of `trim+dup` over that of `trim`, minus 1.

## Gate, per cube; any failure means no verdict

1. `afv_generator_block_seams.identity()`:
   * the #1934 head's stitching and prediction modules equal villa main `7e6b82164`'s;
   * the amended `stitch.py` adds only `CUT_END` and `trim_cut_ends`.
2. The patched `catalog.py` equals villa main's apart from `cross_block_duplicate`, its call and one comment
   (`catalog_problems`).
3. Finding 106's record of the cube has no identity problems and model `e189af75`.
4. The `trim` arm reproduces finding 106's `real/patched` row exactly. Finding 106 ran the patch's first form, which
   trims as the amended one does where the zone is the whole cube. For the zone, the `trim` arm reproduces finding
   107's `patched` row.

## Predictions (the eight held-out cubes)

1. **P1 (moderate):** ERLpen at τ = 4 is higher with the change on at least 6 of 8 cubes.
2. **P2 (moderate):** the median gain at τ = 4 is at least 0.03. At blocks of 256 the trim leaves about half the
   dev screen's doubling (finding 106: a median share of 0.104), so the bar is set below the dev screen's +17.2%.
3. **P3 (moderate):** summed merges at τ = 2 with the change are at most 1.05 times the trim's.
4. **P4 (high):** the median duplicated share with the change is at most 0.7 times the trim's.

Reported, not deciding: the gain at τ = 2, coverage and precision at both tolerances, the face crossings, fibers
written, the seven-cube results, and the zone.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| A gate check fails | `NO_VERDICT`. |
| P1 or P3 misses | `NOT_SUPPORTED`: the change costs continuity or adds merges on held-out data; no villa change. |
| P2 or P4 misses | `PARTIAL`: it helps, but less than the dev screen suggests; whether to propose it is the owner's call. |
| All hold | `SUPPORTED`: a villa change, alone or with the seam trim; posting is the owner's decision. |

## What it cannot say

* **Eight cubes, all Scroll 3, one hand tracing each, at 7.91 µm.**
* **Reused data:** the same cubes scored the trim (finding 106). This is a second test on them, not fresh data.
* **Adjacent fibres:** the change can merge two distinct fibres less than 1.5 voxels apart where both blocks see both.
  Merges and coverage are the check on that; villa's new test covers fibres 2 voxels apart only.
* **Blocks of 256 decide; one zone at 512 is reported.**
