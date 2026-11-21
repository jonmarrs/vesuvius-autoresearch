# Pre-registration: the recipe's fit of a PHerc. 0800 band, read by Studio, as images for the owner

**Written 2026-11-20, before any input of PHerc. 0800 has been downloaded or fitted, and before findings 131 and 132
have run.** Finding 133.

## The question

Findings 125, 126 and 129 read bands of PHerc. 0826, 0358 and 0813 the way finding 124 read PHerc. 211. PHerc. 0800 is
eligible for First Letters. It is clockwise, like PHerc. 343 and 0813, and was scanned at 8.64 µm and 116 keV, as
PHerc. 343 was. **Fitted and read the same way, does any winding of a PHerc. 0800 band show letters to the owner's
eye?**

## Reachability, checked before this was written

- **Every input the fit needs is published** (read 2026-11-20, anonymous listings and headers):
  - the scroll axis `PHerc0800/representations/umbilicus/20250521135224-umbilicus-20260924033751.json`: 151
    control points, z 1728 to 23008;
  - the m7 surface prediction (`representations/predictions/surfaces/`, level 1: 12149 × 4934 × 4934 in 192-voxel
    chunks) and the lasagna run (`nx`, `ny`, `grad_mag`), with the same stamps as the other bands';
  - the CT volume `20250521135224-8.640um-1.2m-116keV-masked.zarr`: level 0 is 24298 × 9867 × 9867 bytes in
    uncompressed 128-voxel chunks, stored as PHerc. 343's and 0826's are;
  - the spiral tracks at `dl.ash2txt.org/datasets/spiral_datasets/PHerc0800/20250521135224/tracks/`: 26,179,300
    tracks and 1,033,288,416 points, from a 13.1 GB track store.
- **The scan.** The band scripts name each scroll's scan, so PHerc. 0800's CT and voxel size are 8.64 µm
  (`env.sh`, commit `f1f813f6`). Every other scroll keeps 9.362 µm.
- **The direction.** The open-data catalog (`metadata.json` at the bucket's root) gives this volume
  `z_direction_is_top_to_bottom` false and `left_handed_coordinates` false: clockwise. The render orientation is
  decided against the published axis and the reading orientation by `band_index.py` from these flags, as for
  PHerc. 0813.
- **The band.** The tracks' `effective_z_bounds` are 4500 to 17500. The middle 1,500 slices of the tracked range
  are **z 10250 to 11750**, inside the axis.
- **The reader is Studio, with the winner's command,** as for finding 129 (findings 127 and 128).
- **The scripts** are finding 129's chain: 18-layer renders, the disk guard, orientation against the axis, and the
  selection of the windings with positive excess. Two options are new.
  - **`FL_OVERLAP=1`** (#476): the renders run in the background, in the same order, while Studio reads each winding
    once its render is recorded. The commands, inputs, gates and logs are the serial read's. Tested on stand-ins
    only; this is its first real use.
  - **`STUDIO_SKIP_EMPTY`**: Studio through `studio_fast.py --skip-empty` (finding 132) or through the winner's
    `inference.py`. The command line of each is tested.
- **Not checked:** nothing of PHerc. 0800 has been downloaded. The band's size, its share of the tracks and the fit's
  cost are unknown. Its track store is about the size of PHerc. 0826's (12 GB of tracks).

## Two choices fixed now, decided by verdicts not yet in

Findings 131 and 132 run before this read. `run_after_controls.sh` reads their records when this read starts, prints
its choices, and runs the chain with them:

| record | verdict | choice |
|---|---|---|
| finding 132 (`pherc0211_control/work/studio_fast.json`) | `SKIP_ADOPTED` | `STUDIO_SKIP_EMPTY=1` |
| | any other, or no record | `STUDIO_SKIP_EMPTY=0`: the winner's `inference.py` |
| finding 131 (`pherc0211_control/work/dense_read.json`) | `DENSE_READS_WORSE` | no `FL_DENSIFY`: the raw selected windings are read (arm `full`) |
| | any other, or no record | `FL_DENSIFY=2`: arm `fulldense`, as finding 129 |

These are finding 132's registered consequence (reads registered after it use the skip if it is adopted) and the
consequence finding 131 registered for finding 129.

## Procedure

```sh
FL_SCROLL=PHerc0800 FL_Z_BEGIN=10250 FL_Z_END=11750 FL_OVERLAP=1 \
  run_after_controls.sh bash run_band_and_read.sh
```

In `repro/first_letters/eligible_band/`, run once after finding 129's chain has ended, each step only if the one
before exited 0. The steps are finding 129's:
1. inputs, distance field, smoke and full fit at villa's defaults;
2. quality, then the selection of the windings with positive excess, and their subdivision if `FL_DENSIFY` is set;
3. the read: snap, the stacked check, flatten, orient, render (18 layers), Studio on our layers 41 down to 26, and the
   images.

Afterwards, described:
- `band_geometry.py --masks`;
- `band_record.py --finding 133` (with `--quality-arm full` if the read arm is `fulldense`);
- the inspection page, `band_index.py --top-to-bottom false --left-handed false --geometry`;
- the overlap's effect: the read's wall time against the sum of its steps' gate seconds.

## Predictions, fixed now

- **The fit:** `PARTLY_ON_SHEETS` or better by finding 112's table, with low-to-moderate confidence.
- **The read:** letter-like shapes on some windings, and a readable run of three or more letters on none, with low
  confidence.
- **The overlap:** the read's wall time is at most 0.8 of the sum of its step times, with moderate confidence. This is
  described, not a verdict.

## Decision rule

As finding 126's: the fit's numbers decide only which windings are read, and the read has no automatic verdict.

- **The owner sees letters:** that place is a candidate. A submission-quality image and whether to submit are
  registered separately and are the owner's decisions.
- **The owner sees none:** this band shows no letters under this pipeline.

## What the result cannot do

- **A negative is weak:** one band, unrefined, windings that can leave their sheet.
- **A positive is the owner's reading.**
- **Disclosure.** PHerc. 0800 is eligible. The images stay on this machine, and the report carries numbers only. I do
  not view them.
- **Licence.** Studio's weights and outputs are CC BY-NC 4.0.

## Cost

- **Downloads:** about 13 GB of tracks and about 9 GB of inputs. At 8.64 µm the band holds about 1.5 times the
  voxels of PHerc. 0826's in each slice (9867² against 8169²).
- **Compute:** finding 125 took a median 80 s to flatten, 140 s to render and 254 s for Studio per winding, and
  finding 130 found the denser flatten takes 134 to 254 s. With canvases about 1.2 times as long, a band of about 100
  windings takes about 4 h of fit, 4 to 5 h of flatten, and, overlapped, about 5 h of renders and Studio together
  (about 3.5 h of Studio with the skip). That is about 14 h in all. GPU memory up to about 15 GB.
- **Disk:** about 22 GB of inputs and 50 to 60 GB of renders. The guard stops the renders, without deleting anything,
  if fewer than 50 GB remain. Whether to delete finding 125's renders (96 GiB) is the owner's decision.
- **When:** after finding 129's chain. Nothing is uploaded.

## Amendment 1, 2026-11-20, before any input of PHerc. 0800 has been downloaded and before findings 131, 132 and 134 have run

**A third choice: how many times the windings are snapped, decided by finding 134.**

- **What was seen, from geometry alone.** On finding 130's six densified windings of PHerc. 0826 (w020 to w070), the
  recipe's snap was run again on its own output, twice. More of each winding came within 2 voxels of the predicted
  sheet at every pass, on all six windings (median over the six):

  | | one pass | two | three |
  |---|---|---|---|
  | nodes | 0.8303 | 0.8736 | 0.8905 |
  | edge midpoints and cell centres (the triangles between nodes) | 0.8166 | 0.8526 | 0.8630 |

  The one-pass node share is finding 130's recorded value. The second pass moved nodes a median of 0.29 to 0.53
  voxels, and the third 0.15 to 0.25.
- **Why this needs a reading test.** A pass moves each node to the centre of the nearest predicted-sheet run along its
  normal. Sitting on the sheet's centre need not read better (the reason finding 131 exists), so finding 134,
  registered separately, reads three passes against one at PHerc. 211's prize place.
- **The code.** `run_snap.sh` takes `FL_SNAP_PASSES` (1 to 5, default 1); each pass snaps the one before.
  - On those six windings, one pass gave finding 130's snap byte for byte, and three passes gave the hand-run third
    pass byte for byte.
  - `run_after_controls.sh` reads finding 134's record. It sets `FL_SNAP_PASSES=3` only if the record's
    `consequence` is `three_passes` and `FL_DENSIFY` is set, since finding 134 tests three passes of the densified
    windings. Otherwise it sets 1, the snap every earlier read used. A missing record also gives 1.
- **Order.** Finding 134 runs after finding 129's chain and before this read.
- **Unchanged:** everything else in this registration.
