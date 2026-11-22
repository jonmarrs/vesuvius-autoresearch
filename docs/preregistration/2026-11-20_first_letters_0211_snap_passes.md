# Pre-registration: does a three-pass snap read better than one pass, where PHerc. 211's First Letters prize was won?

**Written 2026-11-20, before any winding has been snapped more than once at PHerc. 211, and before finding 131 has
run.** Finding 134.

## The question

The recipe's snap (`snap_meshes.py`) moves each node of a fitted winding along its normal to the centre of the
nearest run of the predicted sheet within 15 voxels. It then rejects jumps, fills the gaps from neighbours, and
smooths the offsets. It runs once. Run again on its own output, it puts more of a winding on the predicted sheet.

That was seen on finding 130's six densified windings of PHerc. 0826 (geometry alone, no ink; medians over the six,
the share within 2 voxels of the predicted sheet):

| | one pass | two | three |
|---|---|---|---|
| nodes | 0.8303 | 0.8736 | 0.8905 |
| edge midpoints and cell centres (the triangles between nodes) | 0.8166 | 0.8526 | 0.8630 |

Every winding gained at every pass. The second pass moved nodes a median of 0.29 to 0.53 voxels, and the third 0.15
to 0.25.

Sitting on the centre of the predicted sheet need not read better: the ink lies on the papyrus surface, and Studio
reads 16 layers around ours. **At the place where the text is known, do the densified windings snapped three times
read better or worse than snapped once?**

## Reachability, checked before this was written

- **The code.** `run_snap.sh` takes `FL_SNAP_PASSES` (1 to 5, default 1), each pass snapping the one before. On the
  six windings above, one pass gave finding 130's snap byte for byte (18 of 18 grids), and three passes gave the
  hand-run third pass byte for byte.
- **The arms.** Finding 131 (registered, not yet run) makes three arms of finding 119's windings w033 to w036 and
  scores them by finding 124's statistic:
  - `f124`: finding 124's own windings and maps;
  - `rerun`: finding 121's route again, giving its run-to-run noise;
  - `dense2`: the windings subdivided twice, then snapped once.

  This finding adds `dense2s3`: finding 131's densified windings, snapped three times, then the same steps.
- **The comparison** (`snap_passes_read.py`) uses finding 131's functions, unchanged, on the cells all four arms
  reach. Its dry run gave every arm finding 124's own windings and maps. It reproduced finding 124's r 0.8247 on
  457,405 cells, the same cells as finding 131's dry run, with a change of 0 and the verdict `SNAP3_READS_SAME`.
- **Not checked:** the arm itself, and finding 131's arms, which do not exist yet.

## Procedure

`repro/first_letters/pherc0211_control/run_snap_passes.sh`, once, after finding 129's chain and before finding 133.
Each step runs only if the one before exited 0:
1. **check:** the weights and the winner's `inference.py` against their SHA-256 values; finding 131's arms
   `e2e_rerun` and `e2e_dense2` and its densified windings on disk.
2. **prepare:** the arm's winding list, and finding 131's densified windings as its raw windings.
3. **snap:** three passes.
4. **flatten, orient, render, studio:** finding 121's flatten, orientation against the winner's surface and 66-layer
   render, then Studio with the winner's command on planes 41 down to 26 and reversed. All are finding 131's steps.
5. **compare.**

Described, not registered: whether the first of the three passes equals finding 131's one-pass snap byte for byte.

## Registered measure and verdict

As finding 131: r is finding 124's statistic, on the cells all four arms reach. The margin is
max(0.02, 2 × |r(rerun) − r(f124)|), and the change is r(dense2s3) − r(dense2), both on the 4-decimal values the
record reports.

| verdict | rule |
|---|---|
| `SNAP3_READS_BETTER` | change ≥ margin |
| `SNAP3_READS_WORSE` | change ≤ −margin |
| `SNAP3_READS_SAME` | otherwise |
| `DOES_NOT_RUN` | a step failed; a render samples against the winner's normals; the `f124` arm does not give 0.8247 on its own cells; or the common cells are below finding 118's minimum share |

**Also registered: the geometry gain,** the median over the four windings of dense2s3's share of final nodes within
2 voxels of the predicted sheet, less dense2's.

**The consequence** is written into the record as `consequence`, which finding 133 reads (its amendment 1):

| verdict | geometry gain | consequence |
|---|---|---|
| `SNAP3_READS_BETTER` | any | `three_passes` |
| `SNAP3_READS_SAME` | above 0 | `three_passes` |
| `SNAP3_READS_SAME` | 0 or below, or missing | `one_pass` |
| `SNAP3_READS_WORSE` or `DOES_NOT_RUN` | any | `one_pass` |

So three passes are adopted if they read better, or if they read the same and sit more on the sheet. Reads
registered before this one keep one pass.

## Predictions, fixed now

1. **`SNAP3_READS_SAME`, moderate confidence.** At this place finding 121's windings already lie mostly on the sheet
   (0.90, 0.77, 0.91 and 0.80 of final nodes within 2 voxels). Against finding 124's r on each of them (0.87, 0.78,
   0.82 and 0.75), the least-squares slope is 0.61 per unit of that share. A gain of about 0.05 would then raise r by
   about 0.03, near the 0.02 line.
2. **The geometry gain is above 0** (0.02 to 0.06), with moderate-to-high confidence. So the expected consequence is
   `three_passes`.

## What the result cannot do

It is four windings at one place on one scroll. A `SAME` verdict leaves the reading effect under about 0.02 in r
unknown. The geometry gain, which then decides, was seen on PHerc. 0826 and is measured here.

## Cost

About 45 minutes of GPU time, at up to about 15 GB: four flattens of a densified grid, four 66-layer renders, and
eight Studio runs. About 10 GB of renders and maps. Nothing is uploaded, and Studio's outputs stay on this machine.
