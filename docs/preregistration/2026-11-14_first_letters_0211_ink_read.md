# Pre-registration: does a blinded reader see ink on four fitted windings of PHerc. 0211?

**Written 2026-11-14, before any winding of PHerc. 0211 has been snapped, flattened, rendered or given to an ink
model here.** Finding 113.

PHerc. 0211 is on the prize-eligible list. Every winding, render, ink map and tile this step makes from it stays
on this machine under `spiral_out/first_letters/pherc0211_band`. If the verdict is `LETTER_CANDIDATES`, nothing
about this step is pushed until the owner has seen it and decided; the prize rules forbid making a discovery
public. Otherwise the report carries counts of marks and costs, and no tile.

## The question

Finding 112 put the recipe's fit on predicted sheets of one band of PHerc. 0211 (`ON_SHEETS`). Its registered
consequence is an ink read of a subsample of that band as a detection test, after a check for stacked windings.
Finding 111 fixed what such a read can mean: on a correct surface of an unseen scroll the four released models
find labelled ink at AUC 0.72 to 0.75 and draw no readable letter, one side reads and the other does not, and
a blank result is weak evidence.

## Reachability, checked before this was written

All of this is unregistered scratch work on scrolls that are not eligible, or on the fit's geometry alone.

- **There is no label-free number to register.** On PHerc. 0841's development segment, where the maps exist at
  17 depths on both sides, I tried three statistics that need no labels: the correlation between two models'
  maps, the difference in local contrast between the two sides, and the periodicity of row profiles. With labels,
  the side-contrast difference of a 32-cell block separates ink blocks from bare ones (AUC 0.97 for Hecate and
  0.79 for dense_native at depth −2). Without labels, a fixed threshold on it flags 29.5% of all blocks on the
  reading side and 7.3% with the sides swapped, and that share is the same from depth −8 to +8 (24% to 30%),
  while the labelled ink fades over that range. So the share measures the side of the sheet and not ink. The
  other two did no better. A blind band therefore has to be read by eye.
- **There are almost no known-bare tiles.** At a tile of 96 cells (3.6 mm), the three labelled PHerc. 0841
  segments hold 82 tiles with labelled ink (overlapping by half) and one that is labelled bare. The only
  negative available at the size of a letter is the other side of a tile with ink.
- **Stacking is likely.** Consecutive raw windings of the PHerc. 0211 fit are a median 9.5 voxels apart, and the
  profile in finding 112 puts neighbouring predicted sheets about 14 voxels apart. On PHerc. 343 both are about
  12. The snap step will put some neighbouring windings on one sheet.
- **The side.** On PHerc. 343 the fitted windings' normals point away from the scroll axis (99.8% of nodes), the
  render was not flipped, and the published ink is in the maps the recipe names `_reverse`. On PHerc. 0211 the
  fitted normals point toward the axis (99% of nodes of three windings checked), because the spiral turns the
  other way. Rendered with `--flip-normals`, a PHerc. 0211 winding has PHerc. 343's arrangement, mirrored.
- **Not checked:** the snap, flatten and render scripts in `repro/first_letters/eligible_band/` have not run.
  The first winding is their test. A script that fails is fixed and that winding's step is run again; the
  report lists each such failure.

## Procedure

Scripts in `repro/first_letters/eligible_band/`, `FL_SCROLL=PHerc0211`, arm `full` (finding 112's fit). One step
at a time, each in its own unit, the training loop stopped.

1. **Choose four windings** (`choose_windings.py`): of the windings with finding 112's excess at 0.07 or above,
   in index order, cut into four groups of equal size (the last may be smaller); the highest excess in each.
2. **Snap** the four and both index neighbours of each.
3. **Stacked check** (`stacked_check.py`): a chosen winding is `stacked` on a neighbour if at least 30% of its
   nodes lie within 2 voxels of that neighbour's snapped surface along the normal. A stacked winding is still
   read: it is on a sheet. If two chosen windings are stacked on each other, the one with the lower excess is
   dropped and not replaced.
4. **Flatten** each remaining winding, **render** 66 layers with `--flip-normals`.
5. **Ink:** the recipe's depth sweep, four models, both sides, depths −3 to +2. That range holds the depth the
   published PHerc. 343 image used (+1) and the one chosen on PHerc. 0841 (−2).
6. **Tiles** (`blind_tiles.py`): tiles of 96 lattice cells (384 render pixels, 3.6 mm).
   - PHerc. 0211: per winding, among non-overlapping tiles with CT in at least 90% of their cells, the four with
     the highest score and four drawn at random from the rest (seed 113). The score is the larger of the two
     sides' local contrast of the Hecate map, averaged over the six depths; it treats the sides alike.
   - Anchors: twelve tiles with labelled ink from PHerc. 0841's development segment, drawn at random (seed 113)
     from those with at least 10% of their scored cells ink, at the same six depths.
   - Each tile gives two strips, one a side, each strip the four-model ensemble at the six depths in a row. The
     grey scale is fixed per winding or segment over both sides together. Strips are numbered in a shuffled
     order (seed 113); the key that says which strip is what is written to a separate file.
7. **The reader** is the owner. The reader sees the numbered strips and not the key, and marks each: 0 nothing,
   1 strokes, 2 one or more shapes that look like letters. A PHerc. 0211 strip can be told from a PHerc. 0841
   strip by its texture; what is hidden is the side and whether a tile was chosen by score or at random.
8. `score_marks.py` reads the marks and the key and applies the table below.

The reading side is `_reverse`, by the PHerc. 343 arrangement. The other side is the control.

## Predictions, fixed now

- **Anchors.** The reader marks at least 70% of the anchors' reading-side strips 1 or 2, and at most 30% of
  their other-side strips.
- **What I expect on PHerc. 0211: `NOTHING_SEEN`**, with moderate confidence. The strategy's judged chance of
  letters on a given scroll is a single-digit percentage, and this is four windings of one band.

## Decision rule

| outcome | verdict |
|---|---|
| a step exits non-zero after its fix, or fewer than two windings reach step 6 | `DOES_NOT_RUN` |
| the anchor prediction fails | `READER_NOT_CALIBRATED` |
| at least three PHerc. 0211 reading-side strips are marked 2, and more of them than other-side strips | `LETTER_CANDIDATES` |
| otherwise, reading-side strips marked 1 or 2 outnumber other-side ones, one-sided Fisher exact p below 0.05 | `STROKES` |
| otherwise | `NOTHING_SEEN` |

What each does to the campaign:

- `LETTER_CANDIDATES`: nothing is pushed. The owner decides the follow-up, which is the neighbouring windings and
  a look at the surface in VC3D, and where the outputs are kept.
- `STROKES`: one more band of PHerc. 0211 next to this one, registered separately, to see whether the strokes
  continue. No claim of ink: finding 111 showed strokes of similar strength outside labelled ink.
- `NOTHING_SEEN`: this band counts as PHerc. 0211's read for the campaign's kill criterion. The next scroll is
  PHerc. 0826.
- `READER_NOT_CALIBRATED`: the tiles are too small or the display is wrong. Fix on PHerc. 0841 alone, then
  register again.
- If the other side wins by the same test, it is reported as an unpredicted result and not as a detection.

## What the result cannot do

- **It cannot show there is no ink.** Finding 111: a blank result is weak evidence, and these are four windings.
- **`STROKES` does not separate ink from the side of the sheet.** The two sides differ in texture whether or not
  there is ink; the reader is asked for strokes and letter shapes, which is a judgement.
- **It does not show the windings are the right sheets**, or single sheets along their length.
- The reader knows which scroll a strip is from.
- A PHerc. 0211 strip may be mirrored or rotated against the way the text was written, because the spiral turns
  the other way from PHerc. 343's. The reader is told so. A mirrored letter is harder to recognise.
- The anchors come from the segment on which finding 111 chose its depth and side.

## Limits

One band, four windings at most, one reader, one pass. The tile size, the 30% stacking line and the mark
thresholds are judgements made here.

## Cost

On PHerc. 343 a winding took 41 seconds to snap (two windings), 72 to flatten, 86 to render and about 6 minutes
of ink for one depth. PHerc. 0211's windings have about twice the nodes, so I expect about 1.5 hours a winding and
6 hours in all, at under 4 GB of GPU memory. About 30 minutes of the reader's time. No training. No upload.
