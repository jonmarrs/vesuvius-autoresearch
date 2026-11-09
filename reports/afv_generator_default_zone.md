Finding 107: at villa's default block size, a 1024³ zone of Scroll 3 writes 12.0% of its fiber length beside a same-family copy; the seam trim cuts that to 5.2% and raises the held-out cube's ERLpen by 16.0% at tolerance 4 (2026-11-09)

The result of `docs/preregistration/2026-11-08_afv_generator_default_zone.md`, registered at 904419d5 (pushed 11:57:16
PST on 2026-11-08):
* **First launch:** bash refused the launcher at parse time, so nothing ran. Its quoting was fixed at a1060b39 (pushed
  12:06:06).
* **First run:** started 12:06:16. systemd-oomd killed it at 13:26, while it converted the fetched scan, before any
  field: nothing was written.
* **Amendment 1:** pushed at 1f0f632a (17:45:34 PST). It changed only how the fetch converts the scan.
* **The run:** 18:21:17 PST on 11-08 to 11:48:29 PST on 11-09, on the CPU at nice 19, in its own systemd user unit, by
  `repro/fibers/run_afv_generator_default_zone.sh`.

Inputs: villa main `7e6b82164`, the #1934 head's prediction modules, the amended patch's `stitch.py` (sha256
`362b78b1…`), model `Qualzz20/afv_fiber_9um` at `e189af75`, scored with ScrollGT (scoring version 3). Results:
`reports/afv_generator_default_zone.json`, written once by the runner's verdict step.

**Status OK; decision `BITES_AT_DEFAULTS`.** By the registered rule, that is "the real-use example for the villa PR,
whose posting is the owner's decision." The gate passed:
* the #1934 head's modules equal villa main's, and the patched `stitch.py` adds only `CUT_END` and `trim_cut_ends`;
* the model is at `e189af75`;
* the fetched scan's core equals the cube's own CT, and the zone is 8 blocks, each read as 576³.

## What was run

villa's automated fiber generator (`vesuvius.fiber_spline_generator`, VC3D's **Generate automated fibers…**) on one
1024³ zone of the public Scroll-3 scan (PHerc332 `20231117143551`, 7.91 µm), with villa's defaults:
* **Blocks:** `--block-size 512`, so the zone is 8 blocks, each predicted from its own crop with the 32-voxel margin.
* **Settings:** threshold 60, join angle 45°, minimum length 100, no mirroring, no `--extend`.

The zone is centred on the held-out hand-traced cube `s3_04494_00994_01494_512`. Its three inner faces cross the cube
at cube coordinate 256 on each axis. Two stitchings ran on the same eight fields:
* **main:** villa main's stitching;
* **with the trim:** the amended patch, which drops the 16 voxels at each spline end cut by a border that another
  block of the zone reads past.

There is no one-block arm (registered: it would cost as much CPU again).

## Result

| | main | with the trim |
|---|---|---|
| **The whole 1024³ zone (no ground truth)** | | |
| fibers written | 5,766 | 5,326 |
| written length, voxels | 1,031,976 | 972,804 |
| written length beside a same-family copy | 0.120 | 0.052 |
| **Inside the hand-traced 512³ cube** | | |
| fibers written inside | 1,052 | 904 |
| written length beside a same-family copy | 0.247 | 0.099 |
| merge-penalized ERL, τ = 4 | 35.79 | 41.51 (+16.0%) |
| merge-penalized ERL, τ = 2 | 15.11 | 15.95 (+5.6%) |
| merges, τ = 2 | 92 | 82 |
| merges, τ = 4 | 300 | 269 |
| splits, τ = 4 | 5,450 | 2,649 |
| coverage, τ = 4 | 0.4296 | 0.4138 |
| coverage, τ = 2 | 0.3406 | 0.3273 |
| precision, τ = 4 | 0.8936 | 0.8966 |
| precision, τ = 2 | 0.7084 | 0.7156 |

"Beside a same-family copy" is finding 106's duplicated share: the share of written length within 1.5 voxels of a
different written fiber of the same family.

| prediction | registered | measured | held |
|---|---|---|---|
| P1 (high) | main's zone duplicated share ≥ 0.05 | 0.1203 | yes |
| P2 (moderate) | with the trim, ≤ 0.6 of main's | 0.4347 of main's | yes |
| P3 (moderate) | ERLpen at τ = 4 higher with the trim | +16.0% | yes |
| P4 (moderate) | merges at τ = 2 ≤ 1.05 × main's | 82 against 92 | yes |

## Reading it

* **The defect bites at villa's defaults.** On main, 12.0% of the zone's written length lies beside a same-family copy.
  * **No one-block arm here:** finding 106's eight cubes run as one block had at most 0.0002.
  * **For scale:** 18% of a 1024³ zone lies within 32 voxels of one of its three inner faces (the registration's
    arithmetic).
* **The trim removes most of it.** The zone's share falls to 0.4347 of main's. At blocks of 256 in finding 106, the
  eight cubes' median share went from 0.246 to 0.104.
* **On the cube, the gain is larger than finding 106's on the same cube.** That run used blocks of 256, with faces at
  the same cube coordinates, and gained +11.1% at τ = 4 and +4.0% at τ = 2. This one gained +16.0% and +5.6%. Main's
  own ERLpen is also higher here (35.79 against finding 106's 32.59), but its score is not comparable: the cube's
  outer faces are no longer the scan's edge, and the blocks read past them. The difference was not analysed further.
* **What it costs.** Coverage falls 3.7% at τ = 4 and 3.9% at τ = 2. Finding 106 found the same on all eight cubes
  (−2.2% to −5.6% at τ = 4), and two things there qualify it:
  * on every cube, main's eight blocks covered more of the hand tracing than the cube run as one block, at both
    tolerances;
  * the trim brought coverage back to within −0.005 to +0.014 of one block at τ = 4.

  So there, the coverage the trim gives up is coverage the blocked run had beyond the unblocked generator. This run
  has no one-block arm, so that is not measured on this zone.

## What it cannot say

* **One zone and one cube.** It shows the case, not a rate across zones; finding 106's eight cubes are the estimate.
* **Faces on ground truth:** the zone is placed on a hand-traced cube, so its faces cross ground truth. A user's zone
  has its faces wherever the zone puts them.
* **7.91 µm and the raw scan:** finer than the model's training pitch, and not a masked or standardized volume.
* **One hand tracing.**
* **CPU cost:** the CPU took 61,036.2 s to predict the eight blocks (7,068.7 to 9,158.5 s each). Blocks 1 and 6 ran beside
  a full test suite. No GPU was used (that is the owner's decision), so its time is not measured.

## Records

* the registration, `docs/preregistration/2026-11-08_afv_generator_default_zone.md`, and its amendment 1 (in the same
  file);
* the script, `scripts/afv_generator_default_zone.py`, and its runner, `repro/fibers/run_afv_generator_default_zone.sh`;
* the smoke, `scripts/afv_generator_default_zone_smoke.py`, and its result,
  `reports/evidence/afv_generator_default_zone_smoke_2026-11-08.json`;
* the record, `reports/afv_generator_default_zone.json`;
* the figures here are tested against it by `tests/test_afv_generator_default_zone_report.py`.
