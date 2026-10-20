# Pre-registration: is finding 92's drop the tracer's seeding scale rather than its input pitch?

**Status: REGISTERED 2026-10-20, before any trace with rescaled seeding exists.** Proposed 2026-10-19 (#149) and
approved by the owner ("Run the proposed seeding test"). The registering commit adds the chain
(`repro/fibers/run_neural_tracer_seeding_chain.sh`) and the analysis (`scripts/neural_tracer_seeding_analysis.py`). The
predictions and decision rule below are unchanged from the proposal, and
`tests/test_neural_tracer_seeding_analysis.py` pins them by hash. Registration changed only this paragraph, the
title, the run directories' names and two sentences on how the arms are enforced. **Run 2026-10-20, 00:22–01:28 PDT:
finding 93, `reports/neural_tracer_seeding.md`. All three predictions failed: the seeding scale is not the cause.**

## The question

Finding 92 (`reports/neural_tracer_pitch.md`) resampled ScrollGT's 21 fiber cubes to 9.6 µm, the pitch villa's
neural fiber tracer trained on, and ran it with finding 91's settings. It scored lower on all 21 cubes (merge-penalized
ERL a median 0.63 of native) and lost its Scroll-3 lead over our tracer. ScrollGT 0.8.1 annotates the published row:
"Its Scroll-3 lead depends on running at the cubes' own 7.91 µm."

Two exploratory readings after that result point at seeding:
* **Where the fibers go** (`neural_tracer_pitch_funnel.json`): the 9.6 µm run started 0.56 times as many traces from
  0.49 times as many seed dots. Each trace was as long in grid voxels, and the length it wrote followed coverage per
  cube (r 0.96).
* **What sets the seed count** (`neural_tracer_seed_probe.json`, CPU only): villa's seeding smooths the presence with
  a sigma of 1 grid voxel, fixed in code, and a 9.6 µm grid voxel is 1.21 times longer. Set per micrometre, that
  sigma and the two spacing flags restore the 9.6 µm seeds to 0.90 of native. In reverse, they cut the native seeds
  to 0.56. The flags alone move the 9.6 µm seeds only from 0.49 to 0.52.

**So: given seeding per micrometre, does the drop go away?** If it does, the 0.8.1 note blames the pitch for what is
a seeding scale fixed in grid voxels. If it doesn't, the note stands.

## Reachability, checked (villa `ccb431818`)

* **The smoothing is reachable without editing villa.** `tracing/volume.py` calls `ndimage.gaussian_filter` once, in
  `tile_dots`, at sigma 1.0. `scripts/neural_tracer_seeding.py` substitutes that call on villa's module alone and
  refuses any other sigma, then runs villa's own `main()`.
* **Seeding runs in-process.** Tile workers are spawned and would import villa's module unpatched. So the launcher
  forces `--tile-workers 0`, which villa lists among the settings that only change speed.
* **The manipulation is measured before any trace.** The probe's counts are the seed dots each arm's run must record
  (`tiles.jsonl`), cube by cube.

## Arms, fixed now

r = 9.6 / 7.91 = 1.2137, as finding 92. The chain computes every scaled value from r, not from the rounded figures
here.

| setting | A: 9.6 µm, seeded as natively | B: native, seeded as at 9.6 µm |
|---|---|---|
| CT and presence | finding 92's resampled ones | finding 91's |
| `--box`, `--base-um` | as finding 92 | as finding 91 |
| `--plane-spacing` (64) | 64 / r = 52.73 | 64 × r = 77.67 |
| `--fill-spacing` (4) | 4 / r = 3.30 | 4 × r = 4.85 |
| `--fill-skip` (4) | 4 / r = 3.30 | 4 × r = 4.85 |
| presence smoothing (1, in code) | 1 / r = 0.824 | r = 1.214 |
| expected seed dots, median of native (probe) | 0.90 | 0.56 |

The two spacing flags and the smoothing are the probe's `flags_smooth` variant. `--fill-skip` applies later, to
fill-in dots near written fibers, so the probe cannot count it, but it is scaled as part of seeding. The other
settings stay as finding 91 set them, in grid voxels:
* `--dot-radius` 2: it sets a whole number of voxels, and the probe found no effect from it;
* the Hessian, sigma 1.5: scaling it changed no cube's count by more than 0.03 of native;
* `--dedupe`, `--min-length` and the stop rules, which are tracing rules, not seeding. Finding 92's exploration
  ruled out the minimum-length band.

Same checkpoint and sha256, `--tile-workers 0`, every other default. Run directories `seeding_run/A/` and
`seeding_run/B/`, with the identity smoke in `seeding_run/identity/`. The chain takes every flag from the analysis
script (`args`), and the analysis refuses a verdict (IDENTITY_FAILED) if any run's `run.json` or `seeding.json`
differs from its arm, as finding 92's did.

**Smoke and identity, first:** the launcher at the default smoothing (1.0) and `--tile-workers 0`, on finding 91's
repeat cube `s1_00497_01497_03997_256`, must reproduce finding 91's `fibers.afv` (fiber count and points). That shows
the launcher changes nothing at the default. Arm A's first cube is the same cube.

## Scoring

Arm A as finding 92: the `.afv` scaled back by r into the cube's frame. Arm B as finding 91. Both use thin-centreline
rasterisation and ScrollGT `score_tracing`, scoring version 3, tolerance 2.0. Comparators are finding 91's native
rows, finding 92's 9.6 µm rows, and ScrollGT's rows for our tracer.

## Predictions, fixed now

1. **A recovers.** The median over the 21 cubes of merge-penalized ERL, arm A over native, is at least 0.85.
   Confidence moderate to low. Seeds are restored to 0.90, and coverage followed seeding. But the CT heading test,
   which is the network's read, turned away more dots at 9.6 µm (47% against 36%), and seeding does not touch it.
2. **A's Scroll-3 lead returns.** Arm A's merge-penalized ERL beats our tracer's on at least 6 of the 8 Scroll-3
   cubes. Confidence low: finding 91's lead was 1.11–1.33 times, so a small residual loss removes it.
3. **B falls.** The median over the 21 cubes of merge-penalized ERL, arm B over native, is at most 0.80. Confidence
   moderate: B's seeds are 0.56 of native, and the network's input is finding 91's.

**Descriptive, no prediction:** coverage, precision and instances against both earlier runs; the funnel counters
(`neural_tracer_pitch_funnel.py`) for each arm; per-group medians; runtime.

## Decision rule

| outcome | conclusion |
|---|---|
| the identity smoke differs from finding 91 | no arm runs; amended first |
| a cube's recorded seed dots differ from the probe's | MANIPULATION_FAILED for that cube, which is not scored |
| a cube's run fails or writes no `.afv` | reported as failed, not scored as zero |
| fewer than 17 scored cubes in an arm | that arm's predictions unevaluated; INCOMPLETE |
| P1 and P3 hold | "the seeding scale, fixed in grid voxels, explains most of finding 92's drop": recommend revising ScrollGT 0.8.1's note to say so, with P2's result |
| P3 holds, P1 fails | "seeding density moves the score, but restoring it at 9.6 µm does not recover it": the note stands, with the seeding sensitivity added |
| P1 and P3 fail | "the seeding scale is not the cause": the note stands |
| P1 holds, P3 fails | inconsistent: both reported, no recommendation |

Any change to ScrollGT, and anything posted to villa, is a separate decision by the user.

## What the result cannot do

* **Seeding is restored to 0.90, not 1.** The 3-voxel fill-in window is fixed in code and stays. The rest of the
  shortfall comes from the window, the resampling's interpolation, or both.
* **Resampling is not a 9.6 µm scan**, as in finding 92.
* **A patched run is not villa's tool at its defaults.** A recovered score says what its seeding costs at a coarser
  grid. It does not make the patched run the published row.
* Finding 91's other limits stand: one checkpoint, volume mode, a substitute presence.

## Cost

* **GPU:** the identity smoke (about 1 minute), arm A (about 30 minutes, as finding 92) and arm B (up to about 50,
  as finding 91), with the loop paused (`stop.sh`) and restarted (`start.sh`) after. The chain refuses to start while
  the loop runs.
* **CPU:** scoring, about an hour per arm at nice 19 with the loop running.
