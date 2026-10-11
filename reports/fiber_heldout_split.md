# ScrollGT's fiber mask keeps its recall on Scroll 3, a scroll it never saw, and loses it on two new Scroll-5 cubes

**2026-10-11.** Result of `docs/preregistration/2026-10-11_fiber_heldout_split.md` (pre-registration `8a7b2d4f`, before
any held-out cube was run). The chain ran at that commit. Data: `reports/fiber_heldout_split.json`, written by the
registered analysis `scripts/fiber_heldout_analysis.py`. In-sample rows: `reports/fiber_heldout_in_sample_rows.json`,
ScrollGT 0.5.0 (`af4ab23b`). Post-hoc diagnostic: `reports/fiber_heldout_mask_vs_label.json`
(`scripts/fiber_mask_vs_label.py`).

**Question.** Finding 82 found that `fiber_hz_vt`, ScrollGT's reference mask and our tracer's semantic layer, trained on
all 11 ScrollGT fiber targets. villa's Dataset004 holds 10 annotated cubes it never trained on: eight from Scroll 3 at
512³, a scroll it never saw, and two new Scroll-5 cubes at 256³. Does the mask's recall hold on them, and does the
tracer's standing against connected components?

## Gate: all 10 pass

Every NML node lands on villa's semantic label (1.000000 on all 10). Nodes land on the P ≥ 0.5 mask at 6.44–13.18× its
density, above the gate of 5×. No cube is excluded.

## Results (fiber scoring version 2, tolerance 2.0)

| cube | fibers | mask density | enrichment | oracle ERL | cc coverage | cc precision | cc ERL | cc ERLpen | cc merges |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s5_13497_01497_02497 | 166 | 0.0678 | 7.45 | 205.49 | 0.6427 | 0.1420 | 82.92 | 7.36 | 142 |
| s5_16997_03997_04497 | 282 | 0.0670 | 6.44 | 201.34 | 0.5291 | 0.1774 | 78.18 | 7.10 | 265 |
| s3_00994_00494_01994 | 649 | 0.0712 | 10.18 | 496.71 | 0.8096 | 0.2058 | 231.49 | 18.85 | 600 |
| s3_00994_01994_00494 | 728 | 0.0613 | 11.65 | 524.89 | 0.8097 | 0.2938 | 247.60 | 29.41 | 677 |
| s3_00994_02494_01494 | 656 | 0.0760 | 8.99 | 561.99 | 0.7938 | 0.2333 | 221.46 | 7.86 | 695 |
| s3_01994_01494_00994 | 637 | 0.0699 | 10.87 | 445.11 | 0.8424 | 0.1913 | 232.24 | 18.37 | 572 |
| s3_01994_01994_01494 | 718 | 0.0728 | 10.64 | 388.83 | 0.8626 | 0.1988 | 223.05 | 15.06 | 635 |
| s3_02994_02494_01994 | 602 | 0.0599 | 13.18 | 502.18 | 0.8677 | 0.3014 | 307.42 | 17.09 | 554 |
| s3_03494_01494_00494 | 741 | 0.0634 | 10.13 | 533.99 | 0.7694 | 0.2986 | 205.87 | 33.70 | 981 |
| s3_04494_00994_01494 | 665 | 0.0696 | 10.97 | 479.98 | 0.8573 | 0.2580 | 247.61 | 10.01 | 620 |

| cube | tracer ERL | tracer ERLpen | tracer coverage | tracer precision | tracer merges |
|---|---:|---:|---:|---:|---:|
| s5_13497_01497_02497 | 29.29 | 26.89 | 0.3783 | 0.1904 | 40 |
| s5_16997_03997_04497 | 26.30 | 18.49 | 0.2549 | 0.2153 | 92 |
| s3_00994_00494_01994 | 49.25 | 41.46 | 0.5328 | 0.2700 | 301 |
| s3_00994_01994_00494 | 56.01 | 44.90 | 0.5515 | 0.3539 | 493 |
| s3_00994_02494_01494 | 44.02 | 34.38 | 0.4998 | 0.2863 | 556 |
| s3_01994_01494_00994 | 43.77 | 38.60 | 0.5510 | 0.2412 | 215 |
| s3_01994_01994_01494 | 41.54 | 33.52 | 0.5823 | 0.2440 | 349 |
| s3_02994_02494_01994 | 58.94 | 46.90 | 0.6390 | 0.3482 | 461 |
| s3_03494_01494_00494 | 56.55 | 41.24 | 0.5020 | 0.3884 | 602 |
| s3_04494_00994_01494 | 41.96 | 30.96 | 0.5756 | 0.3064 | 563 |

Against the in-sample targets on the current annotations, by size class:

| quantity | in-sample 512³ (Scroll 5, 3) | held-out Scroll 3 (512³, 8) | in-sample 256³ (Scroll 1 and 5, 8) | held-out Scroll 5 (256³, 2) |
|---|---|---|---|---|
| cc coverage | 0.8130–0.8882 | 0.7694–0.8677 | 0.7617–0.9177 | 0.5291, 0.6427 |
| tracer coverage | 0.5742–0.6716 | 0.4998–0.6390 | 0.5598–0.6755 | 0.2549, 0.3783 |
| mask enrichment | 9.95–14.70 | 8.99–13.18 | 13.45–21.54 | 6.44, 7.45 |
| mask density | 0.0503–0.0640 | 0.0599–0.0760 | 0.0369–0.0599 | 0.0670, 0.0678 |
| cc precision | 0.2323–0.2794 | 0.1913–0.3014 | 0.1863–0.3612 | 0.1420, 0.1774 |
| oracle ERL | 491.18–507.25 | 388.83–561.99 | 228.92–250.55 | 201.34, 205.49 |
| cc ERL ÷ tracer ERL | 5.75–6.25 | 3.64–5.90 | 3.75–5.66 | 2.83, 2.97 |
| tracer ERLpen ÷ cc ERLpen | 2.01–3.24 | 1.22–4.37 | 0.50–1.38 | 2.60, 3.65 |
| mask voxel recall of villa's label (post hoc) | 0.5909–0.7227 | 0.5538–0.6848 | 0.5832–0.7703 | 0.3361, 0.4363 |

* **P1 FAILED.** The median connected-components coverage over the eight Scroll-3 cubes is 0.826, not below 0.8130. The
  in-sample 512³ median is 0.822.
* **P2 HELD.** Both new Scroll-5 cubes are below 0.8666: 0.6427 and 0.5291.
* **P3 HELD, 10 of 10.** Connected components leads the tracer on raw ERL by 3.64–5.90× on Scroll 3 and 2.83–2.97× on
  the two Scroll-5 cubes.
* **P4 HELD, 8 of 8.** On every Scroll-3 cube the tracer's merge-penalized ERL is above connected components', by
  1.22–4.37×.

**Descriptive:**
* **The two new Scroll-5 cubes are where the mask fails.** Enrichment falls to 6.44 and 7.45, about half the lowest
  in-sample 256³ value (13.45). The mask covers more of the cube (density 0.0670–0.0678, against 0.0369–0.0599) and less of the
  fiber.
* **On those two cubes the tracer is ahead of connected components on merge-penalized ERL**, by 2.60× and 3.65×. In
  sample at 256³ it leads on only 1 of 8. This is not the tracer improving. Its own merge-penalized ERL falls (18.49
  and 26.89, against 30.85–44.19 in sample). Connected components' falls further, to 7.10 and 7.36 (24.29–87.47 in
  sample), because it merges far more: 142 and 265 merges, against 38–133.
* **On Scroll 3 the tracer finds a little less fiber than in sample.** Its median coverage is 0.551, against 0.576 on
  the in-sample 512³ cubes, while connected components' does not fall.

## Post-hoc diagnostic, not registered: the mask against villa's own semantic label

Coverage scores the mask along the annotated skeletons, with a 2-voxel tolerance. To check that the Scroll-5 drop is
not an artifact of that scoring, `scripts/fiber_mask_vs_label.py` measures the fraction of villa's labelled fiber voxels
inside the P ≥ 0.5 mask. Labels are villa's current ones:
* Dataset004 for the held-out cubes and the three revised targets;
* the copies ScrollGT was built from for the other eight targets. Their NMLs and CT are byte-identical in Dataset004;
  their labels were not compared.

| cube | split | label | label density | mask recall | mask precision |
|---|---|---|---:|---:|---:|
| s1_00497_01497_03997 | in sample | ScrollGT build copy | 0.0126 | 0.7703 | 0.1619 |
| s1_00497_02497_02997 | in sample | Dataset004 | 0.0208 | 0.6547 | 0.2569 |
| s1_00997_02497_02997 | in sample | ScrollGT build copy | 0.0165 | 0.6421 | 0.1987 |
| s1_08997_02997_02497 | in sample | Dataset004 | 0.0237 | 0.5832 | 0.2843 |
| s1_10997_02997_02997 | in sample | ScrollGT build copy | 0.0116 | 0.7165 | 0.1584 |
| s5_03997_01497_03997 | in sample | ScrollGT build copy | 0.0088 | 0.6842 | 0.1364 |
| s5_06494_01994_03994 | in sample | ScrollGT build copy | 0.0139 | 0.7227 | 0.1991 |
| s5_06994_00994_04994 | in sample | ScrollGT build copy | 0.0201 | 0.6117 | 0.1918 |
| s5_07994_01994_05494 | in sample | ScrollGT build copy | 0.0158 | 0.5909 | 0.1673 |
| s5_07997_02997_05497 | in sample | ScrollGT build copy | 0.0097 | 0.7370 | 0.1946 |
| s5_14997_01497_01497 | in sample | Dataset004 | 0.0249 | 0.6146 | 0.3138 |
| s3_00994_00494_01994 | held out | Dataset004 | 0.0205 | 0.6062 | 0.1744 |
| s3_00994_01994_00494 | held out | Dataset004 | 0.0252 | 0.6026 | 0.2478 |
| s3_00994_02494_01494 | held out | Dataset004 | 0.0250 | 0.5865 | 0.1932 |
| s3_01994_01494_00994 | held out | Dataset004 | 0.0171 | 0.6469 | 0.1586 |
| s3_01994_01994_01494 | held out | Dataset004 | 0.0175 | 0.6823 | 0.1637 |
| s3_02994_02494_01994 | held out | Dataset004 | 0.0217 | 0.6848 | 0.2483 |
| s3_03494_01494_00494 | held out | Dataset004 | 0.0283 | 0.5538 | 0.2473 |
| s3_04494_00994_01494 | held out | Dataset004 | 0.0224 | 0.6772 | 0.2176 |
| s5_13497_01497_02497 | held out | Dataset004 | 0.0179 | 0.4363 | 0.1155 |
| s5_16997_03997_04497 | held out | Dataset004 | 0.0290 | 0.3361 | 0.1454 |

It agrees with coverage on both splits:
* **Scroll 3:** median voxel recall 0.627, against 0.612 on the in-sample 512³ cubes. No drop.
* **New Scroll-5 cubes:** 0.4363 and 0.3361, against 0.6146–0.7370 on the in-sample Scroll-5 256³ cubes. The mask misses
  fiber that villa labelled, so the drop is not an artifact of skeleton scoring.

Even in sample the mask holds only 58–77% of villa's labelled voxels, so this ratio also reflects how thick the label
is. Only its comparison across splits is used here.

`s5_16997_03997_04497` has the densest label of any cube (0.0290). `s5_13497_01497_02497` (0.0179) lies within the
in-sample range (0.0088–0.0249). Label density does not explain both drops.

## What it means

**On Scroll 3, ScrollGT's in-sample numbers turn out to be a fair guide.** The mask trained on none of these eight cubes and
on no Scroll-3 data. Its coverage there (median 0.826) matches its coverage on its own 512³ training cubes (median
0.822), and so does its recall of villa's label. Per the registered decision rule, the in-sample disclosure stands, but
its practical cost is not shown on Scroll 3. The tracer's merge-penalized lead over connected components at 512³ also
holds on all eight Scroll-3 cubes.

**On two new cubes of a scroll it did train on, the mask fails badly.** Its coverage falls to 0.53 and 0.64, against
0.82–0.91 on the in-sample Scroll-5 256³ cubes, and its recall of villa's label falls with it. The cause is unknown:
* the region of the scroll;
* the content of the cubes;
* the annotators.

All three are possible, and two cubes cannot separate them. Here, training on the scroll did not protect the mask, and
never seeing the scroll did not hurt it. A held-out split is the only way ScrollGT can show either.

Connected components suffers most from a bad mask. It merges whatever the mask joins, so on those two cubes its
merge-penalized ERL collapses to about 7, less than a third of its lowest in-sample 256³ value (24.29). The tracer's
(18.49 and 26.89) also falls below its in-sample range (30.85–44.19), but less far. Every labelling built on this
mask inherits its failures, including the tracer.

## Limits

* Scroll 3 confounds an unseen scroll with unseen cubes and a different scan. The absence of a drop there is the
  combined result.
* Two Scroll-5 cubes are two cubes. Everything said about them is descriptive.
* The two splits are labelled at different times. Annotation completeness cannot be compared. The held-out labels are
  denser (Scroll 3: 0.0171–0.0283, against 0.0139–0.0201 in sample at 512³), which would lower recall against them if
  it reflects more complete annotation. Scroll 3 shows no drop anyway.
* The voxel-recall diagnostic was chosen after seeing the results. It is a consistency check, not a test.
* The tracer is classical. Its scores move only through the mask, so this says nothing about a learned tracer.

## What follows

* **ScrollGT adds the 10 cubes as a `held_out` fiber split.** The pre-registration commits to this whatever the outcome.
  They are the only annotated fiber cubes the reference mask did not train on. Each gets the oracle, floor and tracer
  rows measured here. The README quotes both results: no loss on Scroll 3, a large loss on the two new Scroll-5 cubes.
* **The registered generator entrant** (`docs/preregistration/2026-10-11_afv_generator_entrant.md`) now has its held-out
  comparators. This result is `OK`, so its P4 and P5 will be evaluated.
