# Pre-registration: does Studio draw PHerc. 343's letters on our own fit of the place, as on the recipe's published surface?

**Written 2026-11-22, before Studio has read any winding of ours on PHerc. 343.** Finding 136.

## The question

Finding 127 found that Studio draws PHerc. 343's published letters on the recipe's published surface: r 0.6238
against the recipe's ensemble image `u` (`STUDIO_343_AGREES`). That surface is someone else's. Finding 124 found
that our own fit of PHerc. 211, read by Studio, reproduces Studio's read of the winner's surface there (r 0.8247).
No study has read our own fit of PHerc. 343 with Studio. Finding 127's report names this as a limit.

**On finding 110's own windings w047 and w048 of PHerc. 343, carried onto the recipe's published surface, does
Studio's map reproduce Studio's map of that surface?**

PHerc. 343 is clockwise, as PHerc. 0813 is (finding 129, held for disk). Findings 124 and 127 between them checked
the reader and our geometry on a crushed, anticlockwise scroll, and the reader alone on a clockwise one. This checks
our geometry with the reader on the clockwise one, so a blank band of PHerc. 0813 can be weighed like one of
PHerc. 0826 or 0358.

## Reachability, checked before this was written

- **The windings and renders are on this machine.**
  - The windings: finding 110's `pherc343_mesh/work/final_recipe/w047.tifxyz` and `w048.tifxyz`.
  - The renders: its 66-layer `render_recipe/w047_66.zarr` and `w048_66.zarr`, rendered unflipped.
- **Studio's planes.**
  - `studio_e2e.py planes` gives 16 × 2380 × 5480 (w047) and 16 × 2420 × 5640 (w048), 8-bit.
  - The window is layers 41 down to 26, as for finding 127's map of the published surface.
- **The transfer reproduces finding 110.** On all of the published render's 669,771 cells, finding 110's transfer
  from w047 and w048 accepts 0.9357 of them, at 1.62 and 3.06 voxels at the median and 95th percentile. It gives
  358,609 and 268,069 cells to the two windings, with normal cosines 0.9974 and 0.9981. These are finding 110's
  recorded numbers.
- **The comparison runs.** `studio_343_own.py compare` was dry-run today, with the recipe's dnative maps of w047 and
  w048 standing in for Studio's.
  - **Finding 127's gate:** its own number came out again (r 0.6238 for Studio on the published surface against
    `u`).
  - **The cells:** the published image's area holds 556,134 cells that the published render covers. The transfer
    reaches 518,648 of them (share 0.9326), and the normal cosines are 0.9974 and 0.9977 there.
  - **The stand-in:** dnative's map of our windings gave r 0.5895 against Studio's map of the published surface,
    with controls 0.0552 (reversed) and 0.2212 (slid). That is one reader against another and predicts nothing about
    Studio against itself.
- **The weights and environment** are finding 123's, checked by SHA-256 as in findings 124, 127 and 135.

## Procedure

`repro/first_letters/pherc343/run_studio_343_own.sh`, once, each step only if the one before exited 0:

1. **check.** Finding 123's weights and the winner's `inference.py` against their SHA-256 values.
2. **planes.** Layers 41 down to 26 of each winding's 66-layer render, and the same reversed.
3. **infer.** Studio with the winner's command (`--stride 64 --blend hann --batch-size 32`) on all four.
4. **compare.** `studio_343_own.py compare`.

## Registered measure and verdict

- **The cells:** cells of the published image's area (the sidecar's raw-frame area) that the published render
  covers in all 66 layers, that receive a value from our windings within 4 voxels, and where every map has a value.
- **r:** finding 124's statistic, between Studio's map of our windings carried onto the published surface and
  Studio's map of the published surface (finding 127's `forward.npy`), both with the broad background taken off.
- **Controls:** the carried map of our reversed planes, and the carried map slid 64 pixels (the largest absolute
  of four directions).

| verdict | rule |
|---|---|
| `DOES_NOT_RUN` | any of: a step failed; finding 127's r 0.6238 does not come out again; a winding gives no cells, or its render samples against the published normals (median cosine 0 or below); fewer than half the area's covered cells receive a value; a number is missing |
| `STUDIO_343_OWN_CLOSE` | r at least 0.70, and at least twice the absolute value of each control |
| `STUDIO_343_OWN_PARTLY` | r at least 0.40, and at least twice the absolute value of each control |
| `STUDIO_343_OWN_FAR` | otherwise |

These are finding 124's lines, kept so the two places are read by one rule. The tests check that `DOES_NOT_RUN`
gives no read even when r is high, and that a control above half of r keeps a read out of `CLOSE` and `PARTLY`.

**Described, deciding nothing:**

- each winding's r;
- the transfer's distances;
- r with the background in, and the ink overlap;
- **against `u`, on the same reading-frame cells:**
  - our carried map;
  - Studio's map of the published surface;
- an image for the owner and for me: our carried map, Studio's map of the published surface, and `u`, one above
  another. PHerc. 343's letters are published, so the image may be looked at.

## Predictions, fixed now

1. **`STUDIO_343_OWN_CLOSE`, moderate confidence.**
   - For:
     - At PHerc. 211 our carried map agreed with Studio's map of our render of the winner's surface at r 0.8181
       (finding 124, described).
     - Here the transfer is closer (1.62 voxels at the median against 1.94) and reaches more (0.93 against 0.83).
     - The recipe's ensemble, carried the same way, gave r 0.8622 on the letter boxes (finding 110).
     - Finding 135 found Studio's read of this place keeps at least 0.94 of its r within 4 layers of depth.
   - Against: at PHerc. 211 Studio lost far more to our geometry than the four models did (finding 121 against
     finding 124), because a sharp map pays for every voxel of offset.
2. **r between 0.75 and 0.90.**
3. **Against `u`,** our carried map is within 0.10 of Studio's map of the published surface on the same cells. Low
   confidence.
4. **Both windings' r are at least 0.70.**

## Consequences

- **`STUDIO_343_OWN_CLOSE`:** our pipeline with Studio is then checked at two places with known text: PHerc. 211
  (crushed, anticlockwise) and PHerc. 343 (clockwise). Nothing in the band reads changes. A blank band of PHerc.
  0813 (finding 129) would carry the same weight as one of PHerc. 0826 or 0358.
- **`STUDIO_343_OWN_PARTLY`:** the loss is located from the described numbers before finding 129 is restarted.
  If it points at something finding 129 would repeat, an amendment is registered before any of its data exist.
- **`STUDIO_343_OWN_FAR`:** on a clockwise scroll our geometry does not carry Studio's read. The report recommends
  that finding 129 not start until the cause is found. Its start is already held for disk.
- **`DOES_NOT_RUN`:** nothing changes. The cause is fixed and the run repeated only under an amendment.

## What the result cannot do

- **"Reproduces" is agreement with Studio's own map of the published surface, not legibility.** The reference is a
  reader's map, not the ink.
- **It is not a blind read.** Finding 110 chose w047 and w048 against the published windings (its P1).
- **It may flatter our fit on other scrolls.** The recipe was developed on PHerc. 343, so our run of it there had
  the scroll its settings were made for.
- **Studio's training includes the fragment PHerc0343P,** which may come from the same roll (finding 127's
  caveat). That affects both maps alike, so it does not favour either.

## Limits

One place on one scroll, two windings, one reader, one machine. The lines are judgements carried over from finding
124, not fitted here.

## Cost

About 10 minutes:
- four Studio maps of about 100 s each (finding 127: 208 s for two of the published surface's size);
- four plane extractions;
- a comparison of about 2 minutes.

GPU memory up to about 15 GB. The maps take about 0.2 GB of disk; each set of planes, about 0.2 GB, is deleted
after its map. Nothing is fitted, flattened, rendered or downloaded. It runs alone. PHerc. 343's letters are
published, but Studio's weights and outputs (CC BY-NC 4.0) stay on this machine.
