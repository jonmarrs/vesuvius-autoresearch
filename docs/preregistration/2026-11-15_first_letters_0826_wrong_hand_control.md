# Pre-registration: does the sheet-following score fail a spiral fitted with the wrong winding direction?

**Written 2026-11-15, before any fit of PHerc. 0826 with the direction reversed has run here.** Finding 116.

PHerc. 0826 is on the prize-eligible list. Everything this step makes from it stays on this machine under
`spiral_out/first_letters/pherc0826_band`. The report will carry summary numbers about the fit and no mesh,
render or ink map.

## The question

Findings 112, 114 and 115 decided which fits may be read for ink by one number: the median, over a fit's
windings, of the share of nodes inside a predicted sheet minus that share 6 voxels along the normal. Each
report lists the same first limit: a winding can sit on predicted sheets and still switch sheets along its
length. Nothing so far has measured how far that limit reaches. A control exists that can. A spiral declared to
turn the wrong way cannot follow a sheet round the scroll: against the real sheets each of its windings drifts
two sheet spacings a turn, so it must cross sheets or jump between them. If such a fit scores like the right
one, the score reads "near a sheet here" and says nothing about following one, and three verdicts mean less
than their names. If it scores near the floor, the score has passed a control it could have failed.

It also decides something practical. PHerc. 0125 is the third eligible scroll with a published scroll axis, and
its winding direction is not published. If the score separates the two directions, it can be found by fitting
both.

## Reachability, checked before this was written

- **The right-direction fit exists.** Finding 115: PHerc. 0826, z 10250 to 11750, 80 windings, anticlockwise as
  published, 30,000 steps: median excess 0.103, 78.6% of 70 windings positive, floor 0.000.
- **The direction is one field.** `spiral_outward_sense` in the dataset description; `run_sense.sh` changed it
  on PHerc. 343 on November 13 and villa ran. `run_fit.sh` gains the arms `outerN-otherhand` and
  `outerN-otherhand-smoke`, which fit a copy of the description that differs in that field alone.
- **A short fit does not tell the directions apart.** On PHerc. 343 the track term at step 800 was 440.6 declared
  clockwise and 438.8 declared anticlockwise. That is expected: over a track a tenth of a radian long the two
  hands differ by under half a voxel.
- **The tracks do not give the direction directly.** Scratch work today, on the three scrolls where the
  direction is published: the change of radius with angle along 126,000 to 298,000 in-slice tracks a scroll,
  averaged over 72 angle bins, came out at −169, −287 and +348 voxels a turn, against a true 12 to 14, and
  changed sign between sixths of the band on all three. The scrolls are too far from round for it.
- **Only three eligible scrolls have a published axis** (catalog `metadata.json`, read today): PHerc. 0125, 0211
  and 0826. Six more have every other input and a published direction (PHerc. 0191, 0257, 0268, 0358, 0800,
  0813) and no axis.
- **Not checked:** whether the `otherhand` arm runs. The smoke fit is its test.

## Procedure

Scripts in `repro/first_letters/eligible_band/`, `FL_SCROLL=PHerc0826`. Inputs, dataset and distance field are
finding 114's. Each step once, in its own unit, the training loop stopped.

1. `run_fit.sh outer80-otherhand-smoke 300`, then `run_quality.sh outer80-otherhand-smoke`.
2. `run_fit.sh outer80-otherhand`: 30,000 steps, everything but the declared direction as in finding 115.
3. `run_quality.sh outer80-otherhand`, then `band_fit_verdict.py RUN_DIR OUT outer80-otherhand-smoke
   outer80-otherhand` for the summary numbers.
4. `run_spacing.sh outer80-otherhand`.

## Predictions, fixed now

`E` is the wrong-direction fit's median excess over the windings it writes. The right-direction value is 0.103.

- **What I expect: `E` between 0.03 and 0.07** (`SCORE_PARTLY_SEPARATES`), with low confidence. The fit's
  losses on the normals and the distance field act locally and do not know the direction, so I expect windings
  that lie on sheets over most of each turn and cross between them over the rest. I do not expect the floor.
- **The losses.** I expect the track term at step 29,800 to be higher than the right direction's 171.1, by less
  than 25%.

## Decision rule

| outcome | verdict |
|---|---|
| a step exits non-zero, or fewer than 60 windings are scored | `DOES_NOT_RUN` |
| `E` is at most 0.03 | `SCORE_SEPARATES` |
| `E` is above 0.03 and below 0.07 | `SCORE_PARTLY_SEPARATES` |
| `E` is at least 0.07 | `SCORE_BLIND_TO_DIRECTION` |

The lines are P2's and P1's medians, so the verdict says which of finding 112's verdicts a wrong-handed spiral
could have earned on its median.

What each does to the campaign:

- `SCORE_SEPARATES`: the score would have rejected a wrong-handed spiral. The verdicts of findings 112, 114 and
  115 stand as read. PHerc. 0125's direction is found by fitting its band both ways, registered separately, and
  it becomes the third scroll.
- `SCORE_PARTLY_SEPARATES`: a wrong-handed spiral would earn `PARTLY_ON_SHEETS` or less on its median. The
  score carries information about direction and cannot be the only gate. The report gives the gap between the
  two fits against the spread across windings, and says whether two fits of PHerc. 0125 could be told apart.
- `SCORE_BLIND_TO_DIRECTION`: the score does not measure following a sheet. `ON_SHEETS` and `PARTLY_ON_SHEETS`
  in findings 112 and 115 then mean "near predicted sheets locally" and the strategy says so. No further band
  is read for ink on the score alone; the next step is a second instrument, registered separately. Finding
  113's read is not withdrawn: its strips are already with the reader, and what it can show is unchanged, but
  its report says the windings may switch sheets more than assumed.

## Descriptions that are not part of the verdict

- The share of windings with positive excess, the registered thirds and the spacing ratio, as in finding 115.
- The loss terms at step 29,800 beside finding 115's.

## What the result cannot do

- **It does not show the right-direction windings are single sheets.** A wrong-handed spiral must switch
  sheets twice a turn; a right-handed one may switch far less often and score the same as one that never does.
  `SCORE_SEPARATES` bounds the score's blindness at that rate and no further.
- It compares two single fits, one seed each.
- It is one scroll and one band. PHerc. 0826 is crushed; on a round scroll the result may differ.
- It says nothing about ink.

## Limits

One scroll, one band, one seed, 80 windings. The two lines were set for another purpose and are reused here.

## Cost

About 3 h 30 min of GPU and 25 minutes of CPU, on finding 115's timings. No training of any model. No upload.
