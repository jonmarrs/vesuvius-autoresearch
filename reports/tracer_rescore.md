# Our fiber tracer, re-measured with the corrected scorer: still far behind connected components on raw ERL, ahead on merge-penalized ERL on 4 of 11 cubes

**2026-10-09.** Result of `docs/preregistration/2026-10-05_tracer_rescore.md` (committed `f5f775c3` before any tracer
run; Amendment 1 `aa1c5712` before any 512³ result). Data: `reports/tracer_rescore.json`. Labellings:
`spiral_out/tracer_rescore/`.

**Why.** ScrollGT's README said our tracer "lost to connected components on both metrics, on all six cubes it was
scored against". That was measured with fiber scoring version 1, which read runs in stored edge-row order. The tracer
was re-run at its published defaults (relink on, no smoothing, no skipping, no seed suppression) on all 11 ScrollGT
cubes. Each labelling was scored by ScrollGT itself (scoring version 2) against its verified version-2 floors.

## Fidelity: exact

Scored with ScrollGT 0.3.2's version-1 scorer, the re-run labellings reproduce the published July rows to +0.0% on
all six cubes that had one: 26.6, 45.77, 36.32, 34.14, 37.43 and 31.54. The tracer has not changed; only the scorer
moved its numbers. The 512³ cubes were traced in blocks (`--detect-block 128`). That is bit-identical to the dense
path, verified on two real cubes. The dense path needs about 30 GB and was OOM-killed on 2026-10-05.

## Results (scoring version 2)

| cube | size | tracer ERL | cc ERL | cc ÷ tracer | tracer ERLpen | cc ERLpen | tracer ÷ cc | tracer coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| s1_00497_01497_03997 | 256 | 35.39 | 200.47 | 5.66 | 30.85 | 37.09 | 0.83 | 0.6231 |
| s1_00497_02497_02997 | 256 | 55.07 | 213.41 | 3.88 | 40.61 | 65.37 | 0.62 | 0.7038 |
| s1_00997_02497_02997 | 256 | 48.82 | 205.85 | 4.22 | 38.72 | 60.81 | 0.64 | 0.6054 |
| s1_08997_02997_02497 | 256 | 44.91 | 201.51 | 4.49 | 40.58 | 112.16 | 0.36 | 0.6707 |
| s1_10997_02997_02997 | 256 | 48.17 | 200.76 | 4.17 | 44.19 | 58.23 | 0.76 | 0.6164 |
| s5_03997_01497_03997 | 256 | 40.45 | 182.25 | 4.51 | 33.30 | 54.17 | 0.61 | 0.6233 |
| s5_07997_02997_05497 | 256 | 48.00 | 205.25 | 4.28 | 43.65 | 87.47 | 0.50 | 0.6755 |
| s5_14997_01497_01497 | 256 | 46.62 | 188.89 | 4.05 | **38.56** | 33.09 | **1.17** | 0.6586 |
| s5_06494_01994_03994 | 512 | 53.40 | 321.98 | 6.03 | **42.63** | 15.59 | **2.73** | 0.6716 |
| s5_06994_00994_04994 | 512 | 42.65 | 245.23 | 5.75 | **34.14** | 10.55 | **3.24** | 0.5759 |
| s5_07994_01994_05494 | 512 | 41.42 | 258.83 | 6.25 | **34.18** | 17.02 | **2.01** | 0.5742 |

ERL is never compared across size classes; each row is read against its own cube.

* **P1 HELD.** Raw ERL is below connected components on all 11 cubes, with connected components ahead by 3.9–6.3×.
* **P2 FAILED.** Merge-penalized ERL is below connected components on 7 of the 8 cubes at 256³, not all 8. On
  `s5_14997_01497_01497` the tracer is ahead (38.56 vs 33.09). That cube had never been traced before.
* **P3 HELD, 3 of 3.** On every 512³ cube the tracer's merge-penalized ERL is 2.0–3.2× connected components'.

## What it means

* **The published claim is wrong under the corrected scorer.** "Lost on both metrics" holds only for raw ERL. On the
  merge-penalized metric the tracer is ahead on 4 of 11 cubes: one 256³ cube and all three 512³ cubes.
* **Why the large cubes differ.** Connected components merges many fibers in a big cube (cc ERLpen 10.6–17.0, the
  lowest of any cube), while the tracer's runs are short whatever the cube size. Merge-penalized ERL punishes merging,
  which is what ScrollGT's villa-quoted preference asks for: a tracer that follows fewer fibers correctly beats one
  that follows more with errors.
* **The tracer is still weak.** It covers only 57–70% of ground-truth length, and its raw ERL is 4–6× below a trivial
  labelling. Being ahead on merge-penalized ERL means it merges less. It does not mean it follows fibers well.

## Limits

One tracer configuration, the published baseline, not the frozen "improved" configuration from
`reports/fiber_tracer_improvement.md`. P2's single failure is one cube; P3's three cubes are all cross-scroll (Scroll 5)
and from one size class.
