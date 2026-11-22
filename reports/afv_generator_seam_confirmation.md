Finding 109: the fiber generator's two seam changes hold on ten unseen cubes of Scrolls 1 and 5. ERLpen rose over villa main on 10 of 10, by a median +31.2% at tolerance 4 (+23.0% on the four cubes at Scroll 3's block size), with merges at tolerance 2 325 → 297 and coverage down on every cube (2026-11-10)

The result of `docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md`, registered at 9f3bf4f6 (pushed
18:19:23 PST on 2026-11-09). The run: 18:19:29 PST on 11-09 to 12:34:00 PST on 11-10, on the CPU at nice 19, in its
own systemd user unit, by `repro/fibers/run_afv_generator_seam_confirmation.sh`. Every field was predicted in this
run: 16.4 hours of prediction over the ten cubes.

Inputs: villa main `7e6b82164`, the #1934 head's prediction modules, the amended seam-trim `stitch.py` (sha256
`362b78b1…`), the changed `catalog.py` (sha256 `be553b49…`), model `Qualzz20/afv_fiber_9um` at `e189af75`, scored with
ScrollGT (scoring version 3). Results: `reports/afv_generator_seam_confirmation.json`, written once by the runner's
verdict step.

**Decision `CONFIRMED`.** By the registered rule, that is "the PR can state both scrolls' figures; posting is the
owner's decision." The gate passed on all ten cubes:
* the stitching and catalogue modules are the ones findings 106 to 108 measured;
* each cube's image and hand tracing are the registered files;
* villa's `resolve_model` reported revision `e189af75`;
* the cube run as one block came out the same under all three stitchings.

## What was run

villa's automated fiber generator (`vesuvius.fiber_spline_generator`, VC3D's **Generate automated fibers…**) with
villa's defaults (threshold 60, join angle 45°, minimum length 100, margin 32), on the ten fiber-skeletons cubes that
ScrollGT does not ship: three of Scroll 1 and seven of Scroll 5. No step of the generator work had used them. Each
cube was run as one block, and in 8 blocks of half its side, each block predicted from its own crop. The 8 blocks
were stitched three ways from the same fields:
* **main:** villa main's stitching;
* **trim:** the amended seam trim (findings 106 and 107);
* **both:** the trim, plus the catalogue that suppresses a block's copy of a fiber another block also fitted
  (finding 108).

## Result

| cube | block | ERLpen τ = 4, main | trim | both | both over main, τ = 4 | τ = 2 | both over trim, τ = 4 | merges, τ = 2 | written length beside a same-family copy |
|---|---|---|---|---|---|---|---|---|---|
| `s1_02494_01494_03994_512` | 256 | 34.31 | 39.99 | 44.54 | +29.8% | +19.2% | +11.4% | 109 → 103 → 105 | 0.309 → 0.174 → 0.033 |
| `s1_08994_02494_03494_512` † | 256 | 46.96 | 56.91 | 62.03 | +32.1% | +15.2% | +9.0% | 62 → 60 → 58 | 0.290 → 0.132 → 0.049 |
| `s1_09997_02497_03497_256` † | 128 | 39.37 | 52.29 | 61.98 | +57.4% | +45.6% | +18.5% | 5 → 2 → 2 | 0.418 → 0.123 → 0.051 |
| `s5_05497_01997_02997_256` | 128 | 39.91 | 65.31 | 75.94 | +90.3% | +46.6% | +16.3% | 5 → 3 → 3 | 0.504 → 0.235 → 0.101 |
| `s5_05497_02497_02497_256` | 128 | 33.36 | 37.2 | 43.44 | +30.2% | +34.1% | +16.8% | 8 → 7 → 8 | 0.400 → 0.205 → 0.049 |
| `s5_08994_02994_03994_512` | 256 | 43.48 | 48.07 | 50.53 | +16.2% | +9.6% | +5.1% | 38 → 33 → 33 | 0.212 → 0.095 → 0.033 |
| `s5_08997_02497_04997_256` | 128 | 43.35 | 62.09 | 66.87 | +54.3% | +61.1% | +7.7% | 4 → 3 → 3 | 0.429 → 0.110 → 0.030 |
| `s5_11497_05497_03997_256` | 128 | 45.67 | 58.56 | 67.46 | +47.7% | +44.6% | +15.2% | 15 → 14 → 13 | 0.521 → 0.288 → 0.036 |
| `s5_15494_04494_02494_512` † | 256 | 22.18 | 23.11 | 23.85 | +7.5% | +7.1% | +3.2% | 68 → 63 → 62 | 0.195 → 0.074 → 0.031 |
| `s5_16997_03497_03997_256` | 128 | 22.22 | 24.95 | 26.67 | +20.0% | +38.3% | +6.9% | 11 → 10 → 10 | 0.417 → 0.164 → 0.056 |

† not in the base model's training set (`BASE_MODEL_UNSEEN`). Three-part cells read main → trim → both.

| prediction | registered | measured | held |
|---|---|---|---|
| P1 (moderate) | both changes: ERLpen at τ = 4 above main's on at least 8 of 10 cubes | 10 of 10 | yes |
| P2 (moderate) | median gain of both over main at τ = 4 at least 0.10 | 0.3115 | yes |
| P3 (moderate) | summed merges at τ = 2 with both at most 1.05 × main's | 297 against 325 | yes |
| P4 (moderate) | ERLpen at τ = 4 with both above the trim's alone on at least 7 of 10 cubes | 10 of 10 | yes |
| P5 (high) | median duplicated share with both at most 0.5 × main's | 0.0425 against 0.4089 (0.10 ×) | yes |

**Over the ten cubes**

| | main | trim | both |
|---|---|---|---|
| merges, τ = 2, summed | 325 | 298 | 297 |
| merges, τ = 4, summed | 887 | 824 | 817 |
| written length beside a same-family copy, median | 0.409 | 0.148 | 0.043 |
| fibers written, summed (one block: 2,158) | 3,018 | 2,461 | 2,254 |
| written length, voxels, summed (one block: 414,250) | 532,092 | 455,701 | 432,797 |
| face crossings whole / broken / lost, of 910 | 573 / 253 / 84 | 615 / 147 / 148 | 710 / 75 / 125 |
| coverage, τ = 4, median | 0.4380 | 0.4226 | 0.4298 |
| coverage, τ = 2, median | 0.3048 | 0.2959 | 0.2963 |
| precision, τ = 4, median | 0.9146 | 0.9171 | 0.9185 |
| precision, τ = 2, median | 0.6766 | 0.6925 | 0.6916 |
| ERLpen at τ = 4 as a fraction of one block's, range (median) | 0.557 to 0.932 (0.728) | 0.659 to 1.018 (0.911) | 0.704 to 1.110 (1.017) |

## The reported splits (not deciding)

Median gain in ERLpen, with the range. Every cube rose in every row.

| cubes | n | both over main, τ = 4 | both over main, τ = 2 | trim over main, τ = 4 | both over trim, τ = 4 | merges, τ = 2, main → both |
|---|---|---|---|---|---|---|
| all | 10 | +31.2% (+7.5% to +90.3%) | +36.2% (+7.1% to +61.1%) | +18.9% (+4.2% to +63.6%) | +10.2% (+3.2% to +18.5%) | 325 → 297 |
| Scroll 1 | 3 | +32.1% (+29.8% to +57.4%) | +19.2% (+15.2% to +45.6%) | +21.2% (+16.6% to +32.8%) | +11.4% (+9.0% to +18.5%) | 176 → 165 |
| Scroll 5 | 7 | +30.2% (+7.5% to +90.3%) | +38.3% (+7.1% to +61.1%) | +12.3% (+4.2% to +63.6%) | +7.7% (+3.2% to +16.8%) | 149 → 132 |
| 512³, blocks of 256 | 4 | +23.0% (+7.5% to +32.1%) | +12.4% (+7.1% to +19.2%) | +13.6% (+4.2% to +21.2%) | +7.1% (+3.2% to +11.4%) | 277 → 258 |
| 256³, blocks of 128 | 6 | +51.0% (+20.0% to +90.3%) | +45.1% (+34.1% to +61.1%) | +30.5% (+11.5% to +63.6%) | +15.7% (+6.9% to +18.5%) | 48 → 39 |
| `BASE_MODEL_UNSEEN` | 3 | +32.1% (+7.5% to +57.4%) | +15.2% (+7.1% to +45.6%) | +21.2% (+4.2% to +32.8%) | +9.0% (+3.2% to +18.5%) | 135 → 122 |
| in the base model's training set | 7 | +30.2% (+16.2% to +90.3%) | +38.3% (+9.6% to +61.1%) | +16.6% (+10.6% to +63.6%) | +11.4% (+5.1% to +16.8%) | 190 → 175 |

## Reading it

* **Compare like with like: the four 512³ cubes.** They are cut as Scroll 3's eight were, in blocks of 256. Both
  changes raise their ERLpen at τ = 4 by a median +23.0% (+7.5% to +32.1%); on Scroll 3 the median was +17.6% (+6.3%
  to +31.0%). The ten-cube median, +31.2%, is carried by the six 256³ cubes, whose blocks of 128 put a border across
  far more of each fiber: their median written-twice share on main is 0.423, against 0.251 on the 512³ cubes. No
  villa user runs blocks of 128, so +31.2% is not a figure for real use.
* **The defect is in the stitching, not in one scroll.** On main, a median 0.409 of the written length lies beside a
  same-family copy; run as one block, no cube has more than 0.0003. With both changes the median is 0.043, and
  every cube falls to between 0.07 and 0.20 of its share on main.
* **Eight blocks now match one block on most cubes.** With both changes, ERLpen at τ = 4 is at least the one-block
  run's on 7 of 10 cubes (main: none of 10).
* **The exception is `s5_16997_03497_03997_256`:** 0.704 of one block's ERLpen with both changes (main 0.587). It is
  also the one cube where every stitching covers less than one block does (0.318 against 0.356 at τ = 4 with both).
  Blocks of 128 lose something there that neither change returns. Not diagnosed.
* **The cost is coverage.** Coverage with both changes is below main's on 10 of 10 cubes at both tolerances, by a
  median 2.3% at τ = 4 (1.1% to 6.2%) and 2.8% at τ = 2. Main's coverage was above the one-block run's on 9 of 10
  cubes, and with both changes it still is, by −0.038 to +0.032 at τ = 4. So most of what is lost is length that
  the same cube run as one block does not cover either. The catalogue change returns part of the trim's loss:
  coverage with both is above the trim's on 10 of 10 at τ = 4 and on 7 of 10 at τ = 2.
* **Precision** at τ = 2 rose on 10 of 10 over main, by 0.006 to 0.027. At τ = 4 it rose on 9 of 10, by at most
  0.015; the tenth fell 0.0007.
* **Merges** with both changes fell on every cube at τ = 4 (887 → 817) and on 9 of 10 at τ = 2, where the tenth was
  unchanged at 8. Against the trim alone, `s1_02494_01494_03994_512` gained 2 merges at τ = 2 (103 → 105) and
  `s5_05497_02497_02497_256` gained 1.
* **Face crossings:** of the 910 places where a fiber of the cube run as one block crosses a block face, both
  changes make 710 whole, 75 broken and 125 lost, against main's 573 / 253 / 84. As on Scroll 3, more crossings are
  whole and far fewer are broken, but more are lost than on main.
* **The three cubes outside the base model's training set** rose +7.5%, +32.1% and +57.4% at τ = 4. The smallest
  gain of the ten is among them (`s5_15494_04494_02494_512`, whose ERLpen is also the lowest on every arm).

## What it cannot say

* **Ten cubes, one hand tracing each, at 7.91 µm,** finer than the model's 8.64–9.36 µm training pitch.
* **No cube at villa's default block size of 512.** Four are at 256 and six at 128. The one zone run at 512 is
  finding 107's, on Scroll 3.
* **Seven cubes are in the base model's training set.** The comparison is within one field per cube, but the fields
  may be better than on unseen data.
* **Each cube's crop is the cube.** A block at a cube face reads no context beyond it.
* **Nothing about reading.** No ink was scored, and no geometry change measured in this repository has improved a
  reading metric.
* **Neither change alone on main.** The catalogue change was measured only on top of the trim.

## Records

* the registration, `docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md`;
* the script, `scripts/afv_generator_seam_confirmation.py`, and its runner,
  `repro/fibers/run_afv_generator_seam_confirmation.sh`;
* the two changes, `repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch` and
  `repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`;
* the smoke before the run, `reports/evidence/afv_generator_seam_confirmation_smoke_2026-11-09.json`;
* the record, `reports/afv_generator_seam_confirmation.json`;
* the figures here are tested against it by `tests/test_afv_generator_seam_confirmation_report.py`.
