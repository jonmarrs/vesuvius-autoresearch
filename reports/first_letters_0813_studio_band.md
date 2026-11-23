PHerc. 0813's band fits on the sheets (ON_SHEETS), and Studio read all 110 selected windings with no failure; the outermost windings lie past the papyrus, and the images wait for the owner's eye (2026-11-23)

Finding 129. The recipe fitted the middle 1,500 slices of PHerc. 0813's tracked range (z 9996 to 11496) at villa's
defaults. It kept the windings that follow a predicted sheet, subdivided them twice, then snapped, flattened, rendered
and read every one with Studio, the reader that won PHerc. 211's First Letters prize. Registered before anything of
PHerc. 0813 was downloaded: `docs/preregistration/2026-11-20_first_letters_0813_band_read.md` (commit `53e2b8d9`,
amendment 1 at `011b737d`: 18-layer renders). Record: `reports/first_letters_0813_studio_band.json`, assembled from
the run directory by `repro/first_letters/eligible_band/band_record.py`. Scripts as run: `repro/first_letters/eligible_band/`
(`run_band_and_read.sh`, `run_studio_band.sh`, `studio_band.py`).

PHerc. 0813 is still eligible for First Letters, so its images stay on this machine and this report carries numbers
only. I have not looked at them: viewing them would send an eligible scroll's possible text to the model's API.
Studio's weights and outputs are CC BY-NC 4.0.

**The read has no automatic verdict.** The registered outputs are the images, the contact sheet and the numbers
below; the decision is the owner's reading of the images, which is still to come. Every step of the chain exited 0,
and every step of the read exited 0 on all 110 windings.

## Where to look

On this machine, in the band's run directory `spiral_out/first_letters/pherc0813_band/`:

- `work/studio_fulldense/summary/index.html`: every winding's Studio map in reading orientation, in the inspection
  order below, each with its trust mask beside it;
- `work/studio_fulldense/summary/contact_sheet.png`: all 110 at one eighth.

The registered prediction, with low confidence: letter-like shapes on some windings, and a readable run of three or
more letters on none. It is tested only by the owner's reading.

**Described, not registered:** the 19 outermost windings, w111 to w129, lie mostly off the predicted sheet, and at
the band's middle slice those from w115 outward lie past its outermost sheet (below). So most of what their maps show
lies off the predicted papyrus. The page's order is unchanged; none of them is among the first ten.

## The fit, by finding 112's table

| | value |
|---|---|
| windings scored (villa's fit writes w000 to w129; the score starts at w010) | 120 |
| median sheet-following excess, 30,000-step fit | 0.091 (p10 0.0051, p90 0.162) |
| share of windings with positive excess | 0.9167 |
| median excess of the 300-step fit (the floor; at most 0.03) | 0.0004 |
| **finding 112's table** | **`ON_SHEETS`** (lines P1 and P2 both met) |

**The registered prediction (`PARTLY_ON_SHEETS` or better) holds, one line better**, as at PHerc. 0358. The 300-step
fit was scored after the read, as there. The chain scores only the full fit, and finding 112's table needs both.
That score changes nothing registered: the windings had already been chosen from the full fit's score.

| windings, in index order | median excess | positive | median on-sheet share |
|---|---|---|---|
| w010 to w049 | 0.0566 | 0.75 | 0.2564 |
| w050 to w089 | 0.133 | 1.0 | 0.3476 |
| w090 to w129 | 0.0479 | 1.0 | 0.1799 |

**Selected for the read:** the 110 windings with positive excess. Not selected: w010, w011, w015, w017, w018, w020,
w033, w036, w038 and w047, all among the inner 38. Here the middle third follows the sheets best. The outer third's
excess is positive on every winding, but it is the lowest of the three, and so is its on-sheet share.

## The registered numbers of the read

| | value |
|---|---|
| windings snapped, flattened, rendered and read | 110 of 110 (none failed) |
| renders flipped by the registered rule (most normals point inward against the scroll's axis) | none; kept: 110 |
| share of normals pointing inward against the axis | median 0.0675 (0.0302 to 0.1866) |
| reading orientation (the catalog's flags; with them, the recipe's own rule) | both (mirrored and upside down): 110 |
| share of the rendered area at probability 0.5 or more | median 0.0866 (0.0292 to 0.1951) |
| largest share over one 380-pixel tile | median 0.505 (0.1948 to 0.9958) |
| tiles scored | 10,565 |
| rendered pixels | 1,949,561,299 |

**Inspection order** (largest tile share first), the first ten: w059, w037, w064, w081, w060, w075, w101, w091,
w099, w096. As registered, these numbers order the windings and decide nothing: on PHerc. 211 Studio's reversed
planes also drew ink over a fifth to a half of some tiles. The shares here are higher than PHerc. 0358's (median
0.0745 and 0.4406), and that is not evidence of more text.

**No render was flipped**, as the registration expected for a clockwise scroll: on PHerc. 343, also clockwise, the
recipe's windings point outward and were rendered unflipped. Here the most inward winding points inward on 0.1866 of
its nodes.

## Described: the geometry of what was read

From the geometry alone (no ink was looked at), by `band_geometry.py` after the read, against the surface
prediction's signed distance field and the published scroll axis. None of it changes a registered output.

**The orientation is right everywhere.** Against the axis, the least outward winding still points outward on 0.8134
of its nodes, and no render goes against the axis rule. The band-centre measure gives a median 0.0868 inward here,
so on this band the two measures agree.

**Almost nothing is stacked.** Of the 102 pairs of neighbouring windings (both read, indices one apart), 2 have more
than 30% of their nodes within 2 voxels of the neighbour: w012-w013 and w013-w014. On PHerc. 0358, 7 of 104 pairs
were stacked.

**How much of what was rendered lies on the predicted sheet:**

| median over the 110 windings | snapped winding | final (flattened) winding |
|---|---|---|
| nodes within 2 voxels of the predicted sheet | 0.765 | 0.6895 |
| nodes inside the predicted sheet | 0.5851 | 0.5011 |

| final nodes within 2 voxels of the predicted sheet, median | value |
|---|---|
| inner third of radii | 0.7237 |
| middle third | 0.6965 |
| outer third | 0.616 |
| final nodes within 2 voxels of the snapped triangles | 0.9929 |

- **The loss at the outer third is the outermost windings.** Of the 19 read windings w111 to w129, a median 0.2605
  of the snapped nodes and 0.3157 of the final nodes lie within 2 voxels of the predicted sheet, against 0.7722 and
  0.6983 for the 91 windings w010 to w110. A median 0.2189 of their snapped nodes lie outside the surface
  prediction's field altogether, where the 91 have none. So the snap found no sheet to put them on, and the flatten
  kept them where they were (0.9929 of all final nodes lie within 2 voxels of the snapped triangles). These numbers
  are in `reports/first_letters_0813_outer_sheets.json`, taken from `band_geometry.py`'s output.
- **The trusted share** of a winding is its share of final nodes within 2 voxels of the predicted sheet with render
  layers running outward, as where Studio drew PHerc. 211's letters. Median 0.6341 (0.1925 to 0.7069). 23 windings
  are under 0.4: w012, w013, w014 and w016 among the inner ones, and all 19 of w111 to w129, whose median is 0.238
  (w010 to w110: 0.6509).
  The share rendered with layers inward is a median 0.0367. Each winding's trust mask is on the inspection page,
  turned as its image is.

**The fit runs past the papyrus at the band's middle slice.** Checked after the read, from the geometry alone, at
z 10746: rays from the axis were cut into predicted-sheet runs (`repro/first_letters/eligible_band/outer_sheets.py`;
numbers in `reports/first_letters_0813_outer_sheets.json`).

| raw fitted winding | sheet runs beyond it, median (p10 to p90) | outermost sheet minus the winding's radius, median voxels |
|---|---|---|
| w050 | 54 (40 to 68.8) | 1300.6 |
| w090 | 17 (9 to 45.5) | 521.1 |
| w100 | 11 (1 to 38) | 371.8 |
| w105 | 6 (0 to 26.2) | 229.4 |
| w110 | 1 (0 to 28.2) | 53.4 |
| w115 | 0 (0 to 6.1) | -83.0 |
| w120 | 0 (0 to 14) | -215.0 |
| w125 | 0 (0 to 13.5) | -163.9 |
| w129 | 0 (0 to 10) | -174.6 |

So at that slice the predicted papyrus ends near w110, and the windings from w115 outward lie past it on most rays.
Villa's fit writes 130 windings whatever the scroll. On PHerc. 0358 the outermost winding met the edge (a median
-2.1 voxels from it), and on PHerc. 0826 the papyrus ended near the 80th winding (finding 114). Other slices of this
band were not checked.

## What it cost

| step | wall time | registered |
|---|---|---|
| fetch the volumes | 34 min 39 s | |
| fetch the tracks | 9 min 13 s | |
| make the dataset | 0 s | |
| distance field | 12 min 20 s | |
| fit, 300 steps | 4 min 29 s | |
| fit, 30,000 steps | 3 h 8 min 53 s | about 3.5 hours |
| quality | 7 min 58 s | |
| select | 1 s | |
| densify | 18 s | |
| read, 110 windings | 13 h 29 min 45 s | about 15 hours (4 h flatten, 4 h renders, 7 h Studio) |
| **all** | **17 h 48 min** | **about a day and a half** |

| read step | wall time |
|---|---|
| snap | 857 s |
| flatten, 110 windings | 1 h 59 min 51 s (median 69 s, at most 77 s) |
| orient | 5 s |
| render, 110 windings | 2 h 58 min 10 s (median 100 s, at most 138 s) |
| Studio, 110 windings (planes and map) | 8 h 9 min 51 s (median 294 s, at most 409 s) |
| summarise | 7 min 8 s |

- **Under the registration overall, over it for Studio.** Per winding the read took 7.4 minutes, close to finding
  126's 7.3. The flatten took 0.5 of its registered time and the renders 0.74. Studio took 1.17 times its registered
  time: its rate came from finding 125's canvases (a median 37 million pixels), and this band's are a median 49.8932
  million pixels (6.2328 to 70.7328).
- **The 18-layer renders took 0.276 of PHerc. 0358's 66-layer renders per winding on disk**, as amendment 1
  measured on three windings (0.28). Their median time, 100 s, is under PHerc. 0358's 137 s on larger canvases, but
  that is another scroll, and amendment 1 claimed no time.
- **Disk:** the inputs take 10.7 GB and the tracks 18.7 GB (the tracks' listing was 8.2 GB). The renders take
  47.0 GB and Studio's maps 19.7 GB. Studio's input planes were deleted after each read.
- **GPU memory:** the fit peaked at 12,219 MiB in use by all processes (the 300-step fit at 11,119), inside the
  registered 15 GB. Studio's use was not sampled in this read.

## What this does to the campaign

The registered consequences:

- **If the owner sees letters,** the place is a candidate. Making a submission-quality image of it, and whether to
  submit, are registered separately and are the owner's decisions.
- **If the owner sees none,** this band of PHerc. 0813 shows no letters under this pipeline, and the next band or
  scroll is chosen separately.

Three eligible bands now wait for the owner's eye: PHerc. 0826 (finding 125), PHerc. 0358 (finding 126) and this one.
Finding 133 (PHerc. 0800) started when this read ended.

## What this does not show

1. **Anything about letters, yet.** That rests on the owner's reading of the images.
2. **A strong negative, if none are seen.** One band of 1,500 slices was read; the fit is unrefined; finding 119
   found a winding follows one sheet for centimetres and then leaves it; and in the median winding nearly a third of
   the rendered nodes lie more than 2 voxels from the predicted sheet.
3. **That the predicted sheet is the text-bearing one.** The geometry is measured against the surface prediction,
   not against the papyrus the text is on. Finding 116 found the fit's score blind to a wrong-handed spiral.
4. **Where the papyrus ends away from the middle slice.** The edge near w110 was measured at one slice. The
   outermost windings' low trust over the whole band fits it, but does not measure it.
5. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them.
