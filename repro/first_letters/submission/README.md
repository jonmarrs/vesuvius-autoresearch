# A First Letters submission from a band read

If the owner sees letters on a band page, these scripts turn that winding's band-read outputs into the submission
image the rules ask for, with a control beside it and a check of the mesh's flattening. They use our mesh, our
render and Studio's map. The image is made by the PHerc. 343 recipe's own
`make_submission_image.py` (MIT, [Nieuwlaar/pherc343-first-letters](https://github.com/Nieuwlaar/pherc343-first-letters)
at `e8370f1f`, run unchanged from its clone at `pherc343_repro/src/repo`), the script behind an accepted submission.

## What the rules ask, and where it comes from

Read from scrollprize.org/prizes on 2026-11-22 (deadline June 25, 2027, 11:59 p.m. Pacific):

| The rules ask for | Here |
|---|---|
| an image of the virtually unwrapped segment, at least 10 visible and legible letters in one 4 cm² area | `image/<winding>.png`; the script reports the area in cm² and warns above `--max-cm2` (default 4) |
| a scale bar of 1 cm, and pixel and millimetre sizes of a few letters | the script's scale bar; `image/<winding>_letter_sizes.csv` from the letter boxes |
| the rows annotated | the script's row lines, from `ROWS` |
| the mesh in tifxyz with a low-distortion isometric flattening | the band read's `final_<arm>/<winding>.tifxyz`; `isometry.json` measures the distortion |
| which scroll | `--scroll`, `--volume-id`, in the caption and the sidecar |

The area, the rows and the letter boxes are the only hand-made inputs, as in the recipe. Nothing here chooses them.
The method, the false-positive mitigation and the held-out validation are text for the submission. The control
image is one piece of evidence; findings 124 and 136 are the route's checks at two places with known text.

## How to run it

1. A first image without annotations, to place them on (`-` for rows and letters). Use the winding's mesh, its
   66-layer render, Studio's map and the map of the reversed planes from the band read, the published axis, and
   the scroll's two orientation flags from the open-data catalog's `metadata.json`:

   ```sh
   bash repro/first_letters/submission/make_band_submission.sh \
     R/work/final_fulldense/wNNN.tifxyz R/work/render_fulldense/wNNN_66.zarr \
     R/work/studio_fulldense/maps/wNNN.npy REVERSED.npy R/dataset/umbilicus.json \
     ROW0,ROW1,COL0,COL1 - - OUT_FIRST \
     --scroll "PHerc. 0358" --volume-id 20250821151737 --voxel-um 9.362 \
     --top-to-bottom true --left-handed false --render-flipped true
   ```

   `--render-flipped` is the band read's `orient` decision for that winding (`studio_<arm>_orient.log`).
   The band read keeps no reversed-plane map. Make one with `studio_e2e.py planes --reverse` and the winner's
   `inference.py`, as finding 136 did (about 80 s a winding).
2. Place the row lines and letter boxes on that image, in the recipe's JSON formats
   (`make_submission_image.py --help`: `rows.json`, `letters.json`).
3. Run again into a new directory with `ROWS` and `LETTERS`. The output holds the image, its control, both
   sidecars, `isometry.json`, `orientation.json` and `manifest.json` with every file's sha256.

An eligible scroll's outputs stay on this machine. A submission goes to the organisers privately; the rules forbid
making a discovery public before the prize is announced.

## Two things the recipe's script does not do for us

**Reading orientation on volumes in another frame.** The script measures the orientation with a rule written for
PHerc. 343's volume: z bottom to top, right-handed coordinates. A volume whose catalog says z runs top to bottom
turns both senses, and left-handed coordinates turn theta's (the band pages' rule, `band_index.py`). On PHerc. 211
the script's own measurement on our w035 was the 180-degree turn of the orientation the winner's map reads in. So
`orient` computes the flips with the catalog flags, and the wrapper passes them as `--flip-lr/--flip-ud`. It also
passes `--umbilicus` only in PHerc. 343's frame, where the script then checks the flips itself. PHerc. 0358's
catalog flags are PHerc. 211's (z top to bottom, right-handed). PHerc. 0813's and 0800's are PHerc. 343's. Always
pass the scroll's own flags.

**Rendered with flipped normals.** Band reads render a winding whose mesh normals point toward the axis with flipped
normals, so that its layers run outward (finding 125's orient step). The script reads the normal from the mesh and
warns that it points inward. Layer 34 (d = +1) is still 1.5 voxels outside the surface, and `--render-flipped true`
puts a note saying so on the image.

## The control

The same area, from Studio's map of the same 16 layers in reverse order (finding 124's wrong-side control), drawn
with the reading image's own stretch (`stats`), so that a fainter map is not stretched up to look like text. It has
no row lines; the script would derive them from the control's own ink.

## Dry runs at the two places with known text (2026-11-22)

| | PHerc. 343, our w047 (finding 110's fit, finding 136's maps) | PHerc. 211, our w035 (finding 121's fit, finding 124's maps) |
|---|---|---|
| area | 4.00 cm², 14 of the published letter boxes carried through 3D onto our mesh (all within 2.2 voxels) | 3.99 cm² of the winner's crop carried onto our w035 (no letter boxes are published) |
| orientation | flips true/true; the script's own measurement agrees | mirror only; the script alone would have turned it 180 degrees |
| by eye (allowed: both are known-text places) | the published letters, in the published order, bolder than the recipe's ensemble | the winner's rows, in the winner's reading order |
| edges within 10% of their flat length (along rows / columns) | 0.96 / 0.93 | 0.98 / 0.98 |
| median shear | 1.5° | 0.65° |
| 3D / flat area | 0.984 | 0.993 |
| the accepted mesh, same measures | published PHerc. 343, its area: 0.94 / 0.89, 1.8°, 0.979 | the PHerc. 211 winner's crop: 0.98 / 0.98, 0.35°, 0.997 |

So our lasagna flattening is as close to isometric as the accepted submissions' meshes, by these measures. Each
dry run took under 20 s of CPU, after the maps.

## Limits

- **The script needs a 66-layer render.** Finding 129 (PHerc. 0813) renders 18 layers to save disk. For a find
  there, render that one winding again at 66 layers (`RENDER_SLICES=66 run_render.sh`, about 1.5 GB).
- **One model.** The image shows Studio alone. The recipe's ensemble of four is not run on band reads.
- **Legibility is the owner's judgement.** Nothing here reads a letter.
