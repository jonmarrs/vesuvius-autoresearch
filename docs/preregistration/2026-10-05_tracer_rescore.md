# Pre-registration: does our fiber tracer still lose to connected components under the corrected scorer?

**Written 2026-10-05, before any tracer run under current code.** Scripts committed with this file:
`repro/fibers/run_tracer_rescore.sh` and `scripts/tracer_rescore_analysis.py`.

## Why

ScrollGT's README says our tracer "lost to connected components on both metrics, on all six cubes it was scored
against". That was measured with fiber scoring version 1, which read runs in stored edge-row order. The published
rows (`tracer_strict_relink`, 2026-07-30, `e82fa4c9`) are stamped version 1 and listed as not recomputed. Scoring
version 2 (scrollgt#1, ScrollGT v0.4.0; version 4 in this repo) moved the published floors by up to 14%. Five cubes
were never scored with the tracer.

## Method

* **Tracer:** `bench_cli trace` at its published defaults, the configuration of the published row: relink on,
  `--tangent-window 1`, `--max-skip-steps 0`, `--seed-nms-radius 0`, seed percentile 85, continue threshold 0.5,
  min length 15, max angle 25, claim radius 3.5, relink gap 10 and angle 30, tolerance 2.0. It runs on all 11
  ScrollGT cubes with `--save-instances`.
  * Current code recomputes the fiber probability, because the July caches have no provenance manifest. The July
    caches are backed up with checksums in `spiral_out/legacy_fiberprob_2026-07/`.
* **Scores:** each saved labelling is scored by ScrollGT itself (`score_fiber_prediction`, version 2) against
  ScrollGT's published version-2 floors. Those floors were verified 55/55.
* **Fidelity check, reported but not a gate:** on the six cubes with a published row, the same instances are also
  scored with ScrollGT 0.3.2's version-1 scorer and compared with that row. If any cube's version-1 ERL differs by
  more than 5%, the re-run is not the published tracer: both are reported, and the claim is restated for the
  current tracer.

## Predictions, fixed now

1. **Raw ERL: the tracer is below the connected-components floor on all 11 cubes.** Confidence high. Under version 1
   the components led by 4.5–7.4×, and version 2 raised the components floor.
2. **Merge-penalized ERL, 256³: the tracer is below connected components on all 8.** Confidence moderate. Under
   version 1 the components led by 1.6–3.4×.
3. **Merge-penalized ERL, 512³: the tracer is ABOVE connected components on at least 2 of the 3.** Confidence
   low-moderate. On 512³ cubes the components' merge-penalized ERL is only 8.8–15.6, because the components merge
   many fibers, while the tracer's short runs are capped by its fragmentation, not the cube size.

## What gets published

ScrollGT's `tracer_strict_relink` rows (stamped version 2), the BASELINES tracer columns, and the README claim are
all updated to whatever this measures, including any prediction that fails. If the fidelity check fails, the README
says the published version-1 rows came from a tracer that no longer reproduces exactly.
