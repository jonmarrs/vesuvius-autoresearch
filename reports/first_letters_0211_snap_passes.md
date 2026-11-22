A three-pass snap reads the same as one pass where PHerc. 211's prize was won, and puts more of every winding on the predicted sheet, so three passes are adopted (2026-11-21)

Finding 134. Finding 131's densified windings w033 to w036 of PHerc. 211 (band z 7650 to 9150) were snapped three
times, each pass snapping the one before (`run_snap.sh`, `FL_SNAP_PASSES=3`). They then went through finding 121's
route: flatten, orientation against the winner's surface, 66-layer render, Studio. The arm `dense2s3` was scored
beside finding 131's three arms on the cells all four reach, by finding 124's statistic. Registered before any
winding of PHerc. 211 was snapped more than once, and before finding 131 had run:
`docs/preregistration/2026-11-20_first_letters_0211_snap_passes.md` (commit `0bf4748a`). Record:
`reports/first_letters_0211_snap_passes.json`, from the run's `snap_passes.json` and gates. Scripts as run:
`repro/first_letters/pherc0211_control/` (`run_snap_passes.sh`, `snap_passes_read.py`) and
`repro/first_letters/eligible_band/run_snap.sh`.

**Verdict `SNAP3_READS_SAME`**, as predicted, by the registered table. The change, r(`dense2s3`) − r(`dense2`), is
+0.0029, inside the margin of 0.02. Every step exited 0, and the `f124` arm gave finding 124's r 0.8247 on its own
cells. The registered geometry gain is +0.0357, above 0. **So the registered consequence is `three_passes`**, as
predicted: finding 133 snaps three times.

## The registered numbers

On the 435,420 of the winner's 550,482 mask cells that all four arms reach (share 0.791):

| arm | r against the winner's map |
|---|---|
| `f124` (finding 124's windings and maps) | 0.8325 |
| `rerun` (finding 121's route again, finding 131) | 0.8289 |
| `dense2` (subdivided twice, snapped once, finding 131) | 0.8188 |
| `dense2s3` (subdivided twice, snapped three times) | 0.8217 |

| | value | rule |
|---|---|---|
| noise, r(`rerun`) − r(`f124`) | −0.0036 | |
| margin | 0.02 | the larger of 0.02 and twice the noise |
| change, r(`dense2s3`) − r(`dense2`) | +0.0029 | better at +0.02 or more, worse at −0.02 or less |
| geometry gain, the median over the windings of the share of final nodes within 2 voxels of the predicted sheet, `dense2s3` less `dense2` | +0.0357 | three passes if `SAME` and above 0 |

No render samples against the winner's normals (a `DOES_NOT_RUN` condition): the median normal cosines are −0.9961
to −0.9992. The common cells are fewer than finding 131's 442,015, because a fourth arm must reach them too. On them
the three arms finding 131 scored keep their order and stay within 0.0022 of their r there.

**Predictions.** (1) `SNAP3_READS_SAME`, moderate confidence: held. (2) The geometry gain is above 0, 0.02 to 0.06,
moderate-to-high confidence: held (+0.0357). The expected consequence, `three_passes`, followed.

## Described

**On the sheet:** share of final nodes within 2 voxels of the predicted sheet.

| winding | `rerun` | `dense2` | `dense2s3` | `dense2s3` − `dense2` |
|---|---|---|---|---|
| w033 | 0.9047 | 0.9392 | 0.9519 | +0.0127 |
| w034 | 0.7747 | 0.8184 | 0.877 | +0.0586 |
| w035 | 0.9104 | 0.9391 | 0.9519 | +0.0128 |
| w036 | 0.7963 | 0.8304 | 0.8903 | +0.0599 |

The two windings least on the sheet gained most. **Again more on the sheet did not read better.**
- **The registered slope missed.** The prediction leaned on a slope of 0.61 in r per unit of that share, fitted
  across finding 121's windings. It gives +0.022 for this gain, and the change was +0.0029.
- **The baseline still reads best.** Against the fit's own grid snapped once (`rerun`), the densified windings snapped
  three times read 0.0072 lower. They sit 0.0415 to 0.1023 more on the sheet.
- **Within noise.** All four arms lie within 0.0137 of each other.

As in finding 131, at this place the share within 2 voxels did not predict the read.

**Each arm on the common cells and on its own:**

| | `f124` | `rerun` | `dense2` | `dense2s3` |
|---|---|---|---|---|
| r, own cells | 0.8247 (457,405 cells) | 0.8205 (457,557) | 0.8094 (461,277) | 0.8135 (458,383) |
| r with the background in, common cells | 0.7415 | 0.7378 | 0.7353 | 0.7396 |
| reversed planes (control), common cells | −0.0536 | −0.0568 | −0.0655 | −0.0607 |
| slid (control), largest, common cells | 0.1112 | 0.1091 | 0.1051 | 0.1016 |
| ink overlap, common cells | 0.7612 | 0.7597 | 0.7604 | 0.7603 |
| transfer distance, median and 95th percentile (voxels) | 1.91, 3.27 | 1.91, 3.26 | 1.89, 3.21 | 1.87, 3.26 |

**The first of the three passes is finding 131's snap**, byte for byte, on all four windings.

## What it cost

17 min 5 s in all (registered: about 45 minutes). GPU memory peaked at 14,483 MiB in use by all processes
(registered: up to about 15 GB).

| step | wall time |
|---|---|
| snap, three passes, four windings | 46 s |
| flatten, per winding | 39 to 43 s |
| render, four windings | 190 s |
| Studio, four windings in both orders | 595 s |
| compare | 29 s |

The three passes cost 46 s against finding 131's 15 s for one. The flatten of these densified windings took 39 to
43 s a winding. In finding 131 the same windings, snapped once, took 116 s, and the fit's grid took 49 to 66 s. So
the grid's density does not by itself set the flatten's time; what does is not known.

## What this does to the campaign

The registered consequence, `three_passes`: **finding 133 (PHerc. 0800) snaps three times.** Its wrapper
(`run_after_controls.sh`) reads this record when it starts. With finding 131's `DENSE_READS_SAME` and finding 132's
`SKIP_ADOPTED`, it will run with `FL_DENSIFY=2`, `FL_SNAP_PASSES=3` and `STUDIO_SKIP_EMPTY=1`. Reads registered
before this one keep one pass. Finding 133 holds at its start until 170 GB of disk is free; what to free is the
owner's decision.

Findings 131 and 134 add the denser grid and the extra passes to the band reads on geometry alone. At the one place
with a known text, neither read better, and neither read worse beyond the noise. They are cheap. The subdivision took 23 s
on finding 126's band, and its one snap pass 911 s, so two more passes add about half an hour to a read of
more than 13 hours.

## What this does not show

1. **Anything about legibility to an eye.** "Reads" means Studio's map agrees with the winner's Studio map.
2. **That three passes help or hurt the read.** A `SAME` verdict leaves an effect under about 0.02 in r unknown.
3. **Another place.** It is four windings at one place of one crushed scroll, already 77% to 91% on the sheet
   before any of this.
