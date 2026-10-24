# Finding 98: on the 512³ cubes too, real CT around each cube lets villa's neural tracer keep its seeds, and its coverage rises 1.19–1.35× (2026-10-24)

The result of `docs/preregistration/2026-10-24_neural_tracer_ct_context_512.md` (#220). It was pushed at 05:55 PDT,
before any 512³ padded CT was downloaded. Finding 97 (`neural_tracer_ct_context.md`) gave villa's neural tracer 128
voxels of the real scan around each of the ten 256³ cubes. This run did the same for the eleven 512³ cubes, the box
still the cube, everything else as in finding 91.

**Answer: the cube-only protocol held it back on the 512³ cubes too, by less.** Every registered prediction held, on
both sets:
* **Seeds:** the share of seed dots it drops falls from 0.258–0.283 to 0.004–0.012 on the three in-sample Scroll-5
  cubes, and from 0.256–0.357 to 0.011–0.088 on the eight held-out Scroll-3 ones;
* **Coverage:** it rises 1.19–1.35× on every cube, against 1.76–2.78× on the 256³ cubes;
* **Ranking against our tracer:** unchanged at both tolerances. At tolerance 4 it leads on all eleven. At tolerance 2
  it leads on the eight Scroll-3 cubes and trails on the three Scroll-5 ones, by less than before.

## The run

* **Chain:** `repro/fibers/run_neural_tracer_ct_context_512_chain.sh` at 95a560c9, villa `ccb431818`, work directory
  `spiral_out/neural_tracer/ct_context_512_run`.
* **Timing:**
  * the download ran from 06:09 to 07:03 PDT on 2026-10-24, with the loop running;
  * the loop was stopped at 07:08:18, at the end of a cycle;
  * the smoke ran from 07:08:18 to 07:10:33, and the eleven runs from 07:10:33 to 07:48:23;
  * the loop restarted at 07:48:53, before scoring.
* **The download** was interrupted twice by the server (a read timeout at 06:30, resets at 06:50). An unregistered
  helper re-fetched the missing slices with retries. It only downloads: every core is checked below.
* **Identity:**
  * every padded CT's 512³ core equals finding 85's array for the cube, voxel for voxel. Scroll 5 is read from its
    public raw zarr; Scroll 3 from its raw slices by byte range (`scripts/raw_tiff_region.py`);
  * every padded presence's core equals finding 91's level, with zeros outside;
  * the smoke, finding 91's own command on the 512³ cube `s5_06494_01994_03994_512`, reproduced its `fibers.afv`
    point for point.
* **The manipulation took.**
  * Finding 91's closest traced seed lay 19.00 trace-grid voxels from a face on every cube. Here it lies 0 voxels
    from a face on all eleven.
  * The seed dots are the same as finding 91's on every cube. What changed is how many get a heading.
* **Completeness:** all eleven runs finished, in 2.7–3.7 minutes each. The status is `OK` for both sets
  (`neural_tracer_ct_context_512.json`).
* **Scoring:** in each cube's frame, ScrollGT scoring version 3, at tolerances 2 and 4.

## Results

Before → after: finding 91's run (tolerance 2) or finding 94's re-score (tolerance 4) → the padded run. Our tracer's
published row is in parentheses. Bold: the padded run leads our tracer.

| cube | split | dropped as `no_heading` | coverage | output / ground truth | merge-penalized ERL, tolerance 2 (ours) | tolerance 4 (ours) |
|---|---|---|---|---|---|---|
| s5_06494_01994_03994 | in sample | 0.283 → 0.004 | 0.381 → 0.514 | 0.96 → 1.34 | 12.66 → 17.41 (28.63) | 65.29 → **84.90** (59.43) |
| s5_06994_00994_04994 | in sample | 0.258 → 0.012 | 0.333 → 0.450 | 0.98 → 1.33 | 8.46 → 11.43 (19.66) | 42.72 → **62.60** (37.92) |
| s5_07994_01994_05494 | in sample | 0.263 → 0.004 | 0.342 → 0.430 | 1.16 → 1.53 | 9.33 → 11.65 (19.63) | 49.50 → **62.69** (43.69) |
| s3_00994_00494_01994 | held out | 0.256 → 0.074 | 0.541 → 0.643 | 1.43 → 1.75 | 29.48 → **34.65** (22.09) | 86.18 → **105.33** (30.86) |
| s3_00994_01994_00494 | held out | 0.263 → 0.035 | 0.512 → 0.649 | 1.10 → 1.39 | 32.70 → **42.08** (24.76) | 72.50 → **96.38** (35.66) |
| s3_00994_02494_01494 | held out | 0.357 → 0.088 | 0.442 → 0.571 | 1.05 → 1.42 | 22.87 → **29.60** (17.18) | 61.96 → **80.76** (24.35) |
| s3_01994_01494_00994 | held out | 0.345 → 0.071 | 0.442 → 0.578 | 1.00 → 1.32 | 23.69 → **32.12** (21.27) | 62.26 → **83.55** (33.24) |
| s3_01994_01994_01494 | held out | 0.321 → 0.062 | 0.462 → 0.597 | 1.05 → 1.41 | 24.65 → **32.06** (19.52) | 58.17 → **77.78** (28.95) |
| s3_02994_02494_01994 | held out | 0.266 → 0.011 | 0.518 → 0.674 | 1.15 → 1.52 | 33.64 → **41.50** (29.97) | 81.74 → **108.20** (42.63) |
| s3_03494_01494_00494 | held out | 0.306 → 0.053 | 0.461 → 0.611 | 0.83 → 1.13 | 25.96 → **35.03** (20.70) | 62.08 → **89.33** (25.67) |
| s3_04494_00994_01494 | held out | 0.273 → 0.039 | 0.498 → 0.623 | 1.18 → 1.50 | 21.35 → **26.25** (17.82) | 62.54 → **77.71** (25.91) |

**The registered predictions.** Each was judged on its own set.

| | Scroll 5 (in sample) | Scroll 3 (held out) |
|---|---|---|
| P1: fewer seeds dropped on every cube; in sample, below 0.05 | **held** (0.004–0.012) | **held** (0.011–0.088) |
| P2: coverage up on every cube, median ×1.15 or more | **held** (×1.26–1.35, median 1.35) | **held** (×1.19–1.33, median 1.29) |
| P3: the ranking against our tracer unchanged at both tolerances | **held** | **held** |
| P4: Scroll 3 below 0.10 on at least six of eight | | **held** (8 of 8) |

By the registered rule, both read: "on the 512³ cubes too the cube-only protocol held it back, by less: with real CT
around the cube it drops fewer seeds and covers more".

The registration estimated a median coverage factor of about 1.36 from finding 97. The medians are 1.35 and 1.29.

**Descriptive, no prediction:**
* **Traces:** it starts 1.40–1.58 times as many traces.
* **Merge-penalized ERL:** it rises 1.18–1.38× at tolerance 2 (median 1.29), and 1.22–1.47× at tolerance 4 (median
  1.32).
* **Precision:** essentially unchanged, 0.352–0.664 against 0.370–0.675.
* **Output:** 1.13–1.75 of the ground-truth length, against 0.83–1.43.
* **Against our tracer:**
  * at tolerance 2, on Scroll 5 its median ratio to our tracer rises from 0.44 to 0.59. On Scroll 3 it rises from
    1.26 to 1.61;
  * at tolerance 4, from 1.13 to 1.43 on Scroll 5, and from 2.22 to 2.85 on Scroll 3.
* **Scroll 3 keeps a small residual:** 0.011–0.088 of its seed dots, against 0.004–0.012 on Scroll 5. That is far
  below the 0.266 and 0.353 on finding 97's two held-out Scroll-5 cubes.

## What it means

* **With findings 97 and 98, every one of ScrollGT's 21 neural-tracer rows has been run with the scan around the
  cube.** Its coverage rises on all 21: 1.76–2.78× on the 256³ cubes, and 1.19–1.35× on the 512³ ones, where a seed
  window already fitted in more of the cube (0.618 against 0.348).
* **Against our tracer's published rows, given the scan around each cube:**
  * at tolerance 4 it leads on 19 of the 21 cubes, against 11 of 21 with the cube alone;
  * at tolerance 2 it leads on 10 of 21, against 8.

  The two it gains at tolerance 2 are finding 97's held-out Scroll-5 cubes. In sample it still trails at tolerance 2
  on every cube, at a median 0.59 of our tracer on the 512³ cubes and 0.60–0.65 on the 256³ ones.
* **The held-out residual of finding 97 is not what "held out" does in general.** Scroll 3 is held out from the
  reference mask too, yet drops at most 0.088. The two Scroll-5 cubes that keep a residual are also where the
  reference mask fails (finding 84). On Scroll 3, scroll and split cannot be told apart.

## What it does not say

* **Our tracer's rows are as published.** It labels the reference mask, which was also made from the cube alone. P3
  compares a padded neural tracer with an unpadded tracer of ours.
* **The presence is unchanged,** with zeros beyond the cube. The mask model was not re-run with context.
* **Eleven cubes, two scrolls.** On Scroll 3, scroll and split cannot be told apart.
* **One checkpoint, at its defaults.**
* **No ScrollGT change here.** Changing ScrollGT's protocol or rows is a separate decision by the owner.
