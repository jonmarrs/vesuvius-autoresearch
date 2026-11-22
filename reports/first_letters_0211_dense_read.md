The twice-denser snap reads the same as the fit's own grid where PHerc. 211's prize was won, though it puts more of every winding on the predicted sheet (2026-11-21)

Finding 131. Finding 119's raw windings w033 to w036 of PHerc. 211 (band z 7650 to 9150) went through finding 121's
route twice more: once as they are (`rerun`), and once subdivided twice before the snap (`dense2`, as the band reads
since finding 126 do). Each arm was snapped, flattened, oriented against the winner's surface, rendered at 66 layers
and read by Studio. Its map was carried onto the winner's surface and compared with the winner's map, as finding 124
did. Registered before any winding was densified or read for this test:
`docs/preregistration/2026-11-20_first_letters_0211_dense_read.md` (commit `f242f84f`). Record:
`reports/first_letters_0211_dense_read.json`, from the run's `dense_read.json` and gates. Scripts as run:
`repro/first_letters/pherc0211_control/` (`run_dense_read.sh`, `dense_read.py`).

**Verdict `DENSE_READS_SAME`**, as predicted, by the registered table. Every step exited 0, and the `f124` arm gave
finding 124's r 0.8247 on its own cells. The change, r(`dense2`) − r(`rerun`), is −0.0099, inside the margin of
0.02.

## The registered numbers

On the 442,015 of the winner's 550,482 mask cells that all three arms reach (share 0.803):

| arm | r against the winner's map |
|---|---|
| `f124` (finding 124's windings and maps) | 0.8304 |
| `rerun` (finding 121's route again) | 0.8267 |
| `dense2` (subdivided twice, then the same route) | 0.8168 |

| | value | rule |
|---|---|---|
| noise, r(`rerun`) − r(`f124`) | −0.0037 | |
| margin | 0.02 | the larger of 0.02 and twice the noise |
| change, r(`dense2`) − r(`rerun`) | −0.0099 | better at +0.02 or more, worse at −0.02 or less |

No render samples against the winner's normals (a `DOES_NOT_RUN` condition): the median normal cosines are −0.9961
to −0.9989, as in finding 124.

**Predictions.** (1) `DENSE_READS_SAME`, low-to-moderate confidence: held. (2) The noise is below 0.01: held
(0.0037).

## Described

**More on the sheet, not read better.** The denser snap put more of every final winding within 2 voxels of the
predicted sheet:

| winding | `f124` | `rerun` | `dense2` | `dense2` − `rerun` |
|---|---|---|---|---|
| w033 | 0.9034 | 0.9047 | 0.9392 | +0.0345 |
| w034 | 0.7742 | 0.7747 | 0.8184 | +0.0437 |
| w035 | 0.9105 | 0.9104 | 0.9391 | +0.0287 |
| w036 | 0.7973 | 0.7963 | 0.8304 | +0.0341 |

The median gain is +0.0343. Yet the map agrees with the winner's a little less, by half the margin. Across
finding 121's four windings, the windings least on the sheet read worst (finding 134's registration: 0.61 in r per
unit of share). That slope would have predicted about +0.02 here, and the change was −0.0099. A gain within a
winding from the denser snap does not behave like the difference between windings. At this place, a gain of this
size in the share within 2 voxels did not predict a better read.

**Each arm on the common cells and on its own:**

| | `f124` | `rerun` | `dense2` |
|---|---|---|---|
| r, own cells | 0.8247 (457,405 cells) | 0.8205 (457,557) | 0.8094 (461,277) |
| r with the background in, common cells | 0.7404 | 0.7366 | 0.7338 |
| reversed planes (control), common cells | −0.0529 | −0.056 | −0.0645 |
| slid (control), largest, common cells | 0.1125 | 0.1107 | 0.1067 |
| ink overlap, common cells | 0.7601 | 0.7588 | 0.7593 |
| transfer distance, median and 95th percentile (voxels) | 1.91, 3.3 | 1.92, 3.29 | 1.9, 3.29 |

The dense arm reaches 3,720 more cells of its own than the rerun does, and reads lower on its own cells too
(−0.0111).

**The route's noise.** The rerun's snapped windings are byte-identical to finding 121's on all four. Its final
(flattened) windings are not: the flatten runs on the GPU. That difference reads as −0.0037 in r.

## What it cost

39 min 17 s in all (registered: about an hour). GPU memory peaked at 14,936 MiB in use by all processes (registered:
about 15 GB).

| step | `rerun` | `dense2` |
|---|---|---|
| snap | 13 s | 15 s |
| flatten, per winding | 49 to 66 s | 116 s |
| render, four windings | 226 s | 190 s |
| Studio, four windings in both orders | 606 s | 593 s |

Here the denser grid's flatten took about twice as long, as in finding 130 (134 to 254 s a winding on PHerc. 0826).
That is not the grid's density alone. Finding 134 flattened the same densified windings, snapped three times, in 39
to 43 s each. What sets the flatten's time is not known.

## What this does to the campaign

The registered consequence of `DENSE_READS_SAME`: **the band reads keep the denser snap.** Finding 129 (PHerc.
0813) is not amended. Finding 133 (PHerc. 0800) reads this record when it starts and keeps `FL_DENSIFY=2`. Finding
126 (PHerc. 0358) was read with it.

That keeps a step whose only measured benefit is geometric: it does not read better at the one known place, and
the change points slightly the other way.

Finding 134 tests three snap passes of these same densified windings. Its registered consequence adopts three
passes if they read the same and sit more on the sheet. This result weakens the premise of that tie-break, but the
rule was fixed before it and stands.

## What this does not show

1. **Anything about legibility to an eye.** "Reads" means Studio's map agrees with the winner's Studio map.
2. **That the denser snap is worse.** The change is half the margin, on four windings at one place of one crushed
   scroll.
3. **What the denser snap does where windings are further off the sheet.** These were 77% to 91% on it already.
   Finding 130's six windings of PHerc. 0826 were 51% to 78% on it before the denser snap.
