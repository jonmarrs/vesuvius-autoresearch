# Pre-registration: how does villa's neural fiber tracer score against hand-traced fibers, on scrolls it never saw?

**Written 2026-10-16, before the tracer has run on any ScrollGT cube.** Environment
`repro/fibers/setup_neural_tracer_env.sh`; chain `repro/fibers/run_neural_tracer_chain.sh`; analysis
`scripts/neural_tracer_analysis.py`; presence `scripts/make_tracer_presence.py`; rasteriser `scripts/afv_to_labels.py`
(finding 85's, unchanged). All on branch `neural-tracer-entrant`, with tests. The user approved the study on
2026-10-16 ("after the C flow"); the GPU runs follow the loop's v3 noise probe.

## The question

villa #2045 (@bruniss, merged 2026-10-12) adds a neural fiber tracer, `vesuvius.neural_tracing.tracers.fibers`. Its
volume mode traces every fiber in a box from presence seeds and writes an Automated Fiber Volume (`.afv`) for VC3D
and the spiral fit. The default checkpoint, `scrollprize/fiber_single_small`, has no model card and no published
accuracy.

We read its training record from the checkpoint itself (`last.pt`, loaded with an allowlist, never unpickled
freely):
* regression model, step 50,000, 3.2M samples;
* data: 563 Paris 4 (Scroll 1) fibers from the spiral dataset's working set, and four automated fiber volumes:
  PHerc0175A, PHerc1447, PHerc0125 and Paris 4 central;
* no Scroll 3 and no Scroll 5.

So ScrollGT's 8 Scroll-3 cubes and its 2 held-out Scroll-5 cubes are scrolls it never saw. That is the first measurement of
its fibers against human tracing there. It sits beside the same measurement for #1934's generator (finding 85),
connected components and our tracer.

## Reachability — checked before designing the measurement

Checked by reading villa at `ccb431818` and by measurement, before any run:
* **Local CT.** `crop_sampling/volume.py open_ct_array` reads a local store as `<store>/<level>/.zarray` with its
  numcodecs compressor. Finding 85's cube arrays (zarr v2, blosc lz4, uint8) become level 0 of a group by symlink.
* **Grid.** The tracer reads CT through `--ct-grid-scale` and traces on a grid `--grid-scale` base voxels apart.
  Its Paris 4 source reads 9.6 µm CT on a 2-voxel grid; its automated sources read 8.64 and 9.362 µm CT, also
  on a 2-voxel grid. Here: `--ct-level 0 --ct-grid-scale 1 --grid-scale 2` on 7.91 µm CT, so the trace grid is
  15.8 µm, and a 256³ cube is a 128³ box.
* **Presence.** `--presence` must be a uint8 array on the trace grid, in a directory named by an integer. The
  tracer looks beside it for the next level only to weigh tiles.
* **Outside the scan.** A trace stops after 2 decisions with its head on CT value 0, and written fibers lose points on
  CT 0 (see the amendment: 13 of the 21 cubes hold some zero voxels).
* **Output.** `volume_afv.py` writes the run's fibers in level-0 voxels of the run's CT. For a CT that is not an
  open-data store, it takes its frame metadata from a template `.afv` of the same scan. Finding 85's per-cube `.afv`
  files are that template. villa's writer stores little-endian float64 xyz blocks that share boundary points, and
  writes `complete` last. That is the format `afv_to_labels.read_afv` reads.

**Not yet checked: that it runs.** The environment does not exist yet (Python 3.14, torch ≥ 2.12). The first GPU
step is a smoke run on a synthetic volume, not on a cube. If it fails, or needs a change to anything registered
here, this file is amended and committed before any cube runs.

## Amendment 1 — 2026-10-16, before any cube ran (after `8a0d033f`)

* **Correction: zero voxels exist.** The registration said all 21 cubes have no zero voxel. The 6-cube check behind
  it printed a fraction rounded to four decimals. Counted on all 21 before any run, 13 cubes hold some:
  * Scroll 1: 2–196 per cube.
  * Scroll 3: 191–18,579 per cube. The most is 0.014% of `s3_00994_00494_01994_512`.
  * Scroll 5: none.

  So the outside-the-scan rule can stop a trace inside these cubes. The CTs stay as registered: they are the data
  every other entrant was scored on. The analysis now tallies each cube's stop reasons from the `.afv` annotations
  (descriptive), so how often the rule fired is reported, not guessed.
* **Environment.** villa's lockfile puts `volume-cartographer`, a C++/CMake build, in the `models` extra. The tracer
  imports its bindings only lazily: the `vcz1` codec and the `VESUVIUS_CT_READER=vc3d` reader. These cubes are
  blosc-compressed and read with the default reader. So the sync installs every locked package except that one
  (`--no-install-package volume-cartographer`). An import of it would fail loudly.
* **Built and checked:**
  * torch 2.12.1+cu130;
  * `last.pt` and `heading_model.pt` match the registered sha256;
  * the tracer's modules import;
  * #1934's template `.afv` files carry the cube frame (level 0, 7.91 µm, base shape = the cube) and the fibers
    schema with `annotation`.

## The floor

None is inherited. Run-to-run variation is **measured, descriptively**:
* two cubes (`s3_00994_00494_01994_512`, `s1_00497_01497_03997_256`) are traced twice, identically;
* the absolute differences in ERL, merge-penalized ERL, coverage, merges and instance count are reported.

The registered rules do not use it. It is printed beside every comparison whose margin is smaller.

## Entrant, fixed now

* **Code:** villa `ccb431818fa68059138f2c964ae299fc474ff116` (this repository's pin from PR #95). It runs in
  `spiral_out/neural_tracer/venv`, synced with `uv sync --frozen --extra models` from villa's own `vesuvius/uv.lock`.
* **Checkpoint:** `scrollprize/fiber_single_small` at revision `451182558cb3270cfc2ddf967acbd4f36b9b816b`:
  * `last.pt`, sha256 `3268a0ac1807debdeaded05fa7bc90b82d3ca8102125247e5cba688a10a4811f`;
  * `heading_model.pt`, sha256 `c10e21e62d05228bdadeda65334d5c9eede91d942b80ca9d318616eda7cbf35f`.

  Runs are offline (`HF_HUB_OFFLINE=1`) after one download.
* **Command:** `python -m vesuvius.neural_tracing.tracers.fibers.tracing.volume`, every default except:
  * the four flags that point it at a 7.91 µm cube: `--ct`, `--ct-level 0`, `--ct-grid-scale 1`, `--grid-scale 2`;
  * `--presence`;
  * `--box` (the whole cube);
  * `--base-um 7.91` (reported lengths only);
  * `--afv-template`.

  The defaults are the ones `neural_tracer_analysis.SETTINGS` lists: threshold 128, plane spacing 64, minimum
  length 48 grid points, dedupe 2, confidence 0.5, bf16, sampling seed 0, and the rest.
* **Presence:** villa's own runs seed from lasagna's fiber presence, which we do not have for these cubes. Here
  the presence is ScrollGT's reference mask, `scrollprize/fiber_hz_vt`: each cube's stored probability, averaged
  over 2×2×2 blocks and scaled to 0–255. Every ScrollGT entrant in this comparison builds on the same mask, so the
  comparison isolates the tracing step.
* **Identity check:** the analysis refuses any run whose `run.json` differs from the registered checkpoint sha256,
  settings, box, CT or presence.

## Scoring

* `afv_to_labels.py` rasterises each `.afv` as thin centrelines, dropping points outside the cube.
* ScrollGT `score_tracing`, **fiber scoring version 3** (v0.7.0: run lengths normalised by ground-truth length),
  tolerance 2.0. Ground truth is ScrollGT 0.7.0's for all 21 cubes.
* **Comparators**, all under version 3:
  * connected components and our tracer, from ScrollGT's published rows;
  * #1934's generator, re-scored from finding 85's `.afv` files after their identity check.
* **Descriptive:** every row again at tolerance 4.0, for this tracer and the generator. The tracer's own label
  tolerance, 2 grid voxels, is 4 CT voxels here.

## Predictions, fixed now

On the 8 Scroll-3 cubes (unseen by the tracer, the generator and the mask):

1. **It follows fibers further than #1934's generator.** Merge-penalized ERL above the generator's on at least 75%
   of the cubes with both rows. Confidence moderate. Both write thin centrelines. The generator cuts chains at every
   skeleton junction and kept 22–38% coverage. This tracer follows each fiber through the CT from a seed and was
   trained against switching.
2. **It follows fibers further than our tracer.** Merge-penalized ERL above our tracer's on at least 60% of the
   cubes. Confidence low. Our tracer scores 17–30 there with 50–64% coverage.
3. **It finds less of the fiber than our tracer.** Coverage below our tracer's on at least 75% of the cubes.
   Confidence moderate. Three reasons:
   * a thin line must fall within 2 voxels of the hand-traced centreline;
   * pieces under 48 grid points (96 voxels) are not written;
   * seeds come from planes 64 grid voxels apart plus a fill-in pass.

On the 2 held-out Scroll-5 cubes:

4. **Both cubes' coverage falls below its own Scroll-3 median.** Confidence moderate. Its presence, fiber_hz_vt,
   misses 19.6% and 25.2% of their hand-traced fiber outright (finding 84), against 5.7–10.7% on Scroll 3.

**Descriptive, no prediction:**
* the 11 cubes where fiber_hz_vt trained (5 of them from Scroll 1, the tracer's own training scroll, scanned
  differently);
* merges, splits, instance counts and precision;
* the tolerance-4 rows, the repeat, runtime and GPU memory.

## Decision rule

| outcome | conclusion |
|---|---|
| the synthetic smoke run fails | no cube runs; this registration is amended first |
| a cube's run fails or writes no `.afv` | reported as failed, not scored as zero |
| fewer than 6 Scroll-3 rows (or fewer than 6 with a generator row, for P1) | that prediction unevaluated; status INCOMPLETE |
| a missing held-out Scroll-5 row | P4 unevaluated; INCOMPLETE |
| any `run.json` differs from the registration | IDENTITY_FAILED, no verdict |
| ScrollGT's scoring version is not 3 | refused |
| otherwise | each prediction held or failed as registered, every row beside its comparators |
| coverage at tolerance 2 is below 0.05 on most cubes, but not at tolerance 4 | the verdict stands as registered, and the report says the tolerance, not the following, limits the score |

Whatever the outcome, nothing is posted to villa or added to ScrollGT without a separate decision by the user. Anything
posted to villa also falls under villa's posting limits.

## What the result cannot do

* **It does not rank the tracer in general.** It covers one checkpoint and the volume mode's defaults. VC3D's seed
  mode (Line Annotation) is not tested.
* **The presence is a substitute.** The tracer's own runs seed from lasagna presence, and a different presence could
  find more or fewer seeds.
* **Scale.** 7.91 µm is finer than its 8.64–9.6 µm sources.
* **Edges.** 256³ cubes are 128 grid voxels across. The tracer's crop is 144 samples deep and 104 wide at 0.5
  grid-voxel spacing (its checkpoint's `crop`), so near the edges it sees the reader's zero fill. The 512³ Scroll-3
  cubes are less affected.
* **Scroll 1 is not held out.** It is the tracer's training scroll. The training fibers sit in another scan's frame,
  and their overlap with these cubes is unchecked.
* **Thin against thick.** A thin centreline and a mask-thick labelling differ in precision by construction, so
  precision is not compared with connected components or our tracer.

## Cost

* **Environment:** CPU, a few GB of downloads, once.
* **GPU:** a synthetic smoke run, then 21 cubes plus 2 repeats. The Paris 4 run held about 23 GB with
  `--gpu-chunks 1024`; at the default 2048 slots the chunk cache alone is 4 GB.
* **Scheduling:** time per cube is unknown until the smoke run. If the loop is running, sharing the GPU needs the
  user's OK; otherwise the chain waits for a pause.
* **Scoring:** CPU, minutes.
