# Pre-registration: does the sheet-following score, taken per tile, pick out the tiles of a fit that lie on the right sheet?

**Written 2026-11-15, before any tile of a PHerc. 343 fit has been scored or labelled against the published
windings.** Finding 117.

PHerc. 343 is already awarded. Nothing here concerns a scroll that is still eligible.

## The question

Finding 116 showed the sheet-following score (the excess) cannot tell a spiral that follows the sheets from one
turning the wrong way. It also showed the two fits put their surfaces in the same places about half the time. A
First Letters read needs neither the direction nor the order of the turns. It needs the surface on the right sheet
over a tile a few millimetres across. So the question that decides how the next band is chosen is a local one:
**within one fitted winding, do the tiles with a high excess lie on the right sheet more often than the tiles
with a low one?** If yes, the score can choose tiles to read, and the registered consequence of finding 116 can
be narrowed to "no gating by the winding-level score". If no, the score does not choose tiles either, and the
next band needs a different gate.

The only place this can be checked is PHerc. 343, where the recipe's author published two windings (w047 and
w048, z 9500 to 11000) and finding 110 fitted the same band here.

## Reachability, checked before this was written

- **Inputs on disk.** Finding 110's raw fitted windings (`work/fit_recipe/.../meshes/fitted`, w010 to w129, grid
  step 20 voxels), its snapped and flattened windings (`work/final_recipe/w047.tifxyz`, `w048.tifxyz`), the
  published windings (`pherc343_repro/src/repo/outputs/w04[78]_R5B2_z9500-11000.tifxyz`, grid step 20 voxels)
  and the distance field (`work/surf_sdt/PHerc0343_surf_sdt.ome.zarr`).
- **There are wrong tiles to find.** Finding 110's report: the raw fitted w047 and w048 have 33.1% and 47.3% of
  the published nodes within 2 voxels (medians 3.23 and 2.16). After the snap: 75.6% and 80.5%. So the raw
  windings hold right and wrong regions in about equal measure. That is a per-winding number from the report; I
  have not looked at where the wrong regions are.
- **The score was taken on raw windings** in findings 112 to 116, so the registered test is on raw windings.
  The snapped windings, which are what an ink read uses, are a description.
- **Tile size.** Finding 113's tiles are 96 lattice cells, 3.6 mm, about 385 voxels. Here a tile is a block of
  19 by 19 nodes of the fitted grid, about 380 voxels a side.
- **Not checked:** the script below has not run. Its first run on these inputs is the measurement.

## The floor

Measured in the same run, not inherited. The tile labels are slid along the winding by a whole number of tiles,
cyclically in each row of tiles, for every shift that is not zero, and the AUC is recomputed each time. The slid
labels keep their own spatial clustering and lose their alignment with the excess. The floor is the 95th
percentile of those AUCs.

## Procedure

Script `repro/first_letters/pherc343/tile_gate/tile_gate.py`, run once, on CPU.

1. For each of the raw fitted windings w047 and w048: at each node, the excess's two readings as in
   `band_fit_quality.py` (inside a predicted sheet at the node; mean of the same at ±6 voxels along the normal).
2. At each node, the distance along the published winding's normal to the published winding of the same index:
   the nearest of its 12 nearest nodes whose sideways offset is at most 30 voxels (finding 110's
   `LATERAL_MAX`). A node with none is uncovered.
3. Non-overlapping tiles of 19 by 19 nodes. A tile is kept if it has at least 200 nodes with all three distance
   readings and at least half its nodes covered.
4. Per tile: `tile_excess` = share inside a sheet minus displaced share, over its scored nodes; `right` = at
   least half its covered nodes within 2 voxels of the published winding.
5. AUC of `tile_excess` for right against wrong tiles, both windings pooled; its floor (above); the share of
   tiles with `tile_excess` of at least 0.07 that are right, against the share of all tiles that are right.
6. Descriptions: the same with 4 voxels as the line for `right`; the same on the snapped windings.

## Predictions, fixed now

- **What I expect: AUC between 0.60 and 0.75** (`LOCAL_GATE_WEAK`), with low confidence. A tile between sheets
  should score low and one on its sheet high; a tile on the neighbouring sheet scores high and is wrong, and
  finding 116 says such tiles exist in a wrong fit. How many there are in a right one, I do not know.

## Decision rule

| outcome | verdict |
|---|---|
| the script fails, or fewer than 15 right or 15 wrong tiles | `DOES_NOT_RUN` |
| AUC at or below the floor | `LOCAL_GATE_FAILS` |
| AUC above the floor and below 0.60 | `LOCAL_GATE_FAILS` |
| AUC above the floor, 0.60 to 0.75 | `LOCAL_GATE_WEAK` |
| AUC above the floor and at least 0.75, and the share right among tiles at 0.07 or above at least 0.15 above the share right overall | `LOCAL_GATE_WORKS` |
| AUC at least 0.75 and the share condition fails | `LOCAL_GATE_WEAK` |

What each does to the campaign:

- `LOCAL_GATE_WORKS`: the next read of an eligible band (PHerc. 0826's, finding 115's fit) may choose tiles by
  tile excess, registered separately. Whether to do so is the owner's decision, after finding 116.
- `LOCAL_GATE_WEAK`: tile excess is reported beside every tile read and does not choose tiles; reads remain
  detection tests.
- `LOCAL_GATE_FAILS`: the score does not choose windings or tiles. The next gate is built on the snapped
  surface, and nothing further is read until it exists.

## What the result cannot do

- **One scroll, two windings, one fit.** PHerc. 343 is round and well scanned; the eligible scrolls in reach are
  crushed. A gate that works here may not work there.
- **The tiles are not independent.** Neighbouring tiles share sheets and errors; the AUC has no honest standard
  error, which is why the floor is the slid labels and not a formula.
- **"Right" is the published winding**, which is itself one author's surface. A tile could be on the true sheet
  and far from the published one.
- It says nothing about ink.

## Limits

The 19-node tile, the 2-voxel line, the half-covered rule and the three AUC lines are judgements made here.

## Cost

Under an hour of CPU. No GPU, no fit, no upload.
