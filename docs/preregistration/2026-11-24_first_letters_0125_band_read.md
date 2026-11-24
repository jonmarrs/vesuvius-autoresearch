# Pre-registration: the recipe's fit of a PHerc. 0125 band, declared clockwise, read by Studio, as images for the owner

**Written 2026-11-24, before any fit or read of PHerc. 0125.** Its fit inputs were downloaded on 2026-11-13, for a band
fit that was set aside because the scroll's winding direction is not published; nothing of it has been fitted,
snapped, rendered or read. Finding 139.

## The question

Findings 125, 126, 129 and 133 read bands of PHerc. 0826, 0358, 0813 and 0800 the way finding 124 read PHerc. 211.
PHerc. 0125 is eligible for First Letters, and its scroll axis and fit inputs are published, but its winding direction
is not. Finding 137 (`WRONG_HAND_READS_ALIKE`) found that at PHerc. 211's prize place a fit declared to turn the wrong
way reads the winner's text as well as the published direction does (r 0.841 on 0.8337 of the mask cells, against
0.8247 on 0.8309). Its registered consequence: a band read of PHerc. 0125 may be registered with either direction
declared, and its pages would show the sheet crossings as breaks. **Fitted with a declared direction and read the same
way as PHerc. 0800, does any winding of a PHerc. 0125 band show letters to the owner's eye?**

## Reachability, checked before this was written

- **The inputs are on this machine** (`spiral_out/first_letters/pherc0125_band/`, downloaded 2026-11-13 from the
  public bucket, anonymous):
  - the scroll axis `PHerc0125/representations/umbilicus/20250821151825-umbilicus-20260808111524.json`: 83 control
    points, z 2140 to 20354;
  - the m7 surface prediction (`20250821151825-surface-20260413222639-surface-m7-L0-th0.2.zarr`), the lasagna run
    (`nx`, `ny`, `grad_mag`) and the CT `20250821151825-9.362um-1.2m-113keV-masked.zarr` (level 0 is
    20840 × 8387 × 8387 bytes), the chunks the default band touches;
  - the spiral tracks: 13,776,380 tracks and 765,480,031 points (21 GB on disk), `effective_z_bounds` 4500 to 17500.
  The chain's download steps are resumable and fetch only what is missing.
- **The scan:** 9.362 µm, 113 keV, 1.2 m, `env.sh`'s default scan.
- **The band:** the middle 1,500 slices of the tracked range, **z 10250 to 11750**, inside the axis.
- **The direction:** the open-data catalog (`metadata.json`, read 2026-11-15) gives `z_direction_is_top_to_bottom`
  null and `left_handed_coordinates` false, so villa cannot derive it and `env.sh` refuses PHerc. 0125 unless
  `FL_SENSE` is set. Two attempts on 2026-11-22 to measure it from the surface prediction failed (finding 137's
  registration). This read declares **`FL_SENSE=CW`**: villa's own tools assume clockwise when a checkpoint names no
  direction (`flatten_spiral_checkpoint.py`, `find_inconsistent_windings.py`), both in the repository's villa and in
  the copy the fit runs (villa `0fb38c45` with the recipe's patch). The choice rests on that default and on finding
  137, not on any evidence about this scroll.
- **The reader and the scripts** are finding 133's: `run_after_controls.sh` reads findings 131, 132 and 134's records
  (today `STUDIO_SKIP_EMPTY=1`, `FL_DENSIFY=2`, `FL_SNAP_PASSES=3`), and the read overlaps renders and Studio
  (`FL_OVERLAP=1`).
- **Not checked:** the band's size, its share of the tracks and the fit's cost. Each slice of PHerc. 0125's level 0
  is 8387² voxels against PHerc. 0826's 8169², at the same voxel size.

## Procedure

```sh
FL_SCROLL=PHerc0125 FL_SENSE=CW FL_Z_BEGIN=10250 FL_Z_END=11750 FL_OVERLAP=1 \
  run_after_controls.sh bash run_band_and_read.sh
```

In `repro/first_letters/eligible_band/`, run once, each step only if the one before exited 0. The steps are finding
133's:
1. inputs, distance field, smoke and full fit at villa's defaults, declared clockwise;
2. quality, then the selection of the windings with positive excess, and their subdivision;
3. the read: snap (three passes), the stacked check, flatten, orient by the axis, 18-layer renders, Studio on our
   layers 41 down to 26, and the images.

Afterwards, described:
- `run_quality.sh smoke` and `band_fit_verdict.py` (finding 112's table needs the 300-step fit's score);
- `band_geometry.py --masks`;
- `band_record.py --finding 139 --quality-arm full`;
- the inspection page, `band_index.py --top-to-bottom false --left-handed false --geometry`. The catalog's
  `z_direction_is_top_to_bottom` is null; false is assumed. **If it is in truth true, every image on the page stands
  turned by 180 degrees**: the flag reverses both the page's flips, and the mirror is measured from each winding's own
  geometry, so a wrong declared direction does not mirror the images;
- at the band's middle slice, z 11000: `outer_sheets.py` and `sheet_coverage.py`, as for finding 133.

## Predictions, fixed now

- **The fit:** `PARTLY_ON_SHEETS` or better by finding 112's table, low confidence. Finding 116's wrong-handed fit of
  PHerc. 0826 scored like the right one, so the declared direction should not decide this.
- **The read:** letter-like shapes on some windings, and a readable run of three or more letters on none, low
  confidence. If the declared direction is wrong, each winding's text comes in pieces, broken where the winding steps
  to the next sheet (at PHerc. 211 a net 1.78 to 1.89 sheets a turn).

## Decision rule

As finding 133's: the fit's numbers decide only which windings are read, and the read has no automatic verdict.

- **The owner sees letters:** that place is a candidate. Its direction then matters: a submission-quality image is
  registered separately, with a fit declared the other way at that place compared before anything is submitted.
- **The owner sees none:** this band shows no letters under this pipeline. With a direction unknown, a blank band is
  weaker evidence than finding 133's.

## What the result cannot do

- **A negative is weak:** one band, unrefined, a declared direction that may be wrong.
- **A positive is the owner's reading.**
- **The direction.** Nothing here measures it.
- **Disclosure.** PHerc. 0125 is eligible. The images stay on this machine, and the report carries numbers only. I do
  not view them. Nothing of PHerc. 0125 enters the November filing.
- **Licence.** Studio's weights and outputs are CC BY-NC 4.0.

## Cost and when it runs

- **Compute:** finding 129 (PHerc. 0813, the same voxel size) took 3 h 9 min to fit; finding 133's overlapped read
  took 3.4 minutes a winding on canvases a median 23.9 million pixels; PHerc. 0813's were 49.9 million. About 100
  windings would take about 3 h of fit and 6 to 10 h of read: 9 to 13 h. GPU memory up to about 15 GB.
- **Disk:** the inputs and tracks are already on disk (27 GB). Finding 129 wrote 11 GB of distance field, 47 GB of
  renders and 20 GB of Studio's maps. The render guard refuses a render below 50 GB free and deletes nothing. For every
  render to pass it, the read starts with **at least 140 GB free**; under that, the start is held and what to free is
  the owner's decision.
- **When:** after finding 138, and once the disk allows it. Nothing is uploaded.
