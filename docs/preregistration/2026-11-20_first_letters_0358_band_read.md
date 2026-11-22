# Pre-registration: the recipe's fit of a PHerc. 0358 band, read by Studio, as images for the owner

**Written 2026-11-20, before any input of PHerc. 0358 has been downloaded or fitted.** Finding 126.

## The question

Finding 124 showed that at a known text place, this pipeline draws the winner's letters: the recipe's unrefined
spiral fit, snapped, flattened and rendered, then read by Studio (the winning reader the owner approved).
Finding 125 reads every winding of a PHerc. 0826 band that way. PHerc. 0358 is still eligible for First Letters,
and since September it has every input the fit needs. **Fitted and read the same way, does any winding of a
PHerc. 0358 band show letters to the owner's eye?**

## Reachability, checked before this was written

- **Every input the fit needs is published** (read 2026-11-20, anonymous listings):
  - the scroll axis `PHerc0358/representations/umbilicus/20250821151737-umbilicus-20260922235631.json`: 76 manual
    control points, z 1216 to 14064;
  - the m7 surface prediction and the lasagna run with the same stamps as PHerc. 0211's and 0826's;
  - the CT volume `20250821151737-9.362um-1.2m-113keV-masked.zarr`;
  - the spiral tracks at `dl.ash2txt.org/datasets/spiral_datasets/PHerc0358/20250821151737/tracks/`.
- **The direction.** The open-data catalog's `metadata.json` gives `z_direction_is_top_to_bottom` true and
  `left_handed_coordinates` false: anticlockwise, as for PHerc. 0211 and 0826. The same file gives clockwise for
  PHerc. 0800 and 0813, whose axes were also published in September; their orientation and image mirroring have
  not been checked.
- **The band.** The tracks' `effective_z_bounds` are 4500 to 14744. The band scripts' rule is the middle 1,500
  slices of the tracked range: **z 8872 to 10372**, inside the axis.
- **The scripts** are the band's, unchanged except for:
  - PHerc. 0358's entry in `env.sh` (volume, axis, direction);
  - `run_studio_band.sh`, which now takes a list of windings and runs a stacked-winding check after the snap;
  - `studio_band.py`, which gains `select` and `stacked`;
  - `run_band_and_read.sh`, which chains everything.
- **Choosing windings before any ink.** Villa's fit always writes 130 windings, and on PHerc. 0826 the papyrus
  ended near the 80th (finding 114). Setting the count lower helped only weakly (finding 115), and a new scroll's
  count is not known before its fit. So the fit runs at villa's defaults, and the read takes the windings whose
  sheet-following excess (`run_quality.sh`) is above zero. These are windings nearer a predicted sheet than six
  voxels off it. Finding 116 found the excess blind to winding direction, so it chooses where sheets are and
  says nothing about whether the spiral is right.
- **Not checked:** nothing of PHerc. 0358 has been downloaded. Its band's size, track count and fit cost are
  unknown.

## Procedure

`FL_SCROLL=PHerc0358 FL_Z_BEGIN=8872 FL_Z_END=10372 run_band_and_read.sh` (`repro/first_letters/eligible_band/`),
run once, each step only if the one before exited 0:

1. **Inputs.** The band's public chunks and tracks; villa's dataset.
2. **Distance field.**
3. **Fit.** 300 steps (smoke), then the 30,000-step fit at villa's defaults.
4. **Quality.** The sheet-following excess of every raw winding.
5. **Select.** The windings with positive excess.
6. **Read** (`run_studio_band.sh full`, finding 125's read on the selected windings):
   - snap, then the stacked-winding check (consecutive snapped windings with 30% or more of their nodes within
     2 voxels, described);
   - flatten;
   - orient (flip when most normals point toward the band's centre);
   - render;
   - Studio on our layers 41 down to 26;
   - one image per winding and a contact sheet.

## Predictions, fixed now

- **The fit:** `PARTLY_ON_SHEETS` or better by finding 112's table (median excess at least 0.03, 65% of windings
  positive), with low-to-moderate confidence, as on PHerc. 0211 and 0826.
- **The read:** letter-like shapes on some windings, and a readable run of three or more letters on none, with low
  confidence (finding 125's reasons apply).

## Decision rule

The fit's numbers are described with finding 112's table; they decide only which windings are read. The read has
no automatic verdict.

- **The owner sees letters:** that place is a candidate. A submission-quality image and whether to submit are
  registered separately and are the owner's decisions.
- **The owner sees none:** this band shows no letters under this pipeline. The next band or scroll is chosen
  separately.

## What the result cannot do

- **A negative is weak:** one band, unrefined, windings that can leave their sheet.
- **A positive is the owner's reading.**
- **Disclosure:** PHerc. 0358 is eligible, so its outputs stay on this machine and the report carries numbers only.
  I do not view its images.
- **A stacked pair** renders the same papyrus twice. The check flags it, and it is not removed.

## Cost

- **Downloads:** about 18 GB of inputs and tracks (PHerc. 0826's band: 6 GB of inputs and 12 GB of tracks).
- **Compute:** distance field about 10 minutes; fit about 3.5 hours; read about 3.5 minutes a selected winding.
- **When:** about 8 hours in all, after finding 125's read.

Nothing is uploaded.

## Amendment 1, 2026-11-20, before anything of PHerc. 0358 was downloaded

The chain had not started. It was queued behind finding 125's read, and its run directory held only an empty `logs`
folder. Two of the read's steps change, both learnt from finding 125's geometry and decided before any 0358 data
exist:

- **Orientation against the published scroll axis.** `studio_band.py orient` now takes `--umbilicus`, and
  `run_studio_band.sh` passes the band's axis. On PHerc. 0826's read, the band's mean node position lay off the axis.
  Two inner windings that point inward on 90% of their nodes against the axis scored 49% against the mean, and were
  rendered the wrong way (`band_geometry.py`).
- **A twice-denser grid before the snap.** The chain runs with `FL_DENSIFY=2`: the selected raw windings are
  subdivided twice (`densify_winding.py`) and read as arm `fulldense`. Finding 130 found that this keeps more of the
  rendered surface on the predicted sheet: +0.070 at the median over six of 0826's windings (`DENSE_SNAP_HELPS`).

The command becomes `FL_SCROLL=PHerc0358 FL_Z_BEGIN=8872 FL_Z_END=10372 FL_DENSIFY=2 run_band_and_read.sh`.

Two further things are run afterwards and described:
- `band_geometry.py`: normals against the axis, the share of each rendered winding within 2 voxels of the predicted
  sheet, and the trust masks;
- the inspection page with `band_index.py`.

Studio keeps the winner's command (`--stride 64 --blend hann`) whatever finding 128 shows. The fit, the selection,
the predictions and the decision rule are unchanged, and everything else in this registration stands.

The flatten costs about twice as long on the denser grid (finding 130: 134 to 254 s a winding).
