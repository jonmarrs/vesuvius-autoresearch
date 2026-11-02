# Pre-registration: if villa's neural tracer went on from its confidence stops, how much could continuity rise?

**Written 2026-11-01, before any held-out cube's edited labelling was scored.** CPU only, on runs already made: no new tracing, no
GPU, no download. The script is `scripts/neural_tracer_continuity_ceiling.py`, committed with this file.
Before this was pushed, the script ran once on one in-sample cube, `s1_00497_01497_03997_256`, which decides
nothing, for its timing and gate: the gate passed (36 s), U's gain there was 0.103, and nothing in the method changed
after it.
**Pushed at 14:29 PST (3a4821d2); run 14:29–15:56 PST: finding 102, `reports/neural_tracer_continuity_ceiling.md`.
The gate passed on all 21 cubes. P1 and P3 held, P2 missed (median gain of U 0.314, of U_20 0.061): the line stays
open as a continuity lever.**

## The question

[Finding 101](../../reports/neural_tracer_confidence_stops.md) closed premature confidence stops as a *coverage* lever:
perfect continuation along the right fiber from every confidence stop where the hand-traced fiber goes on would add a
median 8.3% of held-out coverage, under the registered 10%. It also showed that the registration measured the wrong
thing. The [research strategy](../RESEARCH_STRATEGY.md) asks for at least a 10% *useful-continuity* gain, with no
increase in wrong connections, and says coverage alone cannot pass. 65% of those continuing stops are splits: another
trace already follows the fiber on. Continuity is quadratic in run length, so a gap filled between two runs can raise
it far more than the coverage it adds. This registration asks the continuity question finding 101 should have asked.

Already seen, from finding 101, and therefore not predicted here: the stops, their gaps (a median 49 voxels per
continuing stop) and the splits (1,383 of 2,135 continuing stops on the held-out cubes). Not yet computed: any edited
labelling's score, and which traces cover more than one reference fiber at baseline beyond findings 97's and 98's
recorded `merged_instances` counts.

## Data

Finding 101's, unchanged: findings 97's and 98's 21 runs (villa `ccb431818`, checkpoint
`scrollprize/fiber_single_small@451182558c`, 128 voxels of CT context), ScrollGT's hand-traced fiber targets from the
sibling checkout `6d05d642` (scoring version 3). The **ten held-out cubes** (eight Scroll-3 512³, two Scroll-5 256³)
decide. The eleven in-sample cubes are reported apart and decide nothing.

## Definitions, fixed now

* **The stops:** finding 101's, at τ = 2: `confidence` ends that touch no written fiber, at least EDGE = 6 voxels from
  every face, within τ of the reference, whose walk along the matched fiber covers at least L = 20 voxels
  (`continues`). Their **gaps** are finding 101's: the samples along the walk that no trace covers within τ, skipping
  the stopping trace's own, up to the first sample another trace covers (a **split**; that trace is the stop's
  **next trace**), the fiber's end, the cube's face or 400 voxels.
* **The labelling:** the run's labels grown at τ by ScrollGT's `_dilate_labels`, the labelling ScrollGT scores. Every
  edit acts on it, and every score is ScrollGT's `score_tracing` on the edited labelling at tolerance 0, which applies
  no second growth.
* **Fill:** each gap sample's voxel (as ScrollGT rounds it) takes the stopping trace's label. A voxel in several
  gaps takes the first, in order of fiber id and then end.
* **Join:** the stopping trace and its next trace take one label (the union over all joins).
* **Merging trace:** a trace whose runs cover more than one reference fiber at baseline, the ones ScrollGT's merge-
  penalized ERL (ERLpen) zeroes.
* **The ceiling U:** merging traces set to 0; the gaps of the other stops filled; each split joined when neither trace
  is merging; then ScrollGT's ERL of the result (not ERLpen: the zeroing has already applied the baseline penalty).
  With no edits, U equals the baseline ERLpen exactly. U bounds the ERLpen of any rule that goes on from these stops
  along the right fiber, no farther than the next trace, and either joins that trace or not: such a rule's unmerged
  traces are unions of baseline-unmerged traces joined at these splits, and filling or joining only lengthens runs,
  which lengthens ERL's squared run lengths.
* **The gain:** U / baseline ERLpen − 1, per cube.
* **Two policies, reported beside the ceiling:** *fill* (fill every gap, no joins) and *fill and join* (fill every gap
  and join every split, whatever the traces cover), each scored by ScrollGT's ERLpen with its own merge penalty. Their
  gains are against the same baseline. Each is a rule a tracer could follow; U is the most any such rule could reach.
* **Bounded continuation, U_k** for k = 10, 20 and 50 voxels: U with only the gap samples within k voxels of
  arclength along the walk filled, and a split joined only if its next trace starts within k.
* **U without joins:** U's fill alone, which separates the fill's share of the ceiling from the joins'.

## Gate, checked before anything else is read

On every cube; if any check fails, the script writes no verdict.

1. Finding 101's gate: `score_tracing` on the run's labels at τ = 2 reproduces finding 97's or 98's recorded row
   exactly; the `.afv` and fiber JSON ids match; every fiber's ends agree within 2.5 voxels.
2. `score_tracing` at tolerance 0 on the grown labelling reproduces the recorded τ row (ERL, ERLpen, both covered-length
   variants, coverage, splits, merges, merged instances, ground-truth length and fiber count), at τ = 2 and 4.
3. The merging traces counted here equal the recorded `merged_instances`, and U with no edits equals the baseline ERLpen.
4. At τ = 2 and 4, the union of the gaps' lengths equals finding 101's recorded `gap_length` for the cube (the same
   stops), and every gap sample's voxel is unlabelled before the fill.
5. Under *fill* (at τ = 4, *fill and join*, whose joins change no coverage), ScrollGT's covered length rises by that
   union length, within 5% or 10 voxels, whichever is larger.
6. The bounds hold: baseline ERLpen ≤ U without joins ≤ U; *fill*, *fill and join* and every U_k ≤ U;
   U_10 ≤ U_20 ≤ U_50 (at τ = 4, those scored there).

## Predictions, recorded so each can be a miss

On the ten held-out cubes, at τ = 2:

1. **P1 (moderate), the decision:** the median gain of U is at least 0.10.
2. **P2 (low):** the median gain of U_20 is at least 0.10, so continuations of 20 voxels or less could clear the bar.
3. **P3 (low):** the median gain of *fill and join* is at least half the median gain of U, so a rule that joins
   whatever it reaches keeps most of the ceiling.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| Any gate check fails on any cube | No verdict. |
| Fewer than the ten held-out cubes scored | No verdict (partial). |
| Median gain of U < 0.10 | Even perfect continuation from the tracer's confidence stops, joining every split it could join without a merge, would raise the median held-out cube's ERLpen by under 10%. With finding 101, **close premature confidence stops** for this tracer, checkpoint and settings, for coverage and continuity alike; spend no GPU time on them. |
| Median gain of U ≥ 0.10 | The line stays open as a continuity lever. The next step is a development-pilot proposal for a continuation rule, judged by ERLpen and wrong connections against the stock tracer, which needs the owner's GPU decision. P2 and P3 scope it: how far the rule must go on, and whether it must refuse to join some traces. |

## What the result cannot do

* **U is a ceiling, not a forecast.** It assumes continuation along the right fiber, at no cost and to the next trace
  exactly. A real rule would follow some stops onto other fibers, which U cannot see, and the CT may not support the
  continuation at all: the tracer stopped because its confidence fell.
* **A passing U does not show that a fix exists**, only that the line is worth a pilot. A failing U closes it for
  this tracer only.
* **This corpus is not unseen.** Findings 91–101 developed on these cubes; this screens a direction.
* **ERLpen against one hand-traced reference** stands in for the strategy's "independently reviewed continuity". It
  is the closest measure available without new review.

## Sensitivity, reported and not decisive

τ = 4 (the baseline, U and *fill and join*); the in-sample cubes; the sixteen Scroll-3 and Scroll-5 cubes together;
U_10, U_20 and U_50; U without joins.

## Limits

Finding 101's: one tracer, checkpoint, operating policy (confidence 0.5) and protocol (128 voxels of CT context); one
reference per cube; ten held-out cubes, eight from one scroll. Villa #2359 refactored the volume tracer's policy after
`ccb431818`, and its outputs on these cubes have not been checked.

## Cost

CPU only, at nice 19 beside the loop. Per cube: finding 101's gate scoring, two label growths (τ = 2 and 4), the
walks of the confidence stops at each, and thirteen scorings at tolerance 0 (no growth): nine at τ = 2,
four at τ = 4.
