# Finding 99: with the scan around each cube, villa's neural tracer drops a seed only where its CT axis misses the fiber, in papyrus sheets tilted far from vertical (2026-10-24)

Exploratory, after finding 97; not pre-registered, but its expectations were pushed before it ran. Findings 97 and 98
gave villa's neural tracer 128 voxels of the real scan around each cube. In sample, the share of seed dots it drops as
`no_heading` fell to 0.002–0.012. It stayed at 0.266 and 0.353 on the two held-out Scroll-5 256³ cubes, and at
0.011–0.088 on Scroll 3, where finding 96's edge rule cannot fire. This asks what drops them.

**Answer: villa's own CT heading, in steep sheets.**
* **The reason.** villa's `_seed_heading` (`tracers/fibers/tracing/volume.py`) drops a dot for four reasons. On all 21
  cubes, every dropped dot fails the last: the CT's axis for the dot's fiber family lies more than 35° from the dot's
  direction, which comes from the presence. None is dropped at the CT's edge, for want of a sheet normal, or as H/V
  ambiguous.
* **Which is wrong.** At the dropped dots near the ground truth, the presence direction lies a median 13–15° from the
  ground-truth tangent on the two held-out Scroll-5 cubes, and 10–16° on Scroll 3. The CT's axis lies 58° and 65–81°
  from it. The CT's axis is the closer of the two on 0.09–0.18 and 0.03–0.19 of those dots.
* **Why.** The CT shows a clear sheet at every dot: no relative eigengap is below villa's `MIN_EIGENGAP`, 0.05. On those
  ten cubes the ground-truth tangent lies a median 6–14° out of that sheet, so its normal is right. But the sheets are
  steep, tilted a median 52–74° from vertical at the dropped dots. villa's axis for an H fiber is the sheet's
  horizontal line, which is the fiber's direction only in a sheet near vertical; 0.83–0.93 of those cubes' dropped
  dots are H dots.
* **Per cube**, the share of its dots in sheets tilted more than 45° tracks the share it drops: Pearson r 0.98 over the
  21 cubes, Spearman 0.92. That share is 0.78 and 0.84 on the two held-out Scroll-5 cubes, 0.04–0.35 on Scroll 3, and
  at most 0.04 in sample. Pooled, it drops 0.410 of the dots in such sheets and 0.011 of the rest.

## The run

* **Script:** `scripts/neural_tracer_heading_residual.py`, in villa's tracer environment, villa `ccb431818`, CPU only,
  at nice 19 beside the loop.
  * Pass 1 at a67e962e, pushed at 19:59 PDT on 2026-10-24 with its expectations, before it ran; it ran 20:48–21:31.
  * Pass 2 at 2bf7c8ba (the sheet evidence, added after pass 1's result) ran 21:37–22:21.
* **Inputs:** findings 97's and 98's runs (`run.json`, `tiles.jsonl`, the fibers written, the padded CT and presence),
  and ScrollGT's ground truth (each skeleton's sha256 is in the JSON).
* **The dots.** villa's own `tile_dots`, at each run's settings, re-derives exactly as many dots as each run recorded,
  on all 21 cubes. Every dot of the 256³ cubes is classified (12,471), and a fixed random sample of 2,000 on each 512³
  cube (of 9,513–13,806).
* **Checks:**
  * villa's `_seed_heading` gives the same verdict on the first 50 dots of each cube, and its `ct_sheet_normal` the
    same normal;
  * all 5,663 written seeds checked match a dot and pass (every one on the 256³ cubes, 300 on each 512³ cube);
  * pass 2 gives pass 1's counts on every cube.
* **Output:** `neural_tracer_heading_residual.json` (pass 2), `neural_tracer_heading_residual_pass1.json`.

## Results

"Run": the run's `no_heading` over its dots. A run never offers a dot that lies on a fiber it has already written, so
it counts only the dots it offered. "Here": the share of all the dots (on a 512³ cube, of the sample) that fail, with
their number. "Steep": the share of the dots in a sheet tilted more than 45° from vertical. The angles are medians over
the dropped dots within 4 voxels of the ground truth, except "tilt, kept".

| cube | split | dropped, run | dropped, here (n) | steep | presence → GT | CT axis → GT | tilt, dropped | tilt, kept | GT out of the CT's sheet |
|---|---|---|---|---|---|---|---|---|---|
| s1_00497_01497_03997_256 | in sample | 0.010 | 0.012 (18) | 0.016 | 15° | 38° | 43° | 11° | 18° |
| s1_00497_02497_02997_256 | in sample | 0.007 | 0.010 (14) | 0.028 | 20° | 63° | 53° | 23° | 28° |
| s1_00997_02497_02997_256 | in sample | 0.002 | 0.003 (4) | 0.005 | 46° | 32° | 13° | 21° | 3° |
| s1_08997_02997_02497_256 | in sample | 0.002 | 0.005 (7) | 0.003 | 11° | 57° | 44° | 14° | 13° |
| s1_10997_02997_02997_256 | in sample | 0.006 | 0.009 (12) | 0.027 | 59° | 42° | 32° | 17° | 6° |
| s5_03997_01497_03997_256 | in sample | 0.010 | 0.013 (14) | 0.011 | 20° | 70° | 20° | 13° | 11° |
| s5_07997_02997_05497_256 | in sample | 0.004 | 0.006 (6) | 0.017 | 20° | 85° | 61° | 14° | 2° |
| s5_14997_01497_01497_256 | in sample | 0.005 | 0.008 (12) | 0.001 | 20° | 29° | 12° | 9° | 23° |
| s5_06494_01994_03994_512 | in sample | 0.004 | 0.009 (19) | 0.002 | 36° | 16° | 11° | 9° | 8° |
| s5_06994_00994_04994_512 | in sample | 0.012 | 0.021 (43) | 0.036 | 28° | 74° | 58° | 13° | 11° |
| s5_07994_01994_05494_512 | in sample | 0.004 | 0.007 (14) | 0.001 | 67° | 28° | 14° | 10° | 11° |
| s5_13497_01497_02497_256 | held out | 0.266 | 0.312 (284) | 0.844 | 15° | 58° | 65° | 55° | 6° |
| s5_16997_03997_04497_256 | held out | 0.353 | 0.421 (377) | 0.778 | 13° | 58° | 74° | 57° | 7° |
| s3_00994_00494_01994_512 | held out | 0.074 | 0.127 (255) | 0.346 | 12° | 72° | 66° | 31° | 7° |
| s3_00994_01994_00494_512 | held out | 0.035 | 0.072 (143) | 0.143 | 13° | 78° | 64° | 19° | 10° |
| s3_00994_02494_01494_512 | held out | 0.088 | 0.169 (338) | 0.337 | 12° | 74° | 71° | 29° | 9° |
| s3_01994_01494_00994_512 | held out | 0.071 | 0.097 (193) | 0.180 | 16° | 68° | 64° | 18° | 14° |
| s3_01994_01994_01494_512 | held out | 0.062 | 0.095 (189) | 0.174 | 13° | 67° | 64° | 19° | 11° |
| s3_02994_02494_01994_512 | held out | 0.011 | 0.020 (40) | 0.036 | 15° | 81° | 52° | 14° | 13° |
| s3_03494_01494_00494_512 | held out | 0.053 | 0.092 (184) | 0.194 | 10° | 74° | 69° | 19° | 9° |
| s3_04494_00994_01494_512 | held out | 0.039 | 0.077 (153) | 0.168 | 13° | 65° | 67° | 21° | 8° |

On the in-sample cubes few dots are dropped (4–43), so their medians move a lot from cube to cube.

**The expectations, written before pass 1 ran:**

| | |
|---|---|
| E1: on the two held-out 256³ cubes most of the dropped dots are `disagree`, and none `edge` | **held** (all of them) |
| E2: at the `disagree` dots near the ground truth, the presence direction is the further from its tangent on most | **failed**, the other way round |
| E3: on every other cube fewer than 0.10 of all dots are dropped | **failed** on two Scroll-3 cubes (0.127, 0.169) |

## What it means

* **Finding 97's held-out residual and Scroll 3's smaller one are one mechanism.** villa's seed-heading policy
  (`ct_sheet_hv_sigma2_8_v2`) takes an H fiber to run along the sheet's horizontal line, and a V fiber up it. That
  holds where the sheets are near vertical, as nearly all the in-sample dots' are. Where the papyrus tilts, the CT's
  axis misses the fiber, and the 35° test drops the seed. The presence direction it is compared with is the one that
  follows the fiber.
* **It is not the mask's model, nor the CT, nor "held out" as such.** The presence direction is the closer to the
  ground truth, and the CT's sheet is clear and correct. On Scroll 3, held out too, it drops 0.020 of the dots on the
  cube with the fewest steep ones and 0.169 on one with many.

## What it does not say

* **Nothing was traced again.** How many traces a heading that followed a steep sheet would add, and what coverage, is
  untested; that is a GPU run.
* **Near the ground truth** means within 4 voxels of a sample of a ScrollGT centreline. Its tangent is that sample's
  edge's; where fibers cross, it can be another fiber's.
* **The tilt was added after a smoke of pass 2** on one cube (`s5_13497_01497_02497_256`). The 45° line was set then,
  before the full pass 2 ran.
* **The pooled shares** mix every dot of the 256³ cubes with 2,000-dot samples of the 512³ ones.
* **Whether the tilt is also why the reference mask covers less** on the two held-out Scroll-5 cubes (finding 84) is
  untested.
* **No villa or ScrollGT change here.**
