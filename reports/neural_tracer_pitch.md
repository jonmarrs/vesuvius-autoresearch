# Finding 92: villa's neural fiber tracer at its training pitch, lower on every cube, its Scroll-3 lead gone (2026-10-19)

The result of `docs/preregistration/2026-10-19_neural_tracer_training_pitch.md`, registered at 5c052f7c before any cube
was resampled or traced. Finding 91 (`neural_tracer_entrant.md`) ran villa's neural fiber tracer on ScrollGT's 21 fiber
cubes at their own 7.91 µm; its checkpoint trained on 8.64–9.6 µm CT, and no flag changes the pitch its network sees.
Here each cube was resampled to 9.6 µm, the pitch of its Scroll 1 source, traced with finding 91's settings, mapped
back into the cube and scored the same way.

**Answer: resampled to its training pitch, it scores lower on all 21 cubes.** Merge-penalized ERL falls to a median
0.63 of the native run's, and its Scroll-3 lead over our tracer is gone: 0 of 8 cubes, against 8 of 8 natively. By the
registered rule:
* **pitch is not the main cause of the in-sample deficit:** it still trails our tracer on all 11 in-sample cubes;
* **the published ScrollGT row moves materially** (P3 failed, and the comparison with our tracer flips on 8 cubes).
  The rule says to recommend updating or annotating the row. Since the native run scores higher on every cube,
  replacing it would understate villa's tool, so the recommendation is to annotate it (below). That is the user's call.

## The run

* **Registered and run at 5c052f7c:** `repro/fibers/run_neural_tracer_pitch_chain.sh`, work directory
  `spiral_out/neural_tracer/pitch_run`, villa `ccb431818`. Traced 12:55:34–13:24:04 PDT with the loop paused; the loop
  was restarted when the last cube finished, before scoring.
* **All 21 cubes ran, and every `run.json` passed the identity check** (`neural_tracer_pitch.json`: status `OK`).
* **The first cube was the smoke run.** I read its fiber count (70, against 119 natively) before the others finished.
  The analysis was fixed in the registration, so this changed nothing.
* **Scored** in each cube's 7.91 µm frame, ScrollGT scoring version 3, tolerance 2.0, beside finding 91's rows and
  ScrollGT's rows for our tracer and connected components.

## Results

| prediction | registered | result |
|---|---|---|
| P1: the in-sample deficit stays | trails our tracer on ≥ 9 of 11 | **held:** 11 of 11 |
| P2: the Scroll-3 lead stays | leads our tracer on ≥ 6 of 8 | **failed:** 0 of 8 |
| P3: pitch moves the score little | median ERLpen ratio in 0.85–1.15 | **failed:** 0.63 |

Medians of merge-penalized ERL (ERLpen) and coverage, by group:

| group | n | ERLpen at 9.6 µm | ERLpen native | our tracer | connected components | ratio | coverage at 9.6 µm | coverage native |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| in sample, 256³ | 8 | 5.91 | 7.22 | 21.26 | 47.44 | 0.86 | 0.173 | 0.240 |
| in sample, 512³ | 3 | 6.95 | 9.33 | 19.66 | 13.85 | 0.69 | 0.271 | 0.342 |
| Scroll 3, 512³ | 8 | 13.93 | 25.30 | 20.98 | 15.04 | 0.53 | 0.313 | 0.480 |
| held-out Scroll 5, 256³ | 2 | 2.62 | 4.25 | 7.44 | 4.25 | 0.61 | 0.062 | 0.115 |

* **Lower on every cube.** ERLpen is lower on all 21 (ratio 0.44–0.94, median 0.63), and so is coverage (ratio
  0.49–0.89, median 0.67).
* **It writes fewer fibers, not worse ones.** The median cube has 0.58 times as many instances, while median
  precision is unchanged (0.507 against 0.501).
* **Scroll 3 loses the most.** There it scores 0.57–0.71 of our tracer's ERLpen, and leads connected components on
  4 of 8 cubes.

## What it means

* **For ScrollGT's published row.** It is the native configuration, which scores higher on every cube, so it stays the
  better measure of villa's tool as run here. What changes is how firm its Scroll-3 lead is. Recommended annotation,
  for the user to decide: *"Its Scroll-3 lead depends on running at the cubes' own 7.91 µm. Resampled to its 9.6 µm
  training pitch, it scores lower on all 21 cubes (median 0.63 of these rows) and leads our tracer on none of the
  Scroll-3 cubes (vesuvius-autoresearch, `reports/neural_tracer_pitch.md`)."*
* **For finding 91's question.** The in-sample deficit holds at both pitches (11 of 11), so pitch is not its main
  cause. The other candidates (the scan, the cube size, annotation style) remain untested.
* **Why it falls is not established.** Resampling changes more than the pitch the network sees:
  * the tracer's settings are in grid voxels, so at 9.6 µm each is 21% longer in physical units: the minimum written
    fiber (48 points), the seed-plane spacing (64), the dedupe radius (2) and the maximum length;
  * a cube has fewer trace voxels (106 or 211 across, against 128 or 256), so a larger share lies near an edge;
  * trilinear interpolation smooths the CT.

  The result says that resampling to 9.6 µm with its defaults does not help it here. It does not say the network
  prefers 7.91 µm data.

## What it does not say

* **Resampling is not a 9.6 µm scan.** A native read at 9.6 µm is not interpolated, and Paris 4's level 2 is a
  downsampled 2.4 µm scan.
* **One target pitch, at the defaults.** 8.64 and 9.362 µm, its other sources, and settings rescaled to keep their
  physical size, are untested.
* Finding 91's other limits stand: one checkpoint, volume mode, a substitute presence.
