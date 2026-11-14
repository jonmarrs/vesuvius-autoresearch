# Pre-registration: on a correct surface of a scroll the ink models never saw, does the recipe's ink step show the labelled ink?

**Written 2026-11-13, before any ink model has been run here on a PHerc. 0841 render.** Finding 111.

PHerc. 0841 is not on the prize-eligible list (`prizeEligibility.json`, read 2026-11-10): the team has
published three of its segments with ink labels. Nothing here concerns a scroll that is still eligible.

## The question

The First Letters campaign in [the strategy](../RESEARCH_STRATEGY.md) reads unread scrolls with the PHerc. 343
recipe: render a surface, run four released 9 µm ink models, look for letters. Findings 110 and the kill test
showed the chain runs here on PHerc. 343, where the result was already known and the depth had been chosen by
its author. They do not say what the ink step shows on a scroll none of the models were trained on.

PHerc. 0841 is the strategy's second control, and it can answer that without any fit: the team's own surfaces
are published on the same 9.366 µm scan the recipe would use, with ink labels drawn on them. If the ink step
shows the labelled ink there, a null on an eligible scroll's surface means something. If it does not, a null
on an eligible scroll says nothing, and the campaign has to change the ink step before it spends fits.

This is the surface-given half of the control. The other half, fitting PHerc. 0841's windings here, is not
reachable from public inputs today: see Reachability.

## Reachability, checked before this was written

- **Inputs are public and on disk.** Three segments under `PHerc0841/segments/` in the open-data bucket, each
  with a mesh on the 9.366 µm scan (`…-on-20250821151531-9.366um.tifxyz`), a mesh on the 2.4 µm scan, the
  team's ink image and ink labels (`inklabels.zarr`, `supervision.zarr`, dated 20260918). The masked 9.366 µm CT
  streams from the same bucket. `repro/first_letters/pherc0841/fetch_segments.sh` fetches them (101 MB).
- **The labels can be carried onto our render.** The labels are drawn on the 2.4 µm mesh's grid. Carried into
  the 9.366 µm scan with the published transform and read at pixel centres, the 2.4 µm mesh lies on the
  9.366 µm mesh: median 0.01 voxels along the normal and 0.01 across it, 95th percentile 0.56 and 0.18, on
  each of the three segments (`surface_control.py instrument`, 33,935 to 35,610 nodes each). A plain resize of
  the labels therefore lines them up to well under one lattice cell.
- **The labels are scoreable.** At the label level nearest our render, the supervised area is 4.5% to 8.0% of
  each frame (0.93 to 1.52 million pixels), and 22% to 32% of it is labelled ink.
- **The labels can be matched by an ink map.** The team's own ink image (its 8× downsampled JPEG, resized)
  scores AUC 0.971, 0.921 and 0.869 against the labels inside the supervised area. That image comes from a
  model trained on this scroll's 2.4 µm scan, so it is a ceiling for reference and not a target.
- **The render runs.** The development segment's 66-layer render was made before this was written (13 min
  11 s with a cold CT cache, 72% of the frame with CT in all 66 layers); no ink model has read it. With the
  labels it gives 97,328 scored cells, 22,150 of them ink.
- **The models' training sets.** The ink_9um card lists PHerc. 0139, 1667, Paris 4 and 0814. The dense_native
  card describes pseudo-labels on native scans added to those checkpoints and names PHerc. 0139, 0814 and 1667
  segments. Hecate's card names Paris 4 and "other scrolls"
  without listing them, so for Hecate "never saw PHerc. 0841" is not verified.
- **Not reachable: the mesh half on PHerc. 0841.** Spiral tracks and the m7 surface prediction are published
  for it, but the lasagna normal and gradient volumes the recipe's fit requires are not (the bucket's
  `representations/predictions/` holds only `surfaces/`), and I found no published scroll axis. Of the 26 scrolls
  with published tracks, 14 have lasagna volumes, among them the eligible PHerc. 0125, 0191, 0211, 0257, 0268,
  0358, 0800, 0813 and 0826.

## The floor

- **Chance.** AUC 0.5.
- **A map that is ink-like but out of place.** The same ensemble slid by 512 render pixels in each of four
  directions, scored against the unmoved labels; the largest of the four is the floor `F`. It is measured in
  the run on each held-out segment, and P1 is written against it.
- **The other side** of the stack at the same depth is reported and is not part of the verdict: on PHerc. 343
  the blind side still correlated at 0.17 with the reading side.

One render and one set of deterministic or near-deterministic model runs per segment: no interval is claimed.

## Segments

| role | segment | grid on the 9.366 µm scan | work dirs under `R/work` |
|---|---|---|---|
| development | `20260220213127-w00` | 211 × 238 | `render/s20260220213127_66.zarr`, `maps/s20260220213127` |
| held out | `20260220214732-auto_grown_20260220144552896` | 232 × 236 | `render/s20260220214732_66.zarr`, `maps/s20260220214732` |
| held out | `20260221022814-auto_grown_20260220174252405` | 188 × 245 | `render/s20260221022814_66.zarr`, `maps/s20260221022814` |

`R` is `spiral_out/first_letters/pherc0841_control` under the workspace root. One renderer image
(`vc-render:sampler-75c79ac5f`), the kill test's four checkpoints and ink environment, the recipe's
`run_depth_sweep.sh` unchanged.

The held-out segments are different meshes, not different papyrus. 27% of the development segment's nodes lie
within 10 voxels of the first held-out segment and 2% within 10 voxels of the second; the second is the more
independent test. What is held out is the choice of depth and side.

## Procedure

1. `run_render.sh SEGMENT` for each segment: 66 layers, no flipped normals.
2. `run_ink.sh DEVELOPMENT -8 8`: four models, both sides, depths −8 to +8.
3. `run_sweep.sh`: on the development segment, the AUC of the ensemble at each of the 34 depth-and-side
   combinations. The highest is chosen (ties: the depth nearest zero, then the `_reverse` side).
4. `run_ink.sh HELD_OUT d d` for each held-out segment, at the chosen depth `d` only.
5. `run_confirm.sh`: the readings below on each held-out segment at the chosen depth and side, and the table.

**The score.** Each model's map is averaged over 4 × 4 render pixels. The ensemble is the mean of the four
models' z-scores over the cells where all 66 render layers have CT, with the broad background removed (as in
finding 110). Labels are resized to the render and averaged over the same cells. A cell is scored if at least
99% of it is supervised and it is either ink (labelled share at least 0.5) or bare (labelled share 0). The
reading is the area under the ROC curve of the ensemble against ink over the scored cells.

The measurements and the table are `repro/first_letters/pherc0841/surface_control.py`, committed with this
document and tested in `tests/test_first_letters_0841_surface_control.py`.

## Predictions, fixed now

- **P1, the ink step sees the ink.** On each held-out segment, an AUC of at least 0.60 and at least 0.05 above
  that segment's slid floor `F`.
- **P2, at letter level.** On each held-out segment, an AUC of at least 0.75.
- **What I expect: P1 holds and P2 fails** (`BLOB_LEVEL_SIGNAL`), with moderate confidence. Reasoning: the
  first-letters-survey, as the strategy summarises it, saw ink only at blob level on these surfaces; the ink_9um
  card warns that its models are sensitive to the depth window, which the sweep addresses; the team's own
  model reaches 0.87 to 0.97. No magnitude beyond the thresholds is predicted.
- **No prediction** for which depth or side the sweep picks.

The 0.75 line is a judgement of where letter strokes start to separate from background at this cell size; it
has not been calibrated against legibility, and the report will show the maps beside the labels.

## Decision rule

| outcome | verdict |
|---|---|
| a render or ink step of a held-out segment exits non-zero or never ran, or the sweep chose nothing | `DOES_NOT_RUN` |
| P1 and P2 hold on both held-out segments | `LETTER_LEVEL_SIGNAL` |
| P1 holds on both, P2 does not hold on both | `BLOB_LEVEL_SIGNAL` |
| P1 fails on either | `NO_SIGNAL` |

What each verdict does to the campaign:

- `LETTER_LEVEL_SIGNAL`: the ink step transfers to an unseen scroll when the depth is right. An eligible-scroll
  band is read with a depth sweep, and its null is evidence.
- `BLOB_LEVEL_SIGNAL`: a surface on an eligible scroll can show that ink is present, not what it says. The
  campaign's first eligible band goes ahead as a detection test, and a letter claim needs a better ink step.
- `NO_SIGNAL`: no fit is spent on an eligible scroll until the ink step shows labelled ink here.

## What the result cannot do

- It says nothing about the mesh half on PHerc. 0841, which was not run.
- The depth and side are chosen with labels. An unread scroll has none, so a positive here is an upper bound
  on what a blind sweep finds there.
- Labels cover 4.5% to 8% of each frame, where the team could see ink. The score says nothing about fainter ink.
- `NO_SIGNAL` would be a statement about these four checkpoints at 9.366 µm on this scan, not about the scroll.

## Limits

One scroll, three overlapping segments from one team, one label set, four checkpoints, one renderer build.

## Cost

Serial; the GPU steps need the training loop stopped (it is). On PHerc. 343 one depth of the four models on a
winding of similar size took about 6 minutes, so the 17-depth development sweep is projected at under 2 hours
and each held-out segment at minutes. Wall time and memory are recorded for every step. No training. No upload.
