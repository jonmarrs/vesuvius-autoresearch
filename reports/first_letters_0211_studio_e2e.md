At the place where PHerc. 211's First Letters prize was won, our own fit read by Studio puts ink where the winner's pipeline did (r 0.82), and draws the winner's letters (2026-11-16)

Finding 124. Our own fit's windings were read by Studio, the reader that won the prize, which the owner approved
on 2026-11-16 and which finding 123 showed runs here as it ran for the winner. Those windings are w033 to w036 of
finding 119's fit, snapped, flattened and rendered as finding 121 did. Studio's maps of them were carried onto the
winner's surface and compared with the winner's map. Registered before Studio read any render of ours:
`docs/preregistration/2026-11-16_first_letters_0211_studio_e2e.md` (commit `eee5f2b9`). Record:
`reports/first_letters_0211_studio_e2e.json`. Scripts as run: `repro/first_letters/pherc0211_control/`
(`run_studio_e2e.sh`, `studio_e2e.py`). The maps and the image stay on this machine (Studio's weights and outputs
are CC BY-NC 4.0); this report carries numbers.

**Verdict `STUDIO_E2E_CLOSE`**, as predicted, by the registered table: every step exited 0, 83.1% of the winner's
mask cells received our map, and r = 0.8247 is above the 0.70 line and more than twice each control (the reversed
planes −0.0471, the largest 64-pixel slide 0.1141).

## The registered numbers

| | value |
|---|---|
| Studio's input from each render | our layers 41 down to 26 (matched to the winner's own input by CT) |
| cells compared (the winner's mask cells that received our map) | 457,405 of 550,482 |
| **r, Studio on our windings carried onto the winner's surface, against the winner's map** | **0.8247** |
| control: Studio on the same planes in reversed order, carried the same way | −0.0471 |
| control: slid 64 pixels, largest absolute of four directions | 0.1141 (down 0.1015, up 0.1141, right 0.0131, left 0.0475) |

## Described, as registered

None of this changes the verdict.

| | r (background off) | r (background in) | overlap | largest slid overlap |
|---|---|---|---|---|
| our windings, carried (the registered map) | 0.8247 | 0.7383 | 0.7574 | 0.4154 |
| our render of the winner's surface | 0.9745 | 0.8368 | 0.8705 | 0.4242 |

- **Where the loss is.** Our renderer on the winner's own surface costs Studio almost nothing (r 0.9745). The
  geometry (our fit, snap, flatten and the transfer) takes it to 0.8247. The two maps agree with each other at r
  0.8181.
- **Per winding:** w033 0.8737 (164,315 cells), w034 0.7776 (95,215), w035 0.8238 (133,557), w036 0.7527 (64,318).
  The two windings that finding 119 found between predicted sheets before the snap are the lowest.
- **By part of the surface** (finding 119's columns): columns 0 to 181, r 0.7972; columns 193 to 300, r 0.8581.
- **The transfer:** median distance 1.94 voxels, 95th percentile 3.45, as in finding 121. Every winding's normals
  point against the winner's (median cosine −0.996 to −0.998) and every render was flipped.

## What the maps look like

My reading of the image (our windings carried, our render of the winner's surface, the winner's map, one above
another), a judgement and not a measurement:

- **The top panel, our whole pipeline with Studio,** draws the winner's letters. The same letter shapes appear in
  the same places in all three lines, among them the sequences the winner's map shows most clearly in the second
  line of the right third and in the first line on the left. They are a little blurrier than the winner's, with
  more broken strokes.
- **The black gaps** are the 17% of cells no winding reached (finding 121). They lie mostly in the upper middle
  and along the seams near the winner's columns 94 and 182.
- **The middle panel** is close to indistinguishable from the winner's.

This is the first image from this campaign's own geometry that shows letters at a place where letters are known.
Findings 118, 120 and 121 showed that the four models and Reader V3 do not draw them there, on either geometry. So
the step from no letters to letters is the reader.

## What it cost

| step | wall time |
|---|---|
| checksums | 2 s |
| planes: our render of the winner's surface, and four windings in both orders | 59 s |
| Studio, nine maps (about 70 s each, at most 14,481 MiB of GPU memory) | 10 min 26 s |
| comparison | 9 s |

## What this does to the campaign

The registered consequence of `STUDIO_E2E_CLOSE` reads: "our pipeline with Studio puts ink where the winning
pipeline did, at a known text place. The owner looks at the image for letters. If letters show, the next step is a
still-eligible band read the same way, registered separately, with that image deciding whether anything is
submitted."

**Letters show,** in my reading. The owner's own look at the image (`work/studio_e2e_v9.png` in finding 118's run
directory, on this machine) is still to come.

**What this establishes about the pipeline.** On one RTX 4090, the following, unrefined and with no hand work,
draws the letters the prize was awarded for, at that place:

- the recipe's 30,000-step spiral fit of a 1,500-slice band (3 h 32 min);
- the snap, flatten and render (minutes);
- Studio (about 70 s a winding).

**What it does not establish.** A blind read would not know which windings to read, or where to look. Finding 119
found that one winding follows a text-bearing sheet for 34 mm and then leaves it. So the next step reads every
winding of an eligible band with Studio, as images for the owner to inspect.

## What this does not show

1. **Legibility as a measurement.** "Draws the winner's letters" is my reading of one image.
2. **A blind read.** The four windings were chosen against the winner's surface.
3. **An untouched test of Studio.** Its continued training evaluated it on PHerc. 211, and the reference is
   Studio's own map.
4. **Studio's performance elsewhere.** This is one place of one scroll.
5. **Whether a submission built on Studio's CC BY-NC weights is accepted.** The owner decided to use them; the prize
   page does not address third-party non-commercial weights in First Letters.
