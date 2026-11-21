PHerc. 0358's band fits on the sheets (ON_SHEETS), and Studio read all 111 selected windings with no failure; the images wait for the owner's eye (2026-11-21)

Finding 126. The recipe fitted the middle 1,500 slices of PHerc. 0358's tracked range (z 8872 to 10372) at villa's
defaults. It kept the windings that follow a predicted sheet, subdivided them twice, then snapped, flattened, rendered
and read every one with Studio, the reader that won PHerc. 211's First Letters prize. Registered before anything of
PHerc. 0358 was downloaded: `docs/preregistration/2026-11-20_first_letters_0358_band_read.md` (commit `3c97310a`,
amendment 1 at `3c37ceb0`). Record: `reports/first_letters_0358_studio_band.json`, assembled from the run directory
by `repro/first_letters/eligible_band/band_record.py`. Scripts as run: `repro/first_letters/eligible_band/`
(`run_band_and_read.sh`, `run_studio_band.sh`, `studio_band.py`).

PHerc. 0358 is still eligible for First Letters, so its images stay on this machine and this report carries numbers
only. I have not looked at them: viewing them would send an eligible scroll's possible text to the model's API.
Studio's weights and outputs are CC BY-NC 4.0.

**The read has no automatic verdict.** The registered outputs are the images, the contact sheet and the numbers
below; the decision is the owner's reading of the images, which is still to come. Every step of the chain exited 0,
and every step of the read exited 0 on all 111 windings.

## Where to look

On this machine, in the band's run directory `spiral_out/first_letters/pherc0358_band/`:

- `work/studio_fulldense/summary/index.html`: every winding's Studio map in reading orientation, in the inspection
  order below, each with its trust mask beside it;
- `work/studio_fulldense/summary/contact_sheet.png`: all 111 at one eighth.

The registered prediction, with low confidence: letter-like shapes on some windings, and a readable run of three or
more letters on none. It is tested only by the owner's reading.

## The fit, by finding 112's table

| | value |
|---|---|
| windings scored (villa's fit writes w000 to w129; the score starts at w010) | 120 |
| median sheet-following excess, 30,000-step fit | 0.0863 (p10 0.0175, p90 0.1415) |
| share of windings with positive excess | 0.925 |
| median excess of the 300-step fit (the floor; at most 0.03) | 0.0 |
| **finding 112's table** | **`ON_SHEETS`** (lines P1 and P2 both met) |

**The registered prediction (`PARTLY_ON_SHEETS` or better) holds, one line better.** The 300-step fit was scored
after the read. The chain scores only the full fit, and finding 112's table needs both. That score changes nothing
registered: the windings had already been chosen from the full fit's score.

| windings, in index order | median excess | positive | median on-sheet share |
|---|---|---|---|
| w010 to w049 | 0.0604 | 0.8 | 0.2835 |
| w050 to w089 | 0.0889 | 0.975 | 0.3102 |
| w090 to w129 | 0.1066 | 1.0 | 0.2964 |

**Selected for the read:** the 111 windings with positive excess. Not selected: w010, w011, w015, w022, w032, w038,
w042, w043 and w060, all among the inner 51. On PHerc. 0826 the papyrus ended near the 80th winding (finding 114).
Here the outermost third of the fit follows the sheets best.

## The registered numbers of the read

| | value |
|---|---|
| windings snapped, flattened, rendered and read | 111 of 111 (none failed) |
| renders flipped by the registered rule (amendment 1: most normals point inward against the scroll's axis) | 111; kept: none |
| share of normals pointing inward against the axis | median 0.961 (0.7804 to 0.9975) |
| reading orientation (the catalog's flags, as on PHerc. 211 and 0826) | mirrored only: 111 |
| share of the rendered area at probability 0.5 or more | median 0.0745 (0.0238 to 0.2034) |
| largest share over one 380-pixel tile | median 0.4406 (0.028 to 0.9359) |
| tiles scored | 10,536 |
| rendered pixels | 1,953,341,496 |

**Inspection order** (largest tile share first), the first ten: w044, w065, w049, w098, w106, w047, w059, w113,
w121, w103. As registered, these numbers order the windings and decide nothing: on PHerc. 211 Studio's reversed
planes also drew ink over a fifth to a half of some tiles. The shares here are higher than PHerc. 0826's
(median 0.0535 and 0.3423), and that is not evidence of more text.

## Described: the geometry of what was read

From the geometry alone (no ink was looked at), by `band_geometry.py` after the read, against the surface
prediction's signed distance field and the published scroll axis. None of it changes a registered output.

**The orientation is right everywhere.** Every render was flipped. Against the axis, the least inward winding still
points inward on 0.7804 of its nodes, and no render goes against the axis rule. The band-centre measure that failed on
PHerc. 0826 gives a median 0.9457 here.

**Few windings are stacked.** Of the 104 pairs of neighbouring windings (both read, indices one apart), 7 have more
than 30% of their nodes within 2 voxels of the neighbour: w012-w013, w013-w014, w016-w017, w033-w034, w034-w035,
w035-w036 and w036-w037. All lie at or inside w037. On PHerc. 0826, 11 of 69 pairs were stacked.

**How much of what was rendered lies on the predicted sheet:**

| median over the 111 windings | snapped winding | final (flattened) winding |
|---|---|---|
| nodes within 2 voxels of the predicted sheet | 0.7635 | 0.7199 |
| nodes inside the predicted sheet | 0.588 | 0.541 |

| final nodes within 2 voxels of the predicted sheet, median | value |
|---|---|
| inner third of radii | 0.728 |
| middle third | 0.7245 |
| outer third | 0.7109 |
| final nodes within 2 voxels of the snapped triangles | 0.9982 |

- **No loss with radius.** On PHerc. 0826, read on the fit's grid, this share fell from 0.7866 at the inner third to
  0.5405 at the outer. Here, on the twice-denser grid, it holds from 0.728 to 0.7109. The flatten also loses less
  of the snapped share than there (0.7635 to 0.7199, against 0.7737 to 0.6676). This fits finding 130's diagnosis, but
  it is another scroll, not a controlled comparison. Finding 131 tests whether the denser grid reads better.
- **The trusted share** of a winding is its share of final nodes within 2 voxels of the predicted sheet with render
  layers running outward, as where Studio drew PHerc. 211's letters. Median 0.68 (0.3521 to 0.7388). Two windings
  are under 0.4, w012 (0.3521) and w013 (0.3925), both in stacked pairs. The share rendered with layers inward is a
  median 0.022. Each winding's trust mask is on the inspection page, turned as its image is.

## What it cost

| step | wall time | registered |
|---|---|---|
| fetch the volumes | 36 min 38 s | |
| fetch the tracks | 6 min 58 s | |
| make the dataset | 1 s | |
| distance field | 14 min 58 s | about 10 minutes |
| fit, 300 steps | 6 min 42 s | |
| fit, 30,000 steps | 3 h 14 min 50 s | about 3.5 hours |
| quality | 7 min 21 s | |
| select | 1 s | |
| densify | 23 s | |
| read, 111 windings | 13 h 28 min 9 s | about 3.5 minutes a winding (6.5 hours for 111) |
| **all** | **17 h 56 min** | **about 8 hours** |

| read step | wall time |
|---|---|
| snap | 911 s |
| flatten, 111 windings | 2 h 10 min 9 s (median 70 s, at most 92 s) |
| orient | 6 s |
| render, 111 windings | 4 h 7 min 39 s (median 137 s, at most 214 s) |
| Studio, 111 windings (planes and map) | 6 h 44 min 40 s (median 248 s, at most 319 s) |
| summarise | 9 min 55 s |

- **Over the registration by a factor of 2.2, most of it in the read.** The fit and the distance field took close to
  what was registered. The read took 2.1 times its registered rate. That rate came from PHerc. 211's small canvases,
  and this band's are a median 38.9952 million pixels (5.7528 to 50.5076). Per winding the read took 7.3 minutes,
  close to finding 125's measured 7.5. The registered total also assumed fewer windings than the 111 selected:
  at the registered rates, the fit, distance field and read alone come to about 10 hours.
- **The flatten did not double.** Amendment 1 expected about twice finding 125's flatten on the denser grid (finding
  130: 134 to 254 s a winding). It took a median 70 s, at most 92 s, below finding 125's 80 s on the fit's grid. The
  denser snap does not by itself slow the flatten. Why finding 130's six were slower is not known.
- **Disk:** the inputs take 10.4 GB and the tracks 13.6 GB (registered: about 18 GB of downloads). The renders take
  171.4 GB and Studio's maps 15.4 GB (neither registered). Studio's input planes were deleted after each read.
- **GPU memory:** the fit peaked at 13,019 MiB in use by all processes (the 300-step fit at 12,015). Studio's peak,
  14,481 MiB (finding 124's figure), covers only the last 22 windings' reads (w108 to w129) and the summary: the
  sampler ran from 10:34 to the end of the read, 359 samples.

## What this does to the campaign

The registered consequences:

- **If the owner sees letters,** the place is a candidate. Making a submission-quality image of it, and whether to
  submit, are registered separately and are the owner's decisions.
- **If the owner sees none,** this band of PHerc. 0358 shows no letters under this pipeline, and the next band or
  scroll is chosen separately.

Two eligible bands now wait for the owner's eye: PHerc. 0826 (finding 125) and this one. Findings 131, 132 and 134,
controls at PHerc. 211, run next. Findings 129 (PHerc. 0813) and 133 (PHerc. 0800) are queued behind them and wait
for disk: each holds at its start until 150 GB or 170 GB is free, and this read's renders alone take 171.4 GB. What
to free is the owner's decision.

## What this does not show

1. **Anything about letters, yet.** That rests on the owner's reading of the images.
2. **A strong negative, if none are seen.** One band of 1,500 slices was read; the fit is unrefined; finding 119
   found a winding follows one sheet for centimetres and then leaves it; and in the median winding more than a
   quarter of the rendered nodes lie more than 2 voxels from the predicted sheet.
3. **That the predicted sheet is the text-bearing one.** The geometry is measured against the surface prediction,
   not against the papyrus the text is on. Finding 116 found the fit's score blind to a wrong-handed spiral.
4. **That the fit misses papyrus outside w129, though at one slice it does not.** The outermost third of the fit
   follows the sheets best, and villa's fit stops at 130 windings. Checked after the read, from the geometry alone,
   at the band's middle slice (z 9622): rays from the axis were cut into predicted-sheet runs
   (`repro/first_letters/eligible_band/outer_sheets.py`; numbers in `reports/first_letters_0358_outer_sheets.json`).
   Along w129's rays, the outermost predicted sheet lies a median -2.1 voxels from it. A median of 0 sheet runs lie
   beyond it (90th percentile 8); beyond w110 there are 18. So at that slice the fit reaches the edge of the
   predicted sheet on most rays. Other slices were not checked.
5. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them.
