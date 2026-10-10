# Pre-registration: does the tracer's frozen "improved" configuration still beat the baseline under scoring version 2?

**Written 2026-10-09, before any frozen-configuration run under current code.** Analysis
`scripts/tracer_frozen_analysis.py`; chain `repro/fibers/run_tracer_rescore.sh` with `W`, `TRACE_EXTRA` and `ANALYSIS`
set. Committed with this file on branch `tracer-frozen-config-v2`.

## Why

`reports/fiber_tracer_improvement.md` froze a configuration, `--tangent-window 5 --max-skip-steps 0
--seed-nms-radius 0.0`, and reported that it raised merge-penalized ERL over the baseline on all six cubes it scored,
mostly by cutting merges. That was measured with fiber scoring version 1. The report carries a "historical scorer, not
recomputed" notice.

Finding 80 re-measured the baseline with scoring version 2 on all 11 ScrollGT cubes. That reversed one published claim,
so this one gets the same treatment.

## Method

* **Frozen configuration:** exactly as the report froze it, all other parameters at the published defaults. It runs on
  all 11 cubes with `--detect-block 128` (bit-identical to dense, shown in finding 80's Amendment 1).
* **Baseline:** finding 80's labellings (`spiral_out/tracer_rescore/`).
* **Scoring:** both are scored by ScrollGT (`score_fiber_prediction`, version 2).
* **Fidelity, reported but not a gate:** the frozen labellings, scored with ScrollGT 0.3.2's version-1 scorer, against
  the report's published frozen ERL and ERLpen on its six cubes.

## Predictions, fixed now

1. **On the report's six cubes, frozen ERLpen > baseline ERLpen on at least 5.** Confidence moderate-high: it was 6 of
   6 under version 1, carried by merge reduction, which version 2 should still reward.
2. **On all 11 cubes, frozen ERLpen > baseline on at least 9.** Confidence moderate.
3. **Raw ERL changes little: frozen within ±10% of baseline on at least 9 of 11.** Confidence moderate. Under version 1
   the raw-ERL changes were −0.8 to +3.4 voxels.

**Descriptive, with no prediction:** on how many cubes the frozen configuration's ERLpen is above connected components'.
The baseline's count is 4 of 11.

## What follows

The report's notice is updated with the measured result, whichever way it falls. Nothing is published to ScrollGT
without a separate decision.
