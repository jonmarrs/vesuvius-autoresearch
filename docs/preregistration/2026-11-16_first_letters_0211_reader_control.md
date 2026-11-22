# Pre-registration: on the surface that won PHerc. 211's First Letters prize, does our reader see the ink the winning reader saw?

**Written 2026-11-16, before our reader has been run on that surface.** Finding 118.

PHerc. 211's First Letters prize was awarded on 2026-11-15 (the organisers' announcement, "First letters emerge
from PHerc. 211": Priyank Aranke, $50K; "There are still seven First Letters Prizes waiting to be awarded on other
scrolls"). The winner published the surface, the probability map and the CT images of the submission under
CC BY-NC 4.0. This step reads those files and the public scan. Our render and ink maps of that surface stay on
this machine until the owner decides otherwise; the report carries numbers.

## The question

Every ink read in this campaign has used the PHerc. 343 recipe's four released models. Finding 111 found that on
a correct surface of an unseen scroll (PHerc. 0841) they locate labelled ink at AUC 0.72 to 0.75 and draw no
readable letter. So a blank read of an eligible band says little until we know what the reader does where letters
are known to be. PHerc. 211 now has such a place: an 8 cm² hand-refined surface on which a different reader drew
eleven letters the organisers accepted. **On that surface, with the geometry taken as given, do our four models
put ink where the winning reader put it?**

This is the reader half of a positive control. The geometry half, whether the recipe's fit puts a winding on that
surface, needs a fit of a new band and is registered separately.

## Reachability, checked before this was written

- **The files.** From the submission's public folder (linked from the announcement): the three-row surface
  `PHerc0211-crop1711-lines123-manual-20261028-1316-legacyuv20-v9` (`_mesh.zip`, SHA-256 `819dcfb4…`), its
  probability map (`_studiosoft_probability_f32.tif`, `527c6fbb…`) and its CT image (`_ct_layer.tif`, `9c4bd4f5…`).
  `repro/first_letters/pherc0211_control/fetch_winner.sh` holds the full checksums.
- **The same scan and raster.** The surface's `meta.json` names the public volume
  `20250821151803-9.362um-1.2m-113keV-masked.zarr`, the one finding 112 read. The surface is a grid of 87 by 301
  nodes at 20 voxels a node; the map, the CT image and the mask are all 1740 by 6020 pixels, the size our renderer
  gives that grid at scale 1.
- **Where it is.** z 7524 to 9312, about 487 voxels (4.6 mm) from the published scroll axis: an inner winding,
  below finding 112's band (z 10250 to 11750). Finding 113's strips therefore cannot serve as this control.
- **The side.** 99.5% of the surface's nodes have normals pointing away from the scroll axis, as finding 110's
  PHerc. 343 windings do. So it is rendered without `--flip-normals`, and by the PHerc. 343 arrangement the
  reading side is the `_reverse` maps at depth +1.
- **Exposure.** The winner's README says PHerc. 211 was not used to train the winning model; the strategy review of
  2026-11-16 notes it was evaluated during that model's development. dense_native's training configuration lists
  no PHerc. 211 data. I have not checked the training data of the two ink_9um seeds or Hecate.
- **Not checked:** the render and ink scripts in `repro/first_letters/pherc0211_control/` have not run, and I have
  not opened the winner's probability map beyond its size and type.

## Procedure

Scripts in `repro/first_letters/pherc0211_control/`, run once each. Run directory
`spiral_out/first_letters/pherc0211_control`, on this machine.

1. `fetch_winner.sh`: the files above, checked against their checksums.
2. `run_render.sh`: 66 layers, one voxel apart, scale 1, not flipped, the image and sampler of the eligible-band
   renders, CT streamed from the public bucket.
3. `run_ink.sh`: the recipe's depth sweep, unchanged: four models, both sides, depths −3 to +2, as finding 113.
4. `compare.py`:
   - **Alignment, before any ink.** Of render layers 25 to 41, the one whose Pearson r with the winner's CT
     image is highest, and the shift of at most 16 pixels that maximises their cross-correlation. Within 1 pixel,
     the rasters are taken as the same. Otherwise our maps are moved by that shift, in whole 4-pixel cells, and
     the report says so. No alignment within 16 pixels: `DOES_NOT_RUN`.
   - **Cells:** 4 by 4 pixel blocks wholly inside the winner's `studiosoft-mask.png`, with CT in all 66 layers of
     our render and a lattice position on the mesh.
   - **Ours:** the four-model ensemble of finding 110 (each model's map scaled as the recipe's `ensemble_maps.py`,
     z-scored over the cells, averaged) on the reading side at depth +1, with its broad background taken off
     (Gaussian, sigma 16 cells). **Theirs:** the winner's probability map, block means, background taken off the
     same way.
   - **r** = Pearson over the cells. **Controls:** our other side at depth +1 against theirs; ours slid by 64
     pixels in each of four directions, the largest absolute r.
5. **Described, not deciding:** each of our models alone; every depth and side; the maps with their background;
   how far our four models agree with each other on this surface; a slide of 256 pixels; the correlation of the
   two maps' row profiles. And an image of the two maps one above the other, for the owner to look at, on this
   machine.

## Predictions, fixed now

- **What I expect: `READER_PARTLY`**, with low confidence. Our models locate ink on an unseen scroll (finding
  111) but drew no letter there; the winning reader is newer and was trained for 9 µm scans from labels distilled
  from a 2 µm model.

## Decision rule

| outcome | verdict |
|---|---|
| a step fails, no alignment within 16 pixels, or fewer than half the mask's cells are compared | `DOES_NOT_RUN` |
| r at least 0.30 and at least twice the absolute value of each control | `READER_AGREES` |
| r at least 0.15 and at least twice each control, below 0.30 | `READER_PARTLY` |
| otherwise | `READER_DISAGREES` |

The 0.30 and 0.15 lines are judgements. The nearest number we have is finding 110's: our ensemble against the
published one on PHerc. 343, the same four models, r 0.86. Two different readers that both find the strokes
should agree less than one reader with itself.

What each does to the campaign:

- `READER_AGREES`: our reader finds, on a readable surface of a crushed scroll, the ink the winning reader found.
  The reader is not what stands between us and letters; the geometry half of the control comes next.
- `READER_PARTLY`: our reader carries some of that ink and would likely miss letters the winning reader shows.
  Before any further band is read, register a run of the winning reader's released weights here, on this
  surface first. Whether its CC BY-NC weights may be used for a submission is the owner's question.
- `READER_DISAGREES`: our reader does not see this surface's ink. No eligible band is read with it again;
  finding 113's read is moot as a detection test. The winning reader is the candidate, on the same terms.

In every case the geometry half follows, registered separately.

## What the result cannot do

- **One surface, one scroll, one reference reader.** The reference is the winning reader's map, not the letters
  themselves. A reader could see the letters and disagree with that map where the map is wrong.
- **Pixels are not letters.** r measures where two maps put ink, not whether ours is legible. The image is for
  the owner's eye and decides nothing here.
- **Exposure is not settled for three of our four models.**
- **The surface is a winner's surface**, refined by hand until letters showed under the winning reader. That
  favours the winning reader's map over ours.

## Limits

The depth, the side, the controls and the lattices are finding 110's. The 0.30 and 0.15 lines, the half of the
mask and the alignment search are judgements made here.

## Cost

Render about 10 minutes on CPU, ink about 20 minutes on the GPU (the recipe's four models, about 7.5 GB), the
comparison under a minute. No fit, no upload.
