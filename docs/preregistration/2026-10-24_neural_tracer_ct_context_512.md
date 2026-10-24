# Pre-registration: villa's neural tracer on the eleven 512³ cubes with real CT around each cube

**Status: REGISTERED 2026-10-24, before any 512³ padded CT was downloaded or traced.** The owner approved the download
and the GPU time on 2026-10-24. The run pauses the autoresearch loop.

## The question

Finding 97 (`reports/neural_tracer_ct_context.md`) gave villa's neural tracer 128 voxels of real CT around each of the
ten 256³ cubes. Its share of seed dots dropped as `no_heading` fell from 0.542–0.696 to 0.002–0.353, and its coverage
rose 1.76–2.78× on every cube. **The 512³ cubes lose less to the rule, and this test measures how much they recover.**
A seed's 77-voxel window fits in 0.618 of a 512³ cube, against 0.348 of a 256³ one (finding 96,
`reports/neural_tracer_boundary.md`). There it dropped 0.256–0.357 of its seed dots.

With this, all 21 of ScrollGT's neural-tracer rows can be stated with the scan around the cube. Any change to ScrollGT
is a separate decision by the owner.

**A second question rides along.** On finding 97's two held-out cubes, 0.266 and 0.353 of seed dots were still dropped
with CT around them, against at most 0.010 on the eight in-sample ones. All eight Scroll-3 cubes are held out.

## The cubes

All eleven 512³ cubes:
* **In sample:** the three Scroll-5 cubes, `s5_06494_01994_03994`, `s5_06994_00994_04994` and `s5_07994_01994_05494`.
* **Held out:** the eight Scroll-3 cubes, `s3_00994_00494_01994`, `s3_00994_01994_00494`, `s3_00994_02494_01494`,
  `s3_01994_01494_00994`, `s3_01994_01994_01494`, `s3_02994_02494_01994`, `s3_03494_01494_00494` and
  `s3_04494_00994_01494`.

Padded by 128, each lies inside its scan.

## Design, fixed now

* **CT:** each cube padded by 128 CT voxels on every side from the raw scan it was cut from. It is converted as villa's
  fibers-dataset generator made the cubes (÷257, clipped, truncated), by `scripts/neural_tracer_ct_context_512.py
  fetch`.
  * Scroll 5 comes from its raw zarr, as in finding 97.
  * Scroll 3 comes from its raw slices (PHerc332, `20231117143551`), read by byte range with
    `scripts/raw_tiff_region.py`. A 4 × 64 × 64 corner of `s3_00994_00494_01994_512` read this way equals the cube
    exactly.
  * The padded array's 512³ core must equal finding 85's array exactly, or the status is IDENTITY_FAILED.
* **Presence:** finding 91's own level, placed in the padded frame (384³ at level 1) with zeros outside the cube. The
  tracer already read zeros beyond the cube, so the presence it reads is unchanged. Its core must equal finding 91's
  level exactly.
* **Box:** the cube, `64,64,64,320,320,320` in the padded trace grid.
  * The tracer lays its tiles from the box's corner, 256 trace-grid voxels each, so the box is one tile, as in finding
    91.
  * Seed planes lie at global multiples of 64 trace-grid voxels, and the margin is 64 of them. So the cube's planes stay
    where finding 91 had them.
* **Everything else is finding 91's command:** checkpoint `scrollprize/fiber_single_small` at 4511825, settings,
  `--base-um 7.91`, and the parent `.afv` as the frame template.
* **Smoke, first:** finding 91's own command, re-run on the 512³ cube `s5_06494_01994_03994_512`, must reproduce its
  `.afv` point for point. Otherwise no padded cube runs (SMOKE_FAILED).
* **Manipulation check:** on at least one cube, a traced seed lies closer than 19 trace-grid voxels to a face of the
  cube. Otherwise the status is MANIPULATION_FAILED.
* **Scoring:** as finding 97. The run's fibers are shifted to the cube's frame and rasterised as finding 91 did. They are
  scored with ScrollGT `score_tracing`, scoring version 3, at tolerances 2 and 4. They are compared with finding 91's
  rows (tolerance 2), finding 94's (tolerance 4), and our tracer's published rows. `score` writes
  `reports/neural_tracer_ct_context_512.json`.
* `repro/fibers/run_neural_tracer_ct_context_512_chain.sh` runs the smoke and the eleven cubes, the three Scroll-5
  cubes first. It freezes every script it runs, and refuses while the loop or another GPU job runs.

## Predictions, fixed now

The two sets, the three Scroll-5 cubes and the eight Scroll-3 ones, are judged apart, by the same predictions.

1. **P1: it drops fewer seeds.** On every cube, the share of seed dots dropped as `no_heading` is below finding 91's
   share for that cube. On the three in-sample cubes it is also below 0.05. Confidence high: it follows from the rule,
   and finding 97's eight in-sample cubes came to at most 0.010.
2. **P2: it covers more, by less than on the 256³ cubes.** Coverage at tolerance 2 rises on every cube. The median
   factor over finding 91's coverage is at least 1.15 in each set. Confidence moderate.
   * Finding 97's median factor, 1.95, is about the 0.63th power of the 256³ cubes' gain in seedable volume, 1/0.348.
     The same power of the 512³ gain, 1/0.618, gives about 1.36.
   * Against: 0.854–0.945 of a 512³ cube's ground-truth length already lies on fibers a seed can reach (finding 96),
     so there is less to gain.
3. **P3: the ranking against our tracer does not change.** Our tracer's rows are the published ones, from the cube
   alone.
   * At tolerance 4 the neural tracer's merge-penalized ERL is above our tracer's on all eleven cubes. Finding 94 had
     it ahead on all eleven.
   * At tolerance 2 it is above ours on all eight Scroll-3 cubes and below ours on all three Scroll-5 ones. This is
     finding 91's ranking: on Scroll 5 at tolerance 2 it scores 0.43–0.48 of ours, so it would need 2.1–2.3× to
     overtake.

   Confidence moderate.
4. **P4: the held-out residual does not recur on Scroll 3.** The dropped share is below 0.10 on at least six of the
   eight Scroll-3 cubes. Confidence low.
   * For it: with the cube alone, Scroll 3 dropped 0.256–0.357, near Scroll 5's in-sample 512³ cubes (0.258–0.283). A
     residual of 0.3, as on finding 97's held-out cubes, would have pushed those shares higher.
   * Against: both cubes that were held out in finding 97 kept a residual.

**Descriptive, no prediction:**
* merge-penalized ERL at both tolerances, coverage and precision, and output over ground-truth length;
* seed, trace and stop counts;
* the closest seed to a face;
* the runtime of each run.

## Decision rule

| outcome | conclusion |
|---|---|
| the smoke does not reproduce finding 91 | SMOKE_FAILED; no padded cube runs |
| a padded CT's or presence's core differs | IDENTITY_FAILED for that set |
| no seed closer than 19 grid voxels to a face | MANIPULATION_FAILED for that set |
| a run fails or writes nothing | INCOMPLETE for that set |
| P1 and P2 hold | "on the 512³ cubes too the cube-only protocol held it back, by less: with real CT around the cube it drops fewer seeds and covers more" |
| P1 holds, P2 does not | "the rule binds, but on the 512³ cubes the scan around the cube adds little coverage" |
| P1 fails | "with CT around the cube it still drops as many seeds: the window rule is not the main reason on the 512³ cubes" |

P3 and P4 are reported for each set, true or false, apart from the reading. The identity checks, the manipulation
check and the readings are per set. The smoke is shared. An identity failure or a missing run in one set leaves the
other set's status unchanged.

## What the result cannot do

* **The presence is unchanged.** The mask model is not re-run with context, so what the presence loses at the faces
  stays lost.
* **Our tracer is not re-run.** Its rows stay those from the cube alone, so P3 compares a padded neural tracer with an
  unpadded tracer of ours.
* **Two scrolls and eleven cubes.** The Scroll-3 cubes are all held out, so on Scroll 3, scroll and split cannot be
  told apart.
* **P4 is a pointer, not an explanation.** A residual that recurs, or does not, would not say what causes it.

## Cost

* **Download:** about 11 GB of public data.
  * Scroll 5: each padded region is 768³ uint16 across 343 chunks of about 3.9 MB, so about 4 GB for three cubes.
  * Scroll 3: 768 slices of 768 row windows of 1.5 KB per cube, so about 7.2 GB for eight.
* **GPU, loop paused:** the smoke and eleven runs. Finding 91's 512³ runs took 2.4–4.0 minutes each, so about 40
  minutes in all.
* **CPU:** scoring, minutes.
