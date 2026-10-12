# Pre-registration: is the fiber mask's failure on two new Scroll-5 cubes a frame offset, a threshold, or a real miss?

**Written 2026-10-11, before any shift or threshold outcome was computed on any cube.** Analysis
`scripts/fiber_miss_diagnostic.py`, tested on synthetic volumes in `tests/test_fiber_miss_diagnostic.py`, committed
with this file on branch `s5-heldout-diagnostic`.

## The question

Finding 83: on two Scroll-5 cubes from villa's Dataset004 that `fiber_hz_vt` never trained on
(`s5_13497_01497_02497_256`, `s5_16997_03997_04497_256`), connected-components coverage, which is the reference mask's
recall of the hand-traced fibers, is 0.64 and 0.53. On the in-sample Scroll-5 256³ cubes it is 0.82–0.91. The report
named three candidate causes (region, content, annotators) and said two cubes cannot separate them. ScrollGT 0.6.0, not
yet merged, ships both cubes as `held_out` targets and says the mask fails there.

Two cheaper explanations were not ruled out, and either would change what ScrollGT should say:
* **A frame offset between the annotation and the CT.** The mask fires on more of these cubes than on any in-sample
  Scroll-5 256³ cube (density 0.068 and 0.067, against 0.037–0.049), yet covers less of the ground truth, and the
  nodes' enrichment on the mask halves. Finding 83's frame gate (enrichment > 5×) rules out an axis swap, not an offset
  of a few voxels. Its other gate (nodes on villa's semantic label) cannot test this, because villa's label is drawn
  from the same skeleton. If this is the cause, the two targets are mis-built and "the mask fails" is wrong.
* **A calibration shift.** If the missed fiber sits just under P = 0.5, an entrant recovers it with a lower threshold.
  The mask would then be shifted, not blind.

If neither holds, the miss is real (the model does not fire where the annotators traced), and finding 83's three
candidates stand.

## Reachability and instrument gates, checked before this registration

Only gate quantities were computed, never a shifted coverage or a sub-0.5 threshold:
* **G1 holds on all 17 targets present** (the other 4 Scroll-3 targets are still being built for ScrollGT 0.6.0).
  P ≥ 0.5 from the cached `fiber_hz_vt` probability equals the shipped `mask.npz` bit for bit. The cache is
  `local_data/fiber_skeletons/` for in-sample cubes and `spiral_out/fiber_heldout/data/` for held-out ones.
* **G2 holds on one cube**: zero-shift coverage on `s1_00497_01497_03997_256` is 0.91771, against the published
  0.9177. It takes 6 s, including the distance transform.
* The script's coverage equals ScrollGT's `score_tracing` coverage exactly on synthetic scenes, including skeletons that
  leave the volume (tests).

## Method

On all 21 ScrollGT fiber targets, against the shipped current annotations (`load_fiber_target`, the scored-fiber
filter), at tolerance 2.0 and resampling step 0.5 (fiber scoring version 2):

* **Coverage**: ScrollGT's definition. It is the length-weighted fraction of in-bounds resampled ground-truth points
  whose rounded voxel lies within 2 voxels (Euclidean) of the mask.
* **Frame check**: coverage of P ≥ 0.5 with the skeleton shifted by every integer offset in [−4, 4]³ (729 shifts).
  Points shifted out of the volume are dropped, so the in-bounds set changes slightly at the edges. Record
  `gain` = best minus zero-shift coverage, the best shift (ties go to the smallest shift), and the single-axis
  profiles.
* **Threshold sweep**: for each in-bounds point, the maximum probability over the 33 voxels within 2 voxels of it
  (the ball-max). Coverage at threshold t is the length fraction with ball-max ≥ t, for t ∈ {0.5, 0.3, 0.2, 0.1, 0.05},
  together with the mask density at each t. The **soft-miss fraction** is (C(0.1) − C(0.5)) / (1 − C(0.5)): of the
  length missed at 0.5, the share that has P ≥ 0.1 nearby.
* **Gates, all 21 cubes:**
  * G1: P ≥ 0.5 equals the shipped mask.
  * G2: both the zero-shift coverage and the ball-max coverage at 0.5 are within 1e-4 of the published
    connected-components coverage (which is rounded to 4 decimals).
* **Control:** every in-sample cube's shift `gain` must be below 0.05. In-sample frames are trusted: the mask trained on
  these annotations.

## Predictions, fixed now

* **P1 (frame offset): withheld.** The reasoning goes both ways. Both cubes come out of the same villa pipeline as the
  in-sample ones. Against that, the mask fires more on these cubes yet covers less, and the nodes' enrichment halves.
  A frame offset produces exactly that pattern. The decision rule below covers both outcomes.
* **P2: a lower threshold does not rescue them.** On both cubes C(0.1) < 0.8185, the lowest in-sample Scroll-5 256³
  coverage at 0.5. Reasoning: nnU-Net probabilities are near-binary away from boundaries, and losing 0.27–0.36 of the
  length is too much to sit in a calibration band.
* **P3: their misses are no softer than in sample.** Each cube's soft-miss fraction is at most the largest of the six
  in-sample Scroll-5 cubes'. Same reasoning, lower confidence.

## Decision rule

| outcome | conclusion |
|---|---|
| G1 or G2 fails on any cube | `INSTRUMENT_FAILED`: no verdict; find the discrepancy first |
| any in-sample cube has gain ≥ 0.05 | `CONTROL_FAILED`: the shift instrument flags trusted frames, so a held-out flag means nothing; report the profiles only |
| gain ≥ 0.05 on both new cubes, and the best-shift coverage reaches 0.8185 on both | `FRAME_OFFSET_EXPLAINS`: the targets are mis-registered. ScrollGT 0.6.0 must not ship them as a mask failure. Hold the PR, report to the user, and re-check the offset against the CT before any fix |
| gain ≥ 0.05 on one or both, without full recovery | `FRAME_OFFSET_PARTIAL`: the offset is part of the drop. Same hold, with the residual drop stated |
| no frame flag, and P2 fails (C(0.1) ≥ 0.8185 on both) | `THRESHOLD_RESCUES`: a calibration shift. ScrollGT says so, with the density cost |
| no frame flag, P2 holds, P3 fails | `SOFTER_BUT_NOT_RESCUED`: partly calibration, mostly a miss |
| no frame flag, P2 and P3 hold | `HARD_MISS`: the mask does not fire where the annotators traced. Finding 83's three candidates stand, and 0.6.0's wording is right |

The verdict comes from `verdict()` in the script. It refuses a sample missing any of the 8 Scroll-5 cubes, and it emits
no conclusion when a gate or the control fails (tests).

## What the result cannot do

* It cannot choose between region, content and annotators. A `HARD_MISS` leaves all three standing.
* A frame flag does not say who is right about the frame. It says the skeleton and the mask disagree by a rigid offset
  the in-sample cubes do not show. Confirming a mis-registration needs a check against the CT, not the mask.
* The soft-miss fraction depends on the 0.1 cutoff. The full sweep is recorded so a reader can pick another cutoff.

## Limits

* Two cubes are tested; the eight Scroll-3 cubes and eleven in-sample cubes are descriptive or controls.
* The search covers rigid integer offsets only. A rotation, a scale error or a sub-voxel offset would not show as a
  clean peak.
* One model and one threshold family.

## Cost

CPU only, no new model or tracer run. About 1 to 2 minutes per 512³ cube (a distance transform and 729 shift lookups)
and seconds per 256³ cube: under 30 minutes for all 21. It runs after ScrollGT's last four held-out targets are built,
because it reads the shipped targets.
