# Finding 100: tracing the seeds villa's tracer skips where its CT axis misses the presence direction adds 1.20–1.43× coverage on the two held-out Scroll-5 cubes, and 1.00–1.02× on Scroll 3 (2026-10-25)

The result of `docs/preregistration/2026-10-25_neural_tracer_steep_heading.md`, pushed at 00:38 PDT (9d31f36d) before
any arm was traced. With the scan around each cube (findings 97 and 98), villa's neural tracer still skips seed dots
whose CT axis lies more than 35° from their presence direction. Finding 99 (`neural_tracer_heading_residual.md`)
associated those skips with steeply tilted sheets. This traced the skipped dots, on findings 97 and 98's inputs and
command, in two arms:
* `sheet` traced them from the presence direction projected into the CT's sheet;
* `keep` traced them from villa's own CT axis, as villa's training seeds are traced. Training never applies the skip.

Every other dot was headed as villa heads it.

**Answer, the registered reading:** "a seed heading that follows the sheet recovers coverage on the two held-out
Scroll-5 cubes, not as registered on Scroll 3, keeping its precision; the heading matters: villa's own axis, kept,
recovers less". Four of the five predictions held. P2 failed.
* **The two held-out Scroll-5 cubes (P1 held).** Sheet's coverage rises from 0.333 to 0.399 and from 0.268 to 0.382
  (1.20× and 1.43×). Merge-penalized ERL rises 1.27× and 1.33×. Precision moves by −0.013 and +0.007.
* **Scroll 3 (P2 failed).** Coverage rises on all eight cubes, but by only 1.003–1.024×, a median of 1.017×. The
  registered median was at least 1.05×. Merge-penalized ERL moves by 0.98–1.02×.
* **Precision (P3 held).** On all ten held-out cubes, sheet's precision is within 0.017 of the baseline's (−0.017 to
  +0.007).
* **The heading matters (P4 held).** Sheet's coverage is above keep's on 9 of the 10 held-out cubes. On the two Scroll-5
  cubes, keep reaches 1.11× and 1.28×.
* **In sample, nothing moves (P5 held).** Sheet's coverage factors lie in 0.995–1.015 on the eleven in-sample cubes,
  and keep's in 0.996–1.003.

## The run

* **Chain:** `repro/fibers/run_neural_tracer_steep_heading_chain.sh` at 9d31f36d, villa `ccb431818`, work directory
  `spiral_out/neural_tracer/steep_heading_run`. The chain and wrapper logs are copied to `reports/evidence/`.
* **Timing, 2026-10-25 PDT:**
  * the loop was stopped at 01:09:57, at the end of a cycle;
  * the smoke ran from 01:09:57 to 01:11:05;
  * the 42 runs ran from 01:11:05 to 02:55:18: sheet, then keep, on the held-out set, then both on the in-sample set;
  * the loop restarted at 02:55:48, 1 h 46 min after it stopped;
  * scoring ran at nice 19 beside the loop, until 04:15:34.
* **Identity:** the smoke was the launcher's `villa` arm on `s5_13497_01497_02497_256`. It reproduced finding 97's run
  of that cube point for point.
  * Before the GPU run, an unregistered CPU pre-flight ran on the same cube, after the registration was pushed. Over
    villa's own spawned axis workers, the launcher's `villa` arm gave villa's own `seed_headings` result on all 910
    dots.
  * In that pre-flight, the two arms gave villa's heading to every dot whose axis agrees.
* **The manipulation took.** No arm skipped a dot on any held-out cube. The baseline had skipped 127–960 per cube.
  * Sheet traced 4,135 skipped dots across the ten held-out cubes; keep traced 4,727.
  * The two counts differ because each arm's new traces change which later dots are already owned.
  * 481 of sheet's dots had a presence direction more than 45° out of the sheet. As registered, they were counted and
    traced.
  * No dot was degenerate, and none lacked a CT axis.
* **Completeness:** all 42 runs finished, and the status is `OK` (`neural_tracer_steep_heading.json`).
* **One edit to the chain after the run.** Its refusal messages were renamed from `SH_ABORTED` to `SC_ABORTED`, the
  prefix the repository's chain guard (`tests/test_fiber_chain_loop_guard.py`) requires. None of them fired during the
  run, and nothing else changed.
* **Scoring:** in each cube's frame, ScrollGT scoring version 3, at tolerances 2 and 4. The baseline is findings 97 and
  98's runs, with the same inputs.

## Results, the held-out cubes

Baseline (findings 97 and 98) → sheet, with keep in parentheses, at tolerance 2. The merge-penalized ERL column gives
keep's value and our tracer's published row in parentheses.

| cube | coverage | precision | merge-penalized ERL (keep; ours) | traced seeds |
|---|---|---|---|---|
| s5_13497_01497_02497 | 0.333 → **0.399** (0.369) | 0.364 → 0.352 (0.347) | 11.41 → 14.44 (12.55; 10.17) | 369 → 532 (556) |
| s5_16997_03997_04497 | 0.268 → **0.382** (0.343) | 0.499 → 0.506 (0.510) | 9.87 → 13.09 (11.82; 4.71) | 288 → 486 (507) |
| s3_00994_00494_01994 | 0.643 → **0.655** (0.649) | 0.486 → 0.469 (0.472) | 34.65 → 34.64 (34.95; 22.09) | 2,375 → 2,788 (2,966) |
| s3_00994_01994_00494 | 0.649 → **0.655** (0.651) | 0.594 → 0.592 (0.591) | 42.08 → 43.01 (42.53; 24.76) | 2,166 → 2,344 (2,482) |
| s3_00994_02494_01494 | 0.571 → **0.585** (0.579) | 0.507 → 0.492 (0.495) | 29.60 → 29.46 (29.02; 17.18) | 2,509 → 2,975 (3,228) |
| s3_01994_01494_00994 | 0.578 → **0.589** (0.585) | 0.560 → 0.545 (0.551) | 32.12 → 32.12 (31.84; 21.27) | 2,949 → 3,439 (3,500) |
| s3_01994_01994_01494 | 0.597 → **0.606** (0.603) | 0.544 → 0.529 (0.537) | 32.06 → 32.30 (32.72; 19.52) | 3,086 → 3,530 (3,607) |
| s3_02994_02494_01994 | 0.674 → **0.679** (0.678) | 0.555 → 0.553 (0.553) | 41.50 → 41.61 (41.79; 29.97) | 2,094 → 2,159 (2,157) |
| s3_03494_01494_00494 | 0.611 → **0.626** (0.615) | 0.664 → 0.654 (0.652) | 35.03 → 35.12 (35.03; 20.70) | 2,016 → 2,247 (2,464) |
| s3_04494_00994_01494 | 0.623 → **0.625** (0.625) | 0.538 → 0.528 (0.533) | 26.25 → 25.76 (25.67; 17.82) | 2,444 → 2,672 (2,789) |

At tolerance 4 the picture is the same: sheet's coverage rises 1.20× and 1.40× on the two Scroll-5 cubes. On no cube,
at either tolerance, does either arm change whether the neural tracer leads or trails our tracer on merge-penalized
ERL. The in-sample cubes' rows are in the JSON. There, both arms' precision moves by at most 0.003.

**The registered predictions:**

| | registered | result |
|---|---|---|
| P1 (moderate) | sheet's coverage at least 1.15× on both held-out Scroll-5 cubes | **held** (1.20×, 1.43×) |
| P2 (moderate) | sheet's coverage rises on at least 6 of 8 Scroll-3 cubes, median at least 1.05× | **failed**: it rises on 8, median 1.017× |
| P3 (moderate) | sheet's precision at most 0.03 lower on at least 8 of 10 held-out cubes | **held** (10 of 10) |
| P4 (low) | sheet's coverage above keep's on at least 7 of 10 held-out cubes | **held** (9 of 10) |
| P5 (high) | both arms' coverage 0.95–1.05× on all 11 in-sample cubes | **held** (0.995–1.015×) |

The registration estimated about 1.3× and 1.5× on the two Scroll-5 cubes, and a median 1.10× on Scroll 3. The
Scroll-5 cubes came near that estimate; Scroll 3 came in far below it.

## What it means

* **On the two held-out Scroll-5 cubes, the 35° skip costs coverage, and the sheet heading recovers it.**
  * These are the cubes with 0.84 and 0.78 of their dots in sheets tilted more than 45° (finding 99), in
    the table's order.
  * Tracing the skipped dots along the sheet adds a fifth and two fifths of the coverage, at the same precision.
  * villa's own axis recovers about half to two thirds of that gain, so the heading matters there, not only the skip.
* **On Scroll 3 the skip is not what limits coverage.** It skipped 0.06–0.28 of the dots it offered there. Tracing them
  added at most 2.4% to coverage and cost up to 0.017 of precision. Why they add so little is untested.
* **In sample nothing changes,** within 1.5% of coverage and 0.003 of precision. A change to villa's heading rule would
  leave the in-sample cubes as they are, under this checkpoint and presence.
* **On merge-penalized ERL, the ranking against our tracer does not change** on any cube at either tolerance. On
  coverage, sheet overtakes our tracer on 1 cube at tolerance 2 and 4 at tolerance 4.

## What it does not say

* **It does not show that tilt is the cause.** Both arms change the dots that the 35° test selects, and tilt was not
  manipulated. The gain is on the two cubes with the most steep sheets, but that is two cubes.
* **The gain rests on two cubes of one scroll.** Both are cubes on which the reference mask also fails (finding 84).
* **One checkpoint at its defaults,** with finding 91's presence, unchanged.
* **Our tracer was not re-run.** Its rows are from the cube alone.
* **On Scroll 3, scroll and split cannot be told apart.** All eight of its cubes are held out.
* **The CPU pre-flight was not registered.** It traced nothing and changed nothing, and it ran after the registration
  was pushed.
* **No villa or ScrollGT change here.** A change to villa's seed heading is the owner's decision.
* **A count in the registration's commit message is wrong.** It says 24 tests; there are 23.
