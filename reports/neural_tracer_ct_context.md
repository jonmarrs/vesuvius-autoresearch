# Finding 97: with real CT around each 256³ cube, villa's neural tracer keeps its seeds and about doubles its coverage (2026-10-23)

The result of `docs/preregistration/2026-10-23_neural_tracer_ct_context.md`. It was registered in #209, and amendment 1
(cb9bd1ab, #212), pushed at 20:29 PDT before any padded run, added the Scroll-1 cubes. Finding 96
(`neural_tracer_boundary.md`, exploratory) found that villa's neural tracer drops any seed whose 77-voxel CT window
crosses the edge of the CT it is given. ScrollGT's protocol gave it each cube alone. This run gave it 128 voxels of
the real scan around each of the ten 256³ cubes, the box still the cube, everything else as in finding 91.

**Answer: the cube-only protocol held it back.** Every registered prediction held, on both sets:
* **Seeds:** the share of seed dots it drops falls from 0.542–0.678 to 0.002–0.010 on the eight in-sample cubes, and
  from 0.695–0.696 to 0.266–0.353 on the two held-out ones;
* **Coverage:** it rises 1.76–2.78× on every cube;
* **Output:** on the eight in-sample cubes it is now 1.04–1.65 of the ground-truth length.

Against our tracer's published rows, it now leads on 8 of the 10 cubes at tolerance 4. At tolerance 2 it leads on the
two held-out cubes and still trails on all eight in-sample ones, by less than before.

## The run

* **Chain:** `repro/fibers/run_neural_tracer_ct_context_chain.sh` at cb9bd1ab, villa `ccb431818`, work directory
  `spiral_out/neural_tracer/ct_context_run`.
* **Timing:** the loop was stopped at 21:01 PDT on 2026-10-23, the runs went from 21:02:27 to 21:14:56, and the loop
  restarted at 21:14:56, before scoring.
* **Identity:**
  * every padded CT's 256³ core equals finding 85's array for the cube, voxel for voxel. Scroll 5 is read from its
    public raw zarr; Scroll 1 from its raw slices by byte range (`scripts/raw_tiff_region.py`);
  * every padded presence's core equals finding 91's level, with zeros outside;
  * the smoke, finding 91's own command on `s5_07997_02997_05497_256`, reproduced its `fibers.afv` point for point.
* **The manipulation took.**
  * Finding 91's closest traced seed lay 19.00 trace-grid voxels from a face on every cube. Here it lies 0 voxels
    from a face on eight cubes, and 1 and 2 on the two held-out ones.
  * The seed dots are the same as finding 91's on every cube (the presence is the same). What changed is how many
    get a heading.
* **Completeness:** all ten runs finished. The status is `OK` for the registered Scroll-5 five and for amendment 1's
  Scroll-1 five (`neural_tracer_ct_context.json`).
* **Scoring:** in each cube's frame, ScrollGT scoring version 3, at tolerances 2 and 4.

## Results

Before → after: finding 91's run (tolerance 2) or finding 94's re-score (tolerance 4) → the padded run. Our tracer's
published row is in parentheses. Bold: the padded run leads our tracer.

| cube | split | dropped as `no_heading` | coverage | output / ground truth | merge-penalized ERL, tolerance 2 (ours) | tolerance 4 (ours) |
|---|---|---|---|---|---|---|
| s5_03997_01497_03997 | in sample | 0.678 → 0.010 | 0.156 → 0.402 | 0.57 → 1.48 | 4.80 → 12.50 (20.75) | 21.10 → **47.44** (42.82) |
| s5_07997_02997_05497 | in sample | 0.605 → 0.004 | 0.235 → 0.456 | 0.61 → 1.37 | 7.82 → 14.64 (29.48) | 24.30 → 52.06 (56.52) |
| s5_14997_01497_01497 | in sample | 0.571 → 0.005 | 0.238 → 0.483 | 0.53 → 1.07 | 6.67 → 13.76 (19.94) | 23.09 → **40.37** (34.43) |
| s5_13497_01497_02497 | held out | 0.695 → 0.266 | 0.134 → 0.333 | 0.51 → 1.16 | 5.71 → **11.41** (10.17) | 13.83 → **25.07** (15.77) |
| s5_16997_03997_04497 | held out | 0.696 → 0.353 | 0.096 → 0.268 | 0.28 → 0.67 | 2.80 → **9.87** (4.71) | 7.70 → **21.80** (9.17) |
| s1_00497_01497_03997 | in sample | 0.577 → 0.010 | 0.212 → 0.382 | 0.78 → 1.65 | 5.20 → 10.03 (19.22) | 29.40 → **38.90** (36.39) |
| s1_00497_02497_02997 | in sample | 0.542 → 0.007 | 0.268 → 0.489 | 0.64 → 1.19 | 7.77 → 15.70 (21.76) | 23.47 → **43.95** (33.00) |
| s1_00997_02497_02997 | in sample | 0.561 → 0.002 | 0.242 → 0.425 | 0.68 → 1.30 | 8.62 → 11.80 (23.44) | 24.96 → 42.62 (42.68) |
| s1_08997_02997_02497 | in sample | 0.558 → 0.002 | 0.242 → 0.461 | 0.55 → 1.04 | 5.88 → 13.15 (20.29) | 25.29 → **43.94** (34.83) |
| s1_10997_02997_02997 | in sample | 0.607 → 0.006 | 0.263 → 0.517 | 0.71 → 1.47 | 11.64 → 20.49 (27.24) | 31.11 → **51.98** (49.72) |

**The registered predictions.** Each was judged on its own five cubes.

| | Scroll 5 (registered) | Scroll 1 (amendment 1) |
|---|---|---|
| P1: dropped share below 0.40 on all five | **held** (0.004–0.353) | **held** (0.002–0.010) |
| P2: coverage up on all five, median ×1.3 or more | **held** (×1.94–2.78, median 2.49) | **held** (×1.76–1.97, median 1.82) |
| P3: in-sample output at least 0.83 of ground truth | **held** (1.07–1.48) | **held** (1.04–1.65) |

By the registered rule, both read: "the cube-only protocol held the neural tracer back on these cubes: with real CT
around the cube it drops fewer seeds and covers more".

**Descriptive, no prediction:**
* **Traces:** it starts 2.1–3.2 times as many traces.
* **Merge-penalized ERL:** it rises 1.37–3.52× at tolerance 2 (median 2.01), and 1.32–2.83× at tolerance 4 (median
  1.78).
* **Precision:** essentially unchanged, 0.289–0.576 against 0.320–0.566.
* **Against our tracer:**
  * at tolerance 4, it leads on 8 of 10. It trails on `s5_07997_02997_05497` (52.06 against 56.52) and
    `s1_00997_02497_02997` (42.62 against 42.68);
  * at tolerance 2, it trails on all eight in-sample cubes. Its median ratio to our tracer rises from 0.27 to 0.60 on
    Scroll 5's three, and from 0.36 to 0.65 on Scroll 1's five. It leads on both held-out cubes (1.12× and 2.10×).
* **The two held-out cubes still drop 0.266 and 0.353 of their seed dots.** That is not the window rule: the padding
  reaches 64 trace-grid voxels beyond each face, past any window's 19-voxel reach from inside the box. Its cause is
  untested. These are the two cubes where the reference mask also fails (finding 84).

## What it means

* **ScrollGT's neural-tracer rows on the 256³ cubes understate the tool as it would run on a scroll.** Given the scan
  around the cube, its coverage is 1.76–2.78 times its published row on all ten. On 8 of 10 it then leads our tracer
  at tolerance 4.
* **What remains in sample is mostly a tolerance-2 gap.** At tolerance 2 it reaches a median 0.60–0.65 of our
  tracer on the in-sample cubes, and at tolerance 4 it leads on 6 of the 8. Finding 94 and #157 found that kind of
  gap on the 512³ cubes. There, thin centrelines lie 2–4 voxels from the ground truth more often, and on 5 of the 11
  in-sample cubes the ground truth sits about a voxel off the CT.
* **On Scroll 1, its own training scroll, it now leads at tolerance 4 on 4 of the 5 cubes.** At tolerance 2 it still
  trails on all five, at a median 0.65 of our tracer rather than 0.36.

## What it does not say

* **Our tracer's rows are as published.** It labels the reference mask, which was also made from the cube alone.
  Finding 96 found no deficit near the faces in its labels (64.5% of them within 38 voxels of a face, against 65.2% of
  the volume), so context is not expected to move it much. That is untested.
* **The presence is unchanged,** with zeros beyond the cube. The mask model was not re-run with context.
* **Ten cubes, two scrolls, all 256³.** The 512³ cubes, which lose one seed plane in four rather than half, were not
  re-run, so neither was Scroll 3.
* **One checkpoint, at its defaults.**
* **No ScrollGT change.** Changing ScrollGT's protocol or rows is a separate decision by the owner.
