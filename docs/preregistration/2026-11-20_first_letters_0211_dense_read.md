# Pre-registration: does the twice-denser snap read better where PHerc. 211's First Letters prize was won?

**Written 2026-11-20, before any winding has been densified, snapped, flattened, rendered or read for this test.**
Finding 131.

## The question

Finding 130 found that subdividing the raw windings twice before the snap keeps more of the rendered surface on the
predicted sheet: +0.0697 at the median within 2 voxels, on six of PHerc. 0826's windings (`DENSE_SNAP_HELPS`). Its
registered consequence put the denser snap into the band reads: finding 126 (PHerc. 0358, running) and finding 129
(PHerc. 0813, queued). That was a measure of geometry. Nothing yet shows that the denser snap reads better, and an
eligible band cannot show it, because no answer is known there. **At the one place where this pipeline reads a known
text, the winner's PHerc. 211 surface, does Studio's map of the denser-snapped windings agree with the winner's map
more, less, or the same?**

## Reachability, checked before this was written

- **The inputs are on this machine:**
  - finding 119's 30,000-step fit of PHerc. 211's band z 7650 to 9150, with its raw windings w033 to w036;
  - finding 121's route for them (arm `e2e`: snap, flatten, orientation against the winner's surface, 66-layer
    renders, all flipped);
  - finding 124's Studio maps of those renders in both orders, and its record: r 0.8247 against the winner's map on
    457,405 of 550,482 mask cells.
- **The comparison code reproduces finding 124.** `dense_read.py compare` carries each arm onto the winner's surface
  with finding 110's transfer and scores it with finding 124's own function (`studio_e2e.score`). It was dry-run
  today with finding 124's windings and maps standing in for all three arms. It gave:
  - r 0.8247 on 457,405 cells;
  - normal cosines −0.9983, −0.9967, −0.9979 and −0.9962;
  - transfer distances of 1.94 and 3.45 voxels at the median and 95th percentile.

  These are finding 124's numbers. The dry run also found and fixed a bug in the new code: every winding's normal
  cosine had been computed from the last winding.
- **Described in the dry run, for the baseline only:** finding 121's final windings have 0.9034, 0.7742, 0.9105 and
  0.7973 of their nodes within 2 voxels of the predicted sheet (w033 to w036). Finding 124's per-winding r was 0.8737,
  0.7776, 0.8238 and 0.7527. The two windings least on the sheet read worst.
- **Not checked:** whether finding 121's route repeats byte for byte. The flatten runs on the GPU, so the re-run arm
  below measures the route's own noise.

## Procedure

`repro/first_letters/pherc0211_control/run_dense_read.sh`, once, after finding 126's chain has finished and before
finding 129's starts. Each step runs only if the one before exited 0. Two new arms of w033 to w036:

- **`rerun`:** the raw windings as they are, through finding 121's route again.
- **`dense2`:** the raw windings subdivided twice (`densify_winding.py --factor 2`, as finding 130 and the band reads
  do), through the same route.

Each arm goes through:

1. snap (`run_snap.sh`);
2. flatten (`run_flatten.sh`);
3. orientation against the winner's surface (`end_to_end.py orient`, finding 121's rule);
4. a 66-layer render, flipped where the orientation says;
5. Studio with the winner's command on layers 41 down to 26 and on the reversed planes.

Then `dense_read.py compare` scores three arms: finding 124's (`f124`), `rerun` and `dense2`.

## Registered measure and verdict

- **The cells:** the winner's mask cells that every arm reaches, with finding 124's other conditions (finite maps,
  the winner's surface valid).
- **r:** finding 124's statistic, Studio's map carried onto the winner's surface against the winner's map, background
  off, for each arm on those cells.
- **noise** = r(`rerun`) − r(`f124`): the same route run twice.
- **margin** = the larger of 0.02 and 2 × |noise|.
- **change** = r(`dense2`) − r(`rerun`).
- noise, margin and change are computed on r as recorded, to 4 decimals, so a change exactly at the margin
  counts.

| verdict | rule |
|---|---|
| `DENSE_READS_BETTER` | change ≥ margin |
| `DENSE_READS_WORSE` | change ≤ −margin |
| `DENSE_READS_SAME` | otherwise |
| `DOES_NOT_RUN` | a step failed; a render samples against the winner's normals; the `f124` arm on its own cells does not give r 0.8247; or the common cells are under half the mask |

**Described, deciding nothing:**

- each arm's numbers on the common cells and on its own cells (r with the background in, the controls, overlap);
- the transfer distances;
- each arm's final nodes within 2 voxels of the predicted sheet;
- whether `rerun`'s snapped and final windings are byte-identical to finding 121's.

## Predictions, fixed now

1. **`DENSE_READS_SAME`, low-to-moderate confidence.**
   - For: these windings already lie 77% to 91% on the predicted sheet, and Studio drew the letters from them.
   - Against: the denser snap's gains in finding 130 were largest where the surface was least on the sheet, and here
     the two windings least on the sheet read worst.
2. The noise is below 0.01.

## Consequences

- **`DENSE_READS_WORSE`:** finding 129 is amended, before any of its data exist, to snap the fit's own grid
  (`FL_DENSIFY` unset). Finding 126's report says its read used a snap that read worse at the known place.
- **`DENSE_READS_SAME` or `DENSE_READS_BETTER`:** the band reads keep the denser snap.
- **`DOES_NOT_RUN`:** the band reads keep it. This test is reported as not run.

## What the result cannot do

- It is four windings at one place of one crushed scroll.
- "Reads better" means Studio's map agrees more with the winner's Studio map. It does not measure legibility to an
  eye.

## Cost

About an hour:
- the snaps, a few minutes;
- eight flattens of 80 to 250 s;
- eight renders of about a minute;
- 16 Studio maps of about 70 s.

GPU memory up to about 15 GB, and about 5 GB of renders. It runs between findings 126 and 129, so it shares the
machine with neither. Nothing is uploaded; PHerc. 211's prize was announced, but these maps stay on this machine as
finding 124's did.
