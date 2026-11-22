Studio draws PHerc. 343's letters on our own fit of the place as it does on the published surface, so our pipeline is now checked at two places with known text (2026-11-22)

Finding 136. Finding 110's own windings w047 and w048 of PHerc. 343 (z 9500 to 11000) were read by Studio (the
winner's command; layers 41 down to 26 of their 66-layer renders, as for every band read). Each map was then
carried onto the recipe's published surface by finding 110's transfer. On the published image's area, the carried
map was scored by finding 124's statistic against Studio's map of the published surface (finding 127's). Nothing was
fitted, snapped, flattened or rendered: the windings and renders are finding 110's. Registered before Studio had
read any winding of ours on PHerc. 343: `docs/preregistration/2026-11-22_studio_343_own_windings.md` (commit
`d5f3330e`). Record: `reports/first_letters_343_studio_own.json`, from the run's `studio_own.json` and gates. Scripts
as run: `repro/first_letters/pherc343/` (`run_studio_343_own.sh`, `studio_343_own.py`).

**Verdict `STUDIO_343_OWN_CLOSE`**, as predicted, by the registered table. r is 0.8999, above the 0.70 line and more
than twice each control. Every step exited 0, and finding 127's own number came out again (r 0.6238 for Studio on
the published surface against `u`). Both renders sample along the published normals (median cosines 0.9974 and
0.9977). **So our pipeline with Studio is now checked at two places with known text:** PHerc. 211, crushed and
anticlockwise (finding 124), and PHerc. 343, clockwise.

## The registered numbers

On the 518,648 of the published area's 556,134 covered cells that our windings reach (share 0.9326):

| | value | rule |
|---|---|---|
| r, Studio on our windings carried, against Studio on the published surface | 0.8999 | `CLOSE` at 0.70 or more |
| reversed planes (control) | 0.1765 | r at least twice its absolute value |
| slid 64 pixels (control), largest of four | 0.3092 | r at least twice its absolute value |

The slid control is high at this place, as in finding 127 (0.2146 there): the letters stand in rows, so a sideways
slide still lines rows up. Up and down it gives −0.0027 and −0.0094; right and left, 0.3092 and 0.3023. The
reversed planes of the published surface itself give 0.1867 against its own forward map, about what our reversed
planes give (0.1765).

**Predictions.**
1. `STUDIO_343_OWN_CLOSE`, moderate confidence: held.
2. r between 0.75 and 0.90: held, at the top (0.8999).
3. Against `u`, our carried map within 0.10 of Studio's map of the published surface on the same cells, low
   confidence: held (0.6042 against 0.6286).
4. Both windings' r at least 0.70: held (0.899 and 0.9025).

## Described

**Each winding:**

| winding | cells | r |
|---|---|---|
| w047 | 331,788 | 0.899 |
| w048 | 186,860 | 0.9025 |

**Against `u`,** the recipe's ensemble image, on the 510,650 reading-frame cells both maps cover:

| | r | reversed planes | slid, largest |
|---|---|---|---|
| Studio on our windings, carried | 0.6042 | 0.1047 | 0.2224 |
| Studio on the published surface | 0.6286 | 0.1 | 0.2214 |

On these cells our geometry costs Studio 0.0244 in r against the published image.

**The carried map's other numbers:** r with the background in 0.7561; ink overlap 0.8129, against a slid overlap of
0.5248 at most. The transfer distances are 1.58 and 3.07 voxels at the median and 95th percentile.

**The two places side by side.** At PHerc. 211 our carried map agreed with Studio's map of our render of the
winner's surface at r 0.8181 (finding 124, described). Here, against Studio's map of our render of the published
surface, it agrees at 0.8999. The transfer here is closer (1.58 voxels at the median against 1.94) and reaches more of
the surface (0.93 of the area against 0.83 of the winner's mask). This study cannot say which of those, or the
difference between a crushed scroll and this one, accounts for the gap between the two places.

**The image** (`pherc343_mesh/work/studio_own/studio_own.png`, on this machine: our carried map, Studio's map of
the published surface and `u`, one above another, in reading orientation). My reading, a judgement and not a
measurement: our panel draws the same letters as Studio's map of the published surface, in the same places, in both
rows on the right and the row on the left. Its strokes are a little softer in places. Both are sharper than `u`.

## What it cost

6 min 55 s in all (registered: about 10 minutes). GPU memory peaked at 14,487 MiB in use by all processes
(registered: up to about 15 GB). The maps take 211 MB on disk.

| step | wall time |
|---|---|
| check | 2 s |
| planes, two windings in both orders | 27 s |
| Studio, four maps | 335 s |
| compare | 51 s |

## What this does to the campaign

The registered consequence of `STUDIO_343_OWN_CLOSE`: nothing in the band reads changes. A blank band of PHerc.
0813 (finding 129, clockwise as PHerc. 343 is) would carry the same weight as one of PHerc. 0826 or 0358. Finding 129
stays held for disk.

Before this, the clockwise direction had been checked with the reader alone, on someone else's surface (finding
127). Now the whole route has been checked there too: the recipe's fit, our snap, flatten and render, and Studio.

## What this does not show

1. **Legibility as a measurement.** "Reproduces" means agreement with Studio's own map of the published surface,
   which is a reader's map, not the ink.
2. **A blind read.** Finding 110 chose w047 and w048 against the published windings.
3. **How our fit does on other scrolls.** The recipe was developed on PHerc. 343, so our run of it there had the
   scroll its settings were made for.
4. **An untouched test of Studio.** Its training includes the fragment PHerc0343P, which may come from the same
   roll. That affects both maps alike.
