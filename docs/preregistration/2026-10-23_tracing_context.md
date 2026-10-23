# Pre-registration: is the neural tracer's tolerance-4 deficit on the 256³ in-sample cubes the tracing context?

**Status: REGISTERED 2026-10-23, before any octant has been traced.** The run needs the GPU with the autoresearch loop
paused, so it waits for the owner's go-ahead. Scoring is CPU only, at nice 19 with the loop running.

## The question

At a 4-voxel tolerance, villa's neural fiber tracer leads our tracer on all three in-sample 512³ cubes, and trails it
on all eight in-sample 256³ ones (finding 94, `reports/tolerance4_rescore.md`). On those eight its merge-penalized
ERL is a median 0.65 of ours (0.43–0.81). Finding 95 (`reports/octant_crop_rescore.md`) cut the 512³ cubes into their
24 octants of 256³ and scored both tracers' whole-cube labellings on each. The lead held on 19 of 24, a median 1.08×.
So the smaller scoring window is not the cause. Nor is the scroll alone, since the three Scroll-5 256³ cubes trail too.

**One difference remains between an octant and a real 256³ cube: on the real cube, everything ran on that cube
alone.** That covers the mask model, our tracer, and the neural tracer's presence, which is built from the mask
model's cached probability (`repro/fibers/run_neural_tracer_chain.sh`). In finding 95 everything saw the whole 512³
cube. This test runs the same steps on each octant as a cube in its own right. It asks whether running small, as a
whole, is the cause. Splitting the mask model from the tracers is a follow-up, only if this reproduces the deficit.

## Design, fixed now

* **Octants as cubes.** Each octant of `s5_06494_01994_03994_512`, `s5_06994_00994_04994_512` and
  `s5_07994_01994_05494_512` becomes a stand-in cube (`scripts/tracing_context.py prepare`). It is named by its
  absolute origin (`s5_<z>_<y>_<x>_256`), so bench_cli's loader places it, and its files are:
  * `<stem>_image.tif`: the octant of the parent's `_image.tif`;
  * `<stem>.nml`: the parent's annotation, which the loader localizes to the octant;
  * no probability. `bench_cli` refuses a cache that is not attested for its image (`inference_identity` hashes the
    image), so a cropped 512³ probability cannot honestly stand in. `bench_cli trace` runs the mask model on the
    octant, as it did for every real cube.
  * The neural tracer's CT is written from the same crop as a zarr array, after finding 85's array for the parent is
    checked equal to the parent's TIFF.
* **Our tracer:** `bench_cli trace --device cuda` at its published defaults (finding 80's settings), as
  `repro/fibers/run_tracer_rescore.sh` ran the real 256³ cubes.
* **villa's neural tracer:** finding 91's command, with checkpoint `scrollprize/fiber_single_small` pinned at 4511825
  and box `0,0,0,128,128,128`. The presence is built by `scripts/make_tracer_presence.py` from the probability bench_cli
  just cached. `--afv-template` is the parent's #1934 `.afv`, which supplies only frame metadata. The fibers are
  written in octant-local voxels and rasterised at origin 0, as finding 91 did.
* **What stays the same, by construction:**
  * **Seed planes.** villa's tracer seeds on planes at global multiples of `--plane-spacing` (64 trace-grid voxels).
    An octant's origin is 0 or 128 in the trace grid, so its planes are its parent's.
  * **Tiling.** Each box is one tile in both runs, since the default tile is 256 trace-grid voxels.
  * **Inputs.** Both tracers see the same voxels.
* **What changes is the context.** Near the faces:
  * the presence and probability are padded, or computed without their neighbours;
  * traces stop at the box;
  * our tracer normalizes its seed response, and picks its seed percentile, over the octant alone.
* **Scoring:** as finding 95, against finding 95's crop of each parent's ScrollGT ground truth, at tolerances 4 and 2
  (ScrollGT `score_tracing`, scoring version 3). Each row's ground truth (`n_gt_fibers`, `gt_length`) must equal
  finding 95's for that octant, or the status is IDENTITY_FAILED.
* **Smoke and identity, first** (`tracing_context.py smoke`). The real in-sample cube `s5_07997_02997_05497_256` is
  copied without its probability cache and run through the same path. All three must hold before any octant runs:
  * the recomputed probability equals the published cache exactly;
  * our tracer's labelling equals finding 94's;
  * the neural tracer's `.afv` equals finding 91's point for point. Finding 91's runs are deterministic, so its
    repeatability floor is zero.

  Otherwise the chain stops, and this registration is amended before anything else runs.
* `repro/fibers/run_tracing_context_chain.sh` runs it all. It freezes every script it runs and refuses to start while
  the loop or another GPU job runs. `scripts/tracing_context.py score` writes `reports/tracing_context.json`.

## Predictions, fixed now

1. **P1: the lead survives running small.** Run on the octants as cubes, the neural tracer's merge-penalized ERL at
   tolerance 4 is above our tracer's on at least two thirds of the octants scored (16 of 24). Confidence moderate.
   * **For it:** to explain the deficit, running small must take the octants from finding 95's median 1.08 to about
     the real cubes' 0.65, a swing of about 40%. The neural tracer's box stops are rare: finding 91's 21 runs record
     92 `bounds` stops against 29,146 others.
   * **Against it:**
     * 13 of finding 95's 19 leads are under 1.15×, so a small loss flips them.
     * 7/8 of an octant lies within 64 voxels of a face, where the mask model's context changes.
2. **P2: running small changes each tracer's score little.** For each tracer, the median over the octants of its
   tolerance-4 merge-penalized ERL, run on the octant over finding 95's crop of its whole-cube run, lies in
   0.90–1.10. Confidence low.

**Descriptive, no prediction:**
* the same counts at tolerance 2;
* each tracer's coverage, merges and instance counts;
* the neural tracer's stop reasons;
* the runtime of each step.

## Decision rule

With n the octants scored for both tracers:

| outcome | conclusion |
|---|---|
| the smoke fails any of its three checks | no octant runs; amended first |
| a run fails or writes nothing | that octant is reported as failed, not scored |
| a row's ground truth differs from finding 95's | IDENTITY_FAILED, no verdict |
| n < 20 | INCOMPLETE |
| leads on ≥ 2n/3 (P1 holds) | "not the tracing context: run on the octants, the neural tracer keeps its tolerance-4 lead, so what remains for the 256³ in-sample deficit is those cubes' own content and annotation" |
| leads on ≤ n/3 | "the tracing context reproduces it: run on the octants as cubes, the neural tracer trails our tracer at tolerance 4 as on the real 256³ cubes" |
| between | "inconclusive: running small weakens the lead without reversing it" |

A tie is not a lead. With n = 24 the thresholds are 16 and 8, as in finding 95. Any change to ScrollGT is a separate
decision by the owner.

## What the result cannot do

* **Three cubes, one scroll.** The octants are Scroll 5. The Scroll-1 256³ cubes are not tested.
* **It does not split the mask model from the tracers.** If the deficit reproduces, the next test re-runs one with
  the other's 512³ context.
* **The octants of one cube are not independent.**
* **"Content and annotation" is what remains, not what is shown.** A lead that survives rules out running small. It
  does not identify what about the 256³ cubes is different.

## Cost

* **GPU, loop paused:** our tracer about 3 minutes per 256³ cube when its probability is cached, plus the mask model on
  each octant (timed by the smoke), and the neural tracer about 45 seconds. That is about 25 runs, expected within
  3 hours and far inside the one GPU day that `docs/PRIZE_PLAN_2026-10_FINAL_WEEK.md` allows.
* **CPU:** scoring, about an hour at nice 19 with the loop running.
