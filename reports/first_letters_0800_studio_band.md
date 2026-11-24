PHerc. 0800's band fits partly on the sheets (PARTLY_ON_SHEETS), and Studio read all 90 selected windings with no failure; a quarter of the fit's windings lie between sheets, the band stops short of the papyrus's edge, and the images wait for the owner's eye (2026-11-23)

Finding 133. The recipe fitted the middle 1,500 slices of PHerc. 0800's tracked range (z 10250 to 11750) at villa's
defaults. It kept the windings that follow a predicted sheet, subdivided them twice, snapped them three times, then
flattened, rendered and read every one with Studio, the reader that won PHerc. 211's First Letters prize. Registered
before anything of PHerc. 0800 was downloaded: `docs/preregistration/2026-11-20_first_letters_0800_band_read.md`
(commit `05822dc0`, amendment 1 at `21c0943c`: the number of snap passes, decided by finding 134). Record:
`reports/first_letters_0800_studio_band.json`, assembled from the run directory by
`repro/first_letters/eligible_band/band_record.py`. Geometry described after the read:
`reports/first_letters_0800_described.json`. Scripts as run: `repro/first_letters/eligible_band/`
(`run_after_controls.sh`, `run_band_and_read.sh`, `run_studio_band.sh`, `studio_band.py`).

The three choices the registration left to earlier findings were read from their records when the chain started:
finding 132 `SKIP_ADOPTED`, finding 131 `DENSE_READS_SAME` and finding 134 `three_passes`, so `STUDIO_SKIP_EMPTY=1`,
`FL_DENSIFY=2` and `FL_SNAP_PASSES=3`. Renders and Studio overlapped (`FL_OVERLAP=1`), as registered.

PHerc. 0800 is still eligible for First Letters, so its images stay on this machine and this report carries numbers
only. I have not looked at them: viewing them would send an eligible scroll's possible text to the model's API.
Studio's weights and outputs are CC BY-NC 4.0.

**The read has no automatic verdict.** The registered outputs are the images, the contact sheet and the numbers
below; the decision is the owner's reading of the images, which is still to come. Every step of the chain exited 0,
and every step of the read exited 0 on all 90 windings.

**The first start was killed, and the chain ran again from the start.** The first start (2026-11-23 07:45) was killed
by systemd-oomd at 09:08:20 during the 300-step fit: memory pressure on the user's session stayed over 50% for more
than 20 seconds while the fit loaded the distance field. Its logs and partial 300-step fit are kept beside the run
(`attempt1_oomkilled/`), and nothing of it was used. The second start (12:19) ran the same command from the
registered worktree with the same settings. The downloads kept the files they had, and the distance field resumed
from its finished chunks, so those steps were short the second time (costs below).

**The second start came close twice.** A sampler beside it read the session's memory pressure (the share of time
stalled on memory over the last 10 s, which systemd-oomd watches) every 2 s:
- as the 30,000-step fit loaded (12:27:41 to 12:27:45), over 50% for about 6 s, at most 58.89%;
- in the summarise step (20:37:13 to 20:38:14), over 50% on 14 of 50 samples, the longest unbroken stretch about
  18 s (20:37:17 to 20:37:35), at most 58.57%. The step's own anonymous memory stayed under 0.8 GiB and at least
  27.6 GiB stayed available. The stall was in the page cache (the unit's cached file pages reached 20.3 GiB) while
  the step read Studio's maps and the surface layer of each render. oomd acts after 20 s.

Between the two it stayed under 23%. Nothing was changed to prevent a kill; a later read's summarise of a larger band
may cross the line.

## Where to look

On this machine, in the band's run directory `spiral_out/first_letters/pherc0800_band/`:

- `work/studio_fulldense/summary/index.html`: every winding's Studio map in reading orientation, in the inspection
  order below, each with its trust mask beside it;
- `work/studio_fulldense/summary/contact_sheet.png`: all 90 at one eighth.

The registered prediction, with low confidence: letter-like shapes on some windings, and a readable run of three or
more letters on none. It is tested only by the owner's reading.

## The fit, by finding 112's table

| | value |
|---|---|
| windings scored (villa's fit writes w000 to w129; the score starts at w010) | 120 |
| median sheet-following excess, 30,000-step fit | 0.1802 (p10 -0.1552, p90 0.3697) |
| share of windings with positive excess | 0.75 |
| median excess of the 300-step fit (the floor; at most 0.03) | -0.0001 |
| **finding 112's table** | **`PARTLY_ON_SHEETS`** (line P2 met; P1 missed) |

**The registered prediction (`PARTLY_ON_SHEETS` or better) holds, at its line.** P1 needs a median excess of at least
0.07 and at least 0.80 of the windings positive. The median, 0.1802, is about twice PHerc. 0813's 0.091, but only 0.75 of
the windings are positive. The 300-step fit was scored after the read, as at PHerc. 0358 and 0813; that score changes
nothing registered, since the windings had already been chosen from the full fit's score.

| windings, in index order | median excess | positive | median on-sheet share |
|---|---|---|---|
| w010 to w049 | 0.1906 | 0.675 | 0.3414 |
| w050 to w089 | 0.1188 | 0.625 | 0.3002 |
| w090 to w129 | 0.1882 | 0.95 | 0.3904 |

**Selected for the read:** the 90 windings with positive excess. Not selected: w013, w014, w017, w018, w019, w021,
w025, w027, w032, w036, w039, w046, w047, w051, w053, w054, w055, w058, w060, w062, w064, w066, w069, w071, w080,
w086, w087, w089, w092 and w104. Every winding from w105 outward is positive. At PHerc. 0813, 10 windings were left
out, all among the inner 38.

**Described, not registered: the 30 left out lie between the sheets.** From the fit's score
(`band_fit_quality.py`): the score reads a winding's nodes against the predicted sheet, and again with the nodes
moved 6 voxels each way along the winding's normal, about half the sheet spacing on PHerc. 343, which was scanned
at the same 8.64 µm. A winding on a sheet has more nodes inside it than its moved copies do.

| median over the windings | positive (90) | not positive (30) |
|---|---|---|
| nodes inside the predicted sheet | 0.3958 | 0.1096 |
| the same, moved 6 voxels each way | 0.1657 | 0.2375 |
| median distance to the sheet, voxels | 2.0 | 5.0 |

So the 30 are more on the sheet when moved half a spacing: they run between the sheets. A fit that lays more windings
than there are sheets would do this. The band's middle slice is consistent with that (below): between w050 and w129,
79 windings apart, the median number of predicted-sheet runs beyond the winding falls by 60, and 17 of the 30 are in
that range. Runs are counted along rays at one slice, and two sheets that touch make one run, so this is a hint, not
a count. The registration did not anticipate it.

## The registered numbers of the read

| | value |
|---|---|
| windings snapped, flattened, rendered and read | 90 of 90 (none failed) |
| renders flipped by the registered rule (most normals point inward against the scroll's axis) | none; kept: 90 |
| share of normals pointing inward against the axis | median 0.0157 (0.0002 to 0.0846) |
| reading orientation (the catalog's flags; with them, the recipe's own rule) | both (mirrored and upside down): 90 |
| share of the rendered area at probability 0.5 or more | median 0.0964 (0.002 to 0.3335) |
| largest share over one 380-pixel tile | median 0.5442 (0.0103 to 0.9666) |
| tiles scored | 7,706 |
| rendered pixels | 1,449,176,431 |

**Inspection order** (largest tile share first), the first ten: w119, w052, w030, w040, w108, w085, w038, w061,
w074, w076. As registered, these numbers order the windings and decide nothing: on PHerc. 211 Studio's reversed
planes also drew ink over a fifth to a half of some tiles. The shares here are higher than PHerc. 0813's (median
0.0866 and 0.505), and that is not evidence of more text.

**No render was flipped**, as for PHerc. 0813 and 343, the other clockwise scrolls. The most inward winding, w010,
points inward on 0.0846 of its nodes.

## Described: the geometry of what was read

From the geometry alone (no ink was looked at), by `band_geometry.py` after the read, against the surface
prediction's signed distance field and the published scroll axis. None of it changes a registered output.

**The orientation is right everywhere.** Against the axis, the least outward winding still points outward on 0.9154
of its nodes, and no render goes against the axis rule. The band-centre measure gives a median 0.0172 inward here,
so the two measures agree.

**Few windings are stacked.** Of the 66 pairs of neighbouring windings (both read, indices one apart), 4 have more
than 30% of their nodes within 2 voxels of the neighbour: w010-w011, w015-w016, w040-w041 and w081-w082. On
PHerc. 0813, 2 of 102 pairs were stacked.

**How much of what was rendered lies on the predicted sheet:**

| median over the 90 windings | snapped winding | final (flattened) winding |
|---|---|---|
| nodes within 2 voxels of the predicted sheet | 0.9338 | 0.907 |
| nodes inside the predicted sheet | 0.8644 | 0.8369 |

| final nodes within 2 voxels of the predicted sheet, median | value |
|---|---|
| inner third of radii | 0.9204 |
| middle third | 0.9307 |
| outer third | 0.8647 |
| final nodes within 2 voxels of the snapped triangles | 1.0 |

- **The trusted share** of a winding is its share of final nodes within 2 voxels of the predicted sheet with render
  layers running outward, as where Studio drew PHerc. 211's letters. Median 0.8948 (0.8075 to 0.9698). No winding is
  under 0.4. At PHerc. 0813 the median was 0.6341, and 23 of its 110 windings were under 0.4. The share rendered with
  layers inward is a median 0.0096. Each winding's trust mask is on the inspection page, turned as its image is.
- **Why so much higher than PHerc. 0813 is only partly the three snap passes.** The snap's own report (each row
  measured before that pass moves the nodes; `snap_meshes.py` counts a node within 2 voxels of the sheet run's centre
  along its normal) gives, at the median over the 90 windings:

  | | before pass 1 | before pass 2 | before pass 3 |
  |---|---|---|---|
  | nodes within 2 voxels of the sheet run's centre | 0.427 | 0.819 | 0.861 |
  | median move of the pass, voxels | 2.055 | 0.25 | 0.12 |
  | share of nodes whose move was rejected as a jump | 0.074 | 0.051 | 0.048 |

  Passes 2 and 3 added 0.042. Before any snap, this band's selected windings were already nearer the sheet than
  PHerc. 0813's were before its one pass (0.427 against 0.309), and fewer of their moves were rejected (0.074 against
  0.164). These are the snap's numbers, not `band_geometry.py`'s, and the two scrolls differ in more than the passes,
  so the split is approximate. How this band would have read with one pass was not tested.

**The band stops short of the papyrus's edge.** Checked after the read, from the geometry alone, at z 11000: rays
from the axis were cut into predicted-sheet runs (`repro/first_letters/eligible_band/outer_sheets.py`; numbers in
`reports/first_letters_0800_described.json`).

| raw fitted winding | sheet runs beyond it, median (p10 to p90) | outermost sheet minus the winding's radius, median voxels |
|---|---|---|
| w050 | 79 (55.6 to 89.6) | 1993.2 |
| w090 | 52 (38 to 62) | 1210.4 |
| w100 | 42 (26 to 53) | 1018.3 |
| w105 | 40.5 (21 to 50) | 957.9 |
| w110 | 35 (20 to 45.1) | 893.1 |
| w115 | 32 (19 to 39) | 698.0 |
| w120 | 27 (19 to 36) | 599.6 |
| w125 | 23.5 (17 to 31) | 524.9 |
| w129 | 19 (11 to 26.5) | 448.2 |

So at that slice, the outermost fitted winding still has a median of 19 predicted-sheet runs outside it, 448 voxels
(3.9 mm at 8.64 µm) short of the outermost sheet. The papyrus outside w129 was not fitted and not read. At PHerc.
0813 the papyrus ended near w110, and villa's fit, which writes 130 windings whatever the scroll, ran past it. Here
it is the other way. Other slices of this band were not checked.

**Checked after this report was first written (not registered): leaving out the 30 cost few sheet crossings.** At
the same slice, each winding was cut by the plane z 11000, and along 360 rays from the axis each predicted-sheet run
inside the band's radial range was marked covered when a cut lay on it
(`repro/first_letters/eligible_band/sheet_coverage.py`; numbers in `reports/first_letters_0800_described.json`):

| windings | share of the 28,877 runs with a winding on them | with two or more |
|---|---|---|
| the raw fit, all 120 | 0.5078 | 0.0595 |
| the raw fit, the 90 read | 0.4638 | 0.0437 |
| the raw fit, the 30 left out | 0.06 | 0.0033 |
| the 90 read, snapped and flattened, as rendered | 0.5942 | 0.124 |

- **Leaving the 30 out lost 0.044 of the runs at this slice**, and the snap more than made it up: the read windings
  as rendered sit on more runs than the whole raw fit does.
- **About two runs in five carry no read winding, as at PHerc. 0813**, whose read windings cover 0.5643 measured the
  same way. The raw fit of PHerc. 211's control band, where Studio read the winner's text, covers 0.3887, less than
  this band's raw fit. A run is not a sheet: the prediction can break one sheet into pieces along a ray or mark both
  of its faces, so these shares compare bands and do not count missed sheets.
- **The inner third of the range is covered least** (0.4085, against 0.5917 and 0.7729 further out), at PHerc. 0813
  too (0.3632).

## What it cost

| step | wall time | registered |
|---|---|---|
| fetch the volumes | 1 min 41 s | |
| fetch the tracks | 4 s | |
| make the dataset | 0 s | |
| distance field | 1 min 45 s | |
| fit, 300 steps | 4 min 7 s | |
| fit, 30,000 steps | 2 h 59 min 38 s | about 4 hours |
| quality | 7 min 31 s | |
| select | 1 s | |
| densify | 19 s | |
| read, 90 windings | 5 h 4 min 0 s | 4 to 5 h of flatten, then about 5 h of renders and Studio together |
| **all** | **8 h 19 min** | **about 14 hours** |

These are the second start's times. The first start fetched the volumes in 46 min 13 s and the tracks in 14 min 53 s,
built the distance field in 19 min 23 s, and was killed 2 min 28 s into the 300-step fit: 1 h 22 min 57 s in all.
With it, the run took 9 h 42 min.

| read step | wall time |
|---|---|
| snap, three passes | 1969 s |
| flatten, 90 windings | 1 h 27 min 42 s (median 65 s, at most 83 s) |
| orient | 3 s |
| render, 90 windings | 2 h 35 min 38 s (median 100 s, at most 175 s) |
| Studio, 90 windings (planes and map, skipping empty windows) | 2 h 47 min 24 s (median 113 s, at most 185 s) |
| summarise | 3 min 46 s |

- **The overlap.** The read took 18,240 s against 26,842 s for its steps one after another: **0.68**, inside the
  registered prediction (at most 0.8, moderate confidence; described, not a verdict). The renders and Studio ran
  together from 17:35:25 to 20:34:45, 2 h 59 min 20 s, against 5 h 23 min 2 s of their steps. Each step's time was
  measured while the other ran, so the saving against a read run one step at a time may be smaller than these ratios
  say. The stacked check, 16 s, is not in the sum and does not change it.
- **Per winding the read took 3.4 minutes**, against 7.4 at PHerc. 0813. Three things differ: the overlap, Studio's
  skip of empty windows (finding 132), and smaller canvases. Studio took a median 113 s a winding against 294 s
  there, and 0.8 of the registered 3.5 hours.
- **The canvases are smaller than registered:** a median 23.854 million pixels (3.6188 to 40.404), against PHerc.
  0813's 49.8932. The registration expected about 1.2 times PHerc. 0826's. Why was not checked.
- **The flatten took 0.29 to 0.37 of its registered 4 to 5 hours**, at a median 65 s a winding; the registration took
  134 to 254 s from finding 130's denser flatten.
- **Disk:** the inputs take 13.8 GB and the tracks 29.9 GB (the track store's listing was 13.1 GB). The renders take
  34.9 GB and Studio's maps 8.3 GB. Studio's input planes were deleted after each read.
- **GPU memory:** the fit peaked at 13,491 MiB in use by all processes (the 300-step fit at 12,603), inside the
  registered 15 GB. Studio's use was not sampled in this read.

## What this does to the campaign

The registered consequences:

- **If the owner sees letters,** the place is a candidate. Making a submission-quality image of it, and whether to
  submit, are registered separately and are the owner's decisions.
- **If the owner sees none,** this band of PHerc. 0800 shows no letters under this pipeline, and the next band or
  scroll is chosen separately.

Four eligible bands now wait for the owner's eye: PHerc. 0826 (finding 125), PHerc. 0358 (finding 126), PHerc. 0813
(finding 129) and this one. Finding 138 (the PHerc. 306B team's window triage, tested at PHerc. 211) started when
this read's described steps ended. If it passes, the owner has decided that the same ranking orders the look at
these four.

## What this does not show

1. **Anything about letters, yet.** That rests on the owner's reading of the images.
2. **A strong negative, if none are seen.** One band of 1,500 slices was read; the fit is unrefined; a quarter of its
   windings lie between sheets and were not read; and the papyrus outside w129 was not fitted.
3. **How many sheets the read misses.** At the middle slice, leaving out the 30 windings cost 0.044 of the
   predicted-sheet runs, and about two runs in five carry no read winding, as at PHerc. 0813. Runs are not sheets,
   and one slice is not the band.
4. **That the predicted sheet is the text-bearing one.** The geometry is measured against the surface prediction,
   not against the papyrus the text is on. Finding 116 found the fit's score blind to a wrong-handed spiral, and
   finding 137 found a wrong-handed fit still reads PHerc. 211's text.
5. **Where the papyrus ends away from the middle slice.** The edge was measured at one slice.
6. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them.
