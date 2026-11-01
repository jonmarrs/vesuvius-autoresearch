# Pre-registration: when villa's neural tracer stops on low confidence, does the hand-traced fiber go on?

**Written 2026-11-01, before any stop was compared with the ground truth.** CPU only, on runs already made: no new
tracing, no GPU, no download. The script is `scripts/neural_tracer_confidence_stops.py`, committed with this file.
**Pushed at 06:57 PST (d2e912a7); run 07:04–07:45 PST: finding 101, `reports/neural_tracer_confidence_stops.md`. The
gate passed on all 21 cubes. P1 and P2 held, P3 missed (median G 0.083): the rule closes the line.**

## The question

The [research strategy](../RESEARCH_STRATEGY.md) ranks conservative fiber tracing second and names "premature
confidence stops" as a failure mode to investigate, with a bar: a candidate needs at least a 10% useful-continuity
gain to justify a larger registered test. In findings 97 and 98, villa's neural tracer
(`scrollprize/fiber_single_small@451182558c`) ended a median 24% of its traced ends on low confidence, 2.8–60.6% by
cube (`stop_confidence` over all stops in each run's `tiles.jsonl`). If those stops fall where the hand-traced fiber goes on, a stop rule that continues
further might extend reach. If they fall where the fiber ends, or if the fiber past them is already covered by other
traces, no confidence-stop fix can clear the bar, and the line closes before any GPU time is spent on it.

A second question rides along: how often does a trace **leave** the fiber before it stops? That is the failure open
villa PR [#2377](https://github.com/ScrollPrize/villa/pull/2377) addresses for villa's C++ beam tracer, a different
tracer. Villa's [open problems](https://scrollprize.org/2026_open_problems) page prefers a tracer that "confidently
follows fewer fibers correctly" over one that follows more with a higher error rate.

## Reachability, checked before this was written

From the tracer's own outputs only (no ground truth read), on findings 97's and 98's 21 runs:

* every run's `.afv` fiber ids equal its fiber JSONs' ids, and each fiber's first and last `.afv` points lie within
  2.0 voxels of its JSON `line_points`' (the JSON is resampled at the trace grid's spacing), so the JSON
  `stop_reasons` and `links` attach to the `.afv` polylines that ScrollGT scored, in the same orientation;
* villa's `_write` (tracers/fibers/tracing/volume.py at `ccb431818`) builds a fiber as the backward half reversed, then
  the forward half, and stores the reasons as (backward, forward), so `stop_reasons[0]` belongs to the first point;
* it also cuts each trace to the box (the cube) and trims overlaps with written fibers, and every piece keeps its
  trace's two reasons. A piece's end is therefore where the trace stopped only if it is inside the cube, away from
  its faces, and touches no written fiber (`links` = −1). On the ten held-out cubes, 7,191 ends with reason
  `confidence` and 4,964 with `owned_or_live` meet that test (6 voxels from every face). `bounds` ends lie on a face;
  none is interior.

## Data

* **Runs:** finding 97 (`spiral_out/neural_tracer/ct_context_run/neural`, the ten 256³ cubes) and finding 98
  (`ct_context_512_run/neural`, the eleven 512³ cubes): villa `ccb431818`, the cube's CT padded by 128 voxels.
  Finding 91 found the tracer deterministic (two cubes traced twice, identical). A re-run at villa `39a8cf3a1`
  reproduced two of these runs exactly, the held-out Scroll-5 256³ cubes
  (`reports/evidence/villa_volume_seed_heading_rerun_39a8cf3a.json`). Villa
  [#2359](https://github.com/ScrollPrize/villa/pull/2359), merged 2026-10-29, moved the volume tracer's policy into a
  new module; its output on these cubes has not been checked. The result describes the tracer at `ccb431818`.
* **Ground truth:** ScrollGT's fiber targets, hand-traced in WEBKNOSSOS at 7.91 µm, from the sibling checkout that
  scored findings 97 and 98 (scoring version 3); each skeleton's sha256 is recorded. The tracer never saw Scrolls 3
  or 5. Scroll 1 is its training scroll, in another frame.
* **Sets:** the **ten held-out cubes** (eight Scroll-3 512³ and two Scroll-5 256³: held out from the presence model,
  the tracer and the generator) decide. The eleven in-sample cubes are reported apart and decide nothing.

## Definitions, fixed now

* **Frame:** `.afv` points in padded-CT XYZ, minus 128, as ZYX in the cube (`afv_to_labels.to_cube_zyx`).
* **Labels:** the run's `.afv` rasterized as finding 91 did (`labels_in_cube`), grown by ScrollGT's own nearest-label
  growth (`_dilate_labels`) at tolerance τ. A fiber's label is 1 plus the rank of its id.
* **A stop:** a fiber end with `links` = −1 lying at least EDGE = 6 voxels from every face. Its direction is the unit
  vector from the fiber's point 8 voxels of arclength back to the end.
* **On the fiber:** the stop lies within τ of a ground-truth sample (each edge resampled as ScrollGT's
  `_resample_fiber`, every ≤ 0.5 voxel, inside the cube). The nearest sample is its match.
* **The walk:** from the match along the matched ground-truth fiber, in the direction whose edge agrees with the stop's
  direction (positive dot product); at a branch (238 of the reference's 464,216 nodes), the edge best aligned with the
  current direction. The walk ends at a fiber end, where it leaves the cube, or at 400 voxels.
* **Classes of an on-fiber stop:** `continues` if the walk covers at least L = 20 voxels; otherwise `fiber_ends` if it
  reached a fiber end, `censored` if it left the cube. **Premature share** = continues / (continues + fiber_ends).
* **Base rate (the control):** 2,000 ground-truth samples per cube drawn at random (seed 0) among those the run covers
  (grown label ≠ 0), each walked in a random direction by the same rules. Its continues share is what a stop placed
  without regard to where fibers end would show.
* **The gap past a stop:** along the walk, the samples labelled 0 (no trace within τ), counted until the first sample
  labelled with another fiber; samples labelled with the stopping fiber itself are skipped. A stop whose gap ends at
  another fiber's label is a **split**: another trace already follows the fiber on.
* **G**, per cube: the union, over the `confidence` stops classed `continues`, of their gap samples' lengths (each
  sample once), over the length the run covers (ScrollGT's coverage × ground-truth length). G is the most that
  perfect continuation along the right fiber at those stops could add to coverage, as a fraction of what is covered.
* **Left the fiber before stopping:** a stop more than τ from every ground-truth sample whose fiber point 20 voxels
  of arclength back lies within τ of one. Reported per reason, as a share of that reason's stops.

## Identity gate, checked before anything else is read

On every cube: ScrollGT's `score_tracing` on the run's labels at τ = 2 reproduces finding 97's or 98's recorded row
exactly (coverage, precision, splits, merges, ground-truth and predicted length); the `.afv` and JSON ids match; every
fiber's ends agree within 2.5 voxels. If any check fails, the script writes no verdict.

## Predictions, recorded so each can be a miss

On the ten held-out cubes, at τ = 2, L = 20, EDGE = 6:

1. **P1 (moderate):** the median cube's premature share is at least 0.5. The tracer was trained on Scroll 1 only, and
   the reference's fibers are long against 20 voxels (149–244 voxels of length per fiber on the 256³ cubes, 280–470
   on the 512³).
2. **P2 (low):** on at least 8 of the 10 cubes, the premature share is at least 0.8 × the cube's base rate, so a
   confidence stop says little about where the fiber ends.
3. **P3 (low), the decision:** the median G is at least 0.10.

No prediction for the share of stops that left the fiber first; it is reported, not judged.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| The identity gate fails on any cube | No verdict. The instrument, not the tracer, is what the data speak to. |
| Fewer than the ten held-out cubes scored, or one with no classified on-fiber confidence stop (its share undefined) | No verdict (partial). |
| Median G < 0.10 | Even perfect continuation at the tracer's confidence stops would add under 10% to the median held-out cube's coverage. **Close the premature-confidence-stop line** for this tracer, checkpoint and settings; spend no GPU time on it. |
| Median G ≥ 0.10 and P1 holds | The line stays open. The next step is a development-pilot proposal (a continuation rule, judged by wrong connections as well as reach), which needs the owner's GPU decision. |
| Median G ≥ 0.10 but P1 fails | The gap is real but most on-fiber confidence stops sit where the fiber ends: the mechanism behind this line is wrong. Report it and propose nothing until the gap is explained. |

## What the result cannot do

* **G is a ceiling, not a forecast.** It assumes a fix that continues along the right fiber and stops at the next
  trace. A real rule would follow some stops onto a wrong fiber, which G cannot see, and the CT may not support the
  continuation at all.
* **A high G does not show that a fix exists.** A low G closes this line for this tracer only, not for other tracers
  or checkpoints.
* **This corpus is not unseen.** Findings 91–100 developed on these 21 cubes. The result screens a direction; it
  cannot confirm a tweak.
* **Censoring:** the reference is clipped to the cube, so a stop near a face cannot show whether its fiber goes on.
  EDGE and the censored class bound this; they do not remove it.

## Sensitivity, reported and not decisive

τ = 4; L = 10 and 40; EDGE = 12; the in-sample cubes; the sixteen Scroll-3 and Scroll-5 cubes together.

## Limits

One tracer, one checkpoint, one operating policy (confidence 0.5), one protocol (128 voxels of CT context), one
reference per cube. Per-cube values are reported with the median and range; ten cubes, eight of them from one scroll.

## Cost

CPU only, at nice 19 beside the loop after the full test suite finishes. Three distance transforms per cube (the gate
at τ = 2, labels at τ = 2 and 4). Finding 91 measured about 5 minutes per 512³ cube for one scoring.
