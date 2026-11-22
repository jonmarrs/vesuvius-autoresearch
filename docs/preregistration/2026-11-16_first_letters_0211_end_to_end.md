# Pre-registration: at the place where PHerc. 211's First Letters prize was won, does our whole pipeline put ink where the winning reader did?

**Written 2026-11-16, before any winding of this band has been flattened, rendered or read.** Finding 121.

## The question

Three findings have each tested one half of the pipeline at the place where the winner read eleven letters:

- **The reader** (finding 118): the recipe's four ink models on the winner's own surface gave r = 0.53 against
  the winning reader's map.
- **The geometry** (finding 119): the recipe's fit of the band reaches the winner's sheet in two pieces. w035
  follows the winner's columns 0 to 181 and w033 follows columns 193 to 300, each at finding 110's P1 line;
  w034 and w036 sit between predicted sheets.
- **A second reader** (finding 120): Reader V3 on the winner's surface gave r = 0.63.

Nothing has yet run end to end at a known place. **Our own fit's windings, snapped, flattened, rendered and read
as a band read would read them, and carried onto the winner's surface: do they put ink where the winning reader
put it?**

## Reachability, checked before this was written

- **The windings: w033, w034, w035 and w036 of finding 119's full fit.** By nearest winding, they hold 29.8%,
  8.5%, 37.3% and 10.3% of the winner's in-band nodes within 2 voxels (86% of the nodes, of the 88% within 2
  voxels of any winding); w037 holds 1.6% and every other winding less. They were chosen from finding 119's record
  by geometry against the winner's surface. No ink map of any of our windings in this band exists.
- **Every step is existing code,** run in this order by `run_end_to_end.sh`
  (`repro/first_letters/pherc0211_control/`):
  - the band's `run_snap.sh`, as arm `e2e` on the same fit;
  - `run_flatten.sh` (lasagna);
  - `run_render.sh`, which now takes `flip` to render with `--flip-normals`;
  - the recipe's `run_depth_sweep.sh` at depth +1;
  - `run_reader_v3.sh`'s villa call at depth +1;
  - `end_to_end.py`, which uses finding 110's transfer and finding 118's and 120's scoring.

  The image `vc-render:sampler-75c79ac5f` lists `--flip-normals`.
- **The flip is expected.** Finding 119's raw windings have a median normal cosine of −0.997 against the winner's
  surface. Finding 118 rendered the winner's surface unflipped and read its reading side at depth +1 (`_reverse`).
  So our windings must be rendered flipped for layer k to lie on the same side.

  `end_to_end.py orient` decides the flip per winding from the final (flattened) mesh, before any ink. The comparison
  stops if a render samples against the winner's normals.
- **The snap is deterministic.** Finding 119's description re-ran the recipe's snap on w028 to w042 into a scratch
  folder, and its report rows for w034 to w036 equal the registered snap's. Its level-0 surface chunks are on disk.
- **Tested on synthetic surfaces** (`tests/test_first_letters_0211_end_to_end.py`):
  - a winding that is the winner's own surface again reproduces finding 118's registered numbers exactly;
  - a mirrored one is refused unflipped and agrees fully when flipped;
  - one moved 10 voxels along the normal gives no cells;
  - with two windings, the nearer one gives the ink.
- **Not checked:** none of these steps has run on these windings. Lasagna has flattened only PHerc. 343's windings
  here (finding 110). This band's CT has not been rendered. How many of the winner's cells receive our ink is not
  known: finding 119 measured nodes along normals, and the transfer takes 4-pixel cells within 4 voxels in the
  scroll.

## Procedure

`run_end_to_end.sh`, run once, unattended, each step only if the one before exited 0:

1. `windings_e2e.txt` = w033 to w036; arm `e2e` reads finding 119's full fit. `run_snap.sh e2e`. Described: whether
   w034 to w036 come out byte-identical to finding 119's snap.
2. `run_flatten.sh e2e W` for each winding.
3. `end_to_end.py orient`: each final winding's median normal cosine against the winner's surface (finding 110's
   `surface_distance` over the winner's nodes in the band); flip if negative. Stop if any is missing or zero.
4. `run_render.sh e2e W [flip]`: 66 layers, CT streamed from the public bucket, as decided in step 3.
5. The recipe's four models at depth +1, both sides: `run_depth_sweep.sh RENDER MAPS 1 1`.
6. Reader V3 at depth +1, both sides (checksum and weights-only load first), for description only.
7. `end_to_end.py compare`.
   - **The transfer is finding 110's.** Each 4 × 4 pixel cell of the winner's render (finding 118's) takes the
     ink of the nearest cell of our four windings within 4 voxels in the scroll, and nothing where none is that
     close.
   - **Cells:** the winner's mask cells that are valid in the winner's render and receive our ink.
   - **The registered numbers are finding 118's.** r is taken between our transferred reading-side ensemble and
     the winner's map, both with their broad background taken off. The controls are our transferred other side
     at depth +1, and ours slid 64 pixels in four directions (the largest absolute value).

## Predictions, fixed now

- **What I expect: `E2E_AGREES`, with moderate confidence.**
  - **Little to lose to depth:** finding 118's r was 0.53 on the winner's own surface and flat (0.50 to 0.54)
    over depths −3 to +2, so a few voxels between our surface and the winner's should cost little.
  - **Close geometry:** 97% of the winner's nodes lie within 4 voxels of one of our raw windings (finding 119).
  - **Against:** the transfer resamples; w034 and w036 lie between sheets and may give cells off the sheet; and our
    renders are of flattened windings of a crushed scroll, which may be distorted where the winner's surface was
    refined by hand.

## Decision rule

| outcome | verdict |
|---|---|
| a step fails, a winding's orientation cannot be decided, a render samples against the winner's normals, or fewer than half of the winner's mask cells receive our ink | `DOES_NOT_RUN` |
| r at least 0.30, and at least twice the absolute value of each control | `E2E_AGREES` |
| r at least 0.15, and at least twice the absolute value of each control | `E2E_PARTLY` |
| otherwise | `E2E_DISAGREES` |

The lines are finding 118's, so the two r values compare directly.

What each does to the campaign:

- `E2E_AGREES`: the pipeline as a band read runs it finds the ink at a known text place, on the windings that lie
  on the sheet. A band read of an eligible scroll is then a working detection test wherever its windings lie on a
  sheet. The distance to letters is then the reader (findings 118 and 120) and following one sheet (finding 119),
  not the render or the transfer.
- `E2E_PARTLY`: our geometry costs much of the reader's agreement. The described comparison with finding 118's
  maps on the same cells says how much. Band reads detect ink weakly until the snap, flatten or render is fixed.
- `E2E_DISAGREES`: even with the right windings, our pipeline does not find the ink where it is known to be. Band
  reads with it say nothing about ink, and no eligible band is read again until the cause is found.

## Described, not deciding

- **Matched cells:** finding 118's maps on the same cells (r and controls), and the r between our transferred
  ensemble and finding 118's ensemble. Same reader on two geometries: what our geometry costs.
- **Per winding:** the cells each gave, and r on them where at least 1,000 cells.
- **By part:** r over finding 119's two parts, columns 0 to 181 and 193 to 300.
- **The transfer:** its distances (median, 95th percentile).
- **The steps:** the orientation records, and the snap's sameness.
- **Reader V3**, transferred the same way: r, controls and overlap.
- **An image** of our transferred ensemble, Reader V3 transferred and the winner's map, one above another, for the
  owner, on this machine.

## What the result cannot do

- **Legibility.** r measures where ink is. Finding 118 found agreement at r 0.53 with no readable letter.
- **A blind read.** The windings were chosen against the winner's surface. A blind band read would read every
  winding and would not know which carries text.
- **One place, one fit, one scroll.** The surface is where letters were found because someone refined it there.

## Cost

Snap under a minute. Flatten about a minute a winding, on the GPU (finding 110: 70 s). Render a few minutes a
winding, CT streamed (finding 110: 67 to 86 s for PHerc. 343). Ink about 6 to 10 minutes a winding at 3 to 4 GB
of GPU memory (finding 110: 5 min 38 s and 6 min 44 s). Reader V3 about 2 minutes a winding. Comparison about a
minute. About an hour in all, after the full test suite now running on #442 finishes. Nothing is uploaded; the
windings, renders, maps and image stay on this machine.
