# Finding 102: perfect continuation from villa's neural tracer's confidence stops would raise held-out ERLpen by a median 31%, so the line stays open as a continuity lever (2026-11-01)

The result of `docs/preregistration/2026-11-01_neural_tracer_continuity_ceiling.md`, pushed at 14:29 PST (3a4821d2)
before any held-out cube's edited labelling was scored. One in-sample cube was smoked first (it decides nothing); the
method was not changed after it.

**Answer: the line stays open.** [Finding 101](neural_tracer_confidence_stops.md) closed premature confidence stops as
a coverage lever. Measured by the strategy's own yardstick, continuity, the same stops clear the bar. Suppose the tracer
went on along the right fiber from every confidence stop where the hand-traced fiber continues, as far as the next
trace, and joined that trace wherever neither of the two merges at baseline. Then ScrollGT's merge-penalized ERL
(ERLpen) would rise by a median **0.314** on the ten held-out cubes (0.149–0.479), as a fraction of its baseline,
against a registered bar of 0.10.
All ten cubes clear it, and at tolerance 4 the median is 0.274. Three things qualify that:

* **It is a ceiling.** The continuation is perfect: it follows the hand-traced fiber exactly, wherever the tracer's
  confidence fell below 0.5. A real rule would recover less, could follow some stops onto other fibers, and might find
  no support in the CT at all.
* **The gain lies far from the stops.** Bounded to 20 voxels past each stop, the ceiling is a median 0.061 (P2
  missed), and only 1 of the 10 cubes reaches 0.10. Bounded to 50 voxels it is 0.130 (6 cubes). A rule must go on
  for tens of voxels on the right fiber, which this measure cannot show the tracer can do.
* **This registration was written after finding 101's result, and because of it.** Its bar, a 10% useful-continuity
  gain, is the research strategy's and predates both. But the second registration reverses the first's conclusion on
  the same 21 cubes, so read it as a screen that keeps a direction alive, not as evidence for any rule.

## Why coverage said close and continuity says open

ERL weights each run of correctly traced fiber by its length, so it squares run lengths. Filling a gap at the end of
a run lengthens that run. Without any joins, the fill alone raises held-out ERLpen by a median 0.277, a median 3.2
times the coverage it adds (2.6–3.9 by cube; coverage is finding 101's G). Joining the split traces adds a further
median 0.043. Of the 2,135 continuing confidence stops, 1,383 are splits, and 897 of those joins involve no trace that merges
at baseline. The ceiling makes no other join: 330 stops end traces that already merge, and 360 splits run into one.

## Two rules a tracer could follow

Both are scored by ScrollGT's ERLpen with their own merges, against the same baseline:

* **Fill only:** a median 0.228.
* **Fill and join every split, whatever the traces cover:** a median 0.215, at least half of the ceiling (P3 held), and
  above 0.10 on all ten cubes. At tolerance 4 it falls to 0.076, and only 4 of the 10 cubes reach 0.10: the wider
  tolerance makes more traces merge, and a join inherits a merge. Which traces a rule joins matters.

**Merges cannot test wrong connections here.** The fill follows the reference by construction, so merge counts move
only through side effects of scoring. Under the fill alone, the count rose on 8 of the 10 held-out cubes, by 1–4: a
filled voxel that another reference fiber's samples also read makes the stopping trace cover that fiber too. Under
fill and join, the merge count fell on 7 held-out cubes, stayed level on 2, and rose by 1 on one
(s5_13497_01497_02497_256). None of this measures how often a real continuation would cross onto another fiber.

| Held-out cube | ERLpen | U | Gain | Without joins | Within 20 voxels | Within 50 voxels | Fill and join |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| s3_00994_00494_01994_512 | 34.65 | 41.67 | 0.203 | 0.168 | 0.039 | 0.076 | 0.147 |
| s3_00994_01994_00494_512 | 42.08 | 51.07 | 0.214 | 0.162 | 0.042 | 0.091 | 0.153 |
| s3_00994_02494_01494_512 | 29.60 | 43.79 | 0.479 | 0.406 | 0.059 | 0.137 | 0.289 |
| s3_01994_01494_00994_512 | 32.12 | 47.48 | 0.478 | 0.388 | 0.097 | 0.211 | 0.407 |
| s3_01994_01994_01494_512 | 32.06 | 46.81 | 0.460 | 0.357 | 0.109 | 0.219 | 0.321 |
| s3_02994_02494_01994_512 | 41.50 | 47.69 | 0.149 | 0.136 | 0.019 | 0.039 | 0.114 |
| s3_03494_01494_00494_512 | 35.03 | 42.85 | 0.223 | 0.196 | 0.027 | 0.064 | 0.169 |
| s3_04494_00994_01494_512 | 26.25 | 32.49 | 0.238 | 0.179 | 0.064 | 0.123 | 0.110 |
| s5_13497_01497_02497_256 | 11.41 | 15.87 | 0.391 | 0.389 | 0.066 | 0.148 | 0.261 |
| s5_16997_03997_04497_256 | 9.87 | 13.78 | 0.395 | 0.372 | 0.088 | 0.201 | 0.388 |

ERLpen is ScrollGT's at tolerance 2, as recorded by findings 97 and 98 and reproduced here. U is in the same units,
voxels; each gain is against the cube's ERLpen. On the eleven in-sample cubes, which decide nothing, the median gain of U is
0.161 (0.041–0.602). On the sixteen Scroll-3 and Scroll-5 cubes, the scrolls the tracer never saw, it is 0.238.

## The run

* **Script:** `scripts/neural_tracer_continuity_ceiling.py` at 3a4821d2, CPU only, at nice 19 beside the loop, from
  14:29:13 to 15:56:00 PST on 2026-11-01. Output: `neural_tracer_continuity_ceiling.json`.
* **Inputs:** finding 101's: findings 97's and 98's runs (villa `ccb431818`; checkpoint
  `scrollprize/fiber_single_small@451182558c`), ScrollGT's fiber targets from the sibling checkout `6d05d642`
  (scoring version 3), and finding 101's recorded gap lengths.
* **Gate, passed on all 21 cubes at both tolerances:**
  * finding 101's identity checks;
  * ScrollGT's `score_tracing` at tolerance 0 on the grown labelling reproduced the recorded row;
  * the merging traces matched the recorded `merged_instances`, and U with no edits equalled the baseline ERLpen
    exactly;
  * the stops' gaps summed to finding 101's recorded lengths, with no gap voxel labelled before the fill;
  * the fill raised ScrollGT's covered length by those lengths, within 0.6%;
  * every bound held: baseline ≤ U without joins ≤ U, and each rule and each bounded ceiling ≤ U.

## What this changes

Finding 101's coverage result stands, but the line is not closed. The registered next step is a development-pilot
proposal for a continuation rule, judged against the stock tracer by ERLpen and wrong connections, and running it is
the owner's GPU decision. This result scopes what such a rule would have to do:

* **Go on for tens of voxels.** Within 20 voxels the ceiling is a median 6.1%. Short extensions cannot reach the bar.
* **Go on only where the trace is on a fiber.** Finding 101 found two-thirds of the tracer's interior confidence stops
  off the reference, most of them already off it 20 voxels before they stop. A rule that continues every confidence
  stop would extend about two off-reference traces for each on-reference one. ERLpen charges that cost only where an
  extension reaches a reference fiber; precision charges all of it. The strategy stops a candidate whose gain depends
  on a precision loss.
* **Choose its joins.** Joining whatever it reaches keeps most of the ceiling at tolerance 2, but little at
  tolerance 4.

## Limits

* **One tracer setup:** one checkpoint, one operating policy (confidence 0.5), one protocol (128 voxels of CT
  context), one hand-traced reference per cube.
* **The cubes:** ten held-out cubes, eight of them from Scroll 3.
* **Development data:** findings 91–101 developed on these cubes. This screens a direction; it confirms no change.
* **The yardstick:** ERLpen against one WEBKNOSSOS reference stands in for the strategy's "independently reviewed
  continuity".
* **The code version:** the result describes the tracer at villa `ccb431818`. Villa #2359 (merged 2026-10-29)
  refactored the volume tracer's policy, and its outputs on these cubes have not been checked.
