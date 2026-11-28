# Pre-registration: does a seam trim that keeps joins and lone traces still remove the generator's seam copies?

**Written 2026-11-27, before the repaired trim has run on any data.** Finding 140.

## The question

villa #2711 trims the ends a block border bends in villa's automated fiber generator (findings 106, 107 and 109).
villa's review (2026-11-25) found two regressions and recommends merging once both are repaired:

1. **A trim can remove a valid join.** It drops 16 voxels at a cut end before the neighbouring block is predicted;
   when the neighbour's copy starts late, the copies keep less than the catalogue's 24-voxel overlap, and main's one
   fiber becomes two. Finding 106's diagnosis counted 63 such degraded crossings on Scroll 3.
2. **A trace only one block detects can disappear,** when every point of it lies in the cut band.

The repair (`fiber-generator-trim-cut-ends` at `accc6d59c` on the owner's villa fork, not yet pushed) drops a cut
end only where another block of the zone has a spline of the same family within 3 voxels of 80% of the dropped
points, and only when both copies, without their own cut ends, still share 28 voxels (the catalogue's 24 plus 4).
Otherwise the end is kept, and a spline the trim would leave too short is kept whole. `generate` holds each block's
untrimmed splines until its neighbours are fitted. Files: `extend/stitch.py` sha256 `62eddc21…`, `cli.py`
`6bb3e869…`; the whole change against villa main `9c1afbb1b` is
`repro/fibers/villa_fiber_generator_trim_cut_ends_repaired_9c1afbb1b.patch`. The runner is
`scripts/afv_generator_seam_repair.py`.

**On the same predictions, does the repaired trim keep the seam fix's gain while losing no more face crossings than
main does?**

## Data and arms

The cached per-block fiber fields of findings 106 and 109, so the predictions are fixed and only the trim differs:
- **Scroll 3:** finding 106's eight held-out 512³ cubes, 8 blocks of 256 (`real` arm: each block predicted from its
  own crop);
- **Scrolls 1 and 5:** finding 109's ten cubes, four 512³ in blocks of 256 and six 256³ in blocks of 128.

Arms, each block's splines fitted from its cached field as before (`extract_splines`, threshold 60), stitched, and
cleaned at the CLI defaults (no `--extend`):
- **main:** untrimmed. **Gate:** each cube's row must equal its recorded `real/main` row exactly.
- **trim:** finding 106's trim. **Gate:** each row must equal its recorded `real/patched` (Scroll 3) or `real/trim`
  (Scrolls 1 and 5) row exactly.
- **repaired:** the new trim, each block trimmed against the untrimmed splines of the blocks whose read box meets its
  own.

Scored as before against the hand tracing: merge-penalized ERL and merges within 2 and 4 voxels, coverage, the
written-twice share (length within 1.5 voxels of a different same-family fiber), and the face crossings of the
one-block reference fibers (whole, broken, lost).

## Predictions

1. On the eight Scroll-3 cubes, repaired over main: merge-penalized ERL at tolerance 4 up on at least 7, median gain
   at least +8% (the trim's: +12.8%). Moderate confidence.
2. Lost face crossings on Scroll 3, summed: at most 190 with the repair (main 172, trim 278). Moderate.
3. The median written-twice share on Scroll 3: at most 0.15 (main 0.246, trim 0.104). Low to moderate.
4. On all eighteen cubes, ERL at tolerance 4 up over main on at least 15. Low to moderate.
5. Coverage at tolerance 4 falls less with the repair than with the trim, at the median over the eighteen. Moderate.

## Verdict, on the eight Scroll-3 cubes

| verdict | rule |
|---|---|
| `REPAIR_KEEPS_THE_GAIN` | ERL at tolerance 4 up over main on at least 7 of 8, median gain at least +6%, and lost crossings at most 190 |
| `REPAIR_LOSES_THE_GAIN` | median gain under +3%, or up on 5 or fewer |
| `REPAIR_PARTLY` | otherwise |
| `DOES_NOT_RUN` | a main or trim row does not reproduce, or a step fails |

The ten Scroll-1 and -5 cubes are described beside it, not part of the verdict.

## What each verdict does

- **`REPAIR_KEEPS_THE_GAIN`:** the repair and these numbers go to villa #2711 as its revision. Pushing to the PR and
  replying to the review are the owner's decisions.
- **`REPAIR_PARTLY`:** the numbers go to the owner, who decides whether to post the revision as it is.
- **`REPAIR_LOSES_THE_GAIN`:** the gain depended on the ends the review asks to keep. The owner decides whether to
  withdraw #2711 or rethink it; the review is told either way.

## Limits

1. Cached fields from #1934's head, as findings 106 and 109 used; villa main has since moved its spline fitting to
   the native `vc_reader`. The stitcher and catalogue are byte-identical to main's.
2. Blocks of 256 and 128, not the default 512. The 1024³ default-zone case (finding 107) is measured after this, the
   same way, and described.
3. One hand tracing per cube.

## Cost

CPU only, from the cached fields: spline fitting, stitching and scoring, about three runs of each cube. A few hours.

## Addendum 1 (2026-11-27, after the eighteen cubes, before the 1024³ zone runs)

The registered verdict is in (`REPAIR_KEEPS_THE_GAIN`); this adds only the measurement limit 2 promised. Finding 107's
1024³ Scroll-3 zone in 8 blocks of 512 (villa's default `--block-size`), from its cached per-block fields
(`prob_block_0..7.npy`) and scan, so nothing is predicted. Three arms, each scored exactly as finding 107 scored its
two: `main` and `patched` (finding 107's zone trim) must equal finding 107's recorded rows, or nothing is reported as a
result; `repaired` is the new trim, each block against the untrimmed splines of the blocks whose read box meets its own
(all eight meet at the zone's centre). Reported, without a verdict: the zone's written fibers, length and written-twice
share, and inside the hand-traced cube the written-twice share and ScrollGT scores at τ = 2 and 4.

## Addendum 2 (2026-11-28, before any run with villa #2434)

**Why.** villa merged #2434 (joins at a shared end point, `22570d2bf`) on 2026-11-25, and #2711's head `8a7f76803`
now merges villa main `ee9198c85` above it. Finding 140's figures predate #2434, which changed three modules every
arm here runs through: the catalogue proposes a join between end points under 0.25 voxels apart (the direction taken
from the end's tangent, never stepping back along either end), `cleanup.cut_sharp_joins` no longer keeps a gap at a
join it cuts, and `stitch._gap_ranges` keeps a gap whose two ends meet at one point. **With #2434 in both arms, does
the repaired trim keep its gain over main?**

**Package.** #1934's head package as before, with #2434's own diff applied
(`repro/fibers/villa_2434_on_pr1934_afv_spline_generator.patch`, sha256 `d4f47ea8…`). Its `extend/catalog.py`,
`extend/stitch.py` and `extend/expander.py` then equal villa `ee9198c85`'s byte for byte; its `cleanup.py` is #1934's
with #2434's hunk (#1934's copy keeps scipy's morphology for `ExteriorBlack`, as every arm of findings 106 to 109 and
140 did). **Gate:** every `.py` file of the package equals #1934's except these four, which must have sha256
`8a488f15…` (`cleanup.py`), `5310073b…` (`catalog.py`), `b575b5d7…` (`expander.py`) and `ddd4cfd9…` (`stitch.py`);
and the loaded stitcher must chain two splines that meet at one shared end point into one fiber (#2434's own test
case), which #1934's makes two.

**Repaired trim.** `extend/stitch.py` at #2711's head `8a7f76803` (sha256 `60d4bc10…`). Its `trim_cut_ends` is
`accc6d59c`'s, the file finding 140 ran (`62eddc21…`): the two differ only in #2434's `_gap_ranges` hunk, and the
arms take only `trim_cut_ends` from it.

**Reproduction gate.** Before the new arms, the first Scroll-3 cube (`s3_00994_00494_01994_512`) runs again exactly as
finding 140 ran it (#1934's package, its three arms, the files whose sha256 finding 140 recorded): main and trim must
reproduce their recorded rows, and repaired must equal finding 140's recorded repaired row. Otherwise nothing is
reported as a result.

**Arms**, on finding 140's cached fields and blocks, scored as finding 140 scored them (the face-crossing reference
stays each cube's recorded one-block main fibers):
- `main`: untrimmed, with #2434;
- `repaired`: the repaired trim, with #2434.

Over the eighteen cubes, then finding 107's 1024³ zone, described as in addendum 1.

**Verdict, on the eight Scroll-3 cubes:** finding 140's rule with #2434 in both arms. Finding 140's lost-crossing line
of 190 was main's 172 plus 18; here it is main's own count plus 18.

| verdict | rule |
|---|---|
| `GAIN_HOLDS_AFTER_2434` | ERL at tolerance 4 up over main on at least 7 of 8, median gain at least +6%, and lost crossings at most main's plus 18 |
| `GAIN_LOST_AFTER_2434` | median gain under +3%, or up on 5 or fewer |
| `GAIN_PARTLY_AFTER_2434` | otherwise |
| `DOES_NOT_RUN` | a gate fails, or a step fails |

**Predictions.**
1. `GAIN_HOLDS_AFTER_2434`. Moderate to high confidence: #2434 joins pieces whose ends coincide, while the trim acts
   on copies that overlap.
2. The median gain at tolerance 4 on Scroll 3 lies within 2 percentage points of finding 140's +9.0%. Moderate.
3. #2434 moves main's own merge-penalized ERL at tolerance 4 by under 2% at the median over the eight Scroll-3 cubes.
   Low to moderate.
4. On the zone, the written-twice share with the repaired trim is at most 0.09 (finding 140: 0.078). Moderate.

**What each verdict does.**
- **`GAIN_HOLDS_AFTER_2434`:** the "figures predate #2434" caveat can come off #2711, with these numbers. Editing the
  PR body or telling the review is the owner's decision.
- **`GAIN_PARTLY_AFTER_2434` or `GAIN_LOST_AFTER_2434`:** the numbers go to the owner. #2711's figures stay labelled
  as measured before #2434, and the owner decides what to tell the review.

**Cost.** CPU, from the cached fields: the gate cube's three arms, two arms on each of the eighteen cubes, and the
zone's two. About three to four hours.
