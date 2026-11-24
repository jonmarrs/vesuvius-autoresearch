# Pre-registration: does the PHerc. 306B team's window triage put PHerc. 211's known text first in a Studio band read?

**Written 2026-11-22, before any band read of PHerc. 211 with Studio and before any triage of a Studio band read.**
Finding 138.

PHerc. 211's First Letters prize was awarded on 2026-11-15, so the place is a positive control and may be viewed.
Studio's weights and outputs, and the glyph CNN's weights, are CC BY-NC 4.0 and stay on this machine.

## The question

Our band reads give the owner one Studio map per winding to look at: 70 windings of PHerc. 0826 and 111 of PHerc.
0358 so far, and 110 of PHerc. 0813 on the way. Nothing ranks where to look. Our own attempts at a label-free text
score (2026-11-13 and 2026-11-22, scratch) found nothing that held on more than the few known-text maps we have.

The PHerc. 306B First Letters team (Liam Warner and Nicola Bodill; prize announced 2026-11-02) found their line in
the same way we read bands. They fit one band per scroll with villa's spiral fitter and inked every winding. Then
they scored every window: "the glyph CNN ranked a window on winding 74 first of 72 candidates"
([repository](https://github.com/SirProdigle/pherc0306b-first-letters), `docs/METHOD.md`). Their code is MIT and
their weights are CC BY-NC 4.0. The CNN (`discovery/x_glyph/models/gA.pt`, 2.6 MB) was trained on synthetic Greek
letters and real text of other scrolls. By its training script it never saw PHerc. 0343, 0841 or 1447. Its maps were
Hecate's and Reader v2's, not Studio's.

So: in a Studio band read of the place where PHerc. 211's text is known, does that CNN rank the windows on the
winner's text first?

## Reachability, checked before this was written

- **The fit exists.** Finding 119's 30,000-step fit of PHerc. 211's band z 7650 to 9150 and its sheet-following
  record are on disk. Of its 120 windings, 80 have positive excess, so finding 126's selection rule reads them.
  The rule keeps w033 and w035, the two windings on the winner's sheet (finding 119: excess 0.459 and 0.637), and
  drops w034 and w036, which sit between sheets (−0.282 and −0.281).
- **The triage reproduces from their commit.** `repro/first_letters/triage/glyph.py` re-implements, at their commit
  `feabff6c`, the inference path of their `glyph_win.py` and the row score of their `spectral_rows.py`. Nothing of
  theirs is imported or run, and the weights are loaded with `weights_only=True` after a sha256 check.
- **Studio's text scores high on it.** A scratch run on finding 124's maps (unregistered, the only look at this
  place before this was written) put the largest glyph score on Studio's map of the winner's surface at 15.26. On
  our w035 it was 14.24, on w033 12.55, and on their reversed-plane controls at most 11.77. The same held at PHerc.
  343: published surface 14.19, our w047 15.03 and w048 12.90, reversed at most 11.45. Their admission line (9.06,
  the p99 of their negative windows on Hecate's maps) does not carry over to Studio's maps, so this registers a
  rank, not a threshold.
- **The place can be found on our windings.** `band_triage.py place` carries the read windings onto the winner's
  surface with finding 110's transfer, as finding 124 did. Dry run on finding 121's four windings: 457,405 of the
  winner's 550,480 mask cells are reached, a share of 0.8309, finding 124's.
- **The chain's last three steps run on stand-ins.** The stand-in band was finding 124's four maps, plus their
  reversed-plane maps under four other winding names standing in for windings without text.
  - **The result:** `glyph.py score` and `band_triage.py place` and `verdict` give 24 windows, 12 of them on the
    place, and `TRIAGE_FINDS_THE_TEXT` at rank 1 (w035, 14.49).
  - **What sits below the controls:** two place windows, w036 at 1,300 (10.67) and w033 at 0 (10.43), score below
    all four reversed controls (11.16 to 11.77). A place window can hold the crop without its letters (limit 4).

## Procedure

`repro/first_letters/pherc0211_control/run_band_triage.sh`, once, under `run_after_controls.sh` (finding 133's
choices: Studio with the skip, windings subdivided twice, three snap passes), each step only if the one before
exited 0:

1. **check:** finding 119's fit and quality record are on disk, nothing of this read is, and the glyph weights
   match `glyph.py`'s sha256 (fetched from their commit if missing).
2. **select:** the windings with positive excess, before any ink (finding 126's rule).
3. **densify, read:** `run_studio_band.sh fulldense`, rendering and reading at once (`FL_OVERLAP=1`), as finding
   133 reads PHerc. 0800: snap, flatten, orient by the axis, 18-layer renders, Studio on our layers 41 to 26.
4. **glyph:** every window of every read winding, as their `glyph_win.py` does it.
   - **The windows:** 2,600 render pixels wide at a 1,300-pixel stride, full height, skipped below 30% on the sheet.
   - **The input:** the map is z-scored over the sheet and drawn as their review overlay at 50 µm.
   - **The score:** a window's score is the largest five-view CNN logit over its 6.4 mm sub-windows (stride 0.8 mm,
     at least 70% on the sheet).
   - **Ours:** the sheet is the render's surface layer above zero, and a last window ends at each winding's end.
   - **Also:** their row score of each window (described).
5. **place:** a window holds the winner's place when at least 1,000 of the winner's mask cells, carried within 4
   voxels, fall in its columns (finding 121's minimum for scoring a winding).
6. **verdict:** every scored window of the band, ranked by glyph score; the rank of the best window that holds the
   place.

## The registered numbers and the verdict

| verdict | the best window on the winner's place |
|---|---|
| `TRIAGE_FINDS_THE_TEXT` | ranks among the band's first 10 windows |
| `TRIAGE_RANKS_THE_TEXT_HIGH` | otherwise, within the first 5% of the band's windows (at least the first 10) |
| `TRIAGE_MISSES_THE_TEXT` | otherwise |
| `BAND_READ_MISSES_THE_PLACE` | no read window holds 1,000 of the place's cells |
| `DOES_NOT_RUN` | a step fails, or windows hold the place but none of them has a score |

Ten windows is a short list for the owner to look at; 5% of a band of about 500 windows is about 25.

Described:
- the row score's rank of the best place window;
- every place window's scores and ranks;
- the twenty top windows, and each winding's rank by its best window;
- the share of windows above their admission line;
- the quantiles of the scores.

I will also look at the windows ranked above the place, since PHerc. 211 may be viewed, and say which show
letters. That look is described, not scored.

## Predictions

1. `TRIAGE_RANKS_THE_TEXT_HIGH`, low confidence. `TRIAGE_FINDS_THE_TEXT` is nearly as likely. Studio's text scored
   above every reversed control at two places, but a band's other windows are not reversed planes. PHerc. 211 may
   also carry text elsewhere in this band that outranks the winner's place.
2. The best place window is on w035, moderate confidence: it follows the winner's sheet for 34 mm (finding 119),
   and its map scored highest of finding 124's four.
3. The row score ranks the place lower than the glyph score, low confidence: the PHerc. 306B team found that it
   misses text with only two rows. In the scratch run it was high on w035 (17.0 and 8.5) and low on w033 (−1.9 and
   3.3).

## What each verdict does

- **`TRIAGE_FINDS_THE_TEXT` or `TRIAGE_RANKS_THE_TEXT_HIGH`:** the band pages of PHerc. 0826, 0358, 0813 and 0800
  get a list of windows in glyph order, the first 10 (or 5%) first, for the owner's look. That needs the owner's
  approval: the weights are CC BY-NC 4.0, as Studio's, and the maps are of eligible scrolls. The ranking only
  orders the look; nothing is dropped from the pages.
- **`TRIAGE_MISSES_THE_TEXT`:** the glyph CNN is not used on Studio's maps. If the row score ranks the place high,
  it is registered separately before any use.
- **`BAND_READ_MISSES_THE_PLACE`:** a band read would not have shown this text at all. The band reads' selection
  and geometry are checked before any more eligible bands are read.

## Limits

1. One place on one scroll. A rank is one number; it says the triage worked once, or failed once.
2. The CNN's training data are not public. Their screening negatives may include windows of PHerc. 211's lanes,
   which was eligible until 2026-11-15. Those were of their maps, not ours, and of their bands.
3. The rank counts windows that may hold other text as if they did not. The look at the windows above the place
   says how many do.
4. The place is the winner's crop, not the letters inside it. A window can hold the place on a part of the crop
   with no letters.

## Cost and when it runs

About 6 hours of GPU after finding 137, and about 20 GB of disk. That covers flattening 80 windings (about 70 s
each, as at PHerc. 0358), renders read by Studio as they finish, and a few minutes of the CNN on the GPU (6% of its
memory, as theirs). A unit waits for findings 129, 133 and 137 to finish first.
