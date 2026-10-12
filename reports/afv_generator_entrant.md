# villa PR #1934's automated fiber generator, scored against hand-traced fibers: it finds a quarter of the fiber, and ScrollGT's ERL flattered it

**2026-10-11.** Result of `docs/preregistration/2026-10-11_afv_generator_entrant.md` (pre-registration `c5b3d6ae`, before
the generator ran on any cube). The user approved running the PR's code on 2026-10-11. The chain is
`repro/fibers/run_afv_generator_chain.sh`; the registered analysis wrote `reports/afv_generator_entrant.json` (status
`OK`). The post-hoc control and re-normalisation are `scripts/erl_coverage_conditioning.py` →
`reports/erl_coverage_conditioning.json`, not registered.

**Entrant.** villa PR #1934 (Qualzz, open) at `2d8577ed`, `vesuvius.afv_spline_generator` with model
`Qualzz20/afv_fiber_9um` at revision `e189af75`, every default:
* threshold 60%, block 512, minimum length 100 voxels;
* black distance 16, join angle 45°;
* no `--extend`, no `--mirror`.

It ran on all 21 ScrollGT fiber cubes at 7.91 µm with no failures. The identity check passed: every `.afv` records this
revision and these settings. Scored with ScrollGT, fiber scoring version 2, tolerance 2.0.

## Registered predictions

* **P1 FAILED.** Its raw ERL is above our tracer's on 5 of the 11 in-sample targets, not the 9 predicted.
* **P2 held.** Its coverage is below the tracer's on 11 of 11 in-sample targets (0.188–0.357, against 0.560–0.675).
* **P3 held.** Connected components' raw ERL is above the generator's on all 8 in-sample 256³ targets.
* **P4 held.** On Scroll 3 its merge-penalized ERL is above the tracer's on 8 of 8.
* **P5 held, narrowly.** Its median coverage on Scroll 3 (0.259) is below its in-sample 512³ median (0.279).

## Results

`gen`: the generator. `tr`: our tracer. The last three columns are ground-truth-normalised merge-penalized ERL (below).

| cube | split | gen ERL | gen ERLpen | gen coverage | gen precision | gen merges | gen fibers | tr ERL | tr ERLpen | tr coverage | gen ERLpen×cov | tr ERLpen×cov | cc ERLpen×cov |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s1_00497_01497_03997 | in sample | 36.07 | 32.19 | 0.230 | 0.490 | 8 | 54 | 35.39 | 30.85 | 0.623 | 7.40 | 19.22 | 34.04 |
| s1_00497_02497_02997 | in sample | 59.86 | 42.10 | 0.268 | 0.637 | 11 | 64 | 52.39 | 35.46 | 0.614 | 11.29 | 21.76 | 37.19 |
| s1_00997_02497_02997 | in sample | 52.88 | 42.81 | 0.284 | 0.505 | 11 | 79 | 48.82 | 38.72 | 0.605 | 12.15 | 23.44 | 50.02 |
| s1_08997_02997_02497 | in sample | 34.69 | 29.37 | 0.205 | 0.658 | 16 | 60 | 44.97 | 36.25 | 0.560 | 6.04 | 20.29 | 47.91 |
| s1_10997_02997_02997 | in sample | 48.96 | 48.09 | 0.357 | 0.479 | 4 | 73 | 48.17 | 44.19 | 0.616 | 17.18 | 27.24 | 49.80 |
| s5_03997_01497_03997 | in sample | 28.53 | 28.53 | 0.265 | 0.381 | 0 | 51 | 40.45 | 33.30 | 0.623 | 7.55 | 20.76 | 46.94 |
| s5_06494_01994_03994 | in sample | 42.33 | 37.53 | 0.355 | 0.562 | 60 | 544 | 53.40 | 42.63 | 0.672 | 13.32 | 28.63 | 13.85 |
| s5_06994_00994_04994 | in sample | 35.60 | 30.00 | 0.223 | 0.543 | 90 | 579 | 42.65 | 34.14 | 0.576 | 6.69 | 19.66 | 8.58 |
| s5_07994_01994_05494 | in sample | 33.87 | 27.85 | 0.279 | 0.437 | 63 | 621 | 41.42 | 34.18 | 0.574 | 7.77 | 19.63 | 14.00 |
| s5_07997_02997_05497 | in sample | 50.06 | 48.25 | 0.282 | 0.456 | 2 | 53 | 48.00 | 43.65 | 0.675 | 13.60 | 29.49 | 79.76 |
| s5_14997_01497_01497 | in sample | 41.99 | 33.49 | 0.188 | 0.675 | 11 | 59 | 44.96 | 33.62 | 0.593 | 6.29 | 19.94 | 19.88 |
| s3_00994_00494_01994 | held out, Scroll 3 | 75.01 | 68.44 | 0.277 | 0.699 | 35 | 494 | 49.25 | 41.46 | 0.533 | 18.96 | 22.09 | 15.26 |
| s3_00994_01994_00494 | held out, Scroll 3 | 75.61 | 68.70 | 0.253 | 0.746 | 46 | 531 | 56.01 | 44.90 | 0.551 | 17.37 | 24.76 | 23.81 |
| s3_00994_02494_01494 | held out, Scroll 3 | 71.07 | 58.73 | 0.264 | 0.722 | 53 | 600 | 44.02 | 34.38 | 0.500 | 15.49 | 17.18 | 6.24 |
| s3_01994_01494_00994 | held out, Scroll 3 | 66.74 | 65.49 | 0.237 | 0.762 | 11 | 337 | 43.77 | 38.60 | 0.551 | 15.53 | 21.27 | 15.47 |
| s3_01994_01994_01494 | held out, Scroll 3 | 77.84 | 70.44 | 0.254 | 0.779 | 35 | 378 | 41.54 | 33.52 | 0.582 | 17.87 | 19.52 | 12.99 |
| s3_02994_02494_01994 | held out, Scroll 3 | 88.65 | 79.63 | 0.380 | 0.726 | 59 | 665 | 58.94 | 46.90 | 0.639 | 30.28 | 29.97 | 14.83 |
| s3_03494_01494_00494 | held out, Scroll 3 | 68.31 | 59.15 | 0.223 | 0.802 | 70 | 503 | 56.55 | 41.24 | 0.502 | 13.19 | 20.70 | 25.93 |
| s3_04494_00994_01494 | held out, Scroll 3 | 63.82 | 54.15 | 0.287 | 0.736 | 72 | 563 | 41.96 | 30.96 | 0.576 | 15.53 | 17.82 | 8.58 |
| s5_13497_01497_02497 | held out, Scroll 5 | 74.05 | 52.17 | 0.041 | 0.777 | 2 | 10 | 29.29 | 26.89 | 0.378 | 2.16 | 10.17 | 4.73 |
| s5_16997_03997_04497 | held out, Scroll 5 | 54.64 | 40.27 | 0.075 | 0.772 | 7 | 27 | 26.30 | 18.49 | 0.255 | 3.02 | 4.71 | 3.76 |

Precision is not compared with the tracer or connected components. A thin centreline and a mask-thick labelling differ
in precision by construction (registered).

## Post hoc: ScrollGT's ERL is conditional on coverage, and that decides P4

ScrollGT computes ERL as Σr²/Σr over the runs a labelling covers. Fiber it misses never enters the denominator. So
deleting any run shorter than the current ERL *raises* the score, and the generator deletes every chain under 100
voxels by design.

**Control on a real labelling.** Take our tracer on `s1_00497_01497_03997` and delete its instances under N voxels.
Unfiltered, it reproduces the published row exactly.

| deleted below | instances | ERL | ERLpen | coverage | ERL×coverage | ERLpen×coverage |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 669 | 35.39 | 30.85 | 0.6231 | 22.05 | 19.22 |
| 100 | 570 | 36.16 | 31.44 | 0.6106 | 22.08 | 19.20 |
| 200 | 321 | 38.84 | 33.38 | 0.5248 | 20.38 | 17.52 |
| 400 | 138 | 41.46 | 34.95 | 0.3759 | 15.58 | 13.14 |

Throwing away 80% of its own instances lifts ScrollGT's ERL by 17% and its merge-penalized ERL by 13%, while coverage
falls from 0.62 to 0.38. Normalising by ground-truth length instead gives the expected run length of a point drawn
uniformly from the hand-traced fibers, with missed points as zero-length runs. Because Σr is the covered length, that
is exactly ERL × coverage. It falls as it should.

**Re-normalised, the generator trails the tracer almost everywhere:**
* raw ERL×coverage: below the tracer on 21 of 21 cubes;
* merge-penalized ERL×coverage: below on 20 of 21. The exception is `s3_02994_02494_01994`, 30.28 against 29.97.

P4 held on ScrollGT's metric as registered, and the verdict stands as registered. But the lead it records comes from
the generator covering about half as much fiber as the tracer, not from following fibers better.

The same re-normalisation touches ScrollGT's own published comparisons. Our tracer's lead over connected components on
merge-penalized ERL survives on the four in-sample cubes, `s5_14997_01497_01497` by 19.94 against 19.88. On the ten
held-out cubes it survives on 9: `s3_03494_01494_00494` reverses, 20.70 against 25.93.

## What it means

* **For the generator's author and #1932's reviewers.** At its defaults, on Scrolls 1, 3 and 5 at 7.91 µm, the
  generator's fibers cover 19–38% of the hand-traced fiber length. What they cover is fairly clean: few merges at 256³,
  precision 0.38–0.80 for a thin centreline.
  * It does not generalise to the two new Scroll-5 cubes: 4% and 8% coverage, 10 and 27 fibers. Its base model,
    `fiber_hz_vt`, misses a fifth of their fiber outright (finding 84), and the fine-tune does not recover it.
  * Coverage is the gap, not run length. The settings that trade coverage away (60% threshold, 100-voxel minimum
    length) are the first thing to test. `--extend` was not tested.
* **For ScrollGT.** Its headline ERL rewards deleting short fragments, an exploit the gaming tests do not cover.
  Reporting ERL×coverage (or replacing the headline with it) closes that. This is a scorer change, so it should land in
  ScrollGT first, versioned and with a notice, as the edge-order fix did.

## Limits

* One model revision and one setting (defaults). The cubes are at 7.91 µm, below the model's 8.64–9.36 µm training
  range.
* In-sample rows are optimistic for the generator: its base model trained on those cubes.
* The re-normalisation is post hoc. Every number in it is a product of registered outputs (ERL, coverage). The control
  is one cube.
* Nothing here is posted to villa or added to ScrollGT without a separate decision by the user.
