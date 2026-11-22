The PHerc. 343 recipe's mesh step runs on this machine: windings fitted here lie on the published sheets (76% and 81% of nodes within 2 voxels) and carry the published ink (r = 0.86 over the letter boxes) (2026-11-12)

Finding 110. The [kill test](first_letters_343_reproduction.md) rebuilt the published PHerc. 343 image from the
published windings. This run made the windings here: distance field, 30,000-step spiral fit, snap and flatten, on
the same band (z 9500 to 11000), then rendered them and ran the four ink models at depth +1. Host: 4 cores, 31 GB
of RAM, one RTX 4090. Registered before any fitted winding was compared with the published ones:
`docs/preregistration/2026-11-10_first_letters_343_mesh_step.md` (commit `ff5ab892`). Record:
`reports/first_letters_343_mesh_step.json`. Scripts as run: `repro/first_letters/pherc343/mesh_step/`.

**Verdict `REPRODUCED`**, by the registered decision table: every step exited 0, P1 holds for both windings and P3
holds. The registered `recipe` arm ran; the reduced-fit rule was not needed. PHerc. 343 is already awarded, so this
is a positive control and not a discovery.

## P1: the fitted windings are on the published sheets

Distance along the normal from each published winding to the final (snapped and flattened) winding chosen for it.
The threshold was at least 50% of published nodes within 2 voxels and a median of at most 3.

| published | chosen here | within 2 voxels | median (voxels) | 95th percentile | covered |
|---|---|---|---|---|---|
| w047 | fitted w047 | 75.6% | 0.90 | 5.02 | 99.7% |
| w048 | fitted w048 | 80.5% | 0.73 | 4.52 | 99.7% |

**Control.** Each published winding against the other final winding, which is the neighbouring sheet: 13.2% and
12.8% within 2 voxels, medians 12.80 and 12.99. That matches the floor measured between the two published windings
before the run (13.1%, 12.82).

The snap and flatten do most of the placing. The raw fitted windings, before the snap, scored 33.1% and 47.3%
within 2 voxels with medians 3.23 and 2.16. Neither would have passed P1.

**P2.** The two chosen windings are consecutive. The fit numbered them 047 and 048, the published indices; the
registration did not predict that.

## P3: the same ink

Our depth +1 maps were carried into the published segment's frame and compared with the kill test's maps of the
published segment, as the mean of the four models' z-scores on the reading side with broad background removed.
The threshold was r of at least 0.50 over the letter boxes and at least twice each control.

| | r |
|---|---|
| ours against published, 18 letter boxes (121,650 of 123,154 cells compared) | **0.862** |
| control: our map slid 64 px, largest of four directions | 0.173 |
| control: the published blind side | 0.167 |
| ours against published, all cells, background removed | 0.770 |

The letter-box r is 5.0 times the larger control. 98.8% of letter-box cells received ink from our windings within
4 voxels (the evaluability condition was half), and 93.6% of all published cells did. The transfer distance was
1.62 voxels at the median and 3.06 at the 95th percentile.

Per model over the letter boxes: dense_native 0.879, Hecate 0.834, ink_9um seed 42 0.590, seed 43 0.600. The two
ink_9um models are the ones the kill test found non-deterministic on this card; whether that explains their lower
agreement was not tested.

## What it cost

| step | wall time | host memory (peak resident) | GPU peak |
|---|---|---|---|
| distance field (`make_surf_sdt.py`, run before registration) | 53 s | not recorded | none |
| spiral fit, 30,000 steps | 3 h 08 min 40 s | 10.8 GB; 17.1 GB for the unit with page cache | 12.7 GB |
| selection of the two windings among 120 | 3 min 45 s | 0.2 GB | none |
| snap (475 level-0 surface chunks, 0.2 GB) | 41 s | 0.2 GB | none |
| flatten, per winding | 72 s, 70 s | 1.6 GB | 0.7 GB |
| render, 66 layers, per winding | 86 s, 67 s | not recorded for the container | none |
| ink, four models at depth +1, per winding | 5 min 38 s, 6 min 44 s | 3.8 GB | 3.4 GB |
| comparison | 11 s | 0.5 GB | none |

From inputs on disk to verdict is about 3 h 31 min, of which the fit is 3 h 09 min. The fit ran at about 2.7 steps
a second after about 6 minutes of preparation. Memory pressure for the user session stayed at or below 0.15%
throughout the fit (systemd-oomd acts at 50%). The run directory is 53 GB, most of it the band's inputs.

The training loop was stopped for the whole run. Nothing else used the GPU.

## Two failures before the fit trained, and their causes

Both are recorded in the registration; neither is an arm.

1. **Killed by systemd-oomd while the distance field loaded (2026-11-11).** Two things differed from the run that
   worked. villa `0fb38c45` rejected the published packed track store, because it identifies the track file by
   its modification time in nanoseconds and an HTTP download keeps whole seconds, so the fit unpickled the 9 GiB
   track file in Python. And it was the first fit on the band, which packs the distance field into a 5.9 GiB file
   before loading it. Three 20-step diagnostic fits separated the second: packing that file while another
   process held 11 GiB drove pressure to 34% and rising within 25 seconds; with the file already packed the same
   load peaked at 1.7%; packing on an idle host peaked at 1.6%. The unpickling path with the file already packed
   was not tested. `setup/fetch_tracks.sh` now restores the recorded modification time, and villa main validates
   the store by content digest (villa #2041).
2. **An import error** before the first step, on the first attempt.

The working rule for a new band or scroll: build the packed distance field on an idle host first, then fit.

## What this does not show

1. That the recipe finds text on an unread scroll, or works where the surface prediction is worse than PHerc. 343's.
2. How often the fit lands on the same sheets. This is one fit with villa's default seed; there is no interval on
   any number here.
3. That the published 31-depth image reproduces from our windings. The comparison is against the kill test's
   depth +1 maps.
4. That the choice of windings can be made blind. The published windings were chosen by their author after seeing
   ink, and ours were chosen by distance to his. On an unread scroll every winding of a band has to be rendered and
   read: 120 windings in this band, at about 8 minutes each for render and depth +1 ink, is about 16 hours.
5. Anything about another host or another villa commit. One scroll, one band, one pair of windings, one machine.

The fit's printed loss rose from 199 to 273 between steps 10,000 and 10,200 and then fell again. The cause was not
looked into.
