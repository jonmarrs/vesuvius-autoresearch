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
  **0 `outside_ct` stops**: no written fiber ended on the zero voxels in 13 cubes (amendment 1). (Corrected
  2026-10-17: this said the zero voxels never stopped a trace. The `.afv` records stop reasons only for written
  fibers, two per fiber; a trace dropped as short or as a duplicate leaves none there. Each run's `tiles.jsonl`
  counts `stop_outside_ct` for every trace, and is not in this repository.)
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
  from the mask itself. Those cubes are where the mask is strongest. (Exploratory, 2026-10-19, in the last section:
  most of the Scroll-3 advantage is where centrelines sit within 2–4 voxels of the GT. #1934's generator shares it,
  and a shift between the GT and the CT or the GT's node spacing do not explain it. Review, 2026-10-20: the shift
  test there can miss a shift along the fibers most of a cube's samples lie on. Measured the same day: on 5 of the
  11 in-sample cubes the GT sits about a voxel off the CT's fibers, which explains part of their gap.)
* **For ScrollGT:** the scroll dependence is the finding a single-scroll benchmark would miss. On Scroll 3, scoring
  version 3 ranks this tracer first on merge-penalized ERL with 42% less coverage than connected
  components (median 0.480 against 0.826). The headline is run length, not recall.

## Limits

* **One checkpoint, volume mode, defaults.** VC3D's seed mode is not tested.
* **The presence is a substitute** (fiber_hz_vt, not lasagna), and on the two held-out Scroll-5 cubes it misses a
  fifth of the fiber outright (finding 84).
* **7.91 µm and 256³ edges**, as registered. (Measured 2026-10-19, finding 92, `neural_tracer_pitch.md`: resampled to
  its 9.6 µm training pitch it scores lower on all 21 cubes, median 0.63 of these rows, and leads our tracer on none
  of the Scroll-3 cubes.)
* **One run per cube.** The runs are deterministic, so a second run adds nothing, but another sampling seed or GPU
  could change them.
* **Nothing is posted to villa or added to ScrollGT** without a separate decision by the user. (Update 2026-10-19: on
  the user's decision, ScrollGT 0.8.0, scrollgt#6, publishes these rows as `villa_neural_tracer`. All 21 equal this
  report's, field for field. Nothing is posted to villa.)

## Exploratory, after finding 92: what the Scroll-3 lead is made of

Not registered. Read on 2026-10-19 from this report's rows (`neural_tracer_entrant.json`, which also holds #1934's
generator and the descriptive tolerance-4 scores), and from where the two thin entrants' centrelines sit relative to
the GT (`scripts/neural_tracer_placement.py`, `neural_tracer_placement.json`).

**On the 512³ cubes, only the thin entrants gain on Scroll 3.** Medians of merge-penalized ERL. The in-sample 512³
cubes are Scroll 5's three, the same size as Scroll 3's:

| entrant | Scroll 3 | in-sample 512³ | ratio | ratio at tolerance 4 |
|---|---:|---:|---:|---:|
| this tracer | 25.30 | 9.33 | 2.71 | 1.26 |
| #1934's generator | 16.45 | 7.77 | 2.12 | 0.81 |
| our tracer | 20.98 | 19.66 | 1.07 | not scored |
| connected components | 15.04 | 13.85 | 1.09 | not scored |

* **Both thin entrants gain, and the two built from the mask do not.** For this tracer every Scroll-3 cube scores
  above every in-sample 512³ one (exact two-sided rank test, p 0.012, the smallest 8 cubes against 3 allow). The mask
  covers both about equally: connected components' coverage is 0.826 against 0.822.
* **At tolerance 4 most of the gain goes.** This tracer's ratio falls from 2.71 to 1.26 (coverage 1.40 to 1.04,
  precision 1.34 to 1.00), and the generator's from 2.12 to 0.81. On those Scroll-5 cubes both find the fibers, but
  lay their centrelines 2–4 voxels from the GT more often.
* **Measured directly:** of the centreline samples within 6 voxels of the GT, the share within 2 is 0.68–0.76 on
  Scroll 3 against 0.43–0.61 on the 11 in-sample cubes for this tracer, and 0.77–0.84 against 0.43–0.67 for the
  generator. For both, every Scroll-3 cube is above every in-sample one.
* **Not a shift between the GT and the CT.** The median displacement from centreline to GT is at most 0.62 voxels
  along any axis, on every cube, for both entrants. (Review, 2026-10-20: this does not exclude every shift.
  * The displacement to the nearest GT point is perpendicular to the fiber, so a shift along a fiber does not show on
    it. Where most of a cube's matched samples lie on fibers along one axis, the median along that axis misses a shift
    there.
  * With three fibers along z and one across it, a 2.5-voxel z shift puts a quarter of the samples beyond 2 voxels and
    leaves the median z displacement at 0 (`tests/test_neural_tracer_placement.py`).
  * The script now also records `median_disp_perp_zyx`: the median along each axis over samples on fibers within 30°
    of perpendicular to it, which keep at least 3/4 of a shift. A shift along another axis can move it by up to 0.43
    of that shift, as it can the plain median.
  * The committed JSON predated it. It was re-run on 2026-10-20: see the next bullet.)
* **But the GT sits about a voxel off the CT's fibers on 5 in-sample cubes, which explains part of their gap.**
  Measured on 2026-10-20 (`scripts/neural_tracer_gt_offset.py`, `neural_tracer_gt_offset.json`). Exploratory, and the
  cut at 1 voxel was chosen after seeing the values.
  * On 5 of the 11 in-sample cubes, the two entrants' shifts (`median_disp_perp_zyx`) agree in sign wherever either
    reaches 0.5 voxels. Their mean is 1.01–1.53 voxels long there. On every Scroll-3 cube it is at most 0.72, and on
    the other in-sample cubes at most 0.78.
  * Moving this tracer's centreline by the generator's shift, which this tracer's data did not inform, raises its
    share within 2 voxels by 0.06–0.09 on those 5 cubes, against 0.004–0.017 on Scroll 3. The opposite shift lowers
    it by 0.16–0.23. The generator, moved by this tracer's shift, gains 0.05–0.10 there.
  * The CT alone, smoothed at sigma 1, is brightest 0.5–0.75 of the way from the GT towards the entrants' centre on
    all 5. It puts the fibers' centres 0.51–0.93 voxels off the GT in the same direction, though the gain in
    brightness is small (0.11–1.06 grey levels).
  * Corrected, this tracer's shares on those cubes (0.52–0.66) still trail Scroll 3's (0.68–0.76). The offset is part
    of the in-sample gap, not all of it. The scores here are against the GT as published, and correcting ScrollGT's
    GT would be the owner's decision.
* **Not the GT's node spacing.** Scroll 3's annotators placed nodes about twice as densely (a median edge of 6.5
  voxels against 12.4). Straight edges between sparse nodes could put a centre-following tracer off the GT mid-edge.
  But within a cube, samples at an annotator's node are within 2 voxels a median of only 0.04 more often than mid-edge
  ones. The in-sample cubes trail even at the nodes, 0.46–0.62 against 0.69–0.77 for this tracer. And
  `s1_08997_02997_02497` has Scroll 3's node spacing (5.1 voxels) with an in-sample share (0.57).
* **What remains, untested:** how precisely each scroll's annotators centred their nodes, how sharply each scan shows a
  fiber's centre, and fiber width. (Review, 2026-10-20: and a shift along the fibers. Measured, a shift of about a
  voxel explains part of the gap on 5 cubes, above.) The two held-out Scroll-5
  cubes do not separate these. The generator's centrelines sit there as on Scroll 3 (0.88 and 0.78), this tracer's
  as on the in-sample cubes (0.55 and 0.54).
* **For ScrollGT:** at its tolerance of 2 voxels, a thin entrant's scores across scrolls turn on placement within 2–4
  voxels. The published Scroll-3 lead is a tolerance-2 result. Whether it holds at 4 is not measured, because our
  tracer and connected components were not rescored there.
