# Pre-registration: does the recipe's fit of a PHerc. 211 band put a winding on the surface that won the prize?

**Written 2026-11-16, before any fit of this band has run.** Finding 119.

PHerc. 211's First Letters prize was awarded on 2026-11-15; the winner published the surface of the submission
under CC BY-NC 4.0. This step fits a band of the public scan around that surface and compares. The fit, its
windings and the distance field stay on this machine until the owner decides otherwise; the report carries
numbers.

## The question

Findings 112 to 117 judged fits by the sheet-following score, which finding 116 showed cannot tell a spiral that
follows the sheets from one turning the wrong way, and finding 117 checked tile by tile only on PHerc. 343, a round
scroll. On a crushed scroll there has been no reference surface to check a fit against. PHerc. 211 now has one: an
8 cm² surface on which the winner read eleven letters. **If the recipe's fit, run unchanged on a band of PHerc. 211
that contains that surface, is snapped as for a read, does one of its windings lie on the winner's sheet?**

This is the geometry half of the positive control whose reader half is finding 118 (registered 2026-11-16 on
branch `research/first-letters-0211-reader-control`, commit `11ba1c41`). Together they say whether the pipeline
of findings 112 and 113 could have found letters where letters are known to be.

## Reachability, checked before this was written

- **The reference.** The winner's three-row surface `PHerc0211-crop1711-lines123-manual-20261028-1316-legacyuv20-v9`
  (finding 118's files, same checksums): 87 by 301 nodes, 20 voxels apart, z 7524 to 9312 in the public volume
  `20250821151803-9.362um-1.2m-113keV-masked.zarr`, about 487 voxels from the published scroll axis.
- **The band.** z 7650 to 9150: 1,500 slices, as in findings 112 and 114 to 116, centred on the surface (its
  middle is z 8418). It holds the second text row whole (z 8107 to 8827) and about 90% of the surface's nodes
  (its 5th to 95th percentile of z is 7752 to 9112). Only the surface's nodes inside the band are measured.
- **The fit reaches that radius.** In finding 112's band, raw windings near a radius of 487 voxels are about w030
  to w035; the fit starts at w010 (median radius 126).
- **The winner's surface came from the same kind of fit.** Its case file names a crop of "a full-height spiral fit
  of PHerc0211 made with the VC spiral fitter", stitched and refined by hand. So our fit is not independent of
  the reference's starting point, and a fit near it is more likely than it would be for an independent surface.
- **Inputs.** The band scripts take a second band of one scroll since commit `cc1fe41f` (run directory
  `spiral_out/first_letters/pherc0211_band_z7650`, chunk ranges from the band, the default band's unchanged and
  tested). The tracks are finding 112's, linked; they cover z 4500 to 17500. The download of this band's arrays
  started before this was written; nothing has been computed from them.
- **Not checked:** nothing of this band has been fitted, snapped or measured.

## Procedure

The eligible-band scripts with `FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150`, unchanged
otherwise: the recipe's overrides and villa's defaults (130 windings, seed 1), direction ACW from the catalog.

1. `setup/fetch_volumes.sh`, `setup/make_dataset.sh`, `run_sdt.sh`.
2. `run_fit.sh smoke 300`, then `run_fit.sh full` (30,000 steps). `run_quality.sh full`: the sheet-following
   score of every raw winding, described.
3. `winner_sheet.py choose` (`repro/first_letters/pherc0211_control/`): every raw winding against the winner's
   nodes in the band by finding 110's `surface_distance`; the chosen winding is finding 110's choice, the smallest
   median among windings that cover at least half of those nodes. It writes the snap list: the chosen winding and
   both index neighbours.
4. `run_snap.sh full`: the recipe's snap of those windings.
5. `winner_sheet.py verdict`: the snapped chosen winding against the winner's nodes, and the verdict.

Described, not deciding: the raw chosen winding's numbers and the next two closest; the share of the winner's nodes
within 2 and 4 voxels of any raw winding; the snapped neighbours; and finding 117's tiles of the chosen raw winding
labelled against the winner's surface, with their AUC if there are at least 15 of each label.

## Predictions, fixed now

- **What I expect: `PARTLY_ON_IT`**, with low confidence. On PHerc. 343 the raw fit had 33% and 47% of the
  published nodes within 2 voxels and the snapped windings 76% and 81%. PHerc. 211 is crushed, and its fit scored
  lower than PHerc. 343's (finding 112: median excess 0.086 against 0.140). Against that, the reference started as
  the same kind of fit.

## Decision rule

| outcome | verdict |
|---|---|
| a step fails, or no raw winding covers half the winner's nodes in the band | `DOES_NOT_RUN` |
| the snapped chosen winding has at least 50% of those nodes within 2 voxels and a median of at most 3 voxels (finding 110's P1) | `ON_THE_WINNERS_SHEET` |
| otherwise, at least 25% within 2 voxels | `PARTLY_ON_IT` |
| otherwise | `OFF_IT` |

What each does to the campaign:

- `ON_THE_WINNERS_SHEET`: unrefined, the recipe's fit and snap reach a readable sheet of a crushed scroll here.
  With finding 118's reader result, the pipeline's sensitivity at one known place is then measured. Next: read the
  snapped winding with the reader finding 118 supports and compare with the winner's map, registered separately.
- `PARTLY_ON_IT`: the fit gets near the sheet but not onto it over most of the area; a read needs local
  refinement, as the winner did by hand. A blank read of an unrefined band is weaker evidence than findings 112 and
  113 assumed.
- `OFF_IT`: the unrefined fit does not reach readable geometry here. Reads of unrefined bands say almost nothing
  about letters, and refinement becomes the campaign's first problem.

## What the result cannot do

- **One place, one surface, one fit.** The surface is where letters were found because someone refined it there.
- **The reference is not independent of the method**, as above. A fit far from it is a strong negative; a fit on
  it is a weaker positive than it would be for an independent surface.
- **"On the sheet" is within 2 voxels of the winner's surface**, which is one author's surface.
- It says nothing about ink; that is finding 118 and the step after.

## Limits

The band, the 25% line and the choice of the snapped winding as the test are judgements made here. The 50% and
3-voxel lines, the distances and the choice rule are finding 110's.

## Cost

Downloads about 7 GB, the distance field about 15 minutes of CPU, the fit about 3.5 hours of the GPU (finding 112:
3 h 19 min, 10.3 GB), the snap tens of minutes of CPU, the comparison under a minute. No upload.
