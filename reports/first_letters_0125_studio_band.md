PHerc. 0125's band, declared clockwise, fits on the sheets (ON_SHEETS), and Studio read all 98 selected windings with no failure; the outermost windings lie past the papyrus, and the images wait for the owner's eye (2026-11-25)

Finding 139. PHerc. 0125's winding direction is not published, so the recipe fitted the middle 1,500 slices of its
tracked range (z 10250 to 11750) at villa's defaults with the spiral declared clockwise, villa's own default where a
checkpoint names no direction; finding 137 found that a fit declared the wrong way still reads PHerc. 211's text. The
read is finding 133's: the windings that follow a predicted sheet, subdivided twice, snapped three times, flattened,
rendered and read by Studio with its empty-window skip, renders and Studio overlapped. Registered before any fit or
read of PHerc. 0125: `docs/preregistration/2026-11-24_first_letters_0125_band_read.md` (commit `2d801cbb`). Record:
`reports/first_letters_0125_studio_band.json`, assembled by `repro/first_letters/eligible_band/band_record.py`.
Geometry described after the read: `reports/first_letters_0125_described.json`.

PHerc. 0125 is still eligible for First Letters, so its images stay on this machine and this report carries numbers
only. I have not looked at them. Studio's weights and outputs are CC BY-NC 4.0.

**The read has no automatic verdict.** The registered outputs are the images, the contact sheet and the numbers
below; the decision is the owner's reading of the images. Every step of the chain exited 0, and every step of the read
exited 0 on all 98 windings.

**Nothing here measures the direction.** The fit's score was blind to a wrong-handed spiral on PHerc. 0826 (finding
116), so `ON_SHEETS` says the windings sit on sheets, not that clockwise is right. If it is wrong, each winding's text
comes in pieces, broken where the winding steps to the next sheet.

## Where to look

On this machine, in `spiral_out/first_letters/pherc0125_band/`:

- `work/studio_fulldense/summary/index.html`: every winding's Studio map, turned by the catalog's flags with
  `z_direction_is_top_to_bottom` assumed false. **If that null flag is in truth true, every image stands turned by
  180 degrees.**
- `work/studio_fulldense/summary/look_first.html`: the windows in the glyph network's order, the first 10 first, as for
  the other eligible bands (finding 138's consequence). It orders the look and says nothing about where text is.
- `work/studio_fulldense/summary/contact_sheet.png`: all 98 at one eighth.

The registered prediction, with low confidence: letter-like shapes on some windings, and a readable run of three or
more letters on none. It is tested only by the owner's reading.

## The fit, by finding 112's table

| | value |
|---|---|
| windings scored (villa's fit writes w000 to w129; the score starts at w010) | 120 |
| median sheet-following excess, 30,000-step fit | 0.1269 (p10 -0.1006, p90 0.2889) |
| share of windings with positive excess | 0.8167 |
| median excess of the 300-step fit (the floor; at most 0.03) | 0.0013 |
| **finding 112's table** | **`ON_SHEETS`** (lines P1 and P2 both met) |

**The registered prediction (`PARTLY_ON_SHEETS` or better) holds, one line better.**

| windings, in index order | median excess | positive | median on-sheet share |
|---|---|---|---|
| w010 to w049 | 0.1007 | 0.675 | 0.3231 |
| w050 to w089 | 0.1719 | 0.85 | 0.3808 |
| w090 to w129 | 0.1099 | 0.925 | 0.2616 |

**Selected for the read:** the 98 windings with positive excess. Not selected: w010, w012, w013, w015, w019, w023,
w027, w029, w031, w033, w035, w038, w049, w055, w060, w062, w065, w067, w082, w093, w118 and w129.

**Described: the 22 left out lie between the sheets,** as at PHerc. 0800. Moved 6 voxels each way along their normals
they lie more on the sheet:

| median over the windings | positive (98) | not positive (22) |
|---|---|---|
| nodes inside the predicted sheet | 0.3512 | 0.1377 |
| the same, moved 6 voxels each way | 0.1897 | 0.2805 |
| median distance to the sheet, voxels | 2.0 | 4.0 |

## The registered numbers of the read

| | value |
|---|---|
| windings snapped, flattened, rendered and read | 98 of 98 (none failed) |
| renders flipped by the registered rule (most normals point inward against the scroll's axis) | none; kept: 98 |
| share of normals pointing inward against the axis | median 0.0485 (0.0081 to 0.0991) |
| reading orientation (the catalog's flags, top-to-bottom assumed false) | both (mirrored and upside down): 98 |
| share of the rendered area at probability 0.5 or more | median 0.0498 (0.0093 to 0.3972) |
| largest share over one 380-pixel tile | median 0.3767 (0.047 to 0.8658) |
| tiles scored | 7,751 |
| rendered pixels | 1,530,651,199 |

**Inspection order** (largest tile share first), the first ten: w066, w068, w011, w016, w069, w017, w087, w057, w042,
w058. These numbers order the windings and decide nothing.

**No render was flipped:** declared clockwise, the windings point outward against the axis. The most inward, w078,
points inward on 0.0991 of its nodes.

## Described: the geometry of what was read

From the geometry alone, by `band_geometry.py` after the read. None of it changes a registered output.

**The orientation is right everywhere.** The least outward winding still points outward on 0.9009 of its nodes. The
band-centre measure gives a median 0.0488 inward, so the two measures agree.

**More windings are stacked than at the other bands.** Of the 78 pairs of neighbouring windings (both read, indices
one apart), 16 have more than 30% of their nodes within 2 voxels of the neighbour. At PHerc. 0800, 4 of 66 were; at
PHerc. 0813, 2 of 102. Whether this has to do with the declared direction was not tested.

| median over the 98 windings | snapped winding | final (flattened) winding |
|---|---|---|
| nodes within 2 voxels of the predicted sheet | 0.9018 | 0.8434 |
| nodes inside the predicted sheet | 0.8036 | 0.7327 |

| final nodes within 2 voxels of the predicted sheet, median | value |
|---|---|
| inner third of radii | 0.9167 |
| middle third | 0.8689 |
| outer third | 0.751 |
| final nodes within 2 voxels of the snapped triangles | 0.9998 |

- **The trusted share** (final nodes within 2 voxels of the predicted sheet with layers running outward) is a median
  0.7836 (0.1622 to 0.9495). 7 windings are under 0.4: w122 to w128, the outermost read.
- **The three snap passes**, by the snap's own report (each row before that pass moves the nodes): nodes within 2
  voxels of the sheet run's centre 0.369, 0.737, 0.794; median move 2.18, 0.33 and 0.16 voxels.

**The band runs past the papyrus's edge at its middle slice.** At z 11000 (`outer_sheets.py`):

| raw fitted winding | sheet runs beyond it, median (p10 to p90) | outermost sheet minus the winding's radius, median voxels |
|---|---|---|
| w050 | 51 (46 to 58) | 1032.8 |
| w090 | 23 (4.4 to 38.6) | 509.1 |
| w100 | 16 (1 to 26.2) | 321.7 |
| w105 | 9.5 (1 to 15) | 266.4 |
| w110 | 1 (0 to 11.1) | 58.0 |
| w115 | 0 (0 to 8) | -16.3 |
| w120 | 0.5 (0 to 2) | 5.9 |
| w125 | 0 (0 to 6) | -76.3 |
| w129 | 0 (0 to 1) | -167.7 |

So at that slice the predicted papyrus ends near w110 to w115, as at PHerc. 0813, and the low trust of w122 to w128
fits it. One slice only.

**Sheet coverage** at the same slice (`sheet_coverage.py`, as for finding 133): of 26,597 predicted-sheet runs in the
band's range, the raw fit covers 0.4459, the 98 read raw windings 0.4171 and the 22 left out 0.0414; the read
windings as rendered cover 0.5677, with 0.1458 covered by two or more. Leaving the 22 out lost 0.029 of the runs. A run
is not a sheet, so these compare bands: at PHerc. 0800 the read windings covered 0.5942, at PHerc. 0813 0.5643.

## What it cost

| step | wall time | registered |
|---|---|---|
| fetch the volumes (on disk since 2026-11-13) | 1 min 12 s | |
| fetch the tracks | 3 s | |
| make the dataset | 0 s | |
| distance field | 11 min 57 s | |
| fit, 300 steps | 6 min 3 s | |
| fit, 30,000 steps | 2 h 50 min 5 s | about 3 hours |
| quality | 6 min 0 s | |
| select | 0 s | |
| densify | 16 s | |
| read, 98 windings | 5 h 5 min 53 s | 6 to 10 hours |
| **all** | **8 h 21 min** | **9 to 13 hours** |

| read step | wall time |
|---|---|
| snap, three passes | 1773 s |
| flatten, 98 windings | 1 h 24 min 25 s (median 42 s, at most 72 s) |
| orient | 3 s |
| render, 98 windings | 2 h 19 min 14 s (median 86 s, at most 143 s) |
| Studio, 98 windings | 3 h 4 min 10 s (median 118 s, at most 176 s) |
| summarise | 3 min 16 s |

- **Per winding the read took 3.1 minutes**, on canvases a median 32.639 million pixels (3.9324 to 41.232). The
  overlapped read took 0.69 of its steps' time.
- **Disk:** the inputs take 8.4 GB and the tracks 22.1 GB. The renders take 36.7 GB and Studio's maps 11.3 GB. The
  read started with 145 GB free, after the owner approved freeing the room; no render met the guard.
- **GPU memory:** the fit peaked at 11,530 MiB in use by all processes (the 300-step fit at 9,911).
- **Memory pressure** on the user's session peaked at 49.84% (sampled every 2 s), in the summarise step at 23:58:30.
  No sample crossed 50%, systemd-oomd's line; at PHerc. 0800 the same step stood over it for about 18 s.

## What this does to the campaign

The registered consequences:

- **If the owner sees letters,** the place is a candidate. Its direction then matters: a submission-quality image is
  registered separately, with a fit declared the other way at that place compared before anything is submitted.
- **If the owner sees none,** this band shows no letters under this pipeline; with the direction unknown, a blank band
  is weaker evidence than finding 133's.

Five eligible bands now wait for the owner's eye: PHerc. 0826, 0358, 0813, 0800 and this one, each with a look-first
page.

## What this does not show

1. **Anything about letters, yet.** That rests on the owner's reading of the images.
2. **The direction.** The fit's score cannot see it.
3. **A strong negative, if none are seen.** One band, unrefined, a declared direction that may be wrong.
4. **That the predicted sheet is the text-bearing one.** The geometry is measured against the surface prediction.
5. **Where the papyrus ends away from the middle slice.**
6. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them.
