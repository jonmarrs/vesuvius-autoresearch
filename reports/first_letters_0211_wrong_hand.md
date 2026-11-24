A fit declared to turn the wrong way reads the text where PHerc. 211's prize was won as well as the published direction does (2026-11-23)

Finding 137. Finding 119's fit of PHerc. 211's band (z 7650 to 9150) was run again with one change: the dataset
description declared the spiral clockwise (`CW`) against the catalog's anticlockwise (`ACW`). The four raw windings
of the new fit that reach the winner's surface most were snapped, flattened, rendered and read by Studio as finding
121's were. Finding 124's statistic then scored them on the winner's surface against Studio's map of it (arm wrong).
Finding 124's own windings and maps were scored the same way (arm right). Registered before any fit with the
direction reversed had run: `docs/preregistration/2026-11-22_first_letters_0211_wrong_hand_read.md` (commit
`e51b57e3`, amendment 1 at `dc232051`). Record: `reports/first_letters_0211_wrong_hand.json`, from the run's
`compare.json`, `choose.json`, gates, GPU trace and snap reports. Scripts as run: `run_wrong_hand.sh` and
`wrong_hand.py` in `repro/first_letters/pherc0211_control/`, and the `full-otherhand` arm of
`repro/first_letters/eligible_band/run_fit.sh`.

**Verdict `WRONG_HAND_READS_ALIKE`**, by the registered table; `WRONG_HAND_READS_PARTLY` was predicted, at low
confidence. Every step exited 0, and arm right gave finding 124's r 0.8247 again. Every render sampled along the
winner's normals. Arm right's renders were flipped, its median cosines −0.9962 to −0.9983. Arm wrong's were kept, at
+0.9972 to +0.9983, the flip a mirrored spiral gives. **So, as registered, a band read of PHerc. 0125 may be
registered with either direction declared.** Its pages would show the sheet crossings as breaks. The checks below
were written after the result and were not registered. They show that the declared direction did reverse the fit in
the scan. They also show the reversed windings paying for it by stepping across sheets: a net 1.78 to 1.89 sheets a
turn.

## The registered numbers

Each arm is scored on its own cells: the winner's mask cells, of 550,482, that its windings reach within 4 voxels
with finite maps.

| arm | windings | cells | cell share | r | wrong-side control | largest slid control |
|---|---|---|---|---|---|---|
| right (finding 121's) | w033, w034, w035, w036 | 457,405 | 0.8309 | 0.8247 | −0.0471 | 0.1141 |
| wrong | w035, w033, w036, w034 | 458,920 | 0.8337 | 0.841 | −0.0442 | 0.1049 |

| rule for `WRONG_HAND_READS_ALIKE` | needed | arm wrong |
|---|---|---|
| r at least the right arm's minus 0.05 | 0.7747 | 0.841 |
| cell share at least 0.8 of the right arm's | 0.6647 | 0.8337 |
| r at least twice the absolute value of each control | 0.2098 | 0.841 |

**Predictions.**
1. `WRONG_HAND_READS_PARTLY`, low confidence: not held. The result is `WRONG_HAND_READS_ALIKE`.
2. On the cells both arms reach, the two r values within 0.05 of each other, moderate confidence: held. On 437,732
   cells (share 0.7952), r is 0.8291 for arm right and 0.8451 for arm wrong, 0.016 apart.
3. The wrong arm's cell share between 0.40 and 0.75, low confidence: not held (0.8337).

The wrong arm's r is 0.0163 above the right arm's on its own cells. That is inside the registered margin. It is not
evidence that the wrong direction reads better: the reversed fit was run once, and how much a refit of this band
moves r is not measured (finding 131's 0.004 is the rerun noise of the steps after the fit).

## Described

**Cells.** Only the wrong arm reaches 0.0385 of the mask cells and only the right arm 0.0357. Transfer distances are
the same: medians 1.94 and 1.95 voxels, 95th percentiles 3.45 and 3.45. With the background left in, r is 0.7383
(right) and 0.7445 (wrong).

**Each winding**, on its arm's own cells:

| arm | winding | cells | r |
|---|---|---|---|
| right | w033 | 164,315 | 0.8737 |
| right | w034 | 95,215 | 0.7776 |
| right | w035 | 133,557 | 0.8238 |
| right | w036 | 64,318 | 0.7527 |
| wrong | w035 | 118,364 | 0.8232 |
| wrong | w033 | 137,695 | 0.8922 |
| wrong | w036 | 98,370 | 0.7823 |
| wrong | w034 | 104,491 | 0.8078 |

In both arms all four windings carry part of the winner's surface, and no winding carries more than 0.36 of the
arm's cells. The names match across the fits, but the windings are different surfaces (below).

**The choice.** The winner's lattice points within 4 voxels of each chosen raw winding: 188,049, 130,244, 83,396
and 67,189 for the reversed fit (the fifth, w037, 8,061), against 220,362, 152,314, 59,464 and 48,445 for finding
119's. Within 2 and 4 voxels of any raw winding: 0.2492 and 0.8089 of the winner's points, against 0.2616 and
0.8189.

**The snap.** The recipe's one-pass snap found both arms' windings as near the predicted surface:

| winding | median offset, right | median offset, wrong | already on the sheet, right | already on the sheet, wrong |
|---|---|---|---|---|
| w033 | 1.18 | 1.12 | 0.68 | 0.676 |
| w034 | 5.53 | 5.11 | 0.055 | 0.113 |
| w035 | 0.68 | 0.77 | 0.792 | 0.727 |
| w036 | 5.19 | 5.09 | 0.065 | 0.119 |

## Checked after the result (not registered)

A result better than predicted gets the hardest look. Two things could make it hollow. The declared direction
might not reverse the fit in the scan. Or the reversed fit might be the same surfaces under other names.
`repro/first_letters/pherc0211_control/wrong_hand_audit.py`, run on the two fits on disk, wrote `audit.json`; the
record keeps it under `audit_after_the_result`.

**The fit did turn the other way.** Villa's fitter mirrors its canonical spiral when the sense is `ACW`
(`transforms.py`: an x → −x flip, applied before the learned flow on the way from the spiral to the scan). Along
their columns, the four read windings of finding 119's fit turn −358.0 to −360.5 degrees around the umbilicus. The
reversed fit's turn +356.3 to +362.6 degrees.

**Its windings lie on the sheets the published fit found, and step across them.** Along 9 rows of each reversed
winding, 0.8932 to 0.9167 of its lattice points lie within 4 voxels of the published fit's raw windings w020 to
w050. Walking along a row, which is one turn, the nearest published winding changes. Leaving out the published fit's
own winding seam, the net change is 1.78 to 1.89 sheets a row. A mirrored spiral that sits on the sheets must cross
2 a turn. The steps are mostly single sheets: 39 to 91 steps outward per winding, offset by 24 to 81 inward, and only
1 to 12 steps of two or three sheets. Some of the single steps may be places where two published windings lie within
4 voxels of each other, not crossings. Nothing here separates the two, so only the net is read. So the reversed fit
did not cross in one narrow seam. Its windings follow the sheets and drift outward across them about twice a turn,
spread around the turn.

**Why the read did not suffer.** The registered read scores every winner cell that any of the four windings reaches.
In both arms the winner's sheet is reached by four windings in pieces (the table above). So a winding stepping off
the winner's sheet costs the read nothing as long as another winding is on it there. This is a reading of the
numbers above, not a separate measurement.

## What it means

- At this place, a local read does not depend on the fit's global winding direction. Reversing it moved r by
  +0.0163 and the cell share by +0.0028.
- A PHerc. 0125 band read may be registered with the direction declared either way, as the registration said. Each
  of its windings would wrap a sheet for only part of a turn before stepping to the next. So a page shows text in
  pieces, with breaks where the winding changes sheet, and reading a page as one sheet would be wrong. The windings
  still lie on sheets, so a letter's place on the scroll is where the page says. A 0125 read waits for the disk
  findings 133 and 138 need. Registering it is the next decision, after the owner's look at the three band pages.
- The band reads already made took the catalog's direction. Finding 116 showed the sheet-following score cannot
  tell the two directions apart. This result says a local read would have survived a wrong catalog direction, at
  least on a scroll like PHerc. 211.

## Limits

1. One place on one scroll: PHerc. 211, crushed, anticlockwise. PHerc. 0125's shape is not known.
2. One reversed fit. Refit-to-refit variation of r at this place is not measured.
3. "Reads" means agreement with Studio's map of the winner's surface on the cells within 4 voxels of it.
4. In the checks, the published fit stands in for the sheets, and it lies on the papyrus only in part (finding 119;
   median snap offsets 0.68 to 5.53 voxels above). "Within 4 voxels" there measures agreement between two fits.
5. Four windings, chosen by reach of the winner's surface; a band read reads every winding. Studio only.

## Cost

| step | time |
|---|---|
| check | 2 s |
| fit (30,000 steps) | 10,317 s |
| choose | 53 s |
| snap | 12 s |
| flatten | 179 s |
| orient | 1 s |
| render | 201 s |
| planes | 42 s |
| infer | 564 s |
| compare | 15 s |

3 h 9 min 46 s in all, against the registration's estimate of 3 h 22 min for the fit and about 40 minutes for the
rest. The fit peaked at 10,613 MiB of GPU memory and the run at 14,483 MiB (all processes). The checks above took a
few minutes on the CPU.
