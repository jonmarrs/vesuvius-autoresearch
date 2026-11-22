On the surface that won PHerc. 211's First Letters prize, Reader V3 comes closer to the winning map than the recipe's four models on both measures, by 0.097 in r where 0.10 was registered: `V3_NO_CLOSER` (2026-11-16)

Finding 120. Finding 118 found that the PHerc. 343 recipe's four ink models put ink where the winning reader put
it on the winner's PHerc. 211 surface (r 0.53) and draw no readable letter. Reader V3 is an MIT-licensed reader
with the architecture of two of those models. The question was whether, on the same render and the same cells, it
agrees with the winning reader's map more closely than the four models do. Registered before Reader V3 ran on the
surface: `docs/preregistration/2026-11-16_first_letters_0211_reader_v3.md` (commit `24281615`). Record:
`reports/first_letters_0211_reader_v3.json`. Scripts as run: `repro/first_letters/pherc0211_control/`
(`fetch_reader_v3.sh`, `run_reader_v3.sh`, `compare_readers.py`). The maps and the image stay on this machine;
this report carries numbers.

**Verdict `V3_NO_CLOSER`**, by the registered table. Reader V3's r clears its controls, and its overlap beats the
ensemble's by 0.1019, past the 0.05 margin. Its r beats the ensemble's by 0.0971, short of the 0.10 margin by
0.0029. I had predicted `V3_CLOSER`.

## The registered numbers

Finding 118's alignment (render layer 33, r 0.8128, shift (0, 0)) and cells (550,480 of 550,482), at depth +1 on
the reading side. The winner's ink cells (probability at least 0.5): 121,191.

| | ensemble (four models) | Reader V3 | difference |
|---|---|---|---|
| **r against the winner's map** | 0.53 | 0.6271 | **+0.0971** (margin +0.10) |
| control: other side | −0.0059 | −0.0194 | |
| control: slid 64 pixels, largest absolute | 0.093 | 0.1531 | |
| **overlap (Dice) with the winner's ink cells** | 0.5076 | 0.6095 | **+0.1019** (margin +0.05) |
| control: overlap slid 64 pixels, largest | 0.3315 | 0.3909 | |

Reader V3's r is more than twice each of its controls (0.6271 against 0.1531), so it does not fail them. The
ensemble's numbers are finding 118's to the last digit; `compare_readers.py` computed them again from the same
maps. Reader V3's slides by direction: down 0.1121, up 0.1531, right 0.0158, left 0.0507.

The slid overlap is high for both readers (0.30 to 0.39) because the ink lies in three lines, and a map slid along
a line still puts ink in it. Above that floor, Reader V3 gains 0.22 and the ensemble 0.18.

## Described, as registered

None of this changes the verdict.

**By depth (Reader V3, reading side).**

| depth | −3 | −2 | −1 | +0 | +1 | +2 |
|---|---|---|---|---|---|---|
| r | 0.6321 | 0.6349 | 0.642 | 0.6412 | 0.6271 | 0.5942 |
| other side | −0.0026 | −0.0063 | −0.0135 | −0.0177 | −0.0194 | 0.0013 |
| overlap | 0.6126 | 0.6133 | 0.6169 | 0.6176 | 0.6095 | 0.5894 |

- **The spread of Δr.** Over 1,000 resamplings of 168 blocks of 64 by 64 cells, the 95% interval of Δr at depth +1
  is 0.0728 to 0.1225. The registered margin lies inside it, so this verdict could have gone the other way on a
  slightly different surface.
- **Reader V3 against the ensemble.** r 0.6554: the two readers agree with each other more than either agrees with
  the winning reader's map.
- **The image** (ensemble, Reader V3 and the winner's map one above another; `work/compare_readers_v9.png` on this
  machine) is described below.

## Not registered

Δr at each depth, against finding 118's ensemble at the same depth: −3 +0.1101, −2 +0.1072, −1 +0.1074, +0 +0.0989,
+1 +0.0971, +2 +0.098. Reader V3 is ahead at every depth, by the margin or more at three of six. The registered
depth, +1, is the smallest difference of the six.

## What the maps look like

This is my reading of the image and of full-resolution crops of Reader V3's map beside the winner's, a judgement
and not a measurement. The registration said the image decides nothing.

- **The ensemble's map** is the one finding 118 described: bright blobs in the three lines over a noisy ground, no
  readable letter.
- **Reader V3's map** has a clean ground. It draws a few letter shapes, each where the winner's map has a letter:
  upright strokes and a curved stroke at the start of the first line in the right third, and a Y-shaped stroke in
  the first line on the left. Most of its map is dots and short strokes. I cannot read a word from it.
- **The winner's map** shows runs of letters in all three lines.

So Reader V3 is the better of the two readers here, in the numbers and to the eye, and it is not legible on this
surface. Neither of our readers does what the winning reader does.

## What it cost

| step | wall time | GPU peak |
|---|---|---|
| fetch, checksum and weights-only load of the checkpoint (138 MB) | not timed | none |
| Reader V3, depths −3 to +2, both sides (12 maps, 0 failed; 279 patches a map) | 8 min 19 s | 2,011 MiB |
| comparison | 43 s | none |

The first depth took 133 s and each later one 70 to 78 s. Maps 45 MB on this machine. villa's log reports the
checkpoint loaded with 0 missing and 0 unexpected keys at every depth. Its warning that the render has no level-3
occupancy scan, so level 0 is used, appears in finding 118's runs as well.

## What this does to the campaign

The registered consequence of `V3_NO_CLOSER` reads: "no MIT reader tried so far comes closer to the winning
reader's ink on this surface. The ensemble stays as the detection reader, and the winning reader is the remaining
candidate, on the owner's licence decision."

- **The rule's decision stands:** Reader V3 does not replace the ensemble on this evidence.
- **Its wording overstates the result.** Reader V3 does come closer on both numbers, at every depth, by less than
  the margin set for r. "Not closer by the registered margin" is what was found.
- **The image settles the practical question either way.** Neither MIT reader tried draws legible letters on a
  surface where the winning reader does. Legibility is what a First Letters claim is judged on. So the winning
  reader, whose weights are CC BY-NC, remains the only reader known to draw letters here. Whether it may be used
  in a submission is the owner's decision, now the campaign's main open question about the reader.
- **The next read can carry both MIT readers.** Reader V3 costs 8 minutes a surface on this machine. Producing its
  map beside the ensemble's costs little and decides nothing unless a registration says it does.

## What this does not show

1. Legibility as a measurement. The statements about letters are my reading of one image.
2. Agreement with the letters themselves. The reference is the winning reader's probability map, which may draw
   strokes differently from a reader that is also right.
3. How Reader V3 compares with the winning reader. The winner's map is the reference, so the winning reader is not
   measured here.
4. More than one surface of one scroll, refined by hand until letters showed under the winning reader.
5. Variation between runs. Each map was made once.
