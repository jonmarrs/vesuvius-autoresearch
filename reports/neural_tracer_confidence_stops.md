# Finding 101: continuing villa's neural tracer past its confidence stops could add at most a median 8.3% to held-out coverage, so that line closes as a coverage lever (2026-11-01)

The result of `docs/preregistration/2026-11-01_neural_tracer_confidence_stops.md`, pushed at 06:57 PST (d2e912a7)
before any stop was compared with the ground truth. One in-sample cube was smoked first (it decides nothing); the
method was not changed after it.

**Answer: close the line, narrowly.** If the tracer continued perfectly along the right fiber from every confidence
stop where the hand-traced fiber goes on, it would add a median **0.083** of the covered length on the ten held-out
cubes (0.038–0.128). The registered bar is 0.10, so the registered rule closes the line. Three things qualify that:

* **It is close.** Five of the ten cubes are at or above 0.10. The median falls between the fifth and sixth cubes
  (0.065 and 0.102).
* **Every variant agrees.** At tolerance 4, L = 10 or 40, and an edge margin of 12, the held-out median stays between
  0.059 and 0.087.
* **It is a ceiling.** It assumes perfect continuation along the right fiber, up to the next trace. A real rule would
  recover less, and could follow some stops onto the wrong fiber, which this measure cannot see.

**The registered rule measures coverage, and the strategy's bar is continuity.** The strategy asks for a 10%
*useful-continuity* gain and says coverage alone cannot pass. G is a coverage ceiling. Of the confidence stops whose
fiber goes on, **65% are splits** (1,383 of 2,135): another trace already follows the fiber on. Joining those would
raise connectivity, not coverage, and nothing here measures that. So this closes premature confidence stops as a
coverage lever. Their effect on connectivity is untested. For scale, those 1,383 splits are 1.6% of the 88,106 that
ScrollGT counts on these cubes. I noticed this gap only after the result arrived.

## What the stops look like

On the ten held-out cubes, tolerance 2:

* **Most confidence stops are not on the reference.** Of the 7,146 interior, unlinked confidence stops, 2,452 (34%)
  lie within 2 voxels of a hand-traced fiber. For the tracer's collision stops (`owned_or_live`) it is 3,379 of 4,947
  (68%).
  * 848 (12%) of the confidence stops left the fiber within their last 20 voxels.
  * 3,846 (54%) were already more than 2 voxels off the reference 20 voxels before they stopped.
  * At tolerance 4, 3,619 (51%) are on the reference.
* **When a confidence stop is on the fiber, the fiber usually goes on.** Of the stops whose class is decided, the
  median cube's share where the fiber continues at least 20 voxels is 0.89 (0.72–0.98). For random covered points of
  the reference, walked in a random direction, it is 0.99 (P1 and P2 held).
  * The reference fibers almost never end inside a cube. They run out through its faces, so a high share was likely
    from the start, and P1 and P2 were weak predictions.
  * The stops do carry some signal. A fiber end within 20 voxels is 3.8–31.5 times as common past a confidence stop as
    past a random covered point (median 15). The ratio is imprecise: of each cube's 2,000 base walks, only 0.2–2.1% of those
    decided end at a fiber end.
* **The gap past a continuing stop:** a median 49 voxels of uncovered fiber per continuing confidence stop, per cube.

| Held-out cube | Coverage | Confidence stops | On the fiber | Continues ≥ 20 | Fiber ends | Censored | Splits | G |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| s3_00994_00494_01994_512 | 0.643 | 910 | 245 | 197 | 41 | 7 | 119 | 0.057 |
| s3_00994_01994_00494_512 | 0.649 | 696 | 261 | 245 | 11 | 5 | 175 | 0.063 |
| s3_00994_02494_01494_512 | 0.571 | 974 | 354 | 317 | 31 | 6 | 224 | 0.105 |
| s3_01994_01494_00994_512 | 0.578 | 1,127 | 376 | 322 | 46 | 8 | 203 | 0.125 |
| s3_01994_01994_01494_512 | 0.597 | 1,310 | 476 | 400 | 67 | 9 | 230 | 0.128 |
| s3_02994_02494_01994_512 | 0.674 | 540 | 134 | 124 | 2 | 8 | 79 | 0.038 |
| s3_03494_01494_00494_512 | 0.611 | 549 | 236 | 213 | 15 | 8 | 140 | 0.059 |
| s3_04494_00994_01494_512 | 0.623 | 823 | 306 | 275 | 18 | 13 | 206 | 0.065 |
| s5_13497_01497_02497_256 | 0.333 | 120 | 29 | 19 | 7 | 3 | 3 | 0.112 |
| s5_16997_03997_04497_256 | 0.268 | 97 | 35 | 23 | 9 | 3 | 4 | 0.102 |

Coverage is ScrollGT's at tolerance 2, as recorded by findings 97 and 98 and reproduced here. On the eleven in-sample
cubes, which decide nothing, the median G is 0.032.

## The run

* **Script:** `scripts/neural_tracer_confidence_stops.py` at d2e912a7, CPU only, at nice 19 beside the loop, from
  07:04:30 to 07:44:56 PST on 2026-11-01. Output: `neural_tracer_confidence_stops.json`.
* **Inputs:** findings 97's and 98's runs (villa `ccb431818`; checkpoint
  `scrollprize/fiber_single_small@451182558c`), and ScrollGT's fiber targets from the sibling checkout `6d05d642`
  (scoring version 3). Each skeleton's sha256 is in the JSON.
* **Gate, passed on all 21 cubes:**
  * ScrollGT's `score_tracing` on each run's labels reproduced the recorded tolerance-2 row exactly (coverage,
    precision, splits, merges, ground-truth and predicted length);
  * every `.afv` id matched a fiber JSON's, and every fiber's ends agreed within 2.5 voxels.

## What this changes

The strategy's rank-2 line named premature confidence stops as one failure mode to investigate. As a way to add
coverage, it closes here without GPU time. A continuity version is a different question. Its ceiling would join each
split's two traces and fill the gap between them, then re-score ERL with merges penalized. That would need its own
registration, and could run CPU-only on these same runs.

The larger observation is not the registered question. Most of the tracer's confidence stops end traces that are
already off the hand-traced fibers. That is the precision side, the trade villa's open problems page asks for:
"a tracer that confidently follows fewer fibers correctly is more useful than one that follows more fibers with a
higher error rate". Open villa #2377 addresses it for villa's C++ beam tracer. This shows only that confidence stops
are where off-reference traces end. It does not show that a stop or trim rule would help.

## Limits

* **One tracer setup:** one checkpoint, one operating policy (confidence 0.5), one protocol (128 voxels of CT
  context), one reference per cube.
* **The cubes:** ten held-out cubes, eight of them from Scroll 3.
* **Development data:** findings 91–100 developed on these cubes. This screens a direction; it confirms no change.
* **The reference:** "off the reference" means more than τ from this hand-traced reference. ScrollGT records that
  every fiber in each cube was traced, but this run does not check that claim.
* **The code version:** the result describes the tracer at villa `ccb431818`. Villa #2359 (merged 2026-10-29)
  refactored the volume tracer's policy, and its outputs on these cubes have not been checked.
