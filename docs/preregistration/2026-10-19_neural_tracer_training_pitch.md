# Pre-registration: does villa's neural fiber tracer score differently at the voxel pitch it trained on?

**Written 2026-10-19, before any resampled cube has been traced or resampled.** Owner's decision the same day: register,
then run now with the loop paused. Finding 91 (`reports/neural_tracer_entrant.md`) is the native-pitch run; its rows
are published in ScrollGT 0.8.0 (scrollgt#6) as `villa_neural_tracer`.

## The question

Finding 91 ran villa's neural fiber tracer (villa #2045, `scrollprize/fiber_single_small` at `4511825`) on ScrollGT's 21
fiber cubes at their own 7.91 µm. Its checkpoint trained on CT at 8.64–9.6 µm; its Scroll 1 source, Paris 4, at 9.6 µm.
Does it score differently when each cube is resampled to 9.6 µm first?

**Why it matters.**
* **The published rows.** ScrollGT now publishes finding 91's rows for villa's tool. If the pitch we chose cost it
  materially, that row understates it.
* **Finding 91's open question.** It trails our tracer on all 11 in-sample cubes, Scroll 1 (its own training scroll)
  included, while leading on all 8 Scroll-3 cubes. The registered limits named scale as one untested candidate.

**What the pitch can and cannot explain.** Every cube was read at the same 7.91 µm, so pitch alone cannot explain the
contrast between Scroll 3 and the in-sample cubes. It could still move the in-sample rows more than the Scroll-3 ones.

## Reachability, checked before designing the measurement (villa `ccb431818`)

* **No flag changes the pitch the network sees.** `crop_sampling/volume.py`: "CT is read at its native resolution",
  and `input_scale = grid_scale / ct_grid_scale` must be a whole number. `--base-um` is not read in volume mode.
  Finding 91 gave it 7.91 µm CT on a 15.8 µm trace grid; Paris 4 is 9.6 µm CT on a 19.2 µm grid.
* **So the cube is resampled** (`scripts/resample_cube_pitch.py`). Output sample j is the source at j × r,
  r = 9.6 / 7.91 = 1.2137, trilinear, edges replicated (the tracer reads CT value 0 as outside the scan). A 256³ cube
  becomes 212³ and a 512³ one 422³, each even for the presence level. CT stays uint8 (rounded).
* **The presence** is fiber_hz_vt's probability resampled the same way, then built by `make_tracer_presence.py`
  exactly as in finding 91 (2×2×2 block means, uint8).
* **Back to the cube.** The `.afv` holds resampled voxels (trace grid × grid_scale). Each point is multiplied by r into
  the cube's own frame (`neural_tracer_pitch_analysis.scale_back`), then rasterised and scored as in finding 91.
  `tests/test_resample_cube_pitch.py` and `tests/test_neural_tracer_pitch_analysis.py` pin both mappings.
* **Inputs present for all 21 cubes:** finding 85's CT arrays, the fiber_hz_vt probabilities, and #1934's `.afv`
  frame templates.

## Entrant, fixed now

Finding 91's entrant in every respect but four:
* the CT and presence are the resampled ones (`ct_9p6/`, `presence_9p6/`);
* `--box 0,0,0,N,N,N` with N = 106 (256³ cubes) or 211 (512³ cubes), the resampled trace grid;
* `--base-um 9.6` (reported lengths only);
* the run directory is `pitch_run/`.

Same checkpoint and sha256, `--ct-level 0 --ct-grid-scale 1 --grid-scale 2`, every other default. The identity check
(`neural_tracer_pitch_analysis.identity_problems`) refuses any `run.json` that differs. No repeat runs: finding 91
measured the tracer deterministic (repeat difference 0).

## Scoring

As finding 91: thin-centreline rasterisation (`afv_to_labels.py`) in the cube's 7.91 µm frame, ScrollGT
`score_tracing`, scoring version 3, tolerance 2.0. Comparators: finding 91's native rows
(`reports/neural_tracer_entrant.json`) and our tracer's and connected components' rows from ScrollGT. Output:
`reports/neural_tracer_pitch.json`.

## Predictions, fixed now

1. **The in-sample deficit stays.** Merge-penalized ERL below our tracer's on at least 9 of the 11 in-sample cubes.
   Confidence moderate: the Scroll-3 / in-sample contrast arose at one pitch, so pitch is unlikely to be its main
   cause.
2. **The Scroll-3 lead stays.** Merge-penalized ERL above our tracer's on at least 6 of the 8 Scroll-3 cubes.
   Confidence moderate. Resampling blurs the CT slightly, and the 512³ cubes shrink to 211 trace voxels, so the lead
   could narrow.
3. **Pitch moves the score little.** The median over the 21 cubes of merge-penalized ERL, pitch-matched over native,
   lies within 0.85–1.15. Confidence low: a CNN can be sensitive to an 18% scale change, or robust to it.

**Descriptive, no prediction:** coverage and precision against native; each group's medians; stop reasons; runtime.

## Decision rule

| outcome | conclusion |
|---|---|
| the first cube (`s1_00497_01497_03997_256`, the smoke) fails mechanically | no further cube runs; amended first |
| a cube's run fails or writes no `.afv` | reported as failed, not scored as zero |
| any `run.json` differs from the registration | IDENTITY_FAILED, no verdict |
| fewer than 9 in-sample / 6 Scroll-3 / 17 total rows | P1 / P2 / P3 unevaluated; INCOMPLETE |
| it no longer trails our tracer on 3 or more in-sample cubes (P1 fails) | "pitch is a material cause of the in-sample deficit" |
| otherwise | "pitch is not the main cause of the in-sample deficit" |
| P3 fails, or the comparison with our tracer flips on 2 or more cubes | the published ScrollGT row moves materially: the report recommends updating or annotating it |
| otherwise | the published row stands, with the pitch disclosed |

Any change to ScrollGT, and anything posted to villa, is a separate decision by the user.

## What the result cannot do

* **Resampling is not a 9.6 µm scan.** Interpolated 7.91 µm data is smoother than a native 9.6 µm read, and differs
  from Paris 4's level-2 downsampling. A null result says pitch-matching by resampling does not help, not that a
  native scan would not.
* **One target pitch.** 9.6 µm is its Scroll 1 source; its other sources are 8.64 and 9.362 µm.
* **Edges grow.** A resampled 256³ cube is 106 trace voxels across, against 128, and the tracer's crop sees the
  reader's zero fill near the edges.
* Finding 91's other limits stand: one checkpoint, volume mode, defaults, a substitute presence.

## Cost

* **CPU:** resampling and presence, about a minute per 512³ cube; scoring about 3 minutes per 512³ cube.
* **GPU:** 21 cubes, about 50 minutes as in finding 91 (fewer voxels here), with the loop paused (`stop.sh`) and
  restarted (`start.sh`) afterwards. The chain refuses to start while the loop runs.
