# The tracer's frozen configuration still beats its baseline under scoring version 2, on all 11 cubes

**2026-10-09.** Result of `docs/preregistration/2026-10-09_tracer_frozen_config_v2.md`: pre-registration `904a5f81`,
and import-order fix `17bdd9e0`, both before any run. Data: `reports/tracer_frozen_v2.json`. Labellings:
`spiral_out/tracer_frozen/`.

**Question.** `reports/fiber_tracer_improvement.md` froze `--tangent-window 5 --max-skip-steps 0 --seed-nms-radius
0.0`. It reported higher merge-penalized ERL than the baseline on all six cubes it scored, measured with fiber scoring
version 1. Finding 80 showed version 1 could reverse a published tracer claim. Does this one survive?

## Fidelity: exact

Scored with version 1, the re-run frozen labellings reproduce the report's published frozen ERL and ERLpen exactly
on all six of its cubes, for example 29.97 / 25.61 on `s1_00497_01497_03997`. The configuration has not changed.

## Results (scoring version 2; baseline = finding 80's labellings)

| cube | size | ERLpen baseline → frozen | change | ERL baseline → frozen | change | merges baseline → frozen |
|---|---:|---|---:|---|---:|---|
| s1_00497_01497_03997 | 256 | 30.85 → 33.52 | +8.7% | 35.39 → 38.56 | +9.0% | 38 → 28 |
| s1_00497_02497_02997 | 256 | 40.61 → 42.83 | +5.5% | 55.07 → 54.51 | −1.0% | 47 → 39 |
| s1_00997_02497_02997 | 256 | 38.72 → 42.95 | +10.9% | 48.82 → 51.15 | +4.8% | 45 → 34 |
| s1_08997_02997_02497 | 256 | 40.58 → 40.75 | +0.4% | 44.91 → 43.70 | −2.7% | 15 → 12 |
| s1_10997_02997_02997 | 256 | 44.19 → 46.73 | +5.7% | 48.17 → 47.41 | −1.6% | 14 → 6 |
| s5_03997_01497_03997 | 256 | 33.30 → 39.84 | +19.6% | 40.45 → 40.59 | +0.3% | 13 → 5 |
| s5_07997_02997_05497 | 256 | 43.65 → 47.75 | +9.4% | 48.00 → 50.75 | +5.7% | 16 → 10 |
| s5_14997_01497_01497 | 256 | 38.56 → 40.28 | +4.5% | 46.62 → 47.42 | +1.7% | 51 → 43 |
| s5_06494_01994_03994 | 512 | 42.63 → 46.13 | +8.2% | 53.40 → 52.87 | −1.0% | 353 → 252 |
| s5_06994_00994_04994 | 512 | 34.14 → 36.90 | +8.1% | 42.65 → 43.54 | +2.1% | 606 → 462 |
| s5_07994_01994_05494 | 512 | 34.18 → 36.96 | +8.1% | 41.42 → 41.50 | +0.2% | 276 → 205 |

* **P1 HELD, 6 of 6.** Merge-penalized ERL rises on every cube the report scored.
* **P2 HELD, 11 of 11.** It rises on every cube, by +0.4% to +19.6%.
* **P3 HELD, 11 of 11.** Raw ERL moves by −2.7% to +9.0%, within ±10% everywhere.
* **The mechanism survives too.** Merges fall on all 11 cubes. As the version-1 report concluded, the gain is
  merge reduction, not longer runs.
* **Descriptive:** the frozen configuration is ahead of connected components on merge-penalized ERL on the same 4 cubes
  as the baseline (`s5_14997` and the three 512³ cubes). It widens those leads but adds no cube.

## What it means

The improvement report's conclusion holds under the corrected scorer, now on 11 cubes instead of 6. Unlike finding 80,
this re-measurement confirms a claim. Its "historical scorer" notice is updated to say so, with this report's numbers.
The gains are modest: the tracer still trails connected components on raw ERL by roughly 4–6×.

## Limits

One configuration, chosen on two development cubes in the original study; 11 cubes from one dataset. ScrollGT
publishes only the baseline tracer row; adding this configuration there would be a separate decision.
