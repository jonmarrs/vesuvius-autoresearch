# Pre-registration: at what depth does Studio read our geometry best, where PHerc. 211's First Letters prize was won?

**Written 2026-11-22, before any Studio map of a shifted set of planes exists.** Finding 135.

## The question

Every band read gives Studio layers 41 down to 26 of the 66-layer render frame. That window was matched to the
winner's own Studio input on the winner's surface (finding 123: plane i against our layer 41 − i, r about 0.95 by
CT). Our surfaces are not the winner's: they are the recipe's fit, snapped to the predicted sheet and flattened by
us. If they sit a voxel or two off where the winner's surface sits, the same window reads a little beside the ink,
on every winding of every band. Nothing has measured this. Findings 131 and 134 moved the surface within the
winding and saw no change in the read; neither moved the window.

**At the one place where this pipeline reads a known text, does Studio agree more with the winner's map when its
16 planes are taken D layers further out or further in?**

Two things change with the answer:

1. **If a shift reads better,** findings 129 (PHerc. 0813) and 133 (PHerc. 0800), held for disk and with no data
   yet, could read with it, and PHerc. 0826 and 0358 could be read again from their 66-layer renders (Studio only).
2. **Either way,** the fall of r with |D| is Studio's tolerance to a depth error on our geometry. It says how far
   off the sheet a band's surface can be before letters there would stop showing. That helps read a blank band.

## Reachability, checked before this was written

- **The planes.** `depth_sweep.py planes --shift 0` on finding 121's w035 render gives a file byte-identical to
  `studio_e2e.py planes` (finding 124's input). Shifts −8 and +8 give layers 33 to 18 and 49 to 34, both inside the
  66-layer frame. The planes move as intended: plane 0 at −8 is plane 8 at 0 (layer 33), and plane 8 at +8 is plane
  0 at 0 (layer 41). A shift of +25 is refused (layer 66 is outside the frame).
- **The 211 comparison reproduces finding 124.** `depth_sweep.py compare` was dry-run today with each arm's existing
  maps (D = 0) standing in for every shift. Arm `e2e` gave r 0.8247 on 457,405 cells, finding 124's registered r on
  its cells, and finding 124's per-winding r (0.8737, 0.7776, 0.8238, 0.7527). Every shift gave the same r, so the
  verdict was `DEPTH_ZERO_BEST`. The final nodes' shares within 2 voxels of the predicted sheet were finding 131's
  (0.9034, 0.7742, 0.9105, 0.7973). Arm `dense2s3` (finding 134's windings and maps) gave r 0.8135 on its 458,383
  cells. Normal cosines were −0.9962 to −0.9992: every winding's normals point against the winner's, so its
  flipped render samples along them, as finding 124 requires. Transfer distances were 1.94/3.45 voxels (e2e) and 1.90/3.44 (dense2s3) at the median and
  95th percentile.
- **The 343 comparison reproduces finding 127.** `depth_sweep.py compare343`, dry-run the same way, gave r 0.6238
  on 551,720 cells, finding 127's registered r.
- **The inputs are on this machine.**
  - Finding 121's four final windings with 66-layer renders, and finding 124's maps of them.
  - Finding 134's dense2s3 windings with 66-layer renders, and its maps.
  - Finding 110's 66-layer render of the recipe's PHerc. 343 surface, and finding 127's maps of it.
- **Which way D points.** A render's layers run outward from the scroll's axis. At 211 that holds because our
  windings' normals point inward and were rendered flipped (finding 121). At 343 the recipe's normals point outward
  (0.9973) and the render is not flipped. So D > 0 reads further from the axis at both places.

## The floor

Within an arm, only Studio's input changes: the geometry, the transfer and the cells are the same for every shift.
The floor is therefore Studio's own repeatability. Finding 132 found the winner's loop gives identical maps when run
again; the `repeat` step measures it once more here (finding 124's w035 planes again), described. The line is
findings 131 and 134's 0.02 in r. Their re-run noise (|r(rerun) − r(f124)| = 0.0037) came from a re-flatten, which
this study does not do.

## Arms

| arm | maps | what varies | held fixed | verified how |
|---|---|---|---|---|
| `e2e` | `pherc0211_control/work/studio_e2e/maps` (D = 0), `pherc0211_control/work/depth_sweep/maps/e2e/d<D>` | D | finding 121's final windings w033 to w036 and renders `pherc0211_band_z7650/work/render_e2e`; Studio's weights, code and command | dry run above |
| `dense2s3` | `pherc0211_control/work/snap_passes/maps/e2e_dense2s3` (D = 0), `pherc0211_control/work/depth_sweep/maps/dense2s3/d<D>` | D | finding 134's windings and renders `pherc0211_band_z7650/work/render_e2e_dense2s3` | dry run above |
| 343 (described) | `pherc343_repro/work/studio_343/maps/forward.npy` (D = 0), `pherc0211_control/work/depth_sweep/maps/343/d<D>` | D | finding 110's render of the recipe's surface | dry run above |

The shifts are D = −8, −6, −4, −2, −1, 0, +1, +2, +4, +6, +8. The neighbouring sheets in PHerc. 211 are about 14
voxels away (finding 112's profile, at the band z 10250 to 11750), so ±8 stays on this sheet's side of them.

## Procedure

`repro/first_letters/pherc0211_control/run_depth_sweep.sh`, once, each step only if the one before exited 0:

1. **check.** Finding 123's weights and the winner's `inference.py` against their SHA-256 values.
2. **sweep211.** For each arm, shift other than 0 and winding: `depth_sweep.py planes`, then Studio with the
   winner's command (`--stride 64 --blend hann --batch-size 32`), exactly as finding 124 ran it.
3. **sweep343.** The same on the PHerc. 343 render.
4. **repeat.** Studio again on finding 124's own w035 planes; the largest difference from finding 124's map.
5. **compare.** `depth_sweep.py compare` (registered) and `depth_sweep.py compare343` (described).

## Registered measure and verdict

- **r:** finding 124's statistic. It is Studio's map carried onto the winner's surface by finding 110's transfer,
  against the winner's map, with the broad background off. It is computed for each arm and shift on the cells that
  every shift of that arm reaches.
- **D\*:** the shift with the largest r summed over the two arms, to 4 decimals. Ties go to the smaller |D|, then to
  D > 0.
- **gain:** for each arm, r(D\*) − r(0), to 4 decimals.

| verdict | rule |
|---|---|
| `DEPTH_SHIFT_READS_BETTER` | D\* ≠ 0, and the gain is at least 0.02 in both arms |
| `DEPTH_SHIFT_WITHIN_MARGIN` | D\* ≠ 0, and the gain is under 0.02 in at least one arm |
| `DEPTH_ZERO_BEST` | D\* = 0 |
| `DOES_NOT_RUN` | any of: a step failed; arm `e2e` at D = 0 does not give r 0.8247 on finding 124's own cells; a winding gives no cells, or its render samples against the winner's normals (cosine 0 or above); an arm reaches under half the winner's mask cells; a shift of either arm is missing or unscored |

The tests check that `DOES_NOT_RUN` gives no shift and no gain even when one shift reads far better. They also check
that a sweep missing an arm or a shift is refused.

**Described, deciding nothing:**

- every arm's r, controls and overlap at every shift;
- each winding's r at every shift;
- half-widths: on each side, the smallest |D| at which r is at most half of r(0);
- the repeat's largest difference;
- at PHerc. 343: r at every shift, its own best shift, whether it reproduces 0.6238, and its half-widths.

## Predictions, fixed now

1. **`DEPTH_ZERO_BEST`, moderate confidence.**
   - For: the window was matched to the winner's input by CT. Our surfaces carry the winner's ink to within 1.94
     voxels at the median, with no measured signed bias. Studio sees 16 layers at once, so a 1-layer shift moves
     only one plane in and one out.
   - Against: our snap pulls a surface to the predicted sheet's middle, and the winner's surface may follow one face.
2. **Shifts of ±1 and ±2 change r by less than 0.05** in both arms.
3. **No prediction on the half-widths or on which side falls faster.** The reasoning does not support one: the ink
   lies on one face of the sheet, so the two sides need not match.
4. **At PHerc. 343 the best shift is −1, 0 or +1**, low confidence.
5. **The repeat is identical** (finding 132).

## Consequences

- **`DEPTH_SHIFT_READS_BETTER`:** nothing is amended yet. 211 is one crushed scroll, and both arms are the same four
  windings. A confirmation on our own windings of PHerc. 343 is registered next: finding 110's w047 and w048, read
  at D\* and at 0 and carried onto the recipe's surface. Only if it agrees are findings 129 and 133 amended, before
  any of their data exist, to read layers 41+D\* down to 26+D\*. Their 18-layer renders would grow to hold those
  layers. Re-reading PHerc. 0826 and 0358 from their 66-layer renders would then be the owner's call, since it keeps
  those renders on disk.
- **`DEPTH_SHIFT_WITHIN_MARGIN`, `DEPTH_ZERO_BEST` or `DOES_NOT_RUN`:** the band reads keep layers 41 to 26. The
  report gives the curve as Studio's depth tolerance on our geometry.

## What the result cannot do

- **"Reads better" is agreement with the winner's Studio map, not legibility to an eye.**
- **A uniform shift is not a sheet switch.** A band's surface that leaves its sheet is off by 14 voxels or more, on
  another sheet. This study's ±8 does not reach there, so the half-widths do not say how a sheet switch reads.
- **The half-widths are not a power calculation for the eligible bands.** Their distances are to a predicted sheet,
  not to a known surface, and their papyrus and ink differ from PHerc. 211's. A report may quote the half-widths
  beside a band's share of nodes within 2 voxels. It may not turn them into a probability that letters would have
  shown.
- **Studio was trained with the winner's preprocessing.** If D\* ≠ 0 at 211 but 0 at 343 on the recipe's surface,
  the shift corrects our geometry, not Studio. If both move, it may be Studio's. Either is a reading, not a test.

## Limits

One place on one scroll for the verdict: four windings, in two geometries that share their fit. One reader, one
machine. The 343 sweep is on someone else's surface, so it describes Studio, not our pipeline.

## Cost

About 2.5 hours:
- 80 Studio maps at 211 of about 74 s each (finding 134's step: 595 s for 8);
- 10 at 343 of about 104 s (finding 127: 208 s for 2);
- 91 plane extractions of about 10 s;
- the comparisons, a few minutes.

GPU memory up to about 15 GB. About 4.3 GB of maps on disk (62 GB free when written); each set of planes, about
0.2 GB, is deleted after its map. Nothing is fitted, flattened, rendered or downloaded. It runs alone: findings 129
and 133 stay held for disk and do not start while it runs. PHerc. 211's prize was announced, and PHerc. 343's letters
are published, but these maps stay on this machine as findings 124 and 127's did.
