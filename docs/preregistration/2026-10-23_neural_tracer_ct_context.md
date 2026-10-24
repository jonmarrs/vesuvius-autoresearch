# Pre-registration: villa's neural tracer on the Scroll-5 256³ cubes with real CT around each cube

**Status: REGISTERED 2026-10-23, before any padded run.** The run needs the GPU with the autoresearch loop paused, and
about 1.5 GB of public download, so it waits for the owner's go-ahead.

**Amended 2026-10-23, also before any padded run** (Amendment 1, at the end): the five Scroll-1 256³ cubes are added,
and judged apart from these five by the same predictions. The amendment leaves the registered five, their predictions
and their decision rule unchanged. **Run 2026-10-23, 21:02–21:15 PDT, with the loop paused: finding 97,
`reports/neural_tracer_ct_context.md`. P1, P2 and P3 held on both sets.**

## The question

Finding 96 (`reports/neural_tracer_boundary.md`, exploratory) found that villa's neural tracer drops any seed whose
77-voxel CT window crosses the edge of the CT it is given. ScrollGT's protocol (finding 91) gave it each cube's CT
alone. In finding 91's runs the closest traced seed is 19.00 trace-grid voxels (38 CT) from a face on all 21 cubes, and
on the 256³ cubes it drops 54–70% of its seed dots as `no_heading`.

**Finding 96 measured the rule, not its cost.** This test gives the tracer what it would have on a scroll: real CT
around the cube. It changes nothing else, and asks how much it recovers.

## Why Scroll 5, and these five cubes

* **Only Scroll 5's raw scan is public as a zarr.**
  * Scroll 5's raw uint16 volume (PHerc 172, `20241024131838`, `volumes_zarr/`), converted as villa's fibers-dataset
    generator made the cubes (÷257, clipped, truncated), reproduces the cube `s5_07997_02997_05497_256` exactly: all
    16,777,216 voxels identical, checked before this registration.
  * Scroll 1's and Scroll 3's public zarrs are intensity-standardized. They share the geometry: for Scroll 1, the
    correlation with the cube is 0.979 at zero shift and lower at every one-voxel shift. But they do not reproduce
    the cubes' values.
* **The cubes:** the five Scroll-5 256³ cubes. Three are in sample (`s5_03997_01497_03997`, `s5_07997_02997_05497`,
  `s5_14997_01497_01497`) and two are held out (`s5_13497_01497_02497`, `s5_16997_03997_04497`).
  * Finding 96: they drop 0.571–0.696 of their seed dots, and the neural tracer covers 0.096–0.238 of their
    ground-truth length.
  * Within in-sample Scroll 5, the 256³ cubes' predicted over ground-truth length is 0.53–0.61, against 0.96–1.16 on
    the 512³ ones.

## Design, fixed now

* **CT:** each cube padded by 128 CT voxels on every side from the raw scan, converted as above
  (`scripts/neural_tracer_ct_context.py fetch`). The padded array's 256³ core must equal finding 85's array for the cube
  exactly, or the status is IDENTITY_FAILED.
* **Presence:** finding 91's own level for the cube, placed in the padded frame with zeros outside the cube (`presence`).
  The tracer already zero-padded it beyond the cube, so the presence it reads is unchanged. Its core must equal finding
  91's level exactly.
* **Box:** the cube, `64,64,64,192,192,192` in the padded trace grid. The margin, 128 CT or 64 trace-grid voxels, is a
  multiple of the 64-voxel seed-plane spacing. So the cube's seed planes stay at its own grid 0 and 64, where finding 91
  had them.
* **Everything else is finding 91's command:** checkpoint `scrollprize/fiber_single_small` at 4511825, settings,
  `--base-um 7.91`, and the parent `.afv` as the frame template. The runs are deterministic (finding 91).
* **What the manipulation is:** real CT within the reach of every seed window and network crop near the faces, as on a
  scroll. The seed rule and the crops near the faces are not separated.
* **Smoke, first:** finding 91's own command, re-run on `s5_07997_02997_05497_256`, must reproduce its `.afv` point for
  point. Otherwise no padded cube runs (SMOKE_FAILED).
* **Manipulation check:** on at least one cube, a traced seed lies closer than 19 trace-grid voxels to a face of the
  cube. Otherwise the status is MANIPULATION_FAILED.
* **Scoring:** the run's fibers shifted to the cube's frame and rasterised as finding 91 did, and scored with ScrollGT
  `score_tracing`, scoring version 3, at tolerances 2 and 4. They are compared with finding 91's rows (tolerance 2),
  finding 94's (tolerance 4), and our tracer's published rows. `score` writes `reports/neural_tracer_ct_context.json`.
* `repro/fibers/run_neural_tracer_ct_context_chain.sh` runs the smoke and the five cubes. It freezes every script it
  runs, and refuses while the loop or another GPU job runs.

## Predictions, fixed now

1. **P1: it drops far fewer seeds.** On every one of the five cubes, the share of seed dots dropped as `no_heading` is
   below 0.40. Finding 91 had 0.571–0.696 here, and 0.256–0.357 on the 512³ cubes. Confidence high: it follows from
   the rule.
2. **P2: it covers more.** Its coverage at tolerance 2 rises on every cube, by a median factor of at least 1.3 over
   finding 91's. Confidence moderate.
3. **P3: on the three in-sample cubes its output reaches the 512³ level.** Predicted over ground-truth length is at
   least 0.83, the lowest 512³ value in finding 96. Confidence low.

**Descriptive, no prediction:**
* merge-penalized ERL at tolerances 2 and 4 against our tracer, and whether it now leads on any cube;
* seed and stop counts;
* the closest seed to a face.

## Decision rule

| outcome | conclusion |
|---|---|
| the smoke does not reproduce finding 91 | SMOKE_FAILED; no padded cube runs |
| a padded CT's or presence's core differs | IDENTITY_FAILED |
| no seed closer than 19 grid voxels to a face | MANIPULATION_FAILED |
| a run fails or writes nothing | INCOMPLETE |
| P1 and P2 hold | "the cube-only protocol held the neural tracer back on these cubes: with real CT around the cube it drops fewer seeds and covers more" |
| P1 holds, P2 does not | "the rule binds, but coverage did not rise as predicted: the gap has another cause too" |
| P1 fails | "with CT around the cube it still drops as many seeds: the window rule is not the main reason" |

Changing ScrollGT's protocol or rows is a separate decision by the owner.

## What the result cannot do

* **Scroll 5 only.** The Scroll-1 cubes, where ScrollGT also shows it trailing, are not tested.
* **The presence is unchanged.** The mask model is not re-run with context, so what the presence loses at the faces
  stays lost.
* **Five cubes.**
* **It does not test the 512³ cubes,** which lose a smaller share.

## Relation to #206

#206 (registered earlier the same day) runs both tracers on finding 95's octants, each with its own CT. It would
therefore hit the same rule. If this test shows the rule is the main cost, #206 mostly re-measures it. Which to run is
the owner's call.

## Cost

* **Download:** about 1.5 GB of public chunks. Each cube's padded region is 512³ uint16, about 125 compressed chunks.
* **GPU, loop paused:** the smoke and five runs, each comparable to finding 91's 256³ runs (46–49 s), so a few
  minutes.
* **CPU:** scoring, minutes.

## Amendment 1: the five Scroll-1 256³ cubes

**Written 2026-10-23, before any padded run.** The Scroll-5 download had begun, and its first cube's padded core had
matched finding 85's array. No tracing had run.

**Why.** ScrollGT shows the neural tracer trailing on these five cubes too. Finding 96 found the same signature on them
as on Scroll 5's 256³ cubes:
* 0.542–0.607 of seed dots dropped as `no_heading`;
* coverage 0.212–0.268;
* predicted over ground-truth length 0.551–0.776.

**Source.** Scroll 1's raw 7.91 µm scan (PHercParis4, `20230205180739`) is public as one uncompressed 16-bit TIFF per
slice. `scripts/raw_tiff_region.py` reads any region of it by HTTP byte ranges, and checks each slice's header first.
Converted as above, a 4 × 64 × 64 corner of `s1_00497_01497_03997`, `s1_00997_02497_02997` and `s1_10997_02997_02997`
equals the cube exactly. That was checked before this amendment. As for Scroll 5, `fetch` requires the whole 256³ core
to match finding 85's array.

**The cubes:** `s1_00497_01497_03997`, `s1_00497_02497_02997`, `s1_00997_02497_02997`, `s1_08997_02997_02497` and
`s1_10997_02997_02997`.
* All are 256³.
* All are in the mask's sample.
* Padded by 128, each lies inside the scan (14,376 × 7,888 × 8,096).

**Design:** as for the registered five, covering the margin, box, presence, command, smoke, identity checks and
scoring. The chain runs the registered five first.

**Predictions, the same three, judged on these five alone:**

1. **P1:** on every one, the share of seed dots dropped as `no_heading` is below 0.40. Finding 91 had 0.542–0.607.
   Confidence high.
2. **P2:** coverage at tolerance 2 rises on every cube, by a median factor of at least 1.3 over finding 91's
   (0.212–0.268). Confidence moderate.
3. **P3:** predicted over ground-truth length is at least 0.83 on all five, since all are in sample. Finding 91 had
   0.551–0.776. Confidence low.

**Decision rule:** the registered table, applied to these five. It is recorded as `status_scroll1` and `scroll1` in
`reports/neural_tracer_ct_context.json`.
* The identity checks and the manipulation check are per set. The smoke is shared.
* An identity failure or a missing run in one set leaves the other's status unchanged.
* `status` and the registered verdict are computed on the five Scroll-5 cubes alone, as before.

**What this changes below "What the result cannot do":** the Scroll-1 256³ cubes are now tested. Scroll 3 (all 512³)
and the 512³ cubes generally are still not.

**Cost:**
* about 1.3 GB more download, since each padded region is 512 slices of 512 row windows of 1 KB;
* five more GPU runs of about a minute each.
