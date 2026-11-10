Finding 108: on top of the seam trim, suppressing a block's copy of a fiber that another block also fitted raises ERLpen on 8 of 8 held-out cubes, by a median +5.7% at tolerance 4, and cuts the median written-twice share from 0.104 to 0.032 (2026-11-09)

The result of `docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md`, registered at 241b0c86 (pushed
13:58:32 PST on 2026-11-09). The run: 13:58:46 to 15:38:00 PST on 11-09, on the CPU at nice 19, in its own systemd
user unit, by `repro/fibers/run_afv_generator_cross_block_duplicates.sh`. No field was predicted: every block's field
is finding 106's or finding 107's cached one.

Inputs: villa main `7e6b82164` (its generator equals `c3d9da6fe`'s), the #1934 head's prediction modules, the amended
seam-trim `stitch.py` (sha256 `362b78b1…`), the changed `catalog.py` (sha256 `be553b49…`), model
`Qualzz20/afv_fiber_9um` at `e189af75`, scored with ScrollGT (scoring version 3). The change is
`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`. Results:
`reports/afv_generator_cross_block_duplicates.json`, written once by the runner's verdict step.

**Status OK; decision `SUPPORTED`.** By the registered rule, that is "a villa change, alone or with the seam trim;
posting is the owner's decision." The gate passed on all eight cubes and on the zone:
* the #1934 head's stitching and prediction modules equal villa main's, and the trim's `stitch.py` adds only `CUT_END`
  and `trim_cut_ends`;
* the changed `catalog.py` equals villa main's apart from `cross_block_duplicate`, its call and one comment;
* finding 106's record of each cube has no identity problems and model `e189af75`;
* the `trim` arm reproduces finding 106's `real/patched` row exactly on every cube, and finding 107's `patched` row
  exactly on the zone.

## What was run

villa's automated fiber generator (`vesuvius.fiber_spline_generator`, VC3D's **Generate automated fibers…**), stitched
twice from the same fields, with villa's defaults (threshold 60, join angle 45°, minimum length 100, margin 32):
* **trim:** the amended seam trim (findings 106 and 107);
* **trim and the change:** the trim, plus a catalogue that suppresses a source when `compare()` classifies it as a
  duplicate of a source from another block (the shorter copy, inside the longer one's box ± 3 voxels). Before, only
  `strict_duplicate` (a median 0.20 voxel) could suppress it. Sources of one block are still never compared this way.

**Deciding:** finding 106's eight held-out Scroll-3 cubes of 512³, each in 8 blocks of 256 predicted from its own crop.
**Reported:** finding 107's 1024³ zone at villa's default block size of 512.

## Result

| cube | ERLpen τ = 4, trim | with the change | gain, τ = 4 | gain, τ = 2 | merges, τ = 2 | written length beside a same-family copy |
|---|---|---|---|---|---|---|
| `s3_00994_00494_01994_512` | 46.5 | 48.76 | +4.9% | +4.1% | 38 → 37 | 0.073 → 0.017 |
| `s3_00994_01994_00494_512` | 38.15 | 39.37 | +3.2% | +6.7% | 53 → 53 | 0.095 → 0.031 |
| `s3_00994_02494_01494_512` | 32.64 | 34.78 | +6.6% | +4.9% | 55 → 55 | 0.114 → 0.026 |
| `s3_01994_01494_00994_512` | 40.27 | 43.47 | +7.9% | +5.9% | 8 → 8 | 0.150 → 0.066 |
| `s3_01994_01994_01494_512` | 37.82 | 39.01 | +3.1% | +4.7% | 30 → 29 | 0.091 → 0.018 |
| `s3_02994_02494_01994_512` | 60.7 | 66.87 | +10.2% | +8.2% | 52 → 51 | 0.166 → 0.037 |
| `s3_03494_01494_00494_512` | 27.01 | 29.47 | +9.1% | +7.2% | 78 → 80 | 0.151 → 0.055 |
| `s3_04494_00994_01494_512` | 36.2 | 37.11 | +2.5% | +3.9% | 72 → 71 | 0.086 → 0.033 |

"Beside a same-family copy" is finding 106's duplicated share: the share of written length within 1.5 voxels of a
different written fiber of the same family.

**Over the eight cubes**

| | trim | trim and the change |
|---|---|---|
| merges, τ = 2, summed | 386 | 384 |
| merges, τ = 4, summed | 1,483 | 1,461 |
| written length beside a same-family copy, median | 0.104 | 0.032 |
| fibers written, summed | 4,469 | 4,231 |
| written length, voxels, summed | 771,968 | 741,638 |
| face crossings whole / broken / lost | 884 / 142 / 278 | 957 / 112 / 235 |
| coverage, τ = 4, median | 0.3197 | 0.3215 |
| coverage, τ = 2, median | 0.2624 | 0.2627 |
| precision, τ = 4, median | 0.8939 | 0.8939 |
| precision, τ = 2, median | 0.7364 | 0.7364 |

| prediction | registered | measured | held |
|---|---|---|---|
| P1 (moderate) | ERLpen at τ = 4 higher with the change on at least 6 of 8 cubes | 8 of 8 | yes |
| P2 (moderate) | median gain at τ = 4 at least 0.03 | 0.0571 | yes |
| P3 (moderate) | summed merges at τ = 2 at most 1.05 × the trim's | 384 against 386 | yes |
| P4 (high) | median duplicated share at most 0.7 × the trim's | 0.0319 against 0.104 (0.31 ×) | yes |

Merge-penalized ERL rose at τ = 4, up on 8 of 8, by a median +5.7% (+2.5% to +10.2%), and at τ = 2, up on 8 of 8, by a
median +5.4% (+3.9% to +8.2%). Coverage rose on 8 of 8 at τ = 4 and on 8 of 8 at τ = 2, by at most 0.003. Precision
moved by at most 0.0034 either way.

**Without `s3_04494_00994_01494_512`** (the cube the residue was diagnosed on): up on 7 of 7 at τ = 4, by a median
+6.6%, and +5.9% at τ = 2; merges at τ = 2 314 → 313; median duplicated share 0.114 → 0.031. That cube gained the
least of the eight at τ = 4 (+2.5%), so the diagnosis did not pick a cube the change favours.

## The 1024³ zone at block 512 (reported, not deciding)

| | trim | trim and the change |
|---|---|---|
| **The whole 1024³ zone (no ground truth)** | | |
| fibers written | 5,326 | 5,212 |
| written length, voxels | 972,804 | 956,815 |
| written length beside a same-family copy | 0.052 | 0.017 |
| **Inside the hand-traced 512³ cube** | | |
| fibers written inside the cube | 904 | 870 |
| written length beside a same-family copy, inside the cube | 0.099 | 0.032 |
| merge-penalized ERL, τ = 4 | 41.51 | 42.94 (+3.4%) |
| merges, τ = 4 | 269 | 255 |
| coverage, τ = 4 | 0.4138 | 0.4158 |
| precision, τ = 4 | 0.8966 | 0.8959 |
| merge-penalized ERL, τ = 2 | 15.95 | 16.68 (+4.6%) |
| merges, τ = 2 | 82 | 80 |
| coverage, τ = 2 | 0.3273 | 0.3287 |
| precision, τ = 2 | 0.7156 | 0.7157 |

Against finding 107's main row, the two changes together cut the zone's written length beside a same-family copy from
main's 0.120 to 0.017. In the cube they raise ERLpen +20.0% at τ = 4 and +10.4% at τ = 2 over main, with merges at
τ = 2 92 → 80. Coverage at τ = 4 stays 3.2% below main's (finding 107: 3.7% below with the trim alone).

## Reading it

* **It is the second half of the seam defect.** The trim made two blocks' copies of a fiber chain at their cut ends.
  The copies that still lay along each other were written twice because only the sub-voxel strict test could suppress
  them. With both changes, the held-out cubes' median written-twice share is 0.032; run as one block, the same cubes
  have at most 0.0002. The change cut it to the same proportion as the dev screen's 0.223 → 0.070 (0.32 ×), on cubes
  of a different scroll and block size.
* **The gain is smaller than the dev screen's, as registered.** At blocks of 256 the trim leaves about half the dev
  screen's doubling (0.104 against 0.223), and the median gain at τ = 4 is +5.7% against the dev screen's +17.2%.
* **The two changes together** raise ERLpen on every cube over main, by a median +17.6% at τ = 4 (+6.3% to +31.0%)
  and +13.2% at τ = 2, with merges at τ = 2 439 → 384 (finding 106's `real/main` rows).
* **Eight blocks now nearly match one block.** As a fraction of the same cube run as one block, ERLpen at τ = 4 is:
  main, 0.703 to 0.923; the trim, 0.822 to 0.963; both, 0.905 to 1.026. Coverage at τ = 4 with both lies within
  −0.003 to +0.016 of one block's.
* **No cost found on the deciding cubes.** Merges at τ = 2 fell on four cubes, held on three and rose by 2 on one
  (`s3_03494_01494_00494_512`, 78 → 80). Coverage rose on every cube. The risk the registration named, two distinct
  fibres less than 1.5 voxels apart merged where both blocks see both, would show in merges and coverage; neither
  moved against the change.
* **Face crossings:** of the 1,304 places where a fiber of the cube run as one block crosses a block face, the change
  makes 957 whole, 112 broken and 235 lost, against the trim's 884 / 142 / 278 and against main's 853 / 279 / 172.
  Lost crossings fall by 43 net, but more remain lost than on main.
  * In finding 106's diagnosis, 28 of the 63 joins main made that the trimmed copies miss had one copy lying along
    the other while the catalogue kept both. That is the case this change addresses. Which crossings it recovered
    here was not diagnosed.
  * The trimmed overlaps shorter than `MIN_OVERLAP` (29 of the 63) and the 125 crossings never chained are not what
    it addresses.
* **At villa's default block size:** on finding 107's zone, the change takes the zone's share from 0.052 to 0.017 and
  adds +3.4% at τ = 4 in the cube, with merges down at both tolerances.

## What it cannot say

* **Eight cubes, all Scroll 3, one hand tracing each, at 7.91 µm.**
* **Reused data:** the same cubes scored the trim (finding 106). This is a second test on them, not fresh data. The
  change's rule was set from villa's code and the zone's doubling, not from any held-out score.
* **On top of the trim only.** The change was not measured on main without the trim.
* **Without villa #2434** (open, by another contributor), which joins splines meeting at a shared end point. It edits
  another part of `_compare_pair`; the two merge cleanly there.
* **Blocks of 256 decide; one zone at 512 is reported.**
* **CPU cost** (from the run's file times; the record keeps none): each cube's two arms, scoring included, took 8 to
  12 minutes, and the zone's two arms 25 minutes.

## Records

* the registration, `docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md`;
* the script, `scripts/afv_generator_cross_block_duplicates.py`, and its runner,
  `repro/fibers/run_afv_generator_cross_block_duplicates.sh`;
* the change, `repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`;
* the dev screen and the zone's diagnosis, `reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json`;
* the record, `reports/afv_generator_cross_block_duplicates.json`;
* the figures here are tested against it by `tests/test_afv_generator_cross_block_duplicates_report.py`.
