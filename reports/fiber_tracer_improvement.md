# Clearing our own published fiber baseline

Pre-registered contract: `docs/superpowers/specs/2026-07-31-fiber-tracer-beat-baseline-design.md`.
Primary metric is merge-penalized ERL against **each cube's own** connected-components floor.
Raw ERL, splits, merges and coverage are reported every time regardless of outcome. An ERLpen
gain accompanied by a rise in merges is a **failure**, not a win.

Dev cubes: `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`.
Held out until the final run: the three other Scroll-1 cubes.
Never used for any decision: `s5_03997_01497_03997_256`.

**Configurations tried so far: 1** (the baseline itself).

## Baseline (reproduced 2026-07-31)

| cube | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 |
| s1_00497_02497_02997 | 45.77 | 33.58 | 64.27 | 0.704 | 2185 | 47 | 524 |

Stop reasons, cube 1: `high_curvature` 750 (46%), `collision` 455 (28%),
`low_response` 243 (15%), `out_of_bounds` 196 (12%).

Stop reasons, cube 2: `high_curvature` 664 (46%), `collision` 427 (30%),
`low_response` 160 (11%), `out_of_bounds` 157 (11%).
