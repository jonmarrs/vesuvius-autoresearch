# Finding 93: villa's neural fiber tracer seeded per micrometre: the seeding scale is not why it falls at 9.6 µm (2026-10-20)

The result of `docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md`, proposed in #149 and registered at
c23d3a08 before any trace with rescaled seeding existed. Finding 92 (`neural_tracer_pitch.md`) found that villa's
neural fiber tracer, resampled to its 9.6 µm training pitch, scores lower on all 21 ScrollGT cubes and loses its
Scroll-3 lead. Two exploratory readings after that result put the loss at seeding. The tracer seeds per grid voxel,
through a presence smoothing fixed in code, so at 9.6 µm it starts fewer traces. This run tested that reading in two
arms:
* **A:** the 9.6 µm cubes, seeded per micrometre as natively;
* **B:** the native cubes, seeded per micrometre as at 9.6 µm.

**Answer: the seeding scale is not the cause.** All three predictions failed. Restoring the seeds at 9.6 µm lifts
merge-penalized ERL only from 0.63 to 0.67 of native. Seeding the native cubes as sparsely as at 9.6 µm costs only a
little: 0.88 of native, with the Scroll-3 lead kept on 7 of 8 cubes. By the registered rule, ScrollGT 0.8.1's note
("Its Scroll-3 lead depends on running at the cubes' own 7.91 µm") stands.

## The run

* **Registered and run at c23d3a08:** `repro/fibers/run_neural_tracer_seeding_chain.sh`, work directory
  `spiral_out/neural_tracer/seeding_run`, villa `ccb431818`. Traced 00:22:53–01:28:20 PDT on 2026-10-20 with the loop
  paused (`stop.sh` at 00:22:45). The loop restarted at 01:28:20, before scoring.
* **The identity smoke passed.** At villa's default smoothing, the launcher reproduced finding 91's `fibers.afv` for
  `s1_00497_01497_03997_256` point for point.
* **All 42 runs finished**, and every `run.json` and `seeding.json` matched its arm. The analysis' status is `OK`
  (`neural_tracer_seeding.json`).
* **The manipulation took.** In every run, the seed dots recorded in `tiles.jsonl` equal the probe's count for its
  arm (`neural_tracer_seed_probe.json`). Arm A's seeds are a median 0.90 of native, and arm B's 0.56.
* **Scored** as finding 92 (arm A, scaled back into each cube's 7.91 µm frame) and finding 91 (arm B). ScrollGT
  scoring version 3, tolerance 2.0.

## Results

| prediction | registered | result |
|---|---|---|
| P1: A recovers | median ERLpen ratio, A over native, ≥ 0.85 | **failed:** 0.67 |
| P2: A's Scroll-3 lead returns | leads our tracer on ≥ 6 of 8 | **failed:** 0 of 8 |
| P3: B falls | median ERLpen ratio, B over native, ≤ 0.80 | **failed:** 0.88 |

Medians of merge-penalized ERL (ERLpen), by group:

| group | n | A | B | native (finding 91) | 9.6 µm (finding 92) | our tracer |
|---|---:|---:|---:|---:|---:|---:|
| in sample | 11 | 7.12 | 7.13 | 7.82 | 6.83 | 20.75 |
| Scroll 3 | 8 | 15.52 | 22.25 | 25.30 | 13.93 | 20.98 |
| held-out Scroll 5 | 2 | 2.80 | 3.33 | 4.25 | 2.62 | 7.44 |

Each run over finding 91's native run, median over the 21 cubes:

| run | ERLpen | below native | coverage |
|---|---:|---:|---:|
| A: 9.6 µm, seeded as natively | 0.67 (0.51–1.20) | 19 of 21 | 0.78 (0.64–0.90) |
| B: native, seeded as at 9.6 µm | 0.88 (0.58–1.19) | 18 of 21 | 0.89 (0.77–1.02) |
| finding 92: 9.6 µm, villa's seeding | 0.63 (0.44–0.94) | 21 of 21 | 0.67 (0.49–0.89) |

* **Restoring the seeds at 9.6 µm restores coverage more than run length.** Arm A's coverage is 0.78 of native,
  against finding 92's 0.67, but its ERLpen is 0.67 against 0.63. It beats finding 92's run on 18 of 21 cubes, and
  trails our tracer on all 8 Scroll-3 cubes.
* **Seeding the native cubes sparsely costs little.** Arm B starts 0.76 as many traces as native from 0.56 of the
  seeds. Its ERLpen is 0.88 of native, and it still leads our tracer on 7 of 8 Scroll-3 cubes.
* **The heading test stays high at 9.6 µm.** With the seeds restored, arm A's network still turns away 44% of seed
  dots for a CT heading that disagrees with the presence, against 36% natively and 47% in finding 92. That test is the
  network's read, and seeding does not touch it.
* **Neither arm changes the in-sample deficit.** Both trail our tracer on all 11 in-sample cubes, as finding 91's and
  finding 92's runs did.

## What it means

* **For ScrollGT's note:** it stands. The Scroll-3 lead depends on the pitch the network reads, or on the
  resampling that produced it, not on how densely the tracer seeds. Seeding explains some of the coverage lost at
  9.6 µm and little of the run length.
* **For the exploratory readings in `neural_tracer_pitch.md`:** fewer seeds did cut the traces at 9.6 µm, but that
  is not why its score fell. Those sections now point here.
* **What remains, untested:** the network's read of 9.6 µm data against interpolated 7.91 µm data, which resampling
  cannot separate (finding 92's limits); and why its runs are shorter there. Finding 92's funnel left open why
  merge-penalized ERL falls further than coverage on Scroll 3, and this run does not answer it.

## What it does not say

* **Seeds were restored to 0.90 of native, not 1.** The 3-voxel fill-in window is fixed in code.
* **Resampling is not a 9.6 µm scan**, as in finding 92.
* **A patched run is not villa's tool at its defaults.** These rows do not replace ScrollGT's published ones.
* Finding 91's other limits stand: one checkpoint, volume mode, a substitute presence.
