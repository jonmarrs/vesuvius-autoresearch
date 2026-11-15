On PHerc. 0826, a fit asked for 80 windings in place of villa's 130 follows predicted sheets on most of them (median excess 0.103, 79% of windings positive), a little better than the same windings in the 130-winding fit (0.083) (2026-11-15)

Finding 115. Finding 114 fitted one band of PHerc. 0826 (z 10250 to 11750) with villa's defaults and failed its
test, because the fit wrote 130 windings and the papyrus in the band ends near the 80th. This is the one change
its consequence named: villa's `shell_outer_winding_idx` set to 80 (and `model_gap_expander_num_windings` to 83,
as villa asks), everything else as before. Host: 4 cores, 31 GB of RAM, one RTX 4090. Registered before any such
fit ran: `docs/preregistration/2026-11-14_first_letters_0826_winding_count.md` (commit `49a5bc66`). Record:
`reports/first_letters_0826_winding_count.json`. Scripts as run: `repro/first_letters/eligible_band/`.

PHerc. 0826 is prize-eligible. This report and its record carry summary numbers about the fit. The windings, the
distance field and the score of each winding are on this machine only, and nothing here is a render or an ink map.

**Verdict `PARTLY_ON_SHEETS`**, by the registered table: every step exited 0, 70 windings were scored in each
fit, the floor is 0.000, P2 holds and P1 fails on the share of windings positive (78.6% against 80%).
**P3 `HELPS`**: the median excess is 0.103, above the registered line of 0.0925. I registered
`PARTLY_ON_SHEETS` with no gain, at low confidence. The verdict was right and the P3 prediction was wrong.

## The score

For each raw winding, `excess` is the share of its nodes inside a predicted sheet minus the same share for the
nodes moved 6 voxels along the winding's normal.

| fit | windings scored | median excess | 10th to 90th percentile | windings with positive excess | median share of nodes inside a sheet |
|---|---|---|---|---|---|
| 80 windings, 300 steps (the floor) | 70 | 0.000 | −0.007 to 0.007 | 54.3% | 0.220 |
| 80 windings, 30,000 steps | 70 | **0.103** | −0.071 to 0.224 | **78.6%** | 0.294 |
| 130 windings (finding 114), the same 70 indices | 70 | 0.083 | −0.055 to 0.200 | 75.7% | not computed |
| 130 windings (finding 114), all | 120 | 0.004 | −0.007 to 0.167 | 59.2% | 0.174 |
| PHerc. 0211, 130 windings (finding 112) | 120 | 0.086 | −0.001 to 0.226 | 88.3% | 0.309 |

P1 asked for a median of at least 0.07 and at least 80% of windings positive; P2 for 0.03 and 65%. The fit
misses P1 by one winding: 55 of 70 are positive and 56 would be 80%.

The registered thirds, in index order:

| windings | median excess | positive | at 0.07 or above | median share inside a sheet | median nodes scored |
|---|---|---|---|---|---|
| w010 to w033 (inner) | 0.004 | 54.2% | 10 of 24 | 0.251 | 6,180 |
| w034 to w057 | 0.103 | 91.7% | 16 of 24 | 0.315 | 12,974 |
| w058 to w079 (outer) | 0.138 | 90.9% | 19 of 22 | 0.285 | 19,856 |

45 of the 70 windings score 0.07 or above and 15 score zero or below. The failure of P1 is the inner third.

## How much the change did

P3 holds by 0.010 over its line and 0.020 over the baseline. The rest of this section was not registered.

The same 70 indices in the two fits, ten at a time. A winding's median distance from the axis is 1% to 8%
larger in this fit than the same index in finding 114's (eight indices checked), so an index is nearly, not
exactly, the same place.

| windings | 80 windings: median excess | share inside a sheet | windings below −0.03 | 130 windings: median excess | share inside a sheet | windings below −0.03 |
|---|---|---|---|---|---|---|
| w010 to w019 | −0.029 | 0.126 | 5 | 0.001 | 0.205 | 5 |
| w020 to w029 | 0.074 | 0.319 | 1 | 0.035 | 0.261 | 3 |
| w030 to w039 | 0.057 | 0.294 | 3 | 0.094 | 0.308 | 2 |
| w040 to w049 | 0.126 | 0.341 | 0 | 0.074 | 0.297 | 0 |
| w050 to w059 | 0.097 | 0.310 | 0 | 0.081 | 0.290 | 0 |
| w060 to w069 | 0.149 | 0.329 | 0 | 0.150 | 0.322 | 0 |
| w070 to w079 | 0.115 | 0.235 | 0 | 0.107 | 0.230 | 0 |

- **The gain is small and not uniform.** Four groups of ten rose, two fell and one did not move. Winding by
  winding, 42 of the 70 score higher in this fit, a median 0.013 higher; a sign test on that gives p = 0.12.
  With one seed for each fit I cannot say the difference is more than a second seed would give.
- **The innermost windings are off their sheets in both fits.** In w010 to w039, nine windings in this fit and
  ten in finding 114's score below −0.03: the copy moved 6 voxels sits inside a sheet more often than the
  winding does. The windings in the air were not the cause, because removing them did not change it.
- **The outermost ten did not suffer for being last.** w070 to w079 score 0.115, against 0.107 when 50 more
  windings lay outside them.
- **Scored over what it was asked for, the fit is in PHerc. 0211's range** (0.103 against 0.086), with a wider
  spread: the 10th percentile is −0.071 against −0.001.

## Winding spacing against sheet spacing

Registered as a description. Consecutive raw windings are a median 10.7 voxels apart (10th to 90th percentile
4.6 to 12.5, over 69 pairs). The share of nodes inside a sheet peaks at zero displacement (0.286), falls to
0.173 at 6 voxels and rises again to 0.216 and 0.219 at 14 voxels on either side, so the predicted sheets are
about 14 voxels apart. The ratio is 0.766. In finding 114's fit it was 0.825 over all 119 pairs. So the fit
still writes about four windings for every three predicted sheets, and an ink read of this band has to check
for windings sharing a sheet, as finding 113 did.

## What the fit did

| | 80 windings | 130 windings (finding 114) |
|---|---|---|
| tracks in the band | 822,420 | 822,420 |
| loss at step 0, 200, 1,000 | 13,463, 5,968, 660 | 13,468, 5,994, 653 |
| total loss at step 29,800 | 387.1 | 377.9 |
| track term | 171.1 | 206.0 |
| distance-field term | 109.9 | 102.6 |
| distortion term (`sym_dirichlet`) | 87.1 | 45.3 |

The track term fell by 17% and the distortion term nearly doubled. The distortion term is an average over the
windings the fit integrates, so 50 undistorted windings in the air would have lowered it in finding 114; I have
not checked that this accounts for the whole difference. villa's warning about `shell_outer_winding_idx` did not
appear.

## What it cost

| step | wall time | host memory (peak resident) | GPU peak |
|---|---|---|---|
| fit, 300 steps | 3 min 25 s | 6.6 GB | 9.6 GB |
| fit, 30,000 steps | 3 h 28 min 6 s | 6.6 GB | 11.9 GB |

Fewer windings did not make the fit cheaper: finding 114's took 3 h 20 min 6 s at 6.6 GB and 10.9 GB. Memory
pressure peaked at 0.6% over ten seconds. The training loop was stopped throughout. The distance field, dataset
and inputs are finding 114's.

## What this does to the campaign

By the registered consequences:

- **PHerc. 0826's band has a fit that can be read for ink, among its 45 windings at 0.07 or above.** That read
  waits for finding 113 to show whether the blinded protocol works, and is registered separately.
- **`HELPS`: PHerc. 0211's band, whose papyrus ends near its 120th winding, is worth refitting at 120 before
  more of it is read.** I hold this more weakly than the label reads. The line was cleared by 0.010 on one seed,
  and PHerc. 0211 has ten windings past its edge where PHerc. 0826 had 50. It does not touch finding 113, whose
  four windings are already rendered.
- **For any new scroll the fit needs a winding count before it is scored.** Here it came from a first fit with
  the default, which costs a second 3.5-hour fit. Counting predicted sheets along rays from the axis
  undercounted by about 1.7 times on the two scrolls where I could check it.
- villa's default of 130 windings overruns a small scroll, and villa's own inference of the outer winding is
  off in this recipe (it needs patches the recipe disables). Whether to describe that to villa, and how, is the
  owner's decision.

## What this does not show

1. That the windings are the right sheets. The distance field is the surface prediction the fit was given.
2. That the gain over the 130-winding fit is real. Two single fits, one seed each, p = 0.12 by a sign test.
3. That 80 is the best count. It was read off finding 114's table; I tried no other.
4. Why the innermost windings sit off their sheets.
5. Anything about ink.
6. Anything beyond this band, this seed and these settings.
