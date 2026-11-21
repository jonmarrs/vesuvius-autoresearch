Studio draws PHerc. 343's published letters (r 0.62 against the recipe's ensemble, above every member's agreement with the rest), so a blind Studio band read tests the band (2026-11-20)

Finding 127. Studio, the reader that won PHerc. 211's First Letters prize, read finding 110's render of the PHerc.
343 recipe's published surface, at the place where the recipe's published image shows 18 letters. Its map was
compared with that image's ensemble ink map `u`. Registered before Studio read any render of PHerc. 343:
`docs/preregistration/2026-11-20_first_letters_343_studio.md` (commit `29d69f40`). Record:
`reports/first_letters_343_studio.json`, which carries the run's `studio_343.json` (its SHA-256 is in the record)
with the step gates and GPU memory added. Scripts as run: `repro/first_letters/pherc343/` (`run_studio_343.sh`,
`studio_343.py`). Studio's weights and outputs are CC BY-NC 4.0; its maps and images stay on this machine, and this
report carries numbers and my reading.

**Verdict `STUDIO_343_AGREES`**, as predicted, by the registered table: every step exited 0, 63.83% of the area's
cells are valid, and r = 0.6238 is above the 0.41 line (the lowest of the recipe's four models against the other
three) and more than twice each control (the reversed planes 0.1015, the largest 64-pixel slide 0.2146).

## The registered numbers

| | value |
|---|---|
| Studio's input | the render's layers 41 down to 26, unflipped (plane 0 the outermost, as on PHerc. 211) |
| cells compared (4 × 4 blocks, every pixel valid) | 551,720 of 864,330 |
| **r, Studio's map against `u`** | **0.6238** |
| control: Studio on the same planes in reversed order | 0.1015 |
| control: slid 64 pixels, largest absolute of four directions | 0.2146 (down 0.0401, up 0.0152, right 0.2075, left 0.2146) |

The sideways slides score highest because they move rows of letters along rows of letters; up and down move them
onto the gaps between lines.

## Described, as registered

None of this changes the verdict.

**Against the readers that made `u`.** Each of the recipe's four models against the mean of the other three, on
the same cells (registered before Studio ran, recomputed by the script to the same values):

| reader | r against the rest | largest slid control |
|---|---|---|
| **Studio, against all four (`u`)** | **0.6238** | 0.2146 |
| dense_native | 0.6195 | 0.1465 |
| ink_9um seed 42 | 0.525 | 0.107 |
| ink_9um seed 43 | 0.5152 | 0.1247 |
| Hecate | 0.41 | 0.1155 |

Studio agrees with the ensemble at least as well as any of its members agrees with the others, though each member
is compared with three models and Studio with four.

- **With the background in:** r 0.5298.
- **Overlap** (Dice) of Studio's strongest cells with `u`'s drawn ink (`u` ≥ 0.35): 0.6318; slid, at most
  0.4434; reversed planes 0.2695.
- **Ink share over the valid area:** Studio 0.1453 (reversed planes 0.0574); `u` draws 0.1485.
- **The 18 letter boxes:** in all 18, Studio's ink share inside the box is above its share over the whole area.
  Inside the boxes Studio's share runs from 0.1549 (box 2) to 0.8186 (box 17), `u`'s from 0.1601 (box 3) to 0.8297
  (box 17). Studio's share is the lower of the two in boxes 2, 10, 11, 12, 13, 16, 17 and 18.

## What the map looks like

My reading of the letter rows (Studio's map, `u`, and Studio on the reversed planes, one above another, in reading
orientation), a judgement and not a measurement. PHerc. 343 is not an eligible scroll and its letters are
published, so I viewed it.

- **Studio's map draws letter shapes along both published rows, in the same places as `u`'s,** as thick,
  continuous strokes on an even dark ground: a run of shapes along the lower row (boxes 1 to 13, rising to the
  right with the surface) from end to end, and a run across the upper row (boxes 14 to 18).
- **`u` shows the same shapes broken into blobs** on a speckled ground. In my reading Studio's are the more
  legible, so the registered third prediction (Studio draws most of the 18 letters, at least as legibly as `u`)
  holds.
- **The reversed planes draw no letter shape:** scattered blobs and a faint vertical streak.
- **Not checked:** whether each shape is the published letter. The published image numbers its boxes; it does not
  name the letters in them.

The image is `pherc343_repro/work/studio_343/studio_343.png` on this machine (Studio's map above `u`), with
`studio_343_reversed.png` beside it.

## What it cost

| step | wall time |
|---|---|
| checksums | 2 s |
| reference (the recipe's image rebuilt, PNG `8954ae31…` as registered) | 13 s |
| planes, both orders | 14 s |
| Studio, two maps of 17.2 megapixels (at most 14,481 MiB of GPU memory) | 208 s |
| comparison | 37 s |
| **all** | **4 min 34 s** (registered: about six minutes) |

## What this does to the campaign

The registered consequence of `STUDIO_343_AGREES` reads: "a blind Studio read of another scroll is a test of the
band, and findings 125 and 126 stand as designed."

So Studio stays the reader for the blind band reads. It has now drawn letters on two scrolls: PHerc. 211, where its
developer evaluated it, and PHerc. 343, which it was not trained on. A blank Studio band is evidence about the
band's geometry and its sheets, not only about the reader. The recipe's slower ensemble is not needed beside it.

## What this does not show

1. **That Studio finds ink wherever it exists.** This is one place of one scroll, where another reader had already
   drawn the letters.
2. **An untouched scroll.** Studio's training includes five label segments of the fragment PHerc0343P, a separate
   sample that may come from the same roll, with the same hand and ink, at the same 8.64 µm.
3. **Studio on our own geometry here.** The surface is the recipe's published one, not a fit of ours as on PHerc.
   211.
4. **Legibility as a measurement.** "More legible than `u`" is my reading of one image.
