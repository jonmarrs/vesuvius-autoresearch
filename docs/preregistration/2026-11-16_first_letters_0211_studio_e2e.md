# Pre-registration: at the place where PHerc. 211's First Letters prize was won, does Studio reading our own geometry put ink where it put ink on the winner's?

**Written 2026-11-16, before Studio has read any render of ours.** Finding 124.

## The question

Findings 118 to 123 established four things at PHerc. 211's winning surface:

- **Our pipeline finds the ink there:** our fit's windings w033 to w036, snapped, flattened, rendered and read,
  give r 0.52 against the winning map, where the same models on the winner's own surface give 0.54 (finding 121).
- **The reader is the gap:** no permissive reader draws a readable word there.
- **Studio is the only reader known to draw letters there,** and the owner approved using it.
- **Studio runs here:** it reproduces the winner's map to bfloat16 rounding on this RTX 4090 (finding 123).

So this asks the question all of those were for. **Rendered and read as a band read would, carried onto the winner's
surface: does Studio on our own fit's windings put ink where Studio put it on the winner's?** The image of that map
is also the first chance to see whether our pipeline draws letters at a place where letters are known.

## Reachability, checked before this was written

- **The windings and their renders** are finding 121's: w033 to w036 of finding 119's fit.
  - **Rendering:** 66 layers each, rendered with `--flip-normals`, so layer k lies on the same side as in finding
    118's unflipped render of the winner's surface.
  - **Coverage:** they gave our ink to 83.1% of the winner's mask cells, transferred from a median of 1.94 voxels
    away.
- **Studio's planes in our renders.** Studio reads 16 planes in a fixed order. The winner's own input
  (`…_model_input_planes16_uint8.npy`, finding 123) was correlated plane by plane with finding 118's render of the
  same surface. That compared CT with CT and involved no ink.
  - **The match:** Studio's plane i matched our layer 41 − i, give or take one, at r 0.94 to 0.97 each. Plane 8 (the
    winner's surface plane) matched our layer 33 (our surface layer).
  - **The input:** our layers 41 down to 26, as uint8 [16, H, W].
  - **The other-side control:** the same planes in reverse order (26 up to 41), as findings 118 and 121 read the
    other side.
- **Studio** runs from finding 123's environment, weights and the winner's `inference.py`, each checksummed, with the
  winner's command (stride 64, Hann blending, batch 32, bfloat16).
- **The comparison** reuses finding 121's transfer and finding 118's numbers. `studio_e2e.py` is tested on finding
  121's synthetic surfaces:
  - Studio maps of a mirrored winding carry back onto the winner's surface at r above 0.9;
  - a reversed order that reads the same fails the controls;
  - an unflipped winding is refused.
- **Not checked:** Studio has not read any render of ours. Our renderer (`vc-render:sampler-75c79ac5f`) is not the
  winner's pinned `vc_render_tifxyz`.

## Procedure

`run_studio_e2e.sh` (`repro/first_letters/pherc0211_control/`), run once, each step only if the one before exited 0:

1. Check the weights' and `inference.py`'s SHA-256 against the winner's record.
2. Planes (`studio_e2e.py planes`) from:
   - finding 118's render of the winner's surface (our layers 41 down to 26);
   - each of w033 to w036, in that order and reversed.
3. Studio on each of the nine, with the winner's command.
4. `studio_e2e.py compare`:
   - each winding's Studio map is carried onto the winner's surface by finding 110's transfer (each 4 × 4 cell
     of the winner's surface takes the nearest cell of our windings within 4 voxels), as finding 121 did;
   - the cells are the winner's mask cells that receive a value.
   - **The registered numbers are finding 118's:**
     - r between the carried map and the winner's map, both with their broad background taken off;
     - controls: the carried map of the reversed planes, and the carried map slid 64 pixels in four directions
       (the largest absolute).

## Predictions, fixed now

- **What I expect: `STUDIO_E2E_CLOSE`, with low-to-moderate confidence.**
  - **For:** Studio is the same reader on both sides, and finding 121 found our geometry costs the four models
    only 0.02 in r.
  - **Against:** Studio's map is sharp, so offsets of 2 voxels and resampling cost it more than they cost a blurry
    map. Our renderer is not the winner's. And finding 121 found the four models agree with themselves across
    the two geometries only at r 0.66.

## Decision rule

| outcome | verdict |
|---|---|
| a step fails, a winding samples against the winner's normals, fewer than half of the winner's mask cells receive a value, or a number is missing | `DOES_NOT_RUN` |
| r at least 0.70, and at least twice the absolute value of each control | `STUDIO_E2E_CLOSE` |
| r at least 0.40, and at least twice the absolute value of each control | `STUDIO_E2E_PARTLY` |
| otherwise | `STUDIO_E2E_FAR` |

The 0.70 and 0.40 lines are judgements, above finding 121's 0.52 because the reference is Studio's own map.

What each does to the campaign:

- **`STUDIO_E2E_CLOSE`:** our pipeline with Studio puts ink where the winning pipeline did, at a known text place.
  The owner looks at the image for letters. If letters show, the next step is a still-eligible band read the same
  way, registered separately, with that image deciding whether anything is submitted.
- **`STUDIO_E2E_PARTLY`:** the losses are located from the described numbers (renderer or geometry) before an
  eligible band is read.
- **`STUDIO_E2E_FAR`:** even with the winning reader, our geometry does not reproduce the winning map at a known
  place. Geometry becomes the campaign's first problem again.

## Described, not deciding

- **Our renderer:** Studio on finding 118's render of the winner's surface (our renderer, the winner's geometry),
  against the winner's map, with the same numbers.
- **The two maps:** the carried map's r with it.
- **Per winding and by part:** r by winding, and over finding 119's two parts of the surface.
- **The transfer** distances.
- **Overlap** (finding 120's) for both maps.
- **An image** of the carried map, our-render map and the winner's map, one above another, for the owner, on this
  machine.

## What the result cannot do

- **Legibility.** r measures where ink is, so the image is for the owner's eye.
- **A blind read.** The four windings were chosen against the winner's surface (finding 121).
- **An untouched test of Studio.** Its continued training evaluated it on PHerc. 211.
- **One place of one scroll.**

## Cost

Nine Studio runs, each at most the size of finding 123's 75-second one: about ten minutes on the GPU. Planes about
1.5 GB on disk. Comparison a minute. Nothing is uploaded; the weights and outputs (CC BY-NC 4.0) stay on this
machine.
