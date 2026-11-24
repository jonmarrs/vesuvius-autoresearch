In a Studio band read of PHerc. 211, the PHerc. 306B team's glyph network ranks a window on the winner's text second of 467 (TRIAGE_FINDS_THE_TEXT), but the windows around it are mostly texture (2026-11-24)

Finding 138. Finding 119's fit of PHerc. 211's band z 7650 to 9150 was read the way finding 133 read PHerc. 0800:
the 80 windings with positive excess, subdivided twice, snapped three times, rendered and read by Studio with its
empty-window skip, renders and Studio overlapped. Then every window of every winding was scored by the glyph network
the PHerc. 306B team used to find their line, re-implemented from their commit `feabff6c` with their weights
(`gA.pt`, sha256 `36ae0d6d…`). Registered before any Studio band read of PHerc. 211 or any triage of one:
`docs/preregistration/2026-11-22_first_letters_0211_band_triage.md` (commit `26d5c8a5`). Record:
`reports/first_letters_0211_band_triage.json`. Scripts: `repro/first_letters/pherc0211_control/run_band_triage.sh`,
`band_triage.py`, `repro/first_letters/triage/glyph.py`.

PHerc. 211's prize was awarded on 2026-11-15, so the place is a positive control and may be viewed. Studio's weights
and outputs and the glyph network's weights are CC BY-NC 4.0, and stay on this machine.

**Verdict: `TRIAGE_FINDS_THE_TEXT`.** Every step exited 0 and all 80 windings were read. The best window holding the
winner's place ranks 2nd of the band's 467 scored windows, inside the registered short list of 10. I predicted
`TRIAGE_RANKS_THE_TEXT_HIGH`, with `TRIAGE_FINDS_THE_TEXT` nearly as likely. As registered, this sends the eligible
bands' pages a list of windows in glyph order, the first 10 first; the owner approved that on 2026-11-23.

**But the network does not separate text from the texture around it.** The one window ranked above the place shows
no letters I can read, and the place's score stands 0.086 above the next window's. Without the window that our
version adds at each winding's end, the place ranks 9th of 400. The list orders the owner's look; it does not say
where text is.

## The registered numbers

| | value |
|---|---|
| windows scored (2,600 render pixels wide, 1,300 apart, at least 30% on the sheet, and one ending at each winding's end) | 467 |
| windows holding the place (at least 1,000 of the winner's mask cells carried within 4 voxels into their columns) | 11, all scored |
| best place window | w033 at x0 2000, glyph score 13.977, holding 180,309 cells |
| **its rank** | **2** |
| lines: first 10; first 5% (at least 10) | 10; 24 |

The 80 read windings reach 438,968 of the winner's 550,480 mask cells (0.7974). Finding 124's four windings reached
0.8309.

## The predictions

1. **`TRIAGE_RANKS_THE_TEXT_HIGH`, low confidence; `TRIAGE_FINDS_THE_TEXT` nearly as likely.** Not as worded: the
   result is the better of the two.
2. **The best place window is on w035, moderate confidence.** Not held: it is on w033. w035's best window ranks 15th.
3. **The row score ranks the place lower than the glyph score, low confidence.** Held: 4th against 2nd.

## Described

| place window | glyph score | rank | row score |
|---|---|---|---|
| w033, x0 2000 | 13.977 | 2 | 6.232 |
| w035, x0 0 | 13.336 | 15 | 11.772 |
| w035, x0 1300 | 13.164 | 19 | 5.096 |
| w033, x0 0 | 13.039 | 23 | -2.053 |
| w033, x0 1300 | 12.766 | 31 | 0.996 |
| w035, x0 2280 | 12.578 | 40 | 11.348 |
| w037, x0 1300 | 10.93 | 173 | 0.998 |
| w037, x0 0 | 10.656 | 201 | 1.073 |
| w032, x0 1820 | 10.609 | 208 | 22.854 |
| w032, x0 1300 | 10.398 | 234 | 5.022 |
| w032, x0 0 | 9.172 | 330 | 3.045 |

- **The first ten windows:** w029 at x0 1200 (14.188), the place (13.977), w086 at 10400 and 10660, w092 at 5200
  and 3900, w090 at 2600, w080 at 7800, w090 at 3900 and w082 at 5200 (13.5).
- **The windings by their best window:** w029, w033, w086, w092, w090, w080, w082, w087, w055, w052, then w035.
- **The scores are bunched:** median 10.398, 90th percentile 12.494, 99th 13.732, the largest 14.188. 0.7302 of the
  windows score above the team's admission line (9.06, the 99th percentile of their negatives on Hecate's maps), so
  that line does not carry over to Studio's maps, as the registration expected.

**The look, as registered.** PHerc. 211 may be viewed, so I looked at the window ranked above the place, w029 at x0
1200, in a crop of its Studio map. It is blocky texture with a few stroke-like marks near its right end, which is the
winding's end. I can read no letters in it. The place window, w033 at x0 2000, shows letter shapes in three lines,
mirrored, as this fit's windings render them.

## Checked after the result (not registered)

A favourable result is the one to check hardest. `repro/first_letters/pherc0211_control/band_triage_audit.py` works
from the records alone and reproduces the verdict's ranking before it reports.

- **The end window.** Our version adds one window per winding where the last window on the grid stops short of the
  winding's end; the team's code never scores those pixels. Both the first-ranked window and the place's best are such
  end windows. They are 67 of the 467 windows (0.1435), but 3 of the first 10, 6 of the first 20 and 9 of the first
  50. Their median score is the others' (10.391 against 10.41).
- **Without them**, ranking only the grid's 400 windows as the team's code would, the best place window ranks 9th:
  still inside the first 10, by one place.
- **The margins are thin.** The place's best window scores 0.211 below the first rank, 0.086 above the next and 0.477
  above the 10th.
- **Beyond the registered look**, the 3rd-ranked window (w086 at x0 10400) is blocky texture with no letters, and the
  5th (w092 at x0 5200) is texture with a few letter-like strokes at its top left.

## What it means

At the one place where we know the text, the triage puts the text near the top of a band read: 2nd of 467, or 9th of
400 by the team's own windows. That is what the registration asked, and its consequence follows: the eligible bands'
pages get their windows in glyph order, the first 10 first, for the owner's look. Nothing is dropped from the pages.

It is an order, not a detector. Texture scores within a fraction of a logit of the text, the windows ranked just above
and below the place show no letters, and the result rests on one place. On an eligible band, a short list headed by
texture is the expected case, and a blank short list says little about the rest of the band.

## Limits

1. **One place on one scroll.** A rank is one number.
2. **Near-ties.** A change of 0.09 in the place's score moves it from 2nd to 3rd, and of 0.48 out of the first 10.
3. **The end window is ours.** The verdict counts it, as registered; without it the place holds the line by one rank.
4. **The network's training data are not public.** Their negatives may include windows of PHerc. 211's lanes, though
   of their maps and bands, not ours.
5. **The place is the winner's crop**, not the letters in it. My look found letters in the best place window.
6. **The look is mine,** at a third of full scale, and is described, not scored.

## Cost

| step | wall time |
|---|---|
| check, select, densify | 16 s |
| read, 80 windings | 15 h 15 min 43 s, of which 11 h 30 min 17 s frozen (below): 3 h 45 min 26 s |
| glyph scores | 7 min 49 s |
| place, verdict | 40 s |
| **all** | **15 h 24 min 28 s; without the freeze, 3 h 54 min 11 s** (registered: about 6 hours) |

| read step | wall time |
|---|---|
| snap, three passes | 1270 s |
| flatten, 80 windings | 1 h 16 min 3 s (median 64 s, at most 97 s) |
| render, 80 windings | 1 h 49 min 34 s (median 81 s, at most 234 s) |
| Studio, 80 windings | 2 h 0 min 1 s (median 88 s, at most 244 s) |
| summarise | 2 min 17 s |

- **The freeze.** At 22:38 on 2026-11-23 the disk had 42 GB free, and the read's render guard refuses a render below
  50 GB. A scratch unit froze the run's processes as its orient stage began, before any render, and thawed them at
  10:08:47 on 2026-11-24, once the owner had approved freeing 71 GB of downloaded tracks. Nothing of the run was
  changed; the frozen time sits inside the orient stage's gate (41,420 s) and the read step's.
- **The overlap.** The renders and Studio ran together for 2 h 5 min 35 s, against 3 h 49 min 35 s of their steps.
- **Disk:** about 34 GiB (renders 21.4 GiB, Studio's maps 6.6 GiB, flattened windings 6.1 GiB, three snap passes 0.3
  GiB), against a registered 20 GB.
