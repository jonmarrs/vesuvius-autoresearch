Studio read all 70 windings of PHerc. 0826's fitted band with no failure; the images wait for the owner's eye, and the two innermost windings were rendered the wrong way (2026-11-20)

Finding 125. Every winding of finding 115's fit `outer80` of PHerc. 0826 (band z 10250 to 11750) was snapped,
flattened, rendered and read by Studio, the reader that won PHerc. 211's First Letters prize, as finding 124 read
PHerc. 211. Registered before any winding of this fit was snapped:
`docs/preregistration/2026-11-20_first_letters_0826_studio_band.md` (commit `d6e5ca0f`). Record:
`reports/first_letters_0826_studio_band.json`, assembled from the run directory by
`repro/first_letters/eligible_band/band_record.py`. Scripts as run: `repro/first_letters/eligible_band/`
(`run_studio_band.sh`, `studio_band.py`).

PHerc. 0826 is still eligible for First Letters, so its images stay on this machine and this report carries numbers
only. I have not looked at them: viewing them would send an eligible scroll's possible text to the model's API.
Studio's weights and outputs are CC BY-NC 4.0.

**No automatic verdict was registered.** The registered outputs are the images, the contact sheet and the numbers
below; the decision is the owner's reading of the images, which is still to come. Every step exited 0 on all 70
windings.

## Where to look

On this machine, in the band's run directory `spiral_out/first_letters/pherc0826_band/`:

- `work/studio_outer80/summary/index.html`: every winding's Studio map in reading orientation, in the inspection
  order below, each with its trust mask (described below) beside it;
- `work/studio_outer80/summary/contact_sheet.png`: all 70 at one eighth.

The registered prediction, with low confidence: letter-like shapes on some windings, and a readable run of three or
more letters on none. It is tested only by the owner's reading.

## The registered numbers

| | value |
|---|---|
| windings snapped, flattened, rendered and read | 70 of 70 (none failed) |
| renders flipped by the registered rule (more than half the normals toward the band's centre) | 68; kept: w010, w011 |
| share of normals toward the band's centre | median 0.6621 (0.4931 to 0.9109) |
| reading orientation (the catalog's flags, as on PHerc. 211) | mirrored only: 70 |
| share of the rendered area at probability 0.5 or more | median 0.0535 (0.002 to 0.1228) |
| largest share over one 380-pixel tile | median 0.3423 (0.0088 to 0.8354) |
| tiles scored | 6,151 |
| rendered pixels | 1,167,228,663 |

**Inspection order** (largest tile share first), the first ten: w062, w065, w073, w041, w066, w047, w060, w075,
w064, w056. As the registration says, these numbers order the windings and decide nothing: on PHerc. 211 Studio's
reversed planes also drew ink over a fifth to a half of some tiles.

## Described: the geometry of what was read

Added while the read ran, from the geometry alone (no ink was looked at); none of it changes a registered output.
`repro/first_letters/eligible_band/band_geometry.py` measures each winding against the surface prediction's signed
distance field (the field the fit and the snap used) and against the published scroll axis.

**The registered orientation rule was wrong for the two innermost windings.** Measured against the published axis at
each node's height, every winding's normals point inward: median 0.8895 (0.8433 to 0.958) after the flatten, 0.9563
after the snap. So every render should have been flipped. The registered rule measured toward the mean of all the
band's nodes instead (median 0.6621), and w010 and w011 fell just under half (0.4931 and 0.4962) and were kept. Their
layers run inward, so Studio read them as it reads the reversed-planes control. **Their maps are not reads.** Finding
126 orients against the axis (its amendment 1, commit `3c37ceb0`, made before any of its data existed), and so do
the band reads after it.

**The inner windings are stacked.** Of the 69 pairs of neighbouring windings, 11 have more than 30% of their nodes
within 2 voxels of the neighbour (finding 113's line): w010-w011, w011-w012, w012-w013, w013-w014, w014-w015,
w015-w016, w016-w017, w017-w018, w019-w020, w023-w024 and w025-w026. All lie between w010 and w026. There, several
fitted windings share one sheet, so their images repeat each other.

**How much of what was rendered lies on the predicted sheet:**

| median over the 70 windings | snapped winding | final (flattened) winding |
|---|---|---|
| nodes within 2 voxels of the predicted sheet | 0.7737 | 0.6676 |
| nodes inside the predicted sheet | 0.5423 | 0.4334 |

| final nodes within 2 voxels of the predicted sheet, median | value |
|---|---|
| inner third of radii | 0.7866 |
| middle third | 0.6613 |
| outer third | 0.5405 |
| final nodes within 2 voxels of the snapped triangles | 0.9728 |

- **Where the loss is.** The flatten keeps to the snapped surface (0.9728 of its nodes within 2 voxels of the snapped
  triangles), yet its nodes are less often on the sheet than the snapped nodes are (0.6676 against 0.7737). The
  final grid samples the snapped triangles evenly; the snapped grid is even in angle, so at large radius its
  triangles are large and cut across the curved sheet between nodes that lie on it. The loss grows with radius.
  Finding 130, registered after this diagnosis, tested a denser snap on six of these windings; its report is on
  the branch that follows this one.
- **The trusted share** of a winding is its share of final nodes within 2 voxels of the predicted sheet with render
  layers running outward, as where Studio drew PHerc. 211's letters. Median 0.6079 (0.0452 to 0.6963). Five
  windings are under 0.4: w010 (0.0452) and w011 (0.0596), rendered the wrong way; and w077 (0.259), w078 (0.2444)
  and w079 (0.3808), the outermost, where the snap is coarsest. Each winding's trust mask (one pixel per node: on
  the sheet with layers outward; on the sheet with layers inward; off the sheet) is on the inspection page, turned
  as its image is.

**A correction.** The message of commit `965771b6` on this branch says the crushed tips are where the flatten leaves
the sheet. That was wrong. It came from distances between nearest nodes of the final and snapped grids, which at
large radius are tens of voxels apart, so the distance measured the grid's spacing, not the surface. Measured
against the snapped triangles (commit `2234a410`), the final nodes lie on the snapped surface (0.9728).

## What it cost

| step | wall time | registered rate |
|---|---|---|
| snap | 224 s | |
| flatten, 70 windings | 1 h 33 min 39 s (median 80 s, at most 177 s) | 77 to 89 s a winding |
| orient | 3 s | |
| render, 70 windings | 2 h 39 min 45 s (median 140 s, at most 247 s) | 54 to 69 s a winding |
| Studio, 70 windings (planes and map) | 4 h 24 min 26 s (median 254 s, at most 430 s) | about 70 s a winding |
| summarise | 6 min 21 s | |
| **all** | **8 h 48 min** | **about four hours** |

- **Over the registration by a factor of 2.2.** The registered rates came from finding 121's and 124's four windings
  of PHerc. 211, whose render canvases are 10.6 to 11.5 million pixels. This band's canvases are larger: median
  37.2614 million pixels (3.2568 to 60.816). The flatten works on the fit's grid and kept its rate; the render and
  Studio scale with the canvas.
- **Disk:** the renders take 102.4 GB (registered: about 35 GB), and Studio's maps 9.3 GB (not registered). Studio's
  input planes were deleted after each read, as registered.
- **GPU memory:** at most 15,428 MiB in use by all processes (registered: about 14.5 GB; finding 124 peaked at
  14,481 MiB).

## What this does to the campaign

The registered consequences:

- **If the owner sees letters,** the place is a candidate. Making a submission-quality image of it (refining the
  surface there, rendering, reading) and whether to submit are registered separately, and are the owner's decisions.
- **If the owner sees none,** this band of PHerc. 0826 shows no letters under this pipeline, and the next band or
  scroll is chosen separately.

Either way, the next band read (finding 126, PHerc. 0358) already orients against the axis and snaps on a denser
grid.

## What this does not show

1. **Anything about letters, yet.** That rests on the owner's reading of the images.
2. **A strong negative, if none are seen.** One band of 1,500 slices was read; the fit is unrefined; finding 119
   found a winding follows one sheet for centimetres and then leaves it; the inner windings are stacked; and in the
   median winding a third of the rendered nodes lie more than 2 voxels from the predicted sheet.
3. **That the predicted sheet is the text-bearing one.** The geometry is measured against the surface prediction,
   not against the papyrus the text is on; finding 116 found the fit's score blind to a wrong-handed spiral.
4. **w010 and w011.** Their maps read the other side of the sheet and are not evidence either way.
5. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them.
