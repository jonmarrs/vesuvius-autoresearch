# Pre-registration: does Studio draw PHerc. 343's published letters, on a scroll it was not trained on?

**Written 2026-11-20, before Studio has read any render of PHerc. 343.** Finding 127.

## The question

Studio is the reader that won PHerc. 211's First Letters prize, and the owner approved its use on 2026-11-16.
Findings 123 and 124 showed it runs here and draws PHerc. 211's letters from our own fit. Findings 125 and 126
read eligible bands of PHerc. 0826 and 0358 with it, blind. A blank band says something about that band only if
Studio sees ink on scrolls other than PHerc. 211, which its developer evaluated on repeatedly. **At the place
where the PHerc. 343 recipe's published image shows 18 letters, does Studio draw them?**

- **If yes:** a blind Studio read of another scroll is a test of the band, and findings 125 and 126 stand as
  designed.
- **If no:** a blank Studio band is close to uninformative. Later bands would also need the recipe's ensemble,
  which drew these letters. At finding 110's rates that costs about 16 minutes of GPU time per 17 megapixels on one
  side, against Studio's two.

## Reachability, checked before this was written

- **Training exposure.** Studio's three READMEs (read 2026-11-20) do not mention the scroll PHerc0343.
  - Its continued training includes five Reader v2/v3 label segments of **PHerc0343P**, at 8.64 µm, from update
    2,000.
  - The open-data catalog lists PHerc0343P as a fragment, a separate sample from the scroll PHerc0343. The fragment
    has its own scans (20250510090703 and 20250512023932). The scroll's volume is 20250521140437, the one read here.
  - So the scroll, its scan and this place are unseen. The fragment may come from the same roll, with the same
    hand and ink, so this is not a test on an unrelated scroll.
- **The render.** Finding 110 rendered the recipe's published surface here: 66 layers of 2560 × 6720, at
  `pherc343_repro/work/concat_w047-w048_R5B2_z9500-11000_66.zarr`. Its layer 34 and its valid mask are
  byte-identical to the published render's.
- **Studio's input, decided from the geometry.**
  - On PHerc. 211, Studio's input was our flipped render's layers 41 down to 26 (findings 123 and 124). Those
    renders' layers run outward, because the windings' normals point inward and the render was flipped.
  - This render's normals point outward on 99.73% of nodes (the recipe's sidecar). Unflipped, its layers also run
    outward.
  - **So the input is layers 41 down to 26, unflipped:** plane 0 is the outermost, as on PHerc. 211. The same
    planes in reversed order, 26 up to 41, are the other-side control.
- **The reference** is the recipe's own ensemble ink image `u`, the 8-bit image under the published overlay.
  - The recipe's `make_submission_image.py` rebuilt it today in a scratch directory, with the published command
    plus `--write-components`. Its PNG is byte-identical to finding 110's rebuild (SHA-256 `8954ae31…`).
  - `u` is 2455 × 5641 pixels in reading orientation. It is the raw render's columns 380 to 6021 and rows 105 to
    2560, mirrored in both directions, as the sidecar records.
  - The 18 letter boxes are in the same frame.
- **How well readers that drew these letters agree with each other,** measured today on the cells below with the
  registered statistic, before any Studio map exists. Each of the recipe's four models, z-scored, was compared with
  the mean of the other three. Each map was read as `make_submission_image.py` reads it, on the 551,720 valid cells
  of 864,330 in the area (63.8%):

  | model | against the other three | largest slid control |
  |---|---|---|
  | dense_native | 0.6195 | 0.147 |
  | Hecate | 0.4100 | 0.116 |
  | ink_9um seed 42 | 0.5250 | 0.107 |
  | ink_9um seed 43 | 0.5152 | 0.125 |

  These members were selected together, and two are seeds of one model, so their agreement is if anything high
  for independent readers. Finding 124's 0.70 line was set for Studio against Studio. No member reaches it
  against the rest, so it would be the wrong line for a cross-reader reference.
- **The comparison code, dry-run on these inputs** in a scratch directory, with dense_native's reading-side map
  standing in for Studio's (and its other side for the reversed map):
  - r 0.7898, which is a member against an ensemble that includes it;
  - the table above, reproduced;
  - `u`'s drawn share of the valid area, 0.1485, which is the sidecar's;
  - all 18 letter boxes scored;
  - 40 s and 1 GB of memory.
- **Cost:** two Studio maps of 17.2 megapixels. At finding 124's 70 s for 10.6 megapixels, that is about four
  minutes of GPU time, plus about a minute on the CPU.

## Procedure

`repro/first_letters/pherc343/run_studio_343.sh`, run once, into `pherc343_repro/work/studio_343`, after finding
125's read has finished. Each step runs only if the one before exited 0:

1. **check:** the SHA-256 values of Studio's weights and `inference.py` (finding 123's).
2. **reference:** the recipe's `make_submission_image.py`, with the published command plus `--write-components`,
   into `studio_343/reference`. It must give the PNG `8954ae31…`.
3. **planes:** `studio_e2e.py planes` gives the render's layers 41 down to 26, and with `--reverse` 26 up to 41.
4. **infer:** the winner's `inference.py` with the winner's command (`--stride 64 --blend hann --batch-size 32`)
   in finding 123's environment, on both inputs, with GPU memory sampled.
5. **compare:** `studio_343.py compare`, below.

## Registered measure and verdict

**The comparison.** Each Studio map is cropped to the area and mirrored, which puts it on `u`'s pixels.

- **Cells:** blocks of 4 × 4 pixels whose 16 pixels are all valid, valid meaning all 66 layers are above 0.
- **Statistic:** finding 118's r, between `u` and Studio's map, each block-averaged, with Studio's map
  standardised. Both have the broad background removed (`highpass`).
- **Controls:**
  - the same r for Studio's map of the reversed planes (the other side);
  - Studio's map slid 64 pixels in each of four directions, taking the largest absolute value.

**Verdict:**

| verdict | rule |
|---|---|
| `STUDIO_343_AGREES` | r ≥ 0.41, at least the lowest member against the other three (Hecate's 0.4100), and r ≥ 2 × each control |
| `STUDIO_343_PARTLY` | r ≥ 0.20 and r ≥ 2 × each control |
| `STUDIO_343_FAR` | otherwise |
| `DOES_NOT_RUN` | a step failed, a shape disagrees, or fewer than half of the area's cells are valid |

**Described, deciding nothing:**

- the overlap (Dice) of Studio's strongest cells with `u`'s drawn ink (`u` ≥ 0.35, the overlay's threshold), and
  its slid control;
- the leave-one-out table above, recomputed by the script;
- per letter box:
  - Studio's ink share (probability ≥ 0.5) inside the box;
  - `u`'s drawn share inside the box;
  - whether Studio's share inside exceeds its share over the whole valid area;
- Studio's ink share over the valid area, for both orders;
- my reading of the image: Studio's map in reading orientation above `u`, at full resolution. PHerc. 343 is not an
  eligible scroll and its letters are published, so I view this image.

## Predictions, fixed now

1. **`STUDIO_343_AGREES`, moderate confidence.** For: the fragment PHerc0343P was in training, and the scan is at
   8.64 µm like that fragment's. Studio also drew PHerc. 211's letters at r 0.82 against its own map. Against:
   PHerc. 211 was the scroll its development was steered on, and this is a different object at a different place.
2. The reversed order scores below 0.2. On PHerc. 211 it was −0.05.
3. In my reading, Studio draws most of the 18 letters, at least as legibly as `u`.

## What the result cannot do

- **A positive** shows Studio sees ink on one scroll other than PHerc. 211, at one place, a place where another
  reader had already drawn the letters. It does not show that Studio finds ink wherever it exists.
- **A negative** against `u` could be the reference's fault: `u` is a different reader's map. My reading of the
  image is the check on that.
- **Disclosure and licence.** Studio's weights and outputs are CC BY-NC 4.0. The maps and images stay on this
  machine, and the report carries numbers.

## Cost

About five minutes of GPU time and a minute of CPU. It runs once, after finding 125, while finding 126's chain is
fetching data and does not use the GPU. Nothing is uploaded.
