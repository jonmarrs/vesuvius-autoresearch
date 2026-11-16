On the surface that won PHerc. 211's First Letters prize, our four ink models put ink where the winning reader put it (r 0.53 against controls of 0.09 and below), and draw no readable letter (2026-11-16)

Finding 118. PHerc. 211's First Letters prize was awarded on 2026-11-15, and the winner published the surface, the
probability map and the CT image of the submission under CC BY-NC 4.0. The question was whether the four released
models of the PHerc. 343 recipe, which every ink read in this campaign has used, put ink where the winning reader
put it on that surface, with the geometry taken as given. Registered before our models ran on it:
`docs/preregistration/2026-11-16_first_letters_0211_reader_control.md` (commit `11ba1c41`). Record:
`reports/first_letters_0211_reader_control.json`. Scripts as run: `repro/first_letters/pherc0211_control/`. Our
render, maps and the side-by-side image stay on this machine, as registered; this report carries numbers.

**Verdict `READER_AGREES`**, by the registered table: every step exited 0, r = 0.53 is above the 0.30 line, and
it is more than twice each control (other side −0.006, largest 64-pixel slide 0.093). I had predicted
`READER_PARTLY`. What the image shows qualifies what that verdict means; see "What the maps look like".

## The registered numbers

| | value |
|---|---|
| alignment: render layer best matching the winner's CT image | 33 (the mesh layer), r = 0.8128 |
| shift between the rasters | (0, 0) pixels: the same raster, nothing moved |
| cells compared (4 × 4 pixel blocks inside the winner's mask) | 550,480 of 550,482 |
| **r, our ensemble (reading side, depth +1) against the winner's map** | **0.53** |
| control: our other side, depth +1 | −0.0059 |
| control: ours slid 64 pixels, largest absolute of four directions | 0.093 (down 0.093, up 0.0838, right 0.0274, left 0.0402) |

Both maps had their broad background taken off (Gaussian, sigma 16 cells) before r was taken, as finding 110 did.

## Not registered

None of this changes the verdict.

**Per model.** dense_native 0.5109, Hecate 0.4254, ink_9um seed 42 0.3079, ink_9um seed 43 0.3137, and the
four-model ensemble 0.53. Our own four models agree with each other at r 0.2307 to 0.4862 on this surface. So the
winning reader's map is about as close to each of our models as they are to one another.

**Depth and side.**

| depth | −3 | −2 | −1 | +0 | +1 | +2 |
|---|---|---|---|---|---|---|
| reading side (`_reverse`) | 0.522 | 0.5277 | 0.5346 | 0.5423 | 0.53 | 0.4962 |
| other side | 0.0049 | 0.0016 | −0.0131 | −0.0096 | −0.0059 | −0.0067 |

The reading side is flat across the six depths. The other side is at zero at every depth. The forward and
`_reverse` maps are the same 16 layers of the same render fed to the models in opposite order, so a model that
only followed CT brightness would give the same map both ways; ours do not.

**A defect found in the first run, and the recheck.** In the first record all six other-side numbers came out the
same (−0.0059). `transfer_maps.side` (finding 110's code) read the other side at depth +1 whatever depth it was
given. The registered control is at depth +1, so it was right; the five other entries of the depth table were not.
The function now passes the depth on, with a test, and `compare.py --recheck` measured everything again into a new
record (`work/compare_recheck.json` on this machine). The registered numbers and the verdict came out identical,
and the first record's checksum is unchanged. The table above is the recheck's. Finding 110 called the function
only at depth +1, so its numbers are unaffected.

**Other descriptions.** With the background left in, r = 0.6063. Slid by 256 pixels, the largest absolute r is
0.0581. The row profiles (the mean of each map along each of 424 rows of cells) correlate at r = 0.8525: both
maps put their ink in the same three lines.

## What the maps look like

This is my reading of the image, a judgement and not a measurement; the registration said the image decides
nothing. Our ensemble puts bright blobs in the same three lines as the winner's map, and in places on the same
letters. **No letter can be read from our map alone.** The winner's map, on the same cells, shows letters. This
is what finding 111 saw on PHerc. 0841 (ink located, AUC 0.72 to 0.75, no readable letter), now against a reader
that does draw letters there.

So r = 0.53 measures where the ink is, and on that our reader agrees with the winning one. It does not measure
legibility, and on legibility the two differ.

## What it cost

| step | wall time | GPU peak |
|---|---|---|
| render, 66 layers, CT streamed from the public bucket | 5 min 37 s | none |
| ink, depths −3 to +2, both sides, four models (48 maps, 0 failed) | 36 min 23 s | 2,914 MiB |
| comparison, and the recheck | under a minute each | none |

Render 750 MB and maps 212 MB on this machine. The training loop was stopped throughout.

## What this does to the campaign

The registered consequence of `READER_AGREES` reads: "The reader is not what stands between us and letters; the
geometry half of the control comes next." The second half stands: finding 119, whether the recipe's own fit of
this part of PHerc. 211 lands on the winner's sheet, is registered (commit `64db6973`) and running. **The first
half was written too broadly, and the image does not support it.** On this surface our reader finds the ink and
does not render it legibly. For a First Letters claim legibility is what is judged, so the reader still stands
between us and letters, even where the geometry is right.

In practice:

1. Our four models can be used to find where ink is on a band (here r 0.53 against a reader that wins prizes, at
   every depth tried).
2. A blank band read with them is weak evidence of no ink. Strokes in their maps are not letters, as finding 111
   already said.
3. A reader that draws letters is the missing piece. The winning reader's weights are CC BY-NC; whether they may
   be used in a submission is the owner's question, and was already open (strategy review of 2026-11-16).

## What this does not show

1. Anything about the geometry. The surface is the winner's, refined by hand until letters showed under the
   winning reader, which favours that reader's map over ours.
2. Agreement with the letters themselves. The reference is the winner's probability map, not a transcription.
3. That all four of our models had never seen PHerc. 211. dense_native's training configuration lists no
   PHerc. 211 data, and the ink_9um model card names its training scrolls as PHerc. 0139, Scroll 1667,
   PHerc. Paris 4 and PHerc. 0814 (read after the run). Hecate's card names Paris 4 and otherwise speaks of other
   scrolls without listing them, so whether Hecate saw PHerc. 211 is unknown. Hecate alone scores 0.4254, below
   dense_native and above the two ink_9um seeds.
4. A measured legibility gap. The statement that our map shows no readable letter is my reading of one image.
5. Variation between runs. Each map was made once.
