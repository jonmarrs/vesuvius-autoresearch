# Pre-registration: the recipe's fit of a PHerc. 0813 band, read by Studio, as images for the owner

**Written 2026-11-20, before any input of PHerc. 0813 has been downloaded or fitted.** Finding 129.

## The question

Findings 125 and 126 read anticlockwise eligible scrolls (PHerc. 0826 and 0358) the way finding 124 read PHerc. 211.
PHerc. 0813 is eligible for First Letters. It is clockwise, like PHerc. 343, where the recipe's fit found letters,
and since September it has every input the fit needs. **Fitted and read the same way, does any winding of a PHerc.
0813 band show letters to the owner's eye?**

## Reachability, checked before this was written

- **Every input the fit needs is published** (read 2026-11-20, anonymous listings and headers):
  - the scroll axis `PHerc0813/representations/umbilicus/20250821151723-umbilicus-20260924033203.json`: 141
    control points, z 1808 to 16864;
  - the m7 surface prediction (level 1: 8497 × 3974 × 3974 in 192-voxel chunks) and the lasagna run
    (`nx`, `ny`, `grad_mag`, group 2: 32-voxel chunks), with the same stamps as PHerc. 0211's, 0826's and 0358's;
  - the CT volume `20250821151723-9.362um-1.2m-113keV-masked.zarr`, at the band scripts' 9.362 µm;
  - the spiral tracks at `dl.ash2txt.org/datasets/spiral_datasets/PHerc0813/20250821151723/tracks/`: 8.2 GB.
- **The direction.** The open-data catalog's `metadata.json` gives `z_direction_is_top_to_bottom` false and
  `left_handed_coordinates` false: clockwise, as for PHerc. 343.
- **Orientation for a clockwise scroll.**
  - The render rule (flip a winding when most of its normals point inward) is physical. It makes layers run
    outward. On PHerc. 343 the recipe's windings point outward (99.73%) and were rendered unflipped.
  - **Inward is now measured against the published scroll axis**, not the band's mean node position. On PHerc.
    0826's read the band's mean lay off the axis (`band_geometry.py`, described after finding 125). Two inner
    windings that point inward on 90% of their nodes against the axis scored 49% against the mean, and were
    rendered the wrong way.
  - The reading-orientation rule of the inspection page (`band_index.py`, from the recipe's `measure_orientation`
    and the catalog's flags) covers both directions. With these flags it is the recipe's own rule, unchanged.
- **The band.** The tracks' `effective_z_bounds` are 4500 to 16993. The middle 1,500 slices of the tracked range
  are **z 9996 to 11496**, inside the axis.
- **The reader is Studio, with the winner's command.**
  - Finding 127 (`STUDIO_343_AGREES`) showed Studio draws PHerc. 343's published letters on the recipe's surface:
    r 0.6238 against the recipe's ensemble, above each of its four models against the other three, with controls of
    0.1015 and 0.2146. PHerc. 343 is clockwise, as PHerc. 0813 is. So a blank Studio band says something about the
    band, and the slower ensemble is not run beside it.
  - Finding 128 (`WINNERS_TILING_KEPT`) found Studio's published tiling 2.4 times faster but short of the winner's
    command (r 0.9396, 94.0% of pixels on the same side of 0.5, against lines of 0.98). So `STUDIO_TILING` is left
    at its default, `winner`.
- **The scripts** are finding 126's chain, unchanged except for:
  - PHerc. 0813's entry in `env.sh`, and the scan named per scroll (the same 9.362 µm for PHerc. 0813);
  - `run_studio_band.sh`'s `STUDIO_TILING` option (finding 128), left at `winner`;
  - a disk guard in `run_studio_band.sh`: a winding is not rendered while the run directory's disk has less than
    50 GB free; its render step exits 28 and is recorded like any failed step, the windings already rendered are
    still read, and nothing is deleted to make room;
  - `studio_band.py orient --umbilicus`, the axis rule above;
  - `FL_DENSIFY=2`: the selected raw windings are subdivided twice before the snap (`densify_winding.py`). Finding 130
    found this keeps more of the rendered surface on the predicted sheet: +0.070 at the median over six of PHerc.
    0826's windings (`DENSE_SNAP_HELPS`), whose registered consequence is that later reads snap a twice-denser grid.
- **Not checked:** nothing of PHerc. 0813 has been downloaded. Its band's size, track count and fit cost are
  unknown.

## Procedure

`FL_SCROLL=PHerc0813 FL_Z_BEGIN=9996 FL_Z_END=11496 FL_DENSIFY=2 run_band_and_read.sh` (`repro/first_letters/eligible_band/`), run
once, each step only if the one before exited 0. The steps are finding 126's: inputs, distance field, smoke and full
fit at villa's defaults, quality, selection of the windings with positive excess, their subdivision, then the read. The read is the
snap, the stacked check, flatten, orient, render, Studio on our layers 41 down to 26, and the images.

Afterwards, described: `band_geometry.py` (normals against the axis, the share of each rendered winding within 2
voxels of the predicted sheet, trust masks), `band_record.py`, and the inspection page with `band_index.py
--top-to-bottom false --left-handed false --geometry`.

## Predictions, fixed now

- **The fit:** `PARTLY_ON_SHEETS` or better by finding 112's table, with low-to-moderate confidence.
- **The read:** letter-like shapes on some windings, and a readable run of three or more letters on none, with low
  confidence.

## Decision rule

As finding 126's: the fit's numbers decide only which windings are read, and the read has no automatic verdict.

- **The owner sees letters:** that place is a candidate. A submission-quality image and whether to submit are
  registered separately and are the owner's decisions.
- **The owner sees none:** this band shows no letters under this pipeline.

## What the result cannot do

- **A negative is weak:** one band, unrefined, windings that can leave their sheet.
- **A positive is the owner's reading.**
- **Disclosure.** The images stay on this machine, and the report carries numbers only. I do not view them.
- **Licence.** Studio's weights and outputs are CC BY-NC 4.0.

## Cost

Finding 125 read 70 windings of PHerc. 0826's band in 8 h 48 min: per winding a median of 80 s to flatten, 140 s to
render and 254 s for Studio, on render canvases of a median 37 million pixels. The renders took 102.4 GB, about 1.5 GB
a winding, and Studio's maps 9.3 GB. Finding 130 found the flatten of a twice-denser snap takes 134 to 254 s a
winding.

So a band of about 100 windings takes about a day and a half: about 3.5 h of fit, then about 4 h of flatten, 4 h of
renders and 7 h of Studio. Its renders take about 150 GB. On 2026-11-20 the disk had 339 GB free, with finding 126's
band read still to write; the guard above stops the renders, without deleting anything, if the two together do not
fit. Whether to delete finding 125's renders (96 GiB) to make room is the owner's decision. It starts after finding
126's chain. GPU memory up to about 15 GB. Nothing is uploaded.

## Amendment 1 (2026-11-20, before any input of PHerc. 0813 has been downloaded)

**The read renders the 18 layers it uses, not 66.** Studio reads layers 41 down to 26 and the summary reads the
surface layer 33; nothing in the read uses the others. Finding 125's 66-layer renders took 102.4 GB for 70 windings,
and with finding 126's read still to write, the disk guard above could stop this read's renders part way.

- **Why 18 layers give the same bytes.** The renderer places layer i of an n-layer render at (i − (n − 1) / 2) along
  the normal, so a render of 18 layers holds layers 24 to 41 of the 66-layer render at the same offsets.
- **Checked on three of PHerc. 0826's windings** (finding 125's arm `outer80`): w010 (rendered unflipped), w012 and
  w050 (flipped).
  - Each 18-layer render's layers equal layers 24 to 41 of its 66-layer render byte for byte.
  - Studio's 16 planes from them (`studio_e2e.py planes`) are byte-identical for w012 and w050.
  - They take 0.28 of the disk: 40 MB, 55 MB and 473 MB, against 145 MB, 199 MB and 1.7 GB.
- **Time is not claimed.** The three renders ran during finding 126's download, at 63, 67 and 179 s, against 117,
  55 and 127 s for their 66-layer renders on 2026-11-20. The renderer is bound by reading the CT's 128-voxel chunks,
  which a thinner shell barely reduces.
- **The change:**
  - `run_render.sh` takes `RENDER_SLICES` (an even number from 18 to 66; default 66, so earlier findings' renders
    are unchanged) and names its output `wNNN_N.zarr`;
  - `run_studio_band.sh` renders and reads 18 layers;
  - `studio_e2e.py planes` and `studio_band.py summarise` find the 66-layer frame's layers in either render
    (`render_frame.py`).
- **Lost:** the CT layers outside 24 to 41 are not kept. A later look at them re-renders the winding.
- **Unchanged:** the band, the fit, the selection, the snap, the orientation rule, the reader, its command and its
  input, the summary's numbers, and the decision rule.
