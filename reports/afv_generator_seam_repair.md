Finding 140: the seam trim repaired as villa's review asked keeps most of its gain and loses almost no face crossings. ERLpen rose over villa main on 8 of 8 Scroll-3 cubes, by a median +9.0% at tolerance 4 (the original trim: +12.8%), with 178 face crossings lost against main's 172 (the original trim: 278) and coverage unchanged (2026-11-27)

The result of `docs/preregistration/2026-11-27_afv_generator_seam_repair.md`, registered at fe726fc7 (pushed 10:04:13
PST on 2026-11-27). The run went from 10:04:28 to 12:26:06 PST on 11-27, on the CPU, in two systemd user units
(the first cube in one, the other seventeen in the next). It was run by the commands that `repro/fibers/run_afv_generator_seam_repair.sh` records. Nothing was predicted:
every field is the cached `real` field of findings 106 and 109.

Inputs:
* villa main `9c1afbb1b`, the base of villa #2711. The #1934 head's `extend/stitch.py`, `catalog.py` and `overlap.py`
  are byte-identical to it.
* The #1934 head's prediction and spline modules.
* The repaired trim: villa #2711's branch plus the local commit `accc6d59c`, whose `extend/stitch.py` has sha256
  `62eddc21…`. The whole change against `9c1afbb1b` is
  `repro/fibers/villa_fiber_generator_trim_cut_ends_repaired_9c1afbb1b.patch`.
* Finding 106's trim: its first form (sha256 `c9ab1700…`) on Scroll 3, and its zone form (sha256 `362b78b1…`) on
  Scrolls 1 and 5.
* Scoring: ScrollGT, scoring version 3.

Results: `reports/afv_generator_seam_repair.json`, written once by the runner's verdict step.

**Decision `REPAIR_KEEPS_THE_GAIN`.** On Scroll 3, ERLpen at τ = 4 rose on 8 of 8 cubes, by a median +9.0%, and 178
crossings were lost, so all three of the rule's conditions held. By the registered rule, "the repair and these numbers
go to villa #2711 as its revision. Pushing to the PR and replying to the review are the owner's decisions."

The gate passed on all eighteen cubes: villa main's stitching and finding 106's trim each reproduced its recorded row
exactly. So the cached fields, the scoring and the two old arms are the ones findings 106 and 109 measured, and only
the trim differs between arms.

## What was run

villa's automated fiber generator (`vesuvius.fiber_spline_generator`, VC3D's **Generate automated fibers…**) at its
defaults (threshold 60, join angle 45°, minimum length 100, margin 32, no `--extend`). Each cube was cut into 8 blocks
of half its side, and each block's field was predicted from its own crop. The splines fitted from those fields were
stitched three ways:
* **main:** villa main's stitching, which trims nothing.
* **trim:** finding 106's trim, which drops 16 voxels at every end a block border cuts. This is villa #2711 as posted.
* **repaired:** the trim villa's review asked for (2026-11-25). A cut end is dropped only under two conditions:
  * another block whose read box meets this one has a spline of the same family within 3 voxels of 80% of the
    dropped points;
  * both copies, each without its own cut ends, still share 28 voxels (the catalogue's 24, plus 4).

  Otherwise the end is kept. A spline the trim would leave too short is kept whole. `generate` holds each block's
  untrimmed splines until every block whose read box meets its own has been fitted.

The review found two regressions in the trim as posted:
1. Trimming before the neighbour is seen can leave two copies less than the 24-voxel overlap they need, so one fiber
   on main becomes two.
2. A trace only one block detects, lying wholly in the cut band, disappears.

Lost face crossings measure the first regression. Coverage measures the second.

## Result: Scroll 3 (the verdict)

Finding 106's eight held-out 512³ cubes, in blocks of 256.

| cube | block | ERLpen τ = 4, main | trim | repaired | repaired over main, τ = 4 | τ = 2 | repaired over trim, τ = 4 | merges, τ = 2 | written length beside a same-family copy | face crossings lost | coverage τ = 4, repaired over main |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `s3_00994_00494_01994_512` | 256 | 37.67 | 46.5 | 44.18 | +17.3% | +9.1% | −5.0% | 43 → 38 → 43 | 0.248 → 0.073 → 0.159 | 29 → 45 → 30 | +0.1% |
| `s3_00994_01994_00494_512` | 256 | 33.3 | 38.15 | 37.22 | +11.8% | +6.1% | −2.4% | 56 → 53 → 56 | 0.217 → 0.095 → 0.143 | 28 → 39 → 30 | +0.2% |
| `s3_00994_02494_01494_512` | 256 | 29.72 | 32.64 | 32.25 | +8.5% | +4.9% | −1.2% | 66 → 55 → 64 | 0.245 → 0.114 → 0.187 | 18 → 27 → 18 | −0.0% |
| `s3_01994_01494_00994_512` | 256 | 33.18 | 40.27 | 38.22 | +15.2% | +7.9% | −5.1% | 12 → 8 → 10 | 0.286 → 0.150 → 0.205 | 18 → 25 → 20 | +0.6% |
| `s3_01994_01994_01494_512` | 256 | 36.71 | 37.82 | 38.04 | +3.6% | +3.2% | +0.6% | 36 → 30 → 35 | 0.175 → 0.091 → 0.137 | 15 → 22 → 14 | +0.5% |
| `s3_02994_02494_01994_512` | 256 | 51.89 | 60.7 | 56.78 | +9.4% | +14.2% | −6.5% | 53 → 52 → 54 | 0.293 → 0.166 → 0.224 | 26 → 42 → 25 | +0.1% |
| `s3_03494_01494_00494_512` | 256 | 25.2 | 27.01 | 26.24 | +4.1% | +4.5% | −2.9% | 88 → 78 → 88 | 0.249 → 0.151 → 0.210 | 13 → 29 → 16 | +0.1% |
| `s3_04494_00994_01494_512` | 256 | 32.59 | 36.2 | 34.8 | +6.8% | +5.5% | −3.9% | 85 → 72 → 83 | 0.235 → 0.086 → 0.165 | 25 → 49 → 25 | −0.2% |

Three-part cells read main → trim → repaired. "−0.0%" is a change smaller than 0.05% in either direction.

**Over the eight Scroll-3 cubes**

| | main | trim | repaired |
|---|---|---|---|
| face crossings whole / broken / lost | 853 / 279 / 172 | 884 / 142 / 278 | 958 / 168 / 178 |
| merges, τ = 2, summed | 439 | 386 | 433 |
| merges, τ = 4, summed | 1610 | 1483 | 1586 |
| written length beside a same-family copy, median | 0.246 | 0.104 | 0.176 |
| fibers written, summed | 5,236 | 4,469 | 4,943 |
| written length, voxels, summed | 879,004 | 771,968 | 846,568 |
| coverage, τ = 4, median | 0.3287 | 0.3197 | 0.3291 |
| coverage, τ = 2, median | 0.2722 | 0.2624 | 0.2717 |
| precision, τ = 4, median | 0.8865 | 0.8939 | 0.8870 |
| splits, τ = 4, summed | 30,903 | 15,989 | 23,368 |

The face crossings are those of the 1,304 reference fibers that the cube as one block writes across a block face.
**Whole** means one written fiber carries the reference fiber across the face; **broken** means its copies on the two
sides were written as separate fibers; **lost** means no fiber is written there.

| prediction | registered | measured | held |
|---|---|---|---|
| P1 (moderate) | ERLpen at τ = 4, repaired over main, up on at least 7 of 8 Scroll-3 cubes, median gain at least +8% | 8 of 8, median +9.0% | yes |
| P2 (moderate) | lost face crossings on Scroll 3, summed, at most 190 | 178 | yes |
| P3 (low to moderate) | median written-twice share on Scroll 3 at most 0.15 | 0.176 | no |
| P4 (low to moderate) | ERLpen at τ = 4 up over main on at least 15 of the 18 cubes | 18 of 18 | yes |
| P5 (moderate) | coverage at τ = 4 falls less with the repair than with the trim, median over the 18 | +0.1% against the trim's −3.3% | yes |

## Result: Scrolls 1 and 5 (described, not deciding)

Finding 109's ten cubes, which no step of the generator work before finding 109 had used. Four are 512³ in blocks of
256, and six are 256³ in blocks of 128.

| cube | block | ERLpen τ = 4, main | trim | repaired | repaired over main, τ = 4 | τ = 2 | repaired over trim, τ = 4 | merges, τ = 2 | written length beside a same-family copy | face crossings lost | coverage τ = 4, repaired over main |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `s1_02494_01494_03994_512` | 256 | 34.31 | 39.99 | 37.93 | +10.6% | +4.3% | −5.2% | 109 → 103 → 109 | 0.309 → 0.174 → 0.249 | 13 → 24 → 13 | +0.6% |
| `s1_08994_02494_03494_512` | 256 | 46.96 | 56.91 | 54.58 | +16.2% | +9.5% | −4.1% | 62 → 60 → 61 | 0.290 → 0.132 → 0.202 | 17 → 32 → 18 | −0.0% |
| `s1_09997_02497_03497_256` | 128 | 39.37 | 52.29 | 44.44 | +12.9% | +13.9% | −15.0% | 5 → 2 → 5 | 0.418 → 0.123 → 0.333 | 3 → 5 → 3 | −0.5% |
| `s5_05497_01997_02997_256` | 128 | 39.91 | 65.31 | 47.7 | +19.5% | +3.6% | −27.0% | 5 → 3 → 5 | 0.504 → 0.235 → 0.416 | 2 → 9 → 2 | +0.1% |
| `s5_05497_02497_02497_256` | 128 | 33.36 | 37.2 | 35.07 | +5.1% | +5.6% | −5.7% | 8 → 7 → 8 | 0.400 → 0.205 → 0.332 | 7 → 6 → 6 | +0.6% |
| `s5_08994_02994_03994_512` | 256 | 43.48 | 48.07 | 47.74 | +9.8% | +2.0% | −0.7% | 38 → 33 → 38 | 0.212 → 0.095 → 0.157 | 8 → 10 → 8 | +0.1% |
| `s5_08997_02497_04997_256` | 128 | 43.35 | 62.09 | 49.66 | +14.6% | +27.5% | −20.0% | 4 → 3 → 3 | 0.429 → 0.110 → 0.340 | 4 → 9 → 4 | −0.0% |
| `s5_11497_05497_03997_256` | 128 | 45.67 | 58.56 | 52.74 | +15.5% | +8.8% | −9.9% | 15 → 14 → 14 | 0.521 → 0.288 → 0.454 | 2 → 12 → 3 | +0.1% |
| `s5_15494_04494_02494_512` | 256 | 22.18 | 23.11 | 23.17 | +4.5% | +5.6% | +0.3% | 68 → 63 → 69 | 0.195 → 0.074 → 0.128 | 20 → 27 → 21 | +0.4% |
| `s5_16997_03497_03997_256` | 128 | 22.22 | 24.95 | 23.84 | +7.3% | +10.4% | −4.4% | 11 → 10 → 10 | 0.417 → 0.164 → 0.310 | 8 → 14 → 8 | +0.2% |

**Over the ten Scroll-1 and -5 cubes**

| | main | trim | repaired |
|---|---|---|---|
| face crossings whole / broken / lost | 573 / 253 / 84 | 615 / 147 / 148 | 638 / 186 / 86 |
| merges, τ = 2, summed | 325 | 298 | 322 |
| merges, τ = 4, summed | 887 | 824 | 872 |
| written length beside a same-family copy, median | 0.409 | 0.148 | 0.321 |
| fibers written, summed | 3,018 | 2,461 | 2,832 |
| written length, voxels, summed | 532,092 | 455,701 | 509,317 |
| coverage, τ = 4, median | 0.4380 | 0.4226 | 0.4375 |
| coverage, τ = 2, median | 0.3048 | 0.2959 | 0.3039 |
| precision, τ = 4, median | 0.9146 | 0.9171 | 0.9132 |
| splits, τ = 4, summed | 22,200 | 11,451 | 17,318 |

**Gains in ERLpen, median (range)**

The last column is the share of the trim's gain over main at τ = 4 that the repair keeps, as a median.

| cubes | trim over main, τ = 4 | repaired over main, τ = 4 | repaired over main, τ = 2 | repaired over trim, τ = 4 | share of the trim's gain kept |
|---|---|---|---|---|---|
| 8 | +12.8% (+3.0% to +23.4%) | +9.0% (+3.6% to +17.3%) | +5.8% (+3.2% to +14.2%) | −3.4% (−6.5% to +0.6%) | 0.72 |
| 10 | +18.9% (+4.2% to +63.6%) | +11.7% (+4.5% to +19.5%) | +7.2% (+2.0% to +27.5%) | −5.4% (−27.0% to +0.3%) | 0.57 |

## What it shows

1. **The review's first regression is gone, to within a few crossings.** The trim as posted lost 106 more face
   crossings than main on Scroll 3 (278 against 172) and 64 more on Scrolls 1 and 5 (148 against 84). The repair loses
   6 and 2 more. Per cube, the repair loses at most 3 crossings more than main, and 1 fewer on three cubes. It also
   carries the most fibers whole across the faces of the three arms: 958 of 1,304 on Scroll 3 (main 853, trim 884).
2. **The second regression is gone as far as coverage can see it.** Coverage at τ = 4 is main's to within 0.7% on all
   eighteen cubes (median +0.1%). The trim was below main on all eighteen (median −3.3%).
3. **The repair keeps about three quarters of the gain on Scroll 3, and somewhat over half on Scrolls 1 and 5.** The
   median ERLpen gain over main at τ = 4 is +9.0% against the trim's +12.8% on Scroll 3, and +11.7% against +18.9% on
   Scrolls 1 and 5. The repair scores below the trim on 7 of 8 and 9 of 10 cubes. The largest losses are on the 256³
   cubes cut in blocks of 128, a size no villa user runs, where the trim's gains were largest.
4. **The gain is fewer breaks, not fewer merges.** Merges are almost main's (433 against 439 at τ = 2 on Scroll 3;
   the trim had 386). Splits at τ = 4 fall by a quarter (30,903 → 23,368), where the trim halved them. The repair
   joins the bent copies that a neighbour holds, and leaves the rest as main does.
5. **More copies are left than predicted (P3 failed).** The written-twice share falls from 0.246 to 0.176 on Scroll 3,
   not to 0.15 or below. The ends the repair keeps are, by construction, ends no neighbouring copy covers closely
   enough, or ends whose trimming would break a join. Some of the length they keep still lies beside a same-family
   fiber. Finding 108's catalogue change, which #2711 does not include, is the measured remedy for that residue.

## Checks made after the result (not registered)

* **The runner's arm is what villa's `generate` does.** The runner fits every block, then trims each block against
  the untrimmed splines of the blocks whose read box meets its own. The repaired `generate` does the same thing in a
  different order: it releases each block once every such block is fitted. Each block's trim depends only on its own
  splines and on those untrimmed neighbours, so the order changes nothing. A simulation of `generate`'s release and
  free bookkeeping, copied from `accc6d59c`, ran on five zone layouts (2×2×2 grids of 128, 256 and 512; 4×2×3 of 512;
  and a 2×3×1 grid of uneven sizes). Every block was released after all its neighbours were fitted, in index order,
  and every held spline set was freed by the end.
* **Previews come later on multi-block zones.** In a 2×2×2 zone, every block's read box meets every other's at the
  centre, so no block is released, and no VC3D preview appears, until the eighth block is fitted. On the 4×2×3 grid,
  at most 17 of the 24 blocks' spline sets are held at once. The splines are point lists, not fields, so the memory
  cost is small, but the live preview is delayed. A one-block zone, VC3D's default, is unchanged.
* **Only the trim differs from villa main.** The #1934 head's `extend/stitch.py`, `catalog.py` and `overlap.py`
  (where `MIN_OVERLAP = 24.0`) are byte-identical to villa main `9c1afbb1b`. The measured `extend/stitch.py`
  (sha256 `62eddc21…`) is `accc6d59c`'s file, and the patch in `repro/fibers/` is `git diff 9c1afbb1b accc6d59c`
  byte for byte.

## Limits

1. **Cached fields from #1934's head**, as findings 106 and 109 used. villa main now fits splines with the native
   `vc_reader`; the stitching and catalogue are villa main's.
2. **Blocks of 256 and 128**, not VC3D's default 512. The 1024³ default-zone case (finding 107) is addendum 1, below.
3. **One hand tracing per cube.** Nothing here measures reading.
4. The written-twice share and the face crossings are this repository's measures, not ScrollGT's.

## Addendum 1: finding 107's 1024³ zone (described)

Registered at 6313e162 (pushed 12:33:11 PST on 11-27), before the zone ran. The run went from 12:33:19 to 13:04:03 PST,
on the CPU at nice 10, in its own systemd user unit. It used finding 107's cached per-block fields and its scan
(sha256 `63865b83…`), so nothing was predicted. Results: `reports/afv_generator_seam_repair_zone.json`.

The gate passed: main and finding 107's zone trim each reproduced finding 107's recorded row exactly.

One 1024³ zone of the Scroll-3 scan, at villa's default `--block-size 512` (8 blocks), centred on the held-out cube
`s3_04494_00994_01494_512`. The zone's three inner faces cross the cube.

| | main | trim | repaired |
|---|---|---|---|
| zone: fibers written | 5,766 | 5,326 | 5,555 |
| zone: written length, voxels | 1,031,976 | 972,804 | 1,009,458 |
| zone: written length beside a same-family copy | 0.120 | 0.052 | 0.078 |
| cube: fibers written inside | 1,052 | 904 | 1,004 |
| cube: written length beside a same-family copy | 0.247 | 0.099 | 0.175 |
| cube: ERLpen, τ = 4 | 35.79 | 41.51 | 39.44 |
| cube: ERLpen, τ = 2 | 15.11 | 15.95 | 15.93 |
| cube: merges, τ = 4 | 300 | 269 | 292 |
| cube: merges, τ = 2 | 92 | 82 | 92 |
| cube: coverage, τ = 4 | 0.4296 | 0.4138 | 0.4323 |
| cube: coverage, τ = 2 | 0.3406 | 0.3273 | 0.3418 |

In the cube, the repair raises ERLpen over main by +10.2% at τ = 4 and +5.4% at τ = 2 (the trim: +16.0% and +5.6%),
with merges at τ = 2 equal to main's and coverage at τ = 4 +0.6% (the trim: −3.7%). Over the zone, the repair
removes 0.62 of the written-twice length the trim removes. The pattern is the one on the eighteen cubes: joins and
coverage stay main's, most of the gain remains, and some seam copies remain.

After the record, villa #2711's local branch gained `53baea280`, which changes only `test_stitch.py`. It adds the
review's two cases at the default block size: main's join of copies at x 100–537 and 507–770, and a 125-voxel trace
only block 0 detects along its face at x 535. Both pass with the repair. With finding 106's trim, the first gives two
fibers and the second loses the trace. The measured `extend/stitch.py` is unchanged.
