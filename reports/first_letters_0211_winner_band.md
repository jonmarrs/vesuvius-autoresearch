The recipe's fit of a PHerc. 211 band lies on the sheet that won the prize almost everywhere, and no one winding follows it: one winding holds its first 60%, a winding two in holds the rest (2026-11-16)

Finding 119. PHerc. 211's First Letters prize was awarded on 2026-11-15, and the winner published the surface of
the submission under CC BY-NC 4.0. The question was whether the PHerc. 343 recipe's spiral fit, run unchanged on a
band of the public scan that contains that surface and snapped as for a read, puts one winding on the winner's
sheet. Registered before any fit of the band ran: `docs/preregistration/2026-11-16_first_letters_0211_winner_band.md`
(commit `64db6973`). Record: `reports/first_letters_0211_winner_band.json`. Scripts as run:
`repro/first_letters/eligible_band/` with `FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150`, and
`repro/first_letters/pherc0211_control/winner_sheet.py` through `run_after_fit.sh`. The fit, its windings and the
distance field stay on this machine; this report carries numbers.

**Verdict `PARTLY_ON_IT`**, as predicted, by the registered table: every step exited 0, and the snapped chosen
winding has 31.2% of the winner's nodes in the band within 2 voxels, above the 25% line and below the 50% line.
What lies behind that number is not what the registered consequence assumed; see "Where the winner's surface lies
among our windings".

## The registered numbers

| | value |
|---|---|
| winner's nodes in the band z 7650 to 9150 | 21,888 of 22,900 |
| raw windings of the fit (villa's `_spliced` twins skipped) | 120 |
| chosen winding (smallest median among those covering half the nodes) | w035, covering 98.3% |
| **snapped w035: share of the winner's nodes within 2 voxels** | **31.2%** |
| snapped w035: median distance | 4.59 voxels |
| snapped w035: within 1, 3 and 5 voxels | 16.9%, 40.9%, 50.3% |
| snapped w035: 5th to 95th percentile | 0.29 to 21.52 voxels |

Distances are finding 110's: from each of the winner's nodes to the nearest node of ours along our normal, a node
uncovered beyond 30 voxels sideways. The lines are finding 110's P1 (50% within 2 voxels and a median of at most 3)
for `ON_THE_WINNERS_SHEET` and 25% within 2 voxels for `PARTLY_ON_IT`.

## Described, as registered

None of this changes the verdict.

| raw winding | within 2 voxels | median | signed median |
|---|---|---|---|
| w035 (chosen) | 29.8% | 4.75 | +1.40 |
| w034 | 5.8% | 8.11 | −4.39 |
| w036 | 6.8% | 8.95 | +8.87 |

- **Near any winding.** 87.9% of the winner's nodes lie within 2 voxels of some raw winding, and 97.1% within 4.
- **The snap.** It moved w035 by a median of 0.68 voxels and raised its share within 2 voxels from 29.8% to 31.2%.
  Snapped w034 has 25.8% within 2 voxels (median 5.25); snapped w036 has 17.3% (median 11.73).
- **Tiles.** Finding 117's tiles of raw w035 against the winner's surface: 24 tiles, of which 19 have at least half
  their nodes within 2 voxels of it and 5 do not. The registration asked for the AUC only with at least 15 tiles of
  each label, so none is reported here (the record keeps the summary).
- **The fit's own score.** The sheet-following score of the 120 windings has a median excess of 0.1096, against
  0.086 for finding 112's band of this scroll and 0.140 for PHerc. 343.

## Where the winner's surface lies among our windings (not registered)

Computed after the verdict, on this machine. The column split below was chosen after seeing the column runs, so
these numbers describe this result and test nothing.

**The surface is longer than one turn.** Along its middle row it is 5,836 voxels long (55 mm); one turn of w035 in
the band is 4,628 voxels. Taking each of the winner's nodes within 2 voxels of a winding (w028 to w042) and the
winding nearest it, column by column along the surface:

| winner's columns (of 301) | nearest winding | |
|---|---|---|
| 0 to 158 | w035 | except column 94 (w034) and column 123 (w036) |
| 159 to 192 | w035 and w036, then w033 and w034 | the change |
| 193 to 300 | w033 | except column 299 (w034) |

On each part, the winding nearest it meets finding 110's P1 line:

| part | winding | within 2 voxels | median |
|---|---|---|---|
| columns 0 to 181 | snapped w035 | 51.7% | 1.87 |
| columns 0 to 181 | raw w035 | 49.6% | 1.98 |
| columns 193 to 300 | raw w033 | 55.2% | 1.74 |
| columns 193 to 300 | raw w035 | 0.1% | 15.88 |

By nearest winding, the winner's nodes within 2 voxels are 37.3% on w035, 29.8% on w033, 10.3% on w036, 8.5% on
w034 and 2.0% on others. The winner's ink (probability at least 0.5) lies 50.1% in columns 0 to 181 and 49.9% in
columns 182 to 300.

So the fit does not miss the winner's sheet. Its windings lie on it over most of its area, and one winding, w035,
follows it for 3,640 voxels (34 mm, 79% of a turn) before the surface goes on two windings further in.

**The neighbours of w035 lie between sheets.** The recipe's snap, run afterwards on w028 to w042 into a scratch
folder (its rows for w034 to w036 equal the registered snap's), reports the share of each winding's nodes already
within 2 voxels of a predicted sheet:

| winding | w029 to w033 | w034 | w035 | w036 | w037 | w038 to w042 |
|---|---|---|---|---|---|---|
| already on a sheet | 51% to 71% | 5.5% | 79.2% | 6.5% | 51.5% | 25% to 69% |
| median move | 0.90 to 1.23 | 5.53 | 0.68 | 5.19 | 1.89 | 0.95 to 3.43 |

On earlier snaps the median share was 41% (finding 112's twelve windings of this scroll) and 26% and 41% (PHerc.
343). w034 and w036 sit between predicted sheets almost everywhere and the snap moves them about 5.5 voxels, in
part onto w035's sheet. Here the fit has more windings than the prediction has sheets, and w033 and w035 may lie
on neighbouring sheets with w034 in the gap.

**Which surface changes sheets is not settled.** On a spiral a surface reaches the next sheet only after a full
turn. Whether the change at column 182 is two of our windings or one sheet, it comes at 79% of a turn, so one of
the two surfaces leaves its sheet there. The winner's surface is a stitched crop, edited by hand, and our fit is
unrefined; nothing measured here says which. The surface prediction used by the snap is thresholded at 0.2 and can
miss a faint sheet, so "between sheets" may mean "on a sheet the prediction does not show".

## Defects found before the measurement

- **The band verdict crashed when the full fit scored no winding** (a `KeyError` in `band_fit_verdict.holds`, and
  a zero step in `by_index`). It now says `DOES_NOT_RUN`, with a test.
- **A dry run of the choose step on the 300-step smoke fit**, writing only to a scratch folder, found two more.
  - villa's Python environment cannot read the winner's LZW-compressed surface files (`imagecodecs` missing), so
    `winner_sheet.py` runs on this repository's environment.
  - It counted villa's `wNNN_spliced` twin of every winding (240 for 120). The registration says raw windings, so
    `raw_windings()` skips them, with a test.

  Its numbers were not looked at as a result and are not reported.

## What it cost

| step | wall time | peak |
|---|---|---|
| distance field | 9 min 51 s | 0.8 GB of host memory |
| smoke fit, 300 steps | 3 min 38 s | 10.6 GB of GPU memory |
| full fit, 30,000 steps | 3 h 32 min 13 s | 12.3 GB of GPU memory, 7.3 GB of host memory |
| sheet-following score, choose, snap of three windings, verdict | 6 min 29 s, 5 min 1 s, 29 s, under 1 s | |

The band's inputs take 4.5 GB on disk and the distance field 6.6 GB. For the description above, the chunk
fetcher checked the 460 chunks of the surface prediction around w028 to w042 (0.18 GB) and fetched those not yet
on disk, by anonymous reads. The training loop was stopped throughout.

## What this does to the campaign

The registered consequence of `PARTLY_ON_IT` reads: "the fit gets near the sheet but not onto it over most of the
area; a read needs local refinement, as the winner did by hand. A blank read of an unrefined band is weaker
evidence than findings 112 and 113 assumed."

- **The last sentence stands, for a sharper reason.** A read of one unrefined winding follows a text-bearing sheet
  here for 34 mm and then is two windings off it. A blank read of one winding says little about the sheet next to
  it.
- **The first clause does not describe what happened.** The fit is on the winner's sheet over most of its area
  (88% of nodes within 2 voxels of some winding, each part at finding 110's P1 line). What fails is that no single
  winding follows it, and that two of w035's neighbours sit between sheets.
- **Refinement is still what the winner did**, and the place to look is now known: around the winner's column 182
  and the windings that sit between sheets.

Together with finding 118: on this surface our reader finds the ink and draws no letter, and our fit reaches the
sheet in two pieces. The next step is the whole pipeline at the known place: our snapped w035 and w033 rendered
and read, compared with the winner's map over the columns each follows. It is registered separately.

## What this does not show

1. Anything about ink. That is finding 118 and the step after.
2. Which of the two surfaces changes sheets at column 182.
3. More than one place of one scroll. The surface is where letters were found because someone refined it there,
   and it started as the same kind of fit, so agreement here is weaker evidence than it would be for an
   independent surface.
4. That "on the sheet" means more than within 2 voxels of one author's surface.
5. Variation between runs. The fit was run once, with villa's seed 1.
