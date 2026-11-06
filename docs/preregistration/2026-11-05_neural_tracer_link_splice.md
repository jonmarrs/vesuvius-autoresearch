# Pre-registration: splicing villa's neural-tracer pieces where they overlap, on the held-out cubes

**Written 2026-11-05, before any held-out cube's spliced labelling was scored.** CPU only, on runs already made: no
new tracing, no GPU, no download. The script is `scripts/neural_tracer_link_splice.py`, committed with this file.
Before this was pushed, the script ran once on one in-sample cube, `s1_00497_01497_03997_256`, for its timing and gate.
The gate passed (30 s), and the result there equals the exploratory screen's below.
**Pushed at 18:45 PST (a70e71ae); run 18:45–19:49 PST: finding 105, `reports/neural_tracer_link_splice.md`. The gate
passed on all 21 cubes. P2, P3 and P4 held and P1 missed (median held-out gain 0.063 at τ = 2, 0.302 at τ = 4):
`SUPPORTED_AT_TOL4_ONLY`.**

## The question

villa's neural volume tracer (`tracing/volume.py`) writes "each fiber once (small overlaps kept for joining)". When a
trace runs along a fiber already written, the run is cut, keeping `--overlap` points beside it. Each written piece
records the fibers its two ends touch (`links`), "so overlapping pieces of one fiber can be joined later". Nothing in
villa joins them: the tiles, the fiber JSONs and the `fibers.vcobj` export keep the pieces apart. The question is how
continuity and wrong connections would move if each piece were spliced to the fiber whose end it overlaps.

## Already seen, and not predicted here

An exploratory screen on the **eleven in-sample cubes only** (scratch, not committed):

* **The links:** 41,974 piece ends in the 21 runs, 11,588 of them linked. 48% of `owned_or_live` ends link, 16% of
  `bounds` ends and 12% of `confidence` ends. Pieces, pieces with a link and linked ends were counted on all 21 cubes,
  the held-out ones included; nothing else about the held-out cubes was computed.
* **Joining every link** (union of labels, chains or not): median ERLpen ×1.049 at τ = 2 (×0.774–×1.423) and ×1.384 at
  τ = 4 (×0.949–×1.862). On the three Scroll-5 512³ cubes the joins added merges at τ = 2, and ERLpen fell there.
* **Where links attach** (in-sample): a piece's linked end lies a median 0.55 voxels from the linked fiber, 78% of
  them within 16 voxels of arclength of that fiber's nearer end and 87% within 32 (median 12.1). That is the overlap
  the tracer keeps when it cuts a run. The splice rule below was set from this, once, before it was scored.
* **The splice rule, scored once on the in-sample cubes:** median ERLpen ×1.134 at τ = 2 (×0.960–×1.436, above 1 on
  8 of 11) and ×1.449 at τ = 4 (×1.168–×1.896, 11 of 11). Summed merges went from 721 to 738 at τ = 2 (+2.4%) and from
  1,468 to 1,435 at τ = 4. Of the splices whose two pieces both touch the reference, 44 of 2,528 (1.7%) join two
  different reference fibers. The three Scroll-5 512³ cubes, the densest in-sample cubes, moved ×0.960–×1.043 at τ = 2.
  No constant was changed after this.

Eight of the ten held-out cubes are Scroll-3 512³ cubes, as dense as those three (1,491 to 1,901 pieces each).

## Data

Findings 97's and 98's 21 runs (villa `ccb431818`, checkpoint `scrollprize/fiber_single_small@451182558c`, 128 voxels
of CT context), as findings 101–102 read them, and ScrollGT's hand-traced fiber targets from the sibling checkout
(scoring version 3). **The ten held-out cubes (eight Scroll-3 512³, two Scroll-5 256³) decide.** The eleven in-sample
cubes are re-run and reported apart; they decide nothing.

## Definitions, fixed now

* **Candidates:** for each written piece P and each end of P with a recorded link to another fiber Q of the run: the
  point of Q nearest P's end (the first, on ties), and Q's nearer end along Q's arclength from it. A candidate when
  that point lies within **32 voxels** of arclength of Q's nearer end, and P, leaving that end (over its last **4**
  points), heads into Q (a positive dot product with Q's direction from that point over 4 points into Q). Coordinates
  are the cube's voxels.
* **Splices:** candidates nearest first (by P's end's distance to Q, then by P, its end, Q and Q's end). A candidate is
  taken unless P's end or Q's end is already in a splice, or P and Q are already in one chain. Every chain of spliced
  pieces is therefore one polyline.
* **The spliced labelling:** the run's labels grown at τ by ScrollGT's `_dilate_labels`, each chain's pieces taking one
  label. Every score is ScrollGT's `score_tracing` on it at tolerance 0, as in findings 101 and 102. The splice moves no
  voxel, so coverage and precision cannot change.
* **The gain:** spliced ERLpen / baseline ERLpen − 1, per cube.
* **Merges:** ScrollGT's `merges`. **A wrong splice** joins two pieces whose labels each cover some reference fiber and
  none in common (ScrollGT's runs, at τ = 2).
* **All (sensitivity):** every recorded link joined, chains or not.

## Gate, checked on every cube; if any check fails, no verdict

1. The run's `.afv` and fiber JSON ids match, and every fiber's ends agree within 2.5 voxels (finding 101's).
2. `score_tracing` on the run's labels at τ = 2 and 4 reproduces finding 97's or 98's recorded row exactly.
3. `score_tracing` at tolerance 0 on the grown labelling reproduces the recorded τ row exactly (ERL, ERLpen, both
   covered variants, coverage, splits, merges, merged instances, ground-truth length and fiber count).
4. Every splice is a candidate, joins two different pieces, uses each piece end at most once, and the splices form no
   ring.
5. Coverage under the splice (and under all) equals the baseline's.

## Predictions, recorded so each can be a miss

On the ten held-out cubes:

1. **P1 (low), at τ = 2:** the median gain is at least 0.10. Low because the dense in-sample cubes stayed near 1.
2. **P2 (moderate):** summed merges at τ = 2 rise by at most 5%.
3. **P3 (moderate), at τ = 4:** the median gain is at least 0.10.
4. **P4 (moderate):** at most 5% of the splices whose pieces both touch the reference are wrong (τ = 2).

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| Any gate check fails | No verdict. |
| Fewer than the ten held-out cubes scored, or a zero baseline | No verdict. |
| P2 misses | `COSTS_MERGES`: the splice adds wrong connections. No proposal as it stands; a stricter rule is a new registration. |
| P2 holds, P1 holds | `SUPPORTED`: splicing the tracer's kept overlaps raises held-out continuity by at least 10% at τ = 2 without materially more merges. Next: the splice as polylines on real outputs, and a proposal to villa, which is the owner's decision. |
| P2 holds, P1 misses, P3 holds | `SUPPORTED_AT_TOL4_ONLY`: the gain shows at the coarser tolerance only, where (after the off-reference analysis) ScrollGT reads connectivity rather than placement. Any proposal says so; the owner decides. |
| P2 holds, P1 and P3 miss | `NOT_SUPPORTED`: close the splice for this tracer and these settings. |

P4 is reported, not decisive.

## What the result cannot do

* **It scores a labelling, not polylines.** A real splice would also drop the overlap points one piece duplicates
  (about 12 voxels per splice). That moves no coverage, since the other piece covers them, but the polyline tool and
  its VC3D export are not tested here.
* **The rule was set on these runs' in-sample cubes,** and this tracer's held-out cubes have been read by findings
  91–104. It tests a fixed rule, not a tuned one, on cubes whose spliced scores nobody has seen.
* **ERLpen against one hand-traced reference** stands in for reviewed continuity.

## Limits

One tracer at villa `ccb431818`, one checkpoint at its defaults (confidence 0.5) and one protocol. villa #2359 refactored
the volume tracer after `ccb431818`, and #2440 changed its presence blur; villa's CLI at `39a8cf3a` (before both)
reproduced two of these runs point for point. Ten held-out cubes, eight from one scroll.

## Cost

CPU only, at nice 19 beside the loop: per cube, finding 101's gate scoring at τ = 2 and 4, two label growths, and three
scorings at tolerance 0 at each τ. About 45 minutes for the 21 cubes.
