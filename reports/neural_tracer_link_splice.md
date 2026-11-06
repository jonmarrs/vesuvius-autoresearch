Finding 105: splicing villa's neural-tracer pieces where they overlap raises held-out ERLpen by a median 30% at tolerance 4 and 6.3% at tolerance 2, with no more merges (2026-11-05)

The result of `docs/preregistration/2026-11-05_neural_tracer_link_splice.md`, registered at a70e71ae (pushed
18:45 PST) before any held-out cube's spliced labelling was scored. Run 18:45–19:49 PST on the CPU at nice 19, from the
registration commit, on findings 97 and 98's runs (villa `ccb431818`, `scrollprize/fiber_single_small` at 4511825), and
scored with ScrollGT c7b2f6f2 (scoring version 3). Results: `reports/neural_tracer_link_splice.json`.

**Status OK; decision `SUPPORTED_AT_TOL4_ONLY`.** The registered reading: "the gain shows at the coarser tolerance
only, where (after the off-reference analysis) ScrollGT reads connectivity rather than placement. Any proposal says
so; the owner decides." The gate passed on all 21 cubes: every baseline reproduced its recorded ScrollGT rows exactly,
and no splice changed coverage.

## What was tested

villa's volume tracer writes "each fiber once (small overlaps kept for joining)". When a trace runs along a fiber
already written, the run is cut, keeping a short overlap, and the piece records the fibers its ends touch ("links").
Nothing in villa joins the pieces. The registered rule splices a piece to the linked fiber whose end it overlaps:
its end lies within 32 voxels of arclength of that fiber's nearer end and heads into it, nearest first, each fiber end
once, no rings. Every chain of spliced pieces is one polyline; the chain takes one label, and ScrollGT scores the
labelling. Gains divide ScrollGT's rows, which give ERLpen to two decimals.

## Result, the ten held-out cubes

| cube | splices | ERLpen τ = 2 | ERLpen τ = 4 | merges τ = 2 |
|---|---|---|---|---|
| s3_00994_00494_01994_512 | 722 | 34.65 → 37.37 | 105.33 → 141.72 | 180 → 193 |
| s3_00994_01994_00494_512 | 728 | 42.08 → 46.25 | 96.38 → 132.64 | 219 → 220 |
| s3_00994_02494_01494_512 | 715 | 29.60 → 30.99 | 80.76 → 96.51 | 257 → 258 |
| s3_01994_01494_00994_512 | 511 | 32.12 → 38.47 | 83.55 → 125.86 | 114 → 116 |
| s3_01994_01994_01494_512 | 493 | 32.06 → 33.36 | 77.78 → 99.32 | 187 → 191 |
| s3_02994_02494_01994_512 | 780 | 41.50 → 49.35 | 108.20 → 150.00 | 169 → 174 |
| s3_03494_01494_00494_512 | 748 | 35.03 → 39.34 | 89.33 → 118.49 | 300 → 290 |
| s3_04494_00994_01494_512 | 720 | 26.25 → 27.05 | 77.71 → 95.05 | 260 → 263 |
| s5_13497_01497_02497_256 | 43 | 11.41 → 11.92 | 25.07 → 28.00 | 24 → 27 |
| s5_16997_03997_04497_256 | 44 | 9.87 → 10.34 | 21.80 → 23.89 | 30 → 29 |

* **At tolerance 4, ERLpen rises on all ten cubes,** by a median 0.302 (0.096 to 0.506). P3 held.
* **At tolerance 2 it also rises on all ten,** but by a median 0.063 (0.030 to 0.198), under the 0.10 bar. P1, which
  decided at this tolerance, missed.
* **No more wrong connections.** Summed merges went from 1,740 to 1,761 at tolerance 2 (+1.2%; P2 allowed 5%) and from
  3,678 to 3,624 at tolerance 4. Of the 4,577 splices whose two pieces both touch the reference, 76 (1.7%) join two
  different reference fibers (P4 held). Another 927 splices join a piece that touches no reference fiber.
* **The rule's restraint is what works.** Joining every link instead, chains or not, lowered the median held-out
  ERLpen at tolerance 2 (−0.027; it rose on 3 of 10 cubes) and raised summed merges there from 1,740 to 1,961. At
  tolerance 4 it gained a median 0.183, against the splice's 0.302.
* **In-sample, reported apart:** median gains 0.134 at tolerance 2 and 0.449 at tolerance 4, as the screen that set the
  rule found.

## What it changes

**The neural volume tracer's own output can be made more continuous without retracing.** Its kept overlaps and links
already say which pieces continue which; spliced, the median held-out cube's merge-penalized ERL rises by 30% at
tolerance 4, with no rise in merges. This is the continuity the [research strategy](../docs/RESEARCH_STRATEGY.md) asks
for, unlike finding 104's refit retry, which raised coverage but not ERLpen and added merges.

**At tolerance 2 the gain is smaller.** There ScrollGT's runs also break where a trace strays more than 2 voxels from
the hand tracing beside the fiber it follows. The [off-reference analysis](neural_tracer_offref_location.md) put 39% of
the tracer's tolerance-2 off-reference length there, and joining pieces cannot mend those breaks.

**Next, before any proposal:** the splice as polylines on real outputs. It must drop the overlap points one piece
duplicates, then pass villa's `fibers.vcobj` export and read back in VC3D. Proposing it to villa is the owner's
decision. It would add a step villa does not have, so it must say where the gain shows (tolerance 4) and where it
does not reach the bar (tolerance 2).

## What it cannot say

* **It scores a labelling, not polylines.** The splice moves no voxel. A polyline tool would also drop about 12 voxels
  of duplicated overlap per splice; the other piece covers them.
* **The rule was set on these runs' eleven in-sample cubes,** whose spliced scores were seen first. The held-out cubes
  had been read by findings 91–104, but no spliced score of theirs before this run.
* **One tracer at villa `ccb431818`, one checkpoint at its defaults, one protocol.** villa #2359 refactored the volume
  tracer since and #2440 changed its presence blur; neither has been run on these cubes.
* **ERLpen against one hand-traced reference per cube** stands in for reviewed continuity. Ten held-out cubes, eight
  from Scroll 3.
