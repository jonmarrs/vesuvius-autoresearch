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
