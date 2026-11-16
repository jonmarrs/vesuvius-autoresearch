# Pre-registration: with the winding count set to what the band holds, does the fit of PHerc. 0826 follow sheets?

**Written 2026-11-14, before any fit of PHerc. 0826 with a changed winding count has run here.** Finding 115.

PHerc. 0826 is on the prize-eligible list. Everything this step makes from it stays on this machine under
`spiral_out/first_letters/pherc0826_band`. The report will carry summary numbers about the fit and no mesh,
render or ink map.

## The question

Finding 114 fitted PHerc. 0826's band with villa's defaults and got `NOT_ON_SHEETS`: the fit wrote windings out
to the 130th, the papyrus in the band ends near the 80th, and the 50 windings past it are 37 to 127 voxels from
any predicted sheet. Its registered consequence is one named change to the fit, registered separately. This is
that change: **villa's outer winding set to 80 in place of 130.** Two questions follow. Does the fit, scored
over the windings it was asked for, now pass the test PHerc. 0211 passed? And did the 50 windings in the air
hurt the 70 on papyrus, or not?

## Reachability, checked before this was written

- **The setting exists and bounds what the fit integrates over.** In villa `0fb38c45`,
  `shell_outer_winding_idx` (default 130) is the winding bound of every sampler that integrates over the spiral:
  the dense lasagna losses, the distortion regulariser and the spacing terms. The step that writes the windings
  stops at it. villa asks for `model_gap_expander_num_windings` to be at least 3 more, and warns when it is not
  (it is not at the defaults: 130 and 130). `run_fit.sh outer80` sets 80 and 83.
- **villa can infer the outer winding itself, but not in this recipe.** The inference reads verified patches and
  point strips, which the recipe's override `input_disable_patches` turns off.
- **Why 80.** Finding 114's table, in groups of ten: w070 to w079 is the last group with windings on sheets
  (median excess 0.107, 23% of nodes inside a sheet), and w080 to w089 has 4% of nodes inside a sheet. The count
  is fixed here, from the earlier fit, before the new one runs.
- **The baseline.** In finding 114's fit, the 70 windings w010 to w079 have a median excess of 0.0825, 75.7% of
  them positive and 40 at 0.07 or above. Scored alone they would be `PARTLY_ON_SHEETS`: they miss P1 on the
  share positive.
- **An estimate from the inputs alone does not give the count.** I counted the predicted sheets crossed by rays
  from the scroll axis in the distance field (1,080 rays a scroll). The medians are 103 on PHerc. 343, 71 on
  PHerc. 0211 and 46 on PHerc. 0826, against fit edges near 120 and 80 on the last two: the rays miss about four
  sheets in ten, by a similar factor on both (1.69 and 1.74). Two points do not make a rule, so the count here
  comes from the fit.
- **Not checked:** whether the `outer80` arm runs. The smoke fit is its test.

## Procedure

Scripts in `repro/first_letters/eligible_band/`, `FL_SCROLL=PHerc0826`. The inputs, dataset and distance field
are finding 114's. Each step once, in its own unit, the training loop stopped.

1. `run_fit.sh outer80-smoke 300`, then `run_quality.sh outer80-smoke`: the floor.
2. `run_fit.sh outer80`: 30,000 steps; everything but the two winding settings as in finding 114.
3. `run_quality.sh outer80`, then `band_fit_verdict.py RUN_DIR OUT outer80-smoke outer80`.
4. `run_spacing.sh outer80`.

## Predictions, fixed now

The lines are finding 112's, taken over every winding the fit writes.

- **P1.** A median excess of at least 0.07 and at least 80% of windings with positive excess.
- **P2.** A median excess of at least 0.03 and at least 65% of windings with positive excess.
- **P3, the windings in the air hurt.** The median excess is at least 0.0925, which is 0.01 above the baseline
  of the same windings in finding 114's fit.
- **What I expect: P2 holds, P1 fails on the share positive, P3 fails** (`PARTLY_ON_SHEETS`, and no gain from the
  change), with low confidence. The baseline is already `PARTLY`, the innermost ten windings scored 0.001 in
  finding 114, and I have no evidence that the outer windings pulled on the inner ones. My last two predictions
  of this score were both wrong, in opposite directions.

## Decision rule

| outcome | verdict |
|---|---|
| a step exits non-zero, or fewer than 60 windings are scored | `DOES_NOT_RUN` |
| the smoke fit's median excess is above 0.03 | `INSTRUMENT_FAILS` |
| P1 holds | `ON_SHEETS` |
| P1 fails and P2 holds | `PARTLY_ON_SHEETS` |
| P2 fails | `NOT_ON_SHEETS` |

P3 is reported beside the verdict as `HELPS` or `NO_GAIN`.

What each does to the campaign:

- `ON_SHEETS` or `PARTLY_ON_SHEETS`: PHerc. 0826's band has a fit that can be read for ink, among its windings
  at 0.07 or above, once finding 113 has shown whether the reading protocol works.
- `HELPS`: the winding count matters to the windings on papyrus, and PHerc. 0211's band (edge near its 120th
  winding) is worth refitting at 120 before more of it is read. `NO_GAIN`: it does not, and the cheaper course
  on any scroll is to fit with the default and discard the windings past the edge.
- `NOT_ON_SHEETS`: the change made the fit worse; finding 114's fit stands as the better one and the report says
  so.
- Either way the default overrunning a small scroll is a defect worth describing to villa; whether and how is
  the owner's decision.

## What the result cannot do

- It does not show the windings are the right sheets: the distance field is the surface prediction the fit was
  given.
- It compares two single fits. A difference of 0.01 may be within what a second seed would give; no fit here
  has been repeated.
- It says nothing about ink.

## Limits

One scroll, one band, one seed, one count. The count came from a fit of the same band.

## Cost

About 3 h 25 min of GPU for the two fits and 25 minutes of CPU for the scores, on finding 114's timings. No
training of any model. No upload.
