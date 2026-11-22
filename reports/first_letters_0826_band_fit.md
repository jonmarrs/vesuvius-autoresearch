On PHerc. 0826 the recipe's spiral fit fails the registered test (median excess 0.004), because its last 50 windings lie outside the papyrus; the 60 before them follow predicted sheets as on PHerc. 0211 (2026-11-14)

Finding 114. PHerc. 0826 is the First Letters campaign's second prize-eligible scroll. The question and the
measurement are finding 112's, unchanged: does the PHerc. 343 recipe's spiral fit, run with villa's defaults on
one band (z 10250 to 11750), write windings that follow predicted sheets? Host: 4 cores, 31 GB of RAM, one RTX
4090. Registered before any fit of PHerc. 0826 ran here:
`docs/preregistration/2026-11-14_first_letters_0826_band_fit.md` (commit `acf767e0`). Record:
`reports/first_letters_0826_band_fit.json`. Scripts as run: `repro/first_letters/eligible_band/`.

PHerc. 0826 is prize-eligible. This report and its record carry summary numbers about the fit. The windings, the
distance field and the score of each winding are on this machine only, and nothing here is a render or an ink map.

**Verdict `NOT_ON_SHEETS`**, by the registered table: every step exited 0, 120 windings were scored in each fit,
the floor is 0.001, and P2 fails. I registered `ON_SHEETS` as the expected outcome, with low confidence. That
prediction was wrong.

## The score

For each raw winding, `excess` is the share of its nodes inside a predicted sheet minus the same share for the
nodes moved 6 voxels along the winding's normal.

| fit | windings scored | median excess | 10th to 90th percentile | windings with positive excess | median share of nodes inside a sheet |
|---|---|---|---|---|---|
| PHerc. 0826, 300 steps (the floor) | 120 | 0.001 | −0.003 to 0.005 | 55.8% | 0.145 |
| PHerc. 0826, 30,000 steps | 120 | **0.004** | −0.007 to 0.167 | **59.2%** | 0.174 |
| PHerc. 0211, 30,000 steps (finding 112) | 120 | 0.086 | −0.001 to 0.226 | 88.3% | 0.309 |
| PHerc. 343, 30,000 steps (finding 110) | 120 | 0.140 | 0.025 to 0.240 | 96.7% | 0.356 |

P1 asked for a median of at least 0.07 and at least 80% of windings positive; P2 for 0.03 and 65%.

The registered thirds, in index order:

| windings | median excess | positive | at 0.07 or above | median share inside a sheet | median nodes scored |
|---|---|---|---|---|---|
| w010 to w049 (inner) | 0.065 | 67.5% | 19 of 40 | 0.282 | 10,240 |
| w050 to w089 | 0.081 | 80.0% | 21 of 40 | 0.263 | 24,527 |
| w090 to w129 (outer) | −0.000 | 30.0% | 0 of 40 | 0.007 | 12,030 |

40 of the 120 windings score 0.07 or above and 49 score zero or below.

## Why it fails: the fit has more windings than the band has papyrus

None of this section was registered, and none of it changes the verdict. The windings in index order, ten at a
time, with PHerc. 0211's beside them:

| windings | PHerc. 0826: median excess | share inside a sheet | PHerc. 0211: median excess | share inside a sheet |
|---|---|---|---|---|
| w010 to w019 | 0.001 | 0.205 | 0.052 | 0.297 |
| w020 to w029 | 0.035 | 0.261 | 0.095 | 0.306 |
| w030 to w039 | 0.094 | 0.308 | 0.181 | 0.381 |
| w040 to w049 | 0.074 | 0.297 | 0.167 | 0.365 |
| w050 to w059 | 0.081 | 0.290 | 0.118 | 0.355 |
| w060 to w069 | 0.150 | 0.322 | 0.075 | 0.314 |
| w070 to w079 | 0.107 | 0.230 | 0.136 | 0.375 |
| w080 to w089 | 0.001 | 0.038 | 0.098 | 0.341 |
| w090 to w099 | 0.000 | 0.028 | 0.153 | 0.360 |
| w100 to w109 | −0.001 | 0.011 | 0.086 | 0.222 |
| w110 to w119 | −0.000 | 0.003 | 0.052 | 0.107 |
| w120 to w129 | −0.000 | 0.001 | 0.001 | 0.012 |

- **From w080 outward the PHerc. 0826 windings are not near any predicted sheet.** Under 4% of their nodes are
  inside one, and the median distance from a node to the nearest sheet is 37 voxels for w080 to w089 and 83 to
  127 beyond, where 127 is the largest value the distance field stores. From w090 a quarter or more of the nodes
  fall outside the distance field altogether. Inside w079 that median distance is 2 to 5.5 voxels. villa's
  default writes 130 windings whatever the scroll's size; in this band the papyrus ends near the 80th.
- **PHerc. 0211 has the same edge, 40 windings later.** Its last ten windings score 0.001 with 1% of nodes inside
  a sheet. Finding 112's report put the weak outer third down to "that default, or the scroll"; this is the
  default.
- **Inside the edge the fit looks like PHerc. 0211's.** Over w020 to w079 the median excess is 0.083, with 80%
  of the 60 windings positive and 36 at 0.07 or above. I chose that range after seeing the table, so it is a
  description and not a test.
- **So the registered score mixed two questions.** A median over all 120 windings asks whether the windings
  follow sheets and also whether 130 is the right number of them. On PHerc. 0211 the second mattered little
  (ten windings past the edge); here it decides the verdict. That is a flaw in the rule I registered.

## Winding spacing against sheet spacing

Registered as a description. Consecutive raw windings are a median 11.6 voxels apart (10th to 90th percentile
6.4 to 14.9, over 119 pairs). The share of nodes inside a sheet peaks at zero displacement (0.171), falls to
0.112 at 6 voxels and rises again to 0.133 and 0.139 at 14 voxels on either side, so the predicted sheets are
about 14 voxels apart. The ratio is 0.825. I expected under 0.85; it is, barely, and it is taken over all 119
pairs, including the windings outside the papyrus. On PHerc. 0211 the ratio was 0.68 by hand.

## What the fit did

| | PHerc. 0826 | PHerc. 0211 (finding 112) | PHerc. 343 (finding 110) |
|---|---|---|---|
| tracks in the band | 822,420 | 1,454,417 | 2,277,921 |
| loss at step 0, 200, 1,000 | 13,468, 5,994, 653 | 6,593, 1,541, 381 | 4,142, 964, 326 |
| total loss at step 29,800 | 377.9 | 241.6 | 234.6 |
| track term | 206.0 | 134.5 | 148.6 |
| distance-field term | 102.6 | 49.7 | 48.4 |
| distortion term (`sym_dirichlet`) | 45.3 | 35.5 | 18.5 |

Every term ended higher than on the other two scrolls, the distance-field term at twice their value. villa gave
the same warning about `shell_outer_winding_idx` as on both; the shell losses are zero by the recipe's overrides.

## What it cost

| step | wall time | host memory (peak resident) | GPU peak |
|---|---|---|---|
| fetch the band's volumes | 17 min 30 s | not recorded | none |
| distance field (CPU) | 12 min 11 s | 0.8 GB | none |
| fit, 300 steps, with pool building | 4 min 6 s | 8.8 GB | 10.1 GB |
| fit, 30,000 steps | 3 h 20 min 5 s | 6.6 GB | 10.9 GB |

Memory pressure during the full fit peaked at 0.6% over ten seconds. The training loop was stopped throughout.
My first launch of the full fit failed in my own command line before the fit script was reached; nothing ran,
and the fit as reported is the only one.

## What this does to the campaign

By the registered consequence: **no ink read of this fit. The next step on PHerc. 0826 is one named change to
the fit, registered separately: the number of windings set to what the band holds, about 80 here, in place of
villa's default of 130.** That registration will also have to say how the count is chosen without looking at
the result, and its score will be taken over the windings the fit is asked for.

For PHerc. 0211 nothing changes: finding 113 reads four windings chosen among those at 0.07 or above, all well
inside its edge.

## What this does not show

1. That the windings inside the edge are the right sheets. The distance field comes from the surface prediction
   the fit was given.
2. That fewer windings would fit better. The windings past the edge may or may not have pulled the others
   off their sheets; this run has no fit without them.
3. Where the papyrus ends, other than by the surface prediction. I did not look at the CT.
4. Anything about ink.
5. Anything beyond this band, this seed and these defaults. Each fit ran once.
6. How this fit compares with the other contributor's attempt on PHerc. 0826 listed on the winners page.
