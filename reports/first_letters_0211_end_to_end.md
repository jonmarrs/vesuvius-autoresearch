At the place where PHerc. 211's First Letters prize was won, our whole pipeline puts ink where the winning reader did, at r 0.52, and our geometry costs almost nothing (2026-11-16)

Finding 121. Findings 118 to 120 tested the reader and the geometry of this campaign's pipeline separately, on the
surface that won PHerc. 211's First Letters prize. This step ran the pipeline end to end, as a band read runs it.
Our own fit's windings w033 to w036 (finding 119) were snapped, flattened, rendered and read by the recipe's four
models, then carried onto the winner's surface by finding 110's transfer. They were compared with the winning
reader's map by finding 118's numbers and lines. Registered before any of these windings was flattened, rendered
or read: `docs/preregistration/2026-11-16_first_letters_0211_end_to_end.md` (commit `42fc47f0`). Record:
`reports/first_letters_0211_end_to_end.json`. Scripts as run: `repro/first_letters/pherc0211_control/`
(`run_end_to_end.sh`, `end_to_end.py`). The windings, renders, maps and image stay on this machine; this report
carries numbers.

**Verdict `E2E_AGREES`**, as predicted, by the registered table: every step exited 0, 83.1% of the winner's mask
cells received our ink, and r = 0.5194 is above the 0.30 line and more than twice each control (other side 0.0031,
largest 64-pixel slide 0.0662).

## The registered numbers

| | value |
|---|---|
| windings (all rendered with `--flip-normals`, from the geometry) | w033, w034, w035, w036 |
| cells compared (the winner's mask cells that received our ink) | 457,405 of 550,482 |
| **r, our transferred ensemble (reading side, depth +1) against the winner's map** | **0.5194** |
| control: our transferred other side, depth +1 | 0.0031 |
| control: ours slid 64 pixels, largest absolute of four directions | 0.0662 (down 0.0662, up 0.0611, right 0.0263, left 0.0142) |

## Described, as registered

None of this changes the verdict.

**What our geometry costs.** On the same 457,405 cells, finding 118's maps (the same four models on the winner's
own surface) give r = 0.5388 against the winner's map; ours give 0.5194. Our ensemble and finding 118's agree with
each other at r = 0.658. Reader V3, carried the same way, gives r = 0.6286 (other side −0.0205, largest slide
0.1409), against 0.6271 on the winner's own surface (finding 120). Our fit, snap, flatten, render and transfer cost
the four models 0.019 in r and Reader V3 nothing measurable.

**Overlap with the winner's ink cells.**

| | overlap | largest slid |
|---|---|---|
| our ensemble | 0.512 | 0.3189 |
| finding 118's maps, same cells | 0.516 | 0.3362 |
| Reader V3 through our geometry | 0.6137 | 0.3953 |

**Per winding.**

| winding | median normal cosine against the winner's | cells given | r on them |
|---|---|---|---|
| w033 | −0.9983 | 164,315 | 0.5528 |
| w034 | −0.9967 | 95,215 | 0.4768 |
| w035 | −0.9979 | 133,557 | 0.5195 |
| w036 | −0.9962 | 64,318 | 0.4828 |

w034 and w036, which finding 119 found mostly between predicted sheets before the snap, still gave more than a
third of the cells, at r near 0.48. After the snap, finding 119 found w034 partly on the winner's sheet.

**By part of the winner's surface** (finding 119's columns): columns 0 to 181, 265,555 cells, r 0.5136 (finding
118's maps 0.5203); columns 193 to 300, 177,215 cells, r 0.536 (0.5492).

**The transfer.** Median distance from a winner's cell to the cell of ours that gave its ink: 1.94 voxels; 95th
percentile 3.45. The snap of w034 to w036 came out byte-identical to finding 119's. All four windings were rendered
flipped: their final meshes' normals point against the winner's (median cosine −0.995 to −0.998, over 99% of the
winner's in-band nodes), as finding 119's raw windings did.

## What the maps look like

My reading of the image (our ensemble, Reader V3 and the winner's map, all on the winner's surface, one above
another), a judgement and not a measurement:

- **Our ensemble** through our geometry looks as it did on the winner's surface in finding 118: blobs in the three
  lines and no readable letter.
- **Reader V3** through our geometry looks as it did in finding 120: a clean ground, a few letter shapes where the
  winner's map has letters, and no readable word.
- **The cells no winding reached** (17%) show as black gaps. They lie mostly in the upper part of the middle third
  and along two vertical seams, near the winner's columns 94 and 182, where finding 119's nearest winding changes.

## What it cost

| step | per winding | in all |
|---|---|---|
| snap of four windings | | 10 s |
| flatten (lasagna) | 77 to 89 s, 0.6 GB of GPU memory | 5 min 21 s |
| render, 66 layers, flipped | 54 to 69 s | 3 min 58 s |
| ink, four models at depth +1, both sides | 5 min 16 s to 6 min 52 s | 25 min 10 s |
| Reader V3 at depth +1, both sides | 92 to 127 s | 7 min 13 s |
| orientation and comparison | | 15 s |

42 minutes from the first step to the verdict (14:15:38 to 14:57:45), unattended. The ink step's GPU peak was not
recorded. Renders take 2.2 GB on disk, maps 129 MB, flattened meshes 65 MB.

## What this does to the campaign

The registered consequence of `E2E_AGREES` reads: "the pipeline as a band read runs it finds the ink at a known
text place, on the windings that lie on the sheet. A band read of an eligible scroll is then a working detection
test wherever its windings lie on a sheet. The distance to letters is then the reader (findings 118 and 120) and
following one sheet (finding 119), not the render or the transfer."

It stands, and the described numbers make it sharper: on the known text, our geometry loses 0.02 of the four
models' r and none of Reader V3's. **What separates this pipeline from letters at this place is the reader.**
Neither reader we have draws a readable word here. The winning reader (Studio, CC BY-NC), the only one known to,
is the open question, and whether it may be used in a submission is the owner's decision.

Following one sheet (finding 119) matters for how a read is shown, not for whether the ink is found. Here the text
lies on w035's render for 60% of its length and on w033's for the rest, so a reader of single-winding renders
would see it in two pieces.

## What this does not show

1. Legibility as a measurement. The statements about letters are my reading of one image.
2. A blind read. The four windings were chosen against the winner's surface; a blind band read would read every
   winding and not know which carries text.
3. That the agreement holds where the geometry is worse. This surface was refined by hand where letters showed,
   and 17% of its cells got no ink of ours.
4. More than one place of one scroll, or variation between runs; each step ran once.
