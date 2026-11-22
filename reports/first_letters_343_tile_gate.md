On PHerc. 343, the sheet-following score taken per tile picks out the tiles of a fitted winding that lie on the published sheet: AUC 0.895, and all 32 tiles at 0.07 or above are right (2026-11-15)

Finding 117. Finding 116 showed the sheet-following score (the excess) cannot tell a spiral turning the right way
from one turning the wrong way. A First Letters read does not need the direction; it needs the surface on the
right sheet over a tile a few millimetres across. This asks the local question on the one scroll where it can be
checked: within finding 110's raw fitted windings w047 and w048 of PHerc. 343 (z 9500 to 11000), do the tiles with
a high excess lie on the published windings more often than those with a low one? Registered before any tile was
scored or labelled: `docs/preregistration/2026-11-15_first_letters_343_tile_gate.md` (commit `381705e7`).
Record: `reports/first_letters_343_tile_gate.json`. Script: `repro/first_letters/pherc343/tile_gate/tile_gate.py`.

PHerc. 343 is already awarded. Nothing here concerns a scroll that is still eligible.

**Verdict `LOCAL_GATE_WORKS`**, by the registered table: the script exited 0, 53 tiles are right and 17 wrong,
the AUC is 0.895 against a floor of 0.777, and 100% of the tiles at 0.07 or above are right against 75.7% of all
tiles. I registered `LOCAL_GATE_WEAK` (AUC 0.60 to 0.75), with low confidence. That prediction was wrong.

## The measurement

A tile is 19 by 19 nodes of the fitted grid, about 380 voxels (3.6 mm) a side, the size of finding 113's tiles.
`tile_excess` is the share of the tile's nodes inside a predicted sheet minus the share for the same nodes moved
6 voxels along the normal. A tile is right when at least half its covered nodes are within 2 voxels of the
published winding, along that winding's normal.

| | tiles | right | wrong | AUC | floor (95th percentile of slid labels) | right, all tiles | right, tiles at 0.07 or above |
|---|---|---|---|---|---|---|---|
| raw windings, 2 voxels (the test) | 70 | 53 | 17 | **0.895** | 0.777 | 75.7% | **100.0%** (32 tiles) |
| raw windings, 4 voxels (described) | 70 | 61 | 9 | 0.856 | 0.714 | 87.1% | 100.0% (32 tiles) |
| snapped windings, 2 voxels (described) | 122 | 122 | 0 | none | none | 100.0% | 100.0% (119 tiles) |

w047 has 23 right tiles of 35, w048 30 of 35. The snapped windings, which are what an ink read renders, have no
wrong tile at all, so the AUC is undefined there.

## Why the floor is high

Not registered. The floor slides each winding's tile labels along its rows of tiles, 11 tiles a row, by every
whole shift. Shifted by one tile either way, the labels keep most of their alignment, because neighbouring tiles
are usually right or wrong together:

| shift (tiles) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| AUC | 0.759 | 0.603 | 0.510 | 0.371 | 0.333 | 0.297 | 0.393 | 0.479 | 0.618 | 0.792 |

Shifts 3 to 8 tiles, where the labels come from elsewhere on the winding, give 0.30 to 0.51. The registered floor
is the 95th percentile over all ten, which the two nearest shifts set. The AUC clears it by 0.117 and clears the
distant shifts by about 0.4.

## What the wrong tiles are

Not registered.

- **All 17 wrong tiles score below zero** (−0.400 to −0.004). Nowhere on these two windings is a tile on the
  wrong sheet while scoring as if it were on a sheet.
- **They are offset rather than on the neighbouring sheet.** 13% to 49% of a wrong tile's nodes are within 2
  voxels of the published winding and 34% to 71% within 4. A tile on the neighbouring sheet, 12 to 13 voxels away,
  would have almost none within 4.
- **The right tiles spread wider.** Their median is 0.188, and 14 of the 53 also score below zero. So a line at
  zero keeps every right tile with a positive score and drops all the wrong ones, at the cost of a quarter of the
  right tiles.

## What this does to the campaign

By the registered consequence: **the next read of an eligible band may choose tiles by tile excess, registered
separately; whether to do so is the owner's decision, after finding 116.** The band would be PHerc. 0826's,
from finding 115's fit.

What I think it means, not registered:

- Finding 116's blindness is about how the turns join, which a tile read does not need. This finding says the
  same score works at the scale a tile read does need, on one scroll where it can be checked.
- On PHerc. 343 the fit's errors are offsets and gaps between sheets, which the score sees. Finding 116's worry
  was tiles on the wrong sheet that score as if they were right. None occurred here, on a fit that turns the right
  way. A wrong-handed fit must make such crossings, and where it makes them is still unknown.
- The snap moves every tile onto the published sheet here. Whether it does so on a crushed scroll is open.

## What it cost

10 seconds of CPU, 1.8 GB of memory. No GPU, no fit, no upload.

## What this does not show

1. **That it holds on a crushed scroll.** PHerc. 343 is round and well scanned; PHerc. 0211 and 0826 are not.
2. **That it holds on more than two windings.** 70 tiles, 17 of them wrong, all from one fit.
3. **That a tile right by the published winding is right.** The published winding is one author's surface.
4. **That the tiles are independent.** They are not; the floor is the slid labels for that reason, and its two
   nearest shifts show how much neighbouring tiles share.
5. Anything about ink.
