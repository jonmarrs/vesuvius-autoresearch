# Pre-registration: Studio reads every winding of PHerc. 0826's band, as images for the owner

**Written 2026-11-20, before any winding of this fit has been snapped, flattened, rendered or read.** Finding 125.

## The question

Finding 124 showed that at the place where PHerc. 211's First Letters prize was won, this pipeline draws the
winner's letters. The pipeline is the recipe's unrefined spiral fit, snapped, flattened, rendered, and read by
Studio, the winning reader the owner approved on 2026-11-16. PHerc. 0826 is still eligible for First Letters.
**Read as finding 124 read PHerc. 211, does any winding of PHerc. 0826's fitted band show letters to the owner's
eye?**

This is a blind read. No reference surface or map exists, so nothing here can be scored against a known answer.
The registered output is the images and the numbers below; the decision is the owner's reading of the images.

## Reachability, checked before this was written

- **The fit:** finding 115's arm `outer80` of band z 10250 to 11750 of PHerc. 0826, with the outer winding set to
  80 (`PARTLY_ON_SHEETS`). It has 70 raw windings, w010 to w079, with a median excess of 0.103, 78.6% positive
  and 45 at or above 0.07.
  - **What that score does and doesn't say:** finding 116 found it cannot tell a wrong-handed spiral, so it says a
    winding lies near predicted sheets locally, not that it follows one sheet round the scroll.
  - **The weakest part:** the innermost windings (w010 to w039) sit off sheets.
- **The steps are the band's scripts** (`run_snap.sh`, `run_flatten.sh`, `run_render.sh`, unchanged since finding
  121) **and finding 124's Studio step:**
  - our render layers 41 down to 26, the order matched to the winner's own Studio input by CT;
  - finding 123's checksummed environment, weights and `inference.py`;
  - the winner's command.
- **Orientation, decided from the geometry before any ink.** On PHerc. 211 our fit's windings w033, w035 and w050
  have 99.8%, 99.8% and 98.8% of their normals pointing toward the band's centre (the mean of every winding's
  nodes), and flipped renders were right (findings 121 and 124). On this fit w020, w040 and w060 have 70.6%,
  92.2% and 96.9%. The rule: **flip a winding when more than half of its normals point toward the band's centre**;
  each winding's share is recorded.
- **Cost.** At finding 121's and 124's rates (flatten 77 to 89 s, render 54 to 69 s, Studio about 70 s a
  winding), 70 windings take about four hours, with renders of about 35 GB on disk.
- **Not checked:** none of this fit's windings has been snapped, flattened, rendered or read. The CT of this band
  has not been rendered.

## Procedure

`FL_SCROLL=PHerc0826 run_studio_band.sh outer80` (`repro/first_letters/eligible_band/`), run once:

1. **Snap** every raw winding (villa's `_spliced` twins are skipped).
2. **Flatten** each.
3. **Orient** each (`studio_band.py orient`), by the rule above.
4. **Render** each, 66 layers, flipped as decided.
5. **Studio** on each: our layers 41 down to 26, with the winner's command.
6. **Summarise** (`studio_band.py summarise`):
   - one 8-bit image of each winding's Studio map;
   - a contact sheet at one eighth;
   - per winding, the share of its rendered area at probability 0.5 or more, and the same share over each tile of
     380 pixels (finding 117's 19 nodes), with the largest tile share.

A winding whose flatten, render or Studio step fails is recorded and skipped; the others go on.

## Predictions, fixed now

- **What I expect, with low confidence:** letter-like shapes on some windings; a readable run of three or more
  letters on none.
  - **Against letters:** this band holds 1,500 of the scroll's slices; the fit is unrefined; finding 119 found a
    single winding follows one sheet for centimetres and then leaves it; and the innermost windings lie off
    sheets.
  - **For letters:** Studio drew the winner's letters from an unrefined fit at a known place.

## Decision rule

This read has no automatic verdict. The registered outputs are the images, the contact sheet and the numbers.

- **The owner sees letters:** the place is a candidate. Making a submission-quality image of it (refining the
  surface there, rendering, reading) and whether to submit are registered separately, and are the owner's
  decisions.
- **The owner sees none:** this band of PHerc. 0826 shows no letters under this pipeline. The next band or scroll
  is chosen separately.

The numbers order the windings for inspection and decide nothing. On PHerc. 211, Studio's reversed planes also drew
ink over a fifth to a half of some tiles, so ink share alone does not separate text from other structure.

## What the result cannot do

- **A negative is weak.** Only one band is read. The fit is unrefined, and a winding can leave its sheet.
- **A positive is the owner's reading,** not a measurement.
- **Disclosure.** The images stay on this machine, as finding 114 set for eligible-scroll outputs, and the report
  carries numbers only. I do not view the images myself, because that would send an eligible scroll's possible
  text off the machine to the model's API; the owner may say otherwise.
- **Licence.** Studio's weights and outputs are CC BY-NC 4.0.

## Cost

About four hours unattended, after the merges of #450, #456 and #458 finish their suites. GPU memory up to about
14.5 GB. Renders about 35 GB on disk; Studio's input planes are deleted after each read. Nothing is uploaded.
