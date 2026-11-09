# Pre-registration: the seam trim at villa's default block size, on one 1024³ zone of Scroll 3

**Written 2026-11-08, before the zone was fetched or run.** The script is `scripts/afv_generator_default_zone.py`,
committed with this file; the patch it runs is finding 106's amended patch,
`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch` (on villa main `7e6b82164`), the one a villa PR
would propose.

**Smoke, before this was pushed** (`scripts/afv_generator_default_zone_smoke.py`, result
`reports/evidence/afv_generator_default_zone_smoke_2026-11-08.json`): `run` on finding 106's one-block field of the cube
placed in the 1088³ layout, with the scan around the cube set to 1 so that nothing is exterior black. Its blocks then
see the cube as finding 106's arm `same` did, and the run reproduced those rows closely: fibers written 651 and 571
(finding 106: 641 and 562), ERLpen at τ = 4 33.45 → 37.45 (33.19 → 37.18), a gain of +12.0% in both, merges at τ = 2
78 → 70 (77 → 69). On block 0 the skeletons are identical voxel for voxel. Of the splines that differ, 23 of 25 come
from chains touching the cube's outer faces, which were the volume's edge in finding 106, where villa's `fit_spline`
rejects a spline that leaves the array. The other 2 lie in the crop's last voxel plane, where a spline's end rounds
5.7e-14 past the edge in one frame and onto it in the other (checked for one).

**Pushed at 11:57 PST (904419d5) and amended at 17:45 PST (1f0f632a: the fetch converts the scan a slab at a time;
nothing had been predicted). Run 18:21 PST on 11-08 to 11:48 PST on 11-09: finding 107,
`reports/afv_generator_default_zone.md`. The gate passed, and P1, P2, P3 and P4 held (zone duplicated share 0.1203,
0.4347 of it with the trim; ERLpen +16.0% at τ = 4; merges at τ = 2 92 → 82): `BITES_AT_DEFAULTS`.**

## The question

Finding 106 measured the trim in blocks of 256 on 512³ cubes, because a hand-traced cube allows no smaller face count.
villa's generator defaults to `--block-size 512`, and VC3D's dialog defaults to a zone of one block, where the trim
changes nothing. The generator has block faces whenever the zone is larger than one block along an axis, and its
documentation describes zones "of any size … read one block at a time". So the question for a villa PR is the case
that bites in practice: **on a zone larger than one default block, does main write fibers twice at the faces, and
does the trim stop it?**

## Already known, and not predicted here

* Finding 106, arm real, blocks of 256: the median share of written length within 1.5 voxels of a same-family copy
  fell from 0.246 to 0.104, and ERLpen at τ = 4 rose on 8 of 8 cubes (median +12.8%).
* On the cube used here, `s3_04494_00994_01494_512`, it rose +11.1% at τ = 4 and +4.0% at τ = 2, with merges at τ = 2
  85 → 72 and a duplicated share 0.235 → 0.086. Its whole face crossings fell 118 → 91, the most of the eight; the
  diagnosis found it lost 19 joins and gained 11.
* Each crop's margin is 32 voxels whatever the block size, so near a face the copies come from the same geometry as in
  finding 106. A larger block puts less of the zone near a face: with one inner face per axis, 1 − (1 − 64/1024)³ =
  0.18 of a 1024³ zone lies within 32 voxels of one, against 0.33 of a 512³ cube in blocks of 256 (arithmetic, not a
  measurement).

## Data and the zone

* **The cube:** of finding 106's eight held-out Scroll-3 cubes, the one with the lower of the two middle arm-real gains
  at τ = 4, whose mean is the eight's median (0.128): `s3_04494_00994_01494_512` (0.111; the other is 0.146). This
  picks a typical cube, not the best (0.234), and of the two typical ones the one where the trim cost the most face
  crossings. The rule was chosen knowing finding 106's results, and no other cube was run at this size.
* **The scan:** the public raw scan the cube was cut from (PHerc332 `20231117143551`, by HTTP byte range), read by
  ScrollGT's `tools/context_ct.py` with a 288-voxel margin and converted as the cube's own CT was: a 1088³ uint8 array,
  the cube at [288, 800) on each axis. Its core must equal the cube's own CT voxel for voxel.
* **The zone:** the array's inner 1024³ (origin 32 on each axis), `--block-size 512`, margin 32: 8 blocks, each read
  as 576³, and the zone's read box is the whole array. Its three inner faces cross the cube at cube coordinate 256 on
  each axis, where finding 106's blocks of 256 met.

## Method, fixed now

`scripts/afv_generator_default_zone.py fetch`, then `run`, then `verdict` (all three in
`repro/fibers/run_afv_generator_default_zone.sh`), with villa's defaults, as in finding 106: model
`Qualzz20/afv_fiber_9um` at `e189af75`, threshold 60%, margin 32, no mirroring, no `--extend`, join angle 45°,
minimum length 100, black distance 16. Each block is predicted from its own crop, as `generate` does. The stitching is
villa main's (`main`) and the amended patch's (`patched`), on the same eight fields. With the read box equal to the
array, the amended trim keeps exactly the ends the scan continues past, as a zone inside the full scan would.

Measured per variant:
* **over the zone, without ground truth:** fibers written, their length, and the share of written length within 1.5
  voxels of a different written fiber of the same family (finding 106's duplicated share);
* **inside the cube:** the written fibers clipped to the cube, scored by ScrollGT `score_tracing` at τ = 2 and 4
  against the hand tracing, and the duplicated share counted on the cube's samples.

There is no one-block arm: one 1088³ block would cost as much CPU again as the eight blocks, and the question is the
trim at the default, not the size of the defect against one block. Device: CPU, at nice 19, about 2 hours per block
here (16 hours in all), unless the owner approves the GPU.

## Gate; any failure means no verdict

`run` checks all three before it predicts a field, and stops if one fails.

1. `afv_generator_block_seams.identity()`: the #1934 head's stitching and prediction modules are byte-identical to
   villa main `7e6b82164`, and the patched `stitch.py` differs from main's only by `CUT_END` and `trim_cut_ends`. The
   patched `stitch.py` is the amended patch's (its sha256 recorded in the script).
2. The model revision is `e189af75`.
3. The fetched array's core equals the cube's own CT, and the zone is 8 blocks each read as 576³.

## Predictions

1. **P1 (high):** on main, the zone's duplicated share is at least 0.05: the generator writes fibers twice at villa's
   default block size.
2. **P2 (moderate):** with the trim, the zone's duplicated share is at most 0.6 of main's.
3. **P3 (moderate):** inside the cube, ERLpen at τ = 4 is higher with the trim than on main.
4. **P4 (moderate):** inside the cube, merges at τ = 2 with the trim are at most 1.05 times main's.

Reported, not deciding: ERLpen at τ = 2, coverage and precision inside the cube; the cube's duplicated share; fibers
written and their length over the zone.

## Decision rule

| Outcome | Conclusion |
| --- | --- |
| A gate check fails | `NO_VERDICT`. |
| P1 misses | `NO_DOUBLING_AT_DEFAULTS`: at the default block size this zone shows no doubling to fix; a villa PR must say the case is the smaller block sizes VC3D offers. |
| P3 or P4 misses | `COSTS_AT_DEFAULTS`: the trim loses continuity or adds merges here, against finding 106; no PR before that is understood. |
| P2 misses | `PARTIAL`: doubling at the default, but the trim removes less of it than at 256. |
| All hold | `BITES_AT_DEFAULTS`: the real-use example for the villa PR, whose posting is the owner's decision. |

## What it cannot say

* **One zone, one cube.** It shows the case, not a rate across zones; finding 106's eight cubes are the estimate.
* **The zone is placed on a hand-traced cube**, so the faces cross ground truth; a user's zone has its faces wherever
  the zone puts them.
* **7.91 µm**, finer than the model's training pitch, and the raw scan, not a masked or standardized volume.
* **One hand tracing.**

## Amendment 1: the fetch converts the scan a slab at a time (2026-11-08, 17:10 PST, before any field)

**What happened.** The run started at 12:06 PST from `a1060b39`. The fetch had cached all 1,088 slices by 13:25:20.
At 13:26:04, systemd-oomd killed the cgroup the run was launched from (a terminal scope, 11 processes, including the
session that launched it) on memory pressure. This login's `user@1000.service` carries Ubuntu's
`ManagedOOMMemoryPressure=kill` at a 50% limit held for 20 s, and the scope's pressure was 61% (avg10). The host was
not out of memory: sysstat shows 18.2 GB available at 13:20, with direct reclaim at 1,897 pages/s in 13:20–13:30.
While converting, the whole-region fetch held the uint16 region (2.58 GB), its uint8 copy (1.29 GB) and float64
temporaries. Nothing was written: no `context.npy`, no field, no row. `setsid` had detached the run from the
terminal's session but not from its cgroup.

**What changes.** `fetch` now writes the uint8 scan into a memory-mapped `.npy`, 16 slices at a time
(`write_uint8_scan`). It calls the same ScrollGT functions (`read_tiff_region`, then `to_uint8`) on the same cache
files: each slice is named by its z and the fixed y, x window, and the conversion goes voxel by voxel. So the voxels
are those of the whole-region fetch. A test compares the two on a synthetic cached region over the full uint16 range
(three slabs, the last one short), and catches 4 seeded off-by-one and wrong-range mutants. The core check is
unchanged, and the file is renamed into place only after it passes. The run is launched in its own systemd user unit
(`systemd-run --user`), still at nice 19. A pressure kill elsewhere in the login then cannot take it, and its own
kill cannot take a session. The method, gate, predictions and decision rule are unchanged. The verdict now falls
about 16 hours after the relaunch.
