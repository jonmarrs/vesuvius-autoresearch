# Finding 91: villa's neural fiber tracer against hand-traced fibers — the best entrant on Scroll 3, behind on every other cube

**2026-10-16.** This is the result of `docs/preregistration/2026-10-16_neural_fiber_tracer_entrant.md`:
* registered at `8a0d033f`, amended at `baa7e917`, both before any cube ran;
* chain `repro/fibers/run_neural_tracer_chain.sh` at `c3f2693e`;
* the registered analysis wrote `reports/neural_tracer_entrant.json` with status `OK`;
* all 21 cubes and both repeats finished (14:09–14:57, loop paused), and every `run.json` passed the identity check.

The synthetic smoke run came first (`reports/neural_tracer_smoke.json`: 11 fibers, 76 s, identity clean). It changed
nothing registered.

**Entrant.**
* villa #2045's `vesuvius.neural_tracing.tracers.fibers.tracing.volume` at villa `ccb431818`;
* checkpoint `scrollprize/fiber_single_small` at `4511825`, with both files matching the registered sha256;
* every default, plus the four flags that read a 7.91 µm cube on a 2-voxel grid;
* fiber_hz_vt's probability as its presence.

Scored by ScrollGT 0.7.0, fiber scoring version 3 (run lengths over ground-truth length), at tolerance 2.0.

## Registered predictions: all four held

* **P1 held.** On Scroll 3 its merge-penalized ERL is above #1934's generator on **8 of 8** cubes.
* **P2 held.** On Scroll 3 it is above our tracer's on **8 of 8**, by 1.11–1.33×. It is also above connected
  components on 8 of 8.
* **P3 held.** On Scroll 3 its coverage is below our tracer's on **7 of 8**. The exception is
  `s3_00994_00494_01994`, 0.5414 against 0.5328.
* **P4 held.** On the two held-out Scroll-5 cubes its coverage, 0.134 and 0.096, is below its Scroll-3 median of 0.480.

## Results

`pen`: merge-penalized ERL (scoring version 3); `cov`: coverage. Comparators are ScrollGT's published rows (connected
components, our tracer), and #1934's generator re-scored from finding 85's `.afv` files.

| cube | for the mask | tracer pen | tracer cov | merges | fibers | our tracer pen | our cov | generator pen | generator cov | CC pen |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s1_00497_01497_03997 | in sample | 5.20 | 0.212 | 9 | 119 | 19.22 | 0.623 | 7.41 | 0.230 | 34.04 |
| s1_00497_02497_02997 | in sample | 7.77 | 0.268 | 20 | 122 | 21.76 | 0.614 | 11.29 | 0.268 | 37.19 |
| s1_00997_02497_02997 | in sample | 8.62 | 0.242 | 16 | 124 | 23.44 | 0.605 | 12.14 | 0.284 | 50.02 |
| s1_08997_02997_02497 | in sample | 5.88 | 0.242 | 11 | 120 | 20.29 | 0.560 | 6.04 | 0.205 | 47.92 |
| s1_10997_02997_02997 | in sample | 11.64 | 0.263 | 2 | 104 | 27.24 | 0.616 | 17.18 | 0.357 | 49.80 |
| s5_03997_01497_03997 | in sample | 4.80 | 0.156 | 0 | 66 | 20.75 | 0.623 | 7.55 | 0.265 | 46.95 |
| s5_07997_02997_05497 | in sample | 7.82 | 0.235 | 1 | 80 | 29.48 | 0.675 | 13.60 | 0.282 | 79.76 |
| s5_14997_01497_01497 | in sample | 6.67 | 0.238 | 22 | 131 | 19.94 | 0.593 | 6.29 | 0.188 | 19.88 |
| s5_06494_01994_03994 | in sample | 12.66 | 0.381 | 101 | 961 | 28.63 | 0.672 | 13.32 | 0.355 | 13.85 |
| s5_06994_00994_04994 | in sample | 8.46 | 0.333 | 210 | 1345 | 19.66 | 0.576 | 6.69 | 0.223 | 8.57 |
| s5_07994_01994_05494 | in sample | 9.33 | 0.342 | 126 | 1115 | 19.63 | 0.574 | 7.77 | 0.279 | 14.00 |
| s3_00994_00494_01994 | held out | 29.48 | 0.541 | 165 | 1374 | 22.09 | 0.533 | 18.95 | 0.277 | 15.26 |
| s3_00994_01994_00494 | held out | 32.70 | 0.512 | 199 | 1310 | 24.76 | 0.551 | 17.37 | 0.253 | 23.81 |
| s3_00994_02494_01494 | held out | 22.87 | 0.442 | 205 | 1345 | 17.18 | 0.500 | 15.49 | 0.264 | 6.24 |
| s3_01994_01494_00994 | held out | 23.69 | 0.442 | 91 | 1075 | 21.27 | 0.551 | 15.52 | 0.237 | 15.48 |
| s3_01994_01994_01494 | held out | 24.65 | 0.462 | 152 | 1183 | 19.52 | 0.582 | 17.87 | 0.254 | 12.99 |
| s3_02994_02494_01994 | held out | 33.64 | 0.518 | 130 | 1274 | 29.97 | 0.639 | 30.28 | 0.380 | 14.83 |
| s3_03494_01494_00494 | held out | 25.96 | 0.461 | 248 | 1232 | 20.70 | 0.502 | 13.19 | 0.223 | 25.93 |
| s3_04494_00994_01494 | held out | 21.35 | 0.498 | 233 | 1370 | 17.82 | 0.576 | 15.53 | 0.287 | 8.58 |
| s5_13497_01497_02497 | held out | 5.71 | 0.134 | 7 | 89 | 10.17 | 0.378 | 2.16 | 0.041 | 4.73 |
| s5_16997_03997_04497 | held out | 2.80 | 0.096 | 14 | 80 | 4.71 | 0.255 | 3.02 | 0.075 | 3.76 |

Medians by group (merge-penalized ERL / coverage):

| group | neural tracer | our tracer | #1934 generator |
|---|---|---|---|
| Scroll 3, 8 cubes | 25.30 / 0.480 | 20.98 / 0.551 | 16.45 / 0.259 |
| in sample for the mask, 11 cubes | 7.82 / 0.242 | 20.75 / 0.614 | 7.77 / 0.268 |
| held-out Scroll 5, 2 cubes | 4.25 / 0.115 | 7.44 / 0.317 | 2.59 / 0.058 |

## Descriptive, as registered

* **The runs are deterministic.** Both repeated cubes (`s3_00994_00494_01994`, `s1_00497_01497_03997`) reproduce
  their first run exactly: 0 difference in ERL, merge-penalized ERL, coverage, merges and instance count. The
  repeatability floor is zero.
* **Stop reasons.** The 21 runs record 17,859 `confidence` stops, 11,287 `owned_or_live` and 92 `bounds`. There are
  **0 `outside` stops**, so the zero voxels in 13 cubes (amendment 1) never stopped a trace.
* **At tolerance 4.0** (the tracer's own label tolerance) its median coverage is 0.612 on Scroll 3 and 0.376 on the
  in-sample cubes.
* **Precision, among thin entrants.** Its median on Scroll 3 is 0.564, against the generator's 0.741.

## What it means

* **For villa's tracer: it is the best entrant ScrollGT has on Scroll 3, a scroll none of the entrants trained on.**
  Its runs there are longer, merge-penalized ERL 1.11–1.33× our tracer's. Coverage is slightly lower: a median
  0.480 against 0.551.
* **It is weak everywhere else, including Scroll 1, its own training scroll.**
  * On the 11 cubes where the reference mask trained (Scrolls 1 and 5) it trails our tracer on all 11: median 7.82
    against 20.75.
  * On the two held-out Scroll-5 cubes it also trails, though it beats the generator on one.
* **Why the scrolls differ is not established.** These candidates are untested:
  * The scan. Its Scroll 1 data is the 2026 2.4 µm rescan read at 9.6 µm, while these cubes come from the older
    7.91 µm scan.
  * The scale. 7.91 µm is finer than any of its sources.
  * The cube size. Ten of these 13 cubes are 256³; the three 512³ in-sample cubes are also low, at 8.46–12.66.
  * Annotation style per scroll.

  The comparison on the in-sample cubes is also tilted towards our tracer and connected components, which are built
  from the mask itself. Those cubes are where the mask is strongest.
* **For ScrollGT:** the scroll dependence is the finding a single-scroll benchmark would miss. On Scroll 3, scoring
  version 3 ranks this tracer first on merge-penalized ERL with 42% less coverage than connected
  components (median 0.480 against 0.826). The headline is run length, not recall.

## Limits

* **One checkpoint, volume mode, defaults.** VC3D's seed mode is not tested.
* **The presence is a substitute** (fiber_hz_vt, not lasagna), and on the two held-out Scroll-5 cubes it misses a
  fifth of the fiber outright (finding 84).
* **7.91 µm and 256³ edges**, as registered.
* **One run per cube.** The runs are deterministic, so a second run adds nothing, but another sampling seed or GPU
  could change them.
* **Nothing is posted to villa or added to ScrollGT** without a separate decision by the user.
