# Pre-registration: does a fit declared to turn the wrong way still read the text where PHerc. 211's prize was won?

**Written 2026-11-22, before any fit of PHerc. 211 with the direction reversed has run.** Finding 137.

PHerc. 211's First Letters prize was awarded on 2026-11-15, so the place is a positive control and may be viewed.
Studio's weights and outputs are CC BY-NC 4.0 and stay on this machine.

## The question

PHerc. 0125 is eligible, its scroll axis is published and its inputs are on this machine, but its winding
direction is not known: the open-data catalog gives `z_direction_is_top_to_bottom` as null. Two attempts on
2026-11-22 to measure the direction from the surface prediction failed (scratch, not registered). The phase of
the sheet pattern around the axis did not close to ±1 sheet per turn. Traces of single sheets lost their sheet
after 10 to 80 degrees at the binary prediction's gaps.

Finding 116 showed that a fit of PHerc. 0826 declared to turn the wrong way scores like the right one on the
sheet-following score (median excess 0.099 against 0.103). Its windings sit on sheets locally; a spiral turning
the wrong way must cross two sheet spacings a turn somewhere. If those crossings stay narrow, a wrong-direction
fit might still read most of a 4 cm² area, and a band of PHerc. 0125 could be read without its direction.

So: at the place where the text is known, PHerc. 211's winner surface, does a fit of finding 119's band declared
clockwise put windings on the winner's sheet, and does Studio read the winner's text on them as it reads it on
finding 121's windings of the published (anticlockwise) fit? Finding 124 scored those at r 0.8247.

## Reachability, checked before this was written

- **The fit differs from finding 119's in the direction alone.** `run_fit.sh` gains the arm `full-otherhand`:
  `full` with a copy of the dataset description whose `spiral_outward_sense` is the other way, as finding 116's
  `outerN-otherhand` arms. `outer130-otherhand` would not do: `outer130` sets villa's gap expander to 133, and
  villa's default, which finding 119's `full` fit used, is 130 (`config.py`). Finding 119's band (z 7650 to 9150),
  its distance field, tracks and axis are on disk.
- **The windings are chosen by a rule that gives finding 121's.** `wrong_hand.py choose` counts, for every raw
  winding, the winner's lattice points in the band (539,518) within 4 voxels of the winding's own lattice
  points (finding 110's transfer distance), and reads the four with the most. On finding 119's fit it gives
  w035, w033, w036 and w034 (220,362, 152,314, 59,464 and 48,445 points; the fifth, w037, has 6,231). That is
  finding 121's set. Villa's `wNNN_spliced` copies are not counted.
- **The comparison gives finding 124's numbers.** `wrong_hand.py compare` scores each arm on its own cells
  with finding 124's statistic (`studio_e2e.score`, via finding 131's carry). Dry run with stand-ins: arm right
  = finding 124's windings and maps gives r 0.8247, controls −0.0471 and 0.1141, cell share 0.8309, exactly
  finding 124's. Arm wrong = finding 131's rerun of the same geometry gives r 0.8205, share 0.8312:
  `WRONG_HAND_READS_ALIKE`, as a rerun should.

## Procedure

`repro/first_letters/pherc0211_control/run_wrong_hand.sh`, once, each step only if the one before exited 0:

1. **check:** finding 123's Studio weights and the winner's `inference.py` against their SHA-256 values.
2. **fit:** `run_fit.sh full-otherhand`: 30,000 steps, the recipe's overrides, villa's defaults otherwise.
3. **choose:** the rule above, on the new fit's raw windings.
4. **snap, flatten:** the recipe's snap (one pass) and lasagna, as finding 121.
5. **orient:** `end_to_end.py orient`: each render flipped or kept from its normals against the winner's.
6. **render:** 66 layers per winding, as orient says.
7. **planes, infer:** our layers 41 down to 26, and the same reversed (the other-side control); the winner's
   `inference.py` with the winner's command (`--stride 64 --blend hann`).
8. **compare:** arm right (finding 124's own windings and maps) against arm wrong (these windings).

## The registered numbers and the verdict

Each arm is scored on its own cells: the winner's mask cells that its windings reach within 4 voxels, with finite
maps (finding 124's cells). The right arm must give r 0.8247 again; if not, `DOES_NOT_RUN`. Every render must
sample along the winner's normals; if not, `DOES_NOT_RUN`.

| verdict | the wrong arm |
|---|---|
| `WRONG_HAND_READS_ALIKE` | r at least the right arm's minus 0.05 (0.7747), cell share at least 0.8 of the right arm's (0.6647), r at least twice the absolute value of each control |
| `WRONG_HAND_READS_PARTLY` | otherwise: r at least 0.40, cell share at least 0.25, r at least twice each control |
| `WRONG_HAND_DOES_NOT_READ` | otherwise |
| `DOES_NOT_RUN` | a step fails, finding 124's r does not come out again, or a render samples against the winner |

The margin of 0.05 is above the rerun noise finding 131 measured (0.004 here) and about what two layers of depth
change (finding 135: at most 0.041 over ±2 layers).

Described: both arms on their common cells; the share of the winner's cells only the wrong arm reaches; each
winding's cells and r; transfer distances; and the choice record's union coverage (winner lattice points within
2 and 4 voxels of any raw winding: 0.2616 and 0.8189 for finding 119's fit).

## Predictions

1. `WRONG_HAND_READS_PARTLY`, low confidence. Along its middle row the winner's crop is 5,832 voxels long and spans
   550 degrees around the axis (median radius 487 voxels), so a wrong-direction spiral must cross sheets inside it.
2. On the cells both arms reach, the two r values within 0.05 of each other, moderate confidence: where a
   winding sits on the winner's sheet, the read should not care how the fit got there.
3. The wrong arm's cell share between 0.40 and 0.75, low confidence.

## What each verdict does

- **`WRONG_HAND_READS_ALIKE`:** a band read of PHerc. 0125 may be registered with either direction declared. Its
  pages would show the sheet crossings as breaks.
- **`WRONG_HAND_READS_PARTLY`:** a 0125 read would lose part of each turn. Register it only after PHerc. 0813 and
  0800 are read, and say how much is lost.
- **`WRONG_HAND_DOES_NOT_READ`:** PHerc. 0125 waits for a measured direction.
- In every case the result also says how far a local read depends on the fit's global winding being right, which
  bears on every band read.

## Limits

1. One place on one scroll: PHerc. 211, crushed, anticlockwise. PHerc. 0125's shape and direction are unknown.
2. "Reads" means agreement with Studio's map of the winner's surface on the cells within 4 voxels of it. A
   winding on a neighbouring sheet may carry legible text that this does not count.
3. Four windings, chosen by reach. A band read reads every winding.
4. Studio only.

## Cost and when it runs

The fit took 3 h 22 min for finding 116's band (12,104 s, 13.8 GB of GPU memory). Snap, flatten, render and
Studio for four windings take about 40 minutes, and the renders about 6 GB of disk. It runs after findings 129
and 133, which hold the GPU now.

## Amendment 1 (2026-11-22, before any reversed fit has run)

A wrong-direction fit that barely reaches the winner's surface is a result the table names
(`WRONG_HAND_DOES_NOT_READ`: cell share under 0.25), but the registered code would have stopped on it with
`DOES_NOT_RUN`. `choose` failed when no raw winding came within 4 voxels. `compare` took percentiles of an empty
array and scored empty cells. Now:

- `choose` writes an empty list when no winding reaches the surface, and the chain records
  `WRONG_HAND_DOES_NOT_READ` with cell share 0 (`wrong_hand.py unreached`) instead of going on to snap nothing.
- An arm with fewer than 1,000 cells (finding 121's minimum for scoring one winding) gets its cell share and no r.
  The table already reads that as `WRONG_HAND_DOES_NOT_READ`. Its described numbers that need cells are left empty.

Nothing else changes: the dry runs give the same numbers (right arm r 0.8247, share 0.8309; the stand-in wrong arm
r 0.8205, share 0.8312, `WRONG_HAND_READS_ALIKE`; `choose` on finding 119's fit gives w035, w033, w036, w034).
