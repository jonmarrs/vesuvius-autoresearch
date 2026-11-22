# Pre-registration: on the surface that won PHerc. 211's First Letters prize, does Reader V3 put ink where the winning reader did, more closely than the recipe's four models?

**Written 2026-11-16, before Reader V3 has been run on that surface.** Finding 120.

## The question

Finding 118 ran the PHerc. 343 recipe's four released ink models on the winner's published PHerc. 211 surface. They
put ink where the winning reader put it (r = 0.53 against controls of 0.09 and below, `READER_AGREES`), and no
letter can be read from their map, where the winner's map shows letters. So the reader is what stands between this
campaign and letters, even where the geometry is right. The strategy review of 2026-11-16 asked for released
readers to be compared on a positive control before any wider search. The winning reader's weights are CC BY-NC,
and whether they may be used in a submission is the owner's question. Reader V3 is MIT. **On the same surface, the
same render and the same cells, does Reader V3 agree with the winning reader's map more closely than the four
models do?**

## Reachability, checked before this was written

- **The reader.** Reader V3 (github.com/DomRusso2/reader-v3, MIT; weights at huggingface.co/domenicor046/reader-v3,
  card licence MIT), revision `aee1d64b`, `reader-v3.pth` 138,379,659 bytes, SHA-256 `ea405417…`
  (`fetch_reader_v3.sh` holds it in full). It was awarded \$5,000 in the October Progress Prizes, and the winners
  page says it is widely used in First Letters submissions.
- **Safe to load.** villa's ink loader calls `torch.load(..., weights_only=False)`. The checkpoint loads with
  torch's weights-only unpickler (`check_checkpoint.py`), so it holds only tensors and plain values: keys
  `config`, `model`, `step`.
- **The recipe's villa runs it unchanged.** In the recipe's villa (`0fb38c45`) the checkpoint's configuration
  builds `vesuvius_unet_3d_stem_2d`, the ink_9um seeds' architecture: 34,546,498 parameters, 508 tensors, 0
  missing and 0 unexpected keys when its weights load (villa loads with `strict=False`, so this was counted). Its
  patch is 17 × 384 × 384 against the seeds' 17 × 128 × 128; its normalisation is the seeds' (`robust_mad`). Its
  README's command is the recipe's call for the seeds with only the checkpoint changed.
- **Exposure.** Its training labels (huggingface.co/datasets/domenicor046/reader-v2-labels, MIT) are 70 segments
  of PHerc. 0139, 0814, 0500P2, 0009B, 0343P and 0172: no PHerc. 211. Reader V3 is Reader v2 trained further on
  the same labels. Reader v2's own starting weights were not checked.
- **What is already known.** Finding 118's ensemble numbers on this surface are measured (r 0.53; other side
  −0.006; slid 0.093), and I have seen finding 118's image of the ensemble beside the winner's map. The ensemble's
  overlap (below) has not been computed. No Reader V3 map of this surface exists.
- **Not checked:** `run_reader_v3.sh` and `compare_readers.py` have not run on real data. Reader V3's speed and GPU
  memory on this host are not measured.

## Procedure

Scripts in `repro/first_letters/pherc0211_control/`, run once each, on finding 118's run directory
(`spiral_out/first_letters/pherc0211_control`), on this machine.

1. `fetch_reader_v3.sh`: the checkpoint at the pinned revision, its checksum, the weights-only load.
2. `run_reader_v3.sh`: on finding 118's 66-layer render, unchanged, depths −3 to +2, both layer orders. The call is
   the recipe's own call for its ink_9um seeds: villa `vesuvius.ink_detection.inference.infer`, `--overlap 0.5
   --blend-mode hann --batch-size 4 --direction both`, layers s to s + 16 with s = depth + 25.
3. `compare_readers.py`, with finding 118's alignment, cells (4 × 4 pixel blocks inside the winner's mask) and
   reference (the winner's probability map, block means), for two readers:
   - **ensemble:** finding 118's four-model maps at depth +1, reading side, unchanged;
   - **Reader V3:** its map at depth +1, reading side (`_reverse`), standardised over the cells.

   For each reader:
   - **r:** finding 118's number, both maps with their broad background taken off (Gaussian, sigma 16 cells).
     Controls: the reader's other side at depth +1, and the reader slid 64 pixels in four directions (the largest
     absolute r).
   - **overlap:** the winner's ink cells (probability at least 0.5) against as many of the reader's strongest cells
     (background off), as the Dice coefficient. Control: the reader slid 64 pixels, the largest of four
     directions, leaving out cells that wrapped round. This is new here: r rewards a map that is bright where the
     ink is, and overlap asks whether a reader's strongest cells are the winner's ink cells rather than blobs
     around them.
4. **Described, not deciding:** Reader V3's r, other side and overlap at every depth; the spread of the difference
   in r over 1,000 resamplings of 64-cell blocks; Reader V3's r with the ensemble; and an image of the ensemble,
   Reader V3 and the winner's map one above another, for the owner, on this machine.

## Predictions, fixed now

- **What I expect: `V3_CLOSER`**, with low-to-moderate confidence. Reader V3 has the seeds' architecture with three
  times their context, its README shows letters drawn whole on segments it never saw at this scan's protocol, and
  finding 118's ensemble already finds this surface's ink at r 0.53. Against it: the reference is a different
  reader's map, which may draw strokes differently from Reader V3 while both are legible.

## Decision rule

Δr and Δoverlap are Reader V3's number minus the ensemble's, each rounded to four places first.

| outcome | verdict |
|---|---|
| a step fails, no alignment within 16 pixels, fewer than half the mask's cells compared, or a number missing | `DOES_NOT_RUN` |
| Reader V3's r is not at least twice the absolute value of each of its controls | `V3_FAILS_CONTROLS` |
| Δr at least +0.10 and Δoverlap at least +0.05 | `V3_CLOSER` |
| Δr at most −0.10, or Δoverlap at most −0.05 | `V3_FARTHER` |
| otherwise | `V3_NO_CLOSER` |

The margins are judgements. Finding 118's r varied by 0.05 across six depths, so 0.10 is twice that. No spread of
the overlap has been measured on this surface.

What each does to the campaign:

- `V3_CLOSER`: Reader V3 replaces the four-model ensemble as this campaign's reader for every later read, from a
  checkpoint with no licence question. The owner looks at the image for legibility before any eligible band is read
  with it.
- `V3_NO_CLOSER`, `V3_FARTHER` or `V3_FAILS_CONTROLS`: no MIT reader tried so far comes closer to the winning
  reader's ink on this surface. The ensemble stays as the detection reader, and the winning reader is the
  remaining candidate, on the owner's licence decision.

## What the result cannot do

- **Legibility.** Neither number says whether a map can be read. The image is for the owner's eye and decides
  nothing here.
- **The reference is one reader's map.** A reader that draws the letters differently from the winning reader, or
  better, is scored down. And this comparison cannot test the winning reader itself: its own map is the reference.
- **One surface of one scroll**, refined by hand until letters showed under the winning reader.
- **The ensemble was seen first.** Its r is known and its image has been looked at; only its overlap is new.

## Cost

Reader V3 on six depths, both orders, on the GPU: not measured here; the ink_9um seeds took about two minutes a
depth (finding 118). The comparison takes a few minutes on CPU. Nothing is uploaded.
