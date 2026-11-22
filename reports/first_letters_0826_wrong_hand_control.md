A spiral fitted to PHerc. 0826 turning the wrong way scores as well on the sheet-following score as the right one (median excess 0.099 against 0.103): the score cannot tell a spiral that follows the sheets from one that must cross them (2026-11-15)

Finding 116. Findings 112, 114 and 115 decided which fits of the prize-eligible scrolls could be read for ink by
one score, the excess. This is a control the score could have failed: the band of finding 115 (PHerc. 0826,
z 10250 to 11750, 80 windings) fitted again with the spiral declared to turn clockwise, against the anticlockwise
the catalog publishes. Nothing else changed. Host: 4 cores, 31 GB of RAM, one RTX 4090. Registered before the
fit ran: `docs/preregistration/2026-11-15_first_letters_0826_wrong_hand_control.md` (commit `8b8b3480`).
Record: `reports/first_letters_0826_wrong_hand_control.json`. Scripts as run: `repro/first_letters/eligible_band/`.

PHerc. 0826 is prize-eligible. This report and its record carry summary numbers about the fit. The windings, the
distance field and the score of each winding are on this machine only, and nothing here is a render or an ink map.

**Verdict `SCORE_BLIND_TO_DIRECTION`**, by the registered table: every step exited 0, 70 windings were scored,
and the wrong-direction fit's median excess is 0.099, above the line of 0.07. I registered
`SCORE_PARTLY_SEPARATES` (between 0.03 and 0.07), with low confidence. That prediction was wrong: the score
separated the two directions not at all.

## The score

For each raw winding, `excess` is the share of its nodes inside a predicted sheet minus the same share for the
nodes moved 6 voxels along the winding's normal.

| fit | windings scored | median excess | 10th to 90th percentile | windings with positive excess | median share of nodes inside a sheet |
|---|---|---|---|---|---|
| wrong direction, 300 steps (the floor) | 70 | −0.001 | −0.007 to 0.006 | 44.3% | 0.217 |
| wrong direction, 30,000 steps | 70 | **0.099** | −0.053 to 0.225 | **80.0%** | 0.290 |
| published direction, 30,000 steps (finding 115) | 70 | 0.103 | −0.071 to 0.224 | 78.6% | 0.294 |

By finding 112's table the wrong-direction fit would have earned `ON_SHEETS`, one step better than the
`PARTLY_ON_SHEETS` the published direction earned: 56 of its 70 windings are positive against 55. 41 of its
windings score 0.07 or above, against 45.

The registered thirds:

| windings | median excess | positive | at 0.07 or above | median share inside a sheet | median nodes scored |
|---|---|---|---|---|---|
| w010 to w033 (inner) | 0.003 | 50.0% | 7 of 24 | 0.221 | 6,533 |
| w034 to w057 | 0.112 | 95.8% | 17 of 24 | 0.315 | 13,676 |
| w058 to w079 (outer) | 0.130 | 95.5% | 17 of 22 | 0.288 | 20,996 |

The pattern is finding 115's: the inner third near zero, the rest well above the line.

## Is it really the other spiral?

Not registered. On the middle row of four windings (w020, w040, w060 and w075), the angle about the scroll axis
swept from one end of the winding to the other is −6.22 to −6.27 radians in finding 115's fit and +6.27 to
+6.30 in this one. Each fit's windings go once round, in opposite senses. villa read the declared direction.

## The two fits side by side

Not registered. The same indices, ten at a time:

| windings | wrong direction: median excess | share inside a sheet | published direction: median excess | share inside a sheet |
|---|---|---|---|---|
| w010 to w019 | −0.043 | 0.135 | −0.029 | 0.126 |
| w020 to w029 | 0.120 | 0.334 | 0.074 | 0.319 |
| w030 to w039 | 0.057 | 0.267 | 0.057 | 0.294 |
| w040 to w049 | 0.141 | 0.338 | 0.126 | 0.341 |
| w050 to w059 | 0.105 | 0.304 | 0.097 | 0.310 |
| w060 to w069 | 0.132 | 0.316 | 0.149 | 0.329 |
| w070 to w079 | 0.109 | 0.238 | 0.115 | 0.235 |

The published direction scores higher on 34 of the 70 windings. The two fits differ by less than either differs
from the 130-winding fit of finding 114.

## Where the two fits lie

Not registered, and measured after the verdict. For every third node of one fit, the distance along the other
fit's normal to its nearest node, the other fit's windings w010 to w079 taken together. As a reference, the same
between two fits of the published direction: finding 115's (80 windings) against finding 114's (130).

| windings of the first fit | wrong direction against finding 115: within 2 voxels | within 4 | median | finding 115 against finding 114: within 2 voxels | within 4 | median |
|---|---|---|---|---|---|---|
| w020 to w039 | 48.8% | 66.4% | 2.1 | 47.3% | 64.5% | 2.2 |
| w040 to w059 | 47.5% | 61.5% | 2.2 | 38.7% | 57.1% | 3.1 |
| w060 to w079 | 48.6% | 62.9% | 2.1 | 38.3% | 55.1% | 3.3 |

Over 90% of nodes had a node of the other fit within 12 voxels sideways in every row.

- **The wrong-direction fit lies on the same surfaces as the right one, about as often as two right-direction
  fits do.** Its windings are other turns joined differently, not other surfaces. The labels differ: the
  surface a node lies on belongs to a different winding in the other fit.
- So whatever the excess misses, it is not local placement. Both fits put about half their area within
  2 voxels of the same places, and the score cannot be expected to tell them apart there.
- A first try at counting how often a winding slips across the predicted sheets as it goes round (the phase of
  the stack along the normal, unwrapped along each row) found no difference between the wrong-direction fit and
  PHerc. 343's correct fit on two windings each. It is too noisy as built, and I have not pursued it.

## What the fit did

| | wrong direction | published direction (finding 115) |
|---|---|---|
| loss at step 0, 200, 1,000 | 13,459, 5,958, 662 | 13,463, 5,968, 660 |
| total loss at step 29,800 | 395.8 | 387.1 |
| track term | 181.6 | 171.1 |
| distance-field term | 107.2 | 109.9 |
| distortion term (`sym_dirichlet`) | 87.4 | 87.1 |

I registered a track term higher than the published direction's by less than 25%. It is 6.1% higher, so that
prediction held. Of every number here, the track term is the only one that favours the published direction, and
by 10.5 on a term of 171. Whether that difference is larger than a second seed would give, I do not know.

The spacing description: consecutive windings a median 10.5 voxels apart over 69 pairs, predicted sheets 14
apart, ratio 0.749 (finding 115: 0.766). The share of nodes inside a sheet peaks at zero displacement (0.286).

## Why, as far as I can tell

Not tested. A spiral turning the wrong way drifts against the real sheets by two sheet spacings each turn, so
each of its windings has to cross sheets somewhere. The fit is a smooth deformation of a spiral, fitted to local
evidence: normals, the distance field, tracks a tenth of a radian long. Nothing in it, or in the score, sees a
whole turn. If the deformation gathers the crossings into a few narrow places, almost every node is on a sheet
and both the loss and the score are content. The innermost windings, where a turn is shortest, are the ones that
score near zero in both fits.

## What it cost

| step | wall time | host memory (peak resident) | GPU peak, all processes |
|---|---|---|---|
| fit, 300 steps | 3 min 50 s | 6.6 GB | 10.1 GB |
| fit, 30,000 steps | 3 h 21 min 44 s | 6.6 GB | 13.8 GB |

Memory pressure peaked at 1.1% over ten seconds. The training loop was stopped. The repository's test suite ran
on the host during part of the fit; the GPU peak counts every process.

## What this does to the campaign

By the registered consequences:

- **`ON_SHEETS` and `PARTLY_ON_SHEETS` in findings 112 and 115 mean "near predicted sheets, locally".** They
  do not mean the windings follow one sheet round the scroll. A spiral that cannot do that scored the same.
  The strategy now says so.
- **No further band is read for ink on the score alone.** The next step is a second instrument, registered
  separately, that a wrong-handed spiral fails. It has to be checked first where the right windings are known:
  PHerc. 343, where finding 110's fit was compared with published windings.
- **Finding 113's read is not withdrawn.** Its strips are with the reader and what it can show is unchanged. Its
  four windings may cross sheets more often than its registration assumed, and its report will say so.
- **My reading, not registered: for First Letters this matters less than the registered consequence says.** A
  First Letters read looks for letters on tiles a few millimetres across. That needs the surface right
  locally, which the table above says the wrong-direction fit gets as often as the right one. Which turn a
  patch belongs to matters for reading text in order, which is the Grand Prize's problem and not this one's.
  The second instrument I would register measures a winding's continuity across a tile, not its direction.
  Whether to read further bands on the score alone until then is the owner's decision.
- **The score cannot find PHerc. 0125's direction**, so PHerc. 0125 does not become the third scroll by this
  route. The converged track term is a lead (6% in favour of the published direction here, one seed); a
  1,000-step fit did not separate the directions on PHerc. 343.

## What this does not show

1. That the published-direction windings cross sheets. The control shows the score cannot tell; it says nothing
   about how often the right-handed fit crosses.
2. Where the wrong-direction fit crosses sheets. Half its area coincides with the right fit; I have not found the
   places where its turns join differently.
3. That the track term separates the directions. One pair of fits, one seed each.
4. Anything about a round scroll. PHerc. 0826 is crushed; finding 110's PHerc. 343 fit, checked against
   published windings, is the one case where the score went with correct windings.
5. Anything about ink.
